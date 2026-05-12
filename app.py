"""SlideScribe web app — FastAPI + custom visionOS-style SPA.

Launch:   python app.py [--port 7860] [--host 0.0.0.0]
Open:     http://localhost:7860

The Python pipeline (stages/, run.run_pipeline) is reused as-is. This file
is just an HTTP shell + job queue.
"""

from __future__ import annotations

import argparse
import os
import shutil
import site
import sys
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import List


# ── Windows CUDA DLL auto-inject ──────────────────────────────────
def _inject_cuda_paths() -> None:
    if sys.platform != "win32":
        return
    for sp in site.getsitepackages():
        for lib in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_runtime/bin"]:
            dll_path = os.path.join(sp, lib.replace("/", os.sep))
            if os.path.isdir(dll_path) and dll_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")


_inject_cuda_paths()

# Defer imports that pull in cv2 / faster-whisper until after PATH injection.
from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse              # noqa: E402
from fastapi.staticfiles import StaticFiles                           # noqa: E402

from run import load_config, run_pipeline, MODES  # noqa: E402


# ── Paths ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
UPLOAD_DIR = ROOT / ".tmp" / "uploads"
RESULT_DIR = ROOT / ".tmp" / "results"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)


# ── Job state (in-memory, single-process) ─────────────────────────
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
JOB_TTL_SEC = 60 * 60 * 6  # 6h


def _job_update(job_id: str, **kw) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(kw)


def _job_get(job_id: str) -> dict | None:
    with JOBS_LOCK:
        j = JOBS.get(job_id)
        return dict(j) if j else None


def _gc_jobs() -> None:
    now = time.time()
    with JOBS_LOCK:
        stale = [jid for jid, j in JOBS.items() if (now - j.get("created", now)) > JOB_TTL_SEC]
        for jid in stale:
            res = JOBS[jid].get("result")
            if res and os.path.isfile(res):
                try:
                    os.remove(res)
                except OSError:
                    pass
            JOBS.pop(jid, None)


# ── FastAPI ───────────────────────────────────────────────────────
app = FastAPI(title="SlideScribe", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html", media_type="text/html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/run")
async def api_run(
    files: List[UploadFile] = File(...),
    mode: str = Form("both"),
    format: str = Form("html"),
    sensitivity: float = Form(2.5),
    merge_score: float = Form(0.07),
    sample_rate: float = Form(2.0),
    min_slide_sec: float = Form(2.0),
    whisper_lang: str = Form(""),
):
    if mode not in MODES:
        raise HTTPException(status_code=400, detail=f"invalid mode: {mode}")
    if format not in ("html", "pdf", "markdown"):
        raise HTTPException(status_code=400, detail=f"invalid format: {format}")
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    _gc_jobs()

    # Persist uploads with sanitized names
    saved: list[str] = []
    for f in files:
        if not f.filename:
            continue
        safe = Path(f.filename).name  # strip any directory component
        dest = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{safe}"
        with open(dest, "wb") as fp:
            shutil.copyfileobj(f.file, fp)
        saved.append(str(dest))

    if not saved:
        raise HTTPException(status_code=400, detail="no valid files")

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "pending",
            "progress": 0.0,
            "message": "Queued",
            "summary": "",
            "result": None,
            "created": time.time(),
        }

    threading.Thread(
        target=_run_job_thread,
        args=(job_id, saved, mode, format, sensitivity, merge_score,
              sample_rate, min_slide_sec, whisper_lang),
        daemon=True,
    ).start()

    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str):
    j = _job_get(job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="job not found")
    # don't leak server filesystem path
    if j.get("result"):
        j["has_result"] = True
    j.pop("result", None)
    return j


@app.get("/api/jobs/{job_id}/download")
def api_job_download(job_id: str):
    with JOBS_LOCK:
        j = JOBS.get(job_id)
        result = j.get("result") if j else None
    if not result or not os.path.isfile(result):
        raise HTTPException(status_code=404, detail="result not ready")
    return FileResponse(
        result,
        filename=f"slidescribe_{job_id[:8]}.zip",
        media_type="application/zip",
    )


# ── Background pipeline thread ────────────────────────────────────
def _run_job_thread(
    job_id: str,
    paths: list[str],
    mode: str,
    fmt: str,
    sensitivity: float,
    merge_score: float,
    sample_rate: float,
    min_slide_sec: float,
    whisper_lang: str,
) -> None:
    try:
        _job_update(job_id, status="running", message="Loading config…", progress=0.01)

        cfg = load_config()
        cfg["export"]["format"] = fmt
        cfg["slide_detection"]["sensitivity"] = float(sensitivity)
        cfg["slide_detection"]["merge_score"] = float(merge_score)
        cfg["slide_detection"]["frame_sample_rate"] = float(sample_rate)
        cfg["slide_detection"]["min_slide_sec"] = float(min_slide_sec)
        cfg["stt"]["language"] = (whisper_lang or "auto").strip() or "auto"

        total = len(paths)
        collected: list[str] = []
        summary_lines: list[str] = []

        for i, src in enumerate(paths):
            name = Path(src).name
            # Strip the uuid_ prefix we added for display
            display_name = name.split("_", 1)[1] if "_" in name else name
            base_frac = i / total

            def _cb(msg: str, frac: float, _i=i, _name=display_name) -> None:
                # frac is per-file 0..1; map to global progress
                g = (_i + max(0.0, min(1.0, frac))) / total
                _job_update(job_id, message=f"[{_i+1}/{total}] {_name} · {msg}", progress=g)

            _cb("Starting", 0.0)
            try:
                res = run_pipeline(src, cfg, mode=mode, progress_cb=_cb)
                for p in (res.get("note"), res.get("slides_pdf"), res.get("transcript")):
                    if p and os.path.isfile(p):
                        collected.append(p)
                summary_lines.append(
                    f"✓ {display_name}  →  {len(res.get('slides', []))} slides / "
                    f"{len(res.get('segments', []))} segments  ({res.get('mode', mode)})"
                )
            except Exception as e:
                summary_lines.append(f"✗ {display_name}  ERROR: {e}")

            _job_update(job_id, progress=(i + 1) / total)

        if not collected:
            _job_update(
                job_id, status="error",
                message="No output files were produced.",
                summary="\n".join(summary_lines),
                progress=1.0,
            )
            return

        zip_path = RESULT_DIR / f"slidescribe_{job_id[:8]}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            seen: set[str] = set()
            for p in collected:
                if p in seen:
                    continue
                seen.add(p)
                zf.write(p, arcname=os.path.basename(p))

        _job_update(
            job_id,
            status="done",
            progress=1.0,
            message="Done",
            summary="\n".join(summary_lines),
            result=str(zip_path),
        )

    except Exception as e:
        _job_update(job_id, status="error", message=f"Pipeline crash: {e}", progress=1.0)


# ── Entrypoint ────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="SlideScribe web UI")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--reload", action="store_true", help="dev mode (uvicorn reload)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("FastAPI / uvicorn not installed. Run: pip install -r requirements.txt")
        sys.exit(1)

    display_host = "localhost" if args.host in ("0.0.0.0", "::") else args.host
    print(f"\n  SlideScribe  →  http://{display_host}:{args.port}")
    if args.host == "0.0.0.0":
        print(f"  (listening on all interfaces; open the URL above in your browser)\n")
    else:
        print()
    uvicorn.run(
        "app:app" if args.reload else app,
        host=args.host, port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
