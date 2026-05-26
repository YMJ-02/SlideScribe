"""launcher.py — entry point for the bundled SlideScribe.exe.

Run from source:
    python launcher.py

When frozen by PyInstaller, this becomes SlideScribe.exe and the bundled
files live next to it (one-dir layout) or inside sys._MEIPASS (one-file).
The launcher:
  1. Picks a per-user writable directory for config / outputs / tmp.
  2. Copies the bundled default config.yaml there on first run.
  3. Prepends the bundle's `bin/` (ffmpeg.exe etc.) to PATH.
  4. Starts the FastAPI app on localhost:7860.
  5. Auto-opens the user's default browser.
  6. Closes everything when the console window is closed.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path


HOST = "127.0.0.1"
PORT = 7860


def _bundle_dir() -> Path:
    """Directory containing the bundled data files (config.yaml, web/, ...)."""
    if getattr(sys, "frozen", False):
        # PyInstaller one-file: data extracted to sys._MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        # PyInstaller 6.x one-dir: only the exe sits at <install>/;
        # bundled data files live under <install>/_internal/
        exe_dir = Path(sys.executable).resolve().parent
        internal = exe_dir / "_internal"
        if internal.is_dir():
            return internal
        return exe_dir
    return Path(__file__).resolve().parent


def _user_data_dir() -> Path:
    """Per-user writable directory for config / outputs / tmp."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "SlideScribe"


_BATCH_SIZE_RE = re.compile(r"^(\s*batch_size\s*:\s*)(\d+)", re.MULTILINE)


def _migrate_user_config(user_cfg: Path) -> None:
    """기존 user config 의 알려진 위험 값을 안전한 default 로 마이그레이션.

    - stt.batch_size > 1 → 1
      RTX 2070 (8GB VRAM) + large-v3 환경에서 BatchedInferencePipeline 이
      첫 세그먼트 출력 전에 멈추는 사례 다수 확인됨. 구버전 SlideScribe 의
      기본값(8)이 그대로 남아있는 사용자가 새 .exe 를 실행해도 행이 재발하므로
      여기서 일괄 1 로 강제하고 원본은 .bak 으로 백업한다.
    """
    if not user_cfg.is_file():
        return
    try:
        text = user_cfg.read_text(encoding="utf-8")
    except OSError:
        return
    m = _BATCH_SIZE_RE.search(text)
    if not m:
        return
    try:
        current = int(m.group(2))
    except ValueError:
        return
    if current <= 1:
        return

    bak = user_cfg.with_suffix(".yaml.bak")
    try:
        shutil.copy2(user_cfg, bak)
    except OSError:
        bak = None  # 백업 실패해도 마이그레이션은 진행

    new_text = _BATCH_SIZE_RE.sub(r"\g<1>1", text, count=1)
    try:
        user_cfg.write_text(new_text, encoding="utf-8")
    except OSError:
        return

    msg = (f"[Config 마이그레이션] stt.batch_size {current} → 1 "
           "(BatchedInferencePipeline 행 방지)")
    if bak is not None:
        msg += f"  · 백업: {bak.name}"
    print(msg)


def _setup_runtime() -> tuple[Path, Path]:
    bundle = _bundle_dir()
    user_dir = _user_data_dir()
    user_dir.mkdir(parents=True, exist_ok=True)

    # First-run: copy default config.yaml from bundle so user can edit it.
    user_cfg = user_dir / "config.yaml"
    if not user_cfg.exists():
        bundled_cfg = bundle / "config.yaml"
        if bundled_cfg.is_file():
            try:
                shutil.copy2(bundled_cfg, user_cfg)
            except OSError:
                pass
    else:
        # 기존 config 마이그레이션 (구버전 기본값으로 인한 행 방지)
        _migrate_user_config(user_cfg)

    # Make bundled ffmpeg (if shipped at bundle/bin/ffmpeg.exe) discoverable.
    bundled_bin = bundle / "bin"
    if bundled_bin.is_dir():
        os.environ["PATH"] = str(bundled_bin) + os.pathsep + os.environ.get("PATH", "")

    # Run the app from user_dir so config's relative paths (.tmp, output)
    # resolve under user_dir instead of Program Files.
    os.chdir(user_dir)
    return bundle, user_dir


def _open_browser_when_ready(url: str, delay: float = 1.8) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    bundle, user_dir = _setup_runtime()
    url = f"http://localhost:{PORT}"

    print("=" * 60)
    print("  SlideScribe")
    print("=" * 60)
    print(f"  Open in browser : {url}")
    print(f"  Data folder     : {user_dir}")
    print(f"  Config file     : {user_dir / 'config.yaml'}")
    print()
    print("  Close this window or press Ctrl+C to stop the app.")
    print("=" * 60)
    print()

    threading.Thread(
        target=_open_browser_when_ready, args=(url,), daemon=True,
    ).start()

    # Import AFTER cwd / PATH are set up so the FastAPI app sees the right env.
    import uvicorn  # noqa: WPS433
    from app import app as fastapi_app  # noqa: WPS433

    try:
        uvicorn.run(
            fastapi_app,
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=False,
        )
    except KeyboardInterrupt:
        print("\nShutting down…")


def _run_with_error_pause() -> None:
    """Wrap main() so the console window stays open on crash.

    When SlideScribe.exe is launched by double-click, a Python exception
    closes the console instantly and the user sees nothing. Catch
    everything, dump the traceback to both screen and a log file under
    the user data dir, and wait for ENTER before exiting.
    """
    import traceback
    log_path = None
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        tb = traceback.format_exc()
        # Best-effort log file for after-the-fact inspection
        try:
            log_path = _user_data_dir() / "crash.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as fp:
                fp.write("=" * 60 + "\n")
                fp.write(f"  Crash at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                fp.write("=" * 60 + "\n")
                fp.write(tb)
                fp.write("\n")
        except Exception:
            pass

        print()
        print("=" * 60)
        print("  SlideScribe crashed.")
        print("=" * 60)
        print(tb)
        if log_path:
            print(f"  Full log saved to: {log_path}")
        print()
        try:
            input("  Press ENTER to close this window.")
        except EOFError:
            pass
        sys.exit(1)


if __name__ == "__main__":
    _run_with_error_pause()
