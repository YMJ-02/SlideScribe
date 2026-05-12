"""CLI entry point: python run.py <input> [--mode both|slides|whisper] [--format html|pdf|markdown]

Modes:
  both    : 슬라이드 + Whisper (기본)
  slides  : 슬라이드만 (Whisper 생략 — 빠름)
  whisper : Whisper만 (슬라이드 감지 생략)

오디오 파일이 입력되면 자동으로 whisper 모드로 전환된다.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import yaml

from stages import stage1_segment
from stages import stage2_pdf
from stages import stage3_audio
from stages import stage4_stt
from stages import stage5_match
from stages import stage6_export

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}

MODES = ("both", "slides", "whisper")


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_mode(input_path: str, mode: str) -> str:
    """오디오 입력은 강제로 whisper 모드로 전환."""
    ext = Path(input_path).suffix.lower()
    if ext in AUDIO_EXTS and mode != "whisper":
        print(f"[run] 오디오 입력 감지 → mode='{mode}' 무시, 'whisper' 로 전환")
        return "whisper"
    return mode


def run_pipeline(
    input_path: str,
    cfg: dict,
    mode: str = "both",
    progress_cb=None,
    output_stem: str | None = None,
) -> dict:
    """3가지 모드를 지원하는 파이프라인.

    Args:
        progress_cb: 선택적 콜백 fn(message: str, fraction: float) — UI 진행률 업데이트.
                     fraction 은 0.0~1.0.
        output_stem: 출력 파일명 기반 (e.g. "lecture_week3").
                     None 이면 input_path 의 stem 을 사용.
                     웹 업로드처럼 충돌 방지 prefix 가 붙은 경우, 호출자가
                     원래 파일명을 명시적으로 전달해야 한다.

    Returns:
        dict: slides, slides_pdf, segments, matched, note, transcript, slides_dir
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {input_path}")

    if mode not in MODES:
        raise ValueError(f"mode 는 {MODES} 중 하나여야 합니다: {mode}")

    def _emit(msg: str, frac: float) -> None:
        if progress_cb is not None:
            try:
                progress_cb(msg, frac)
            except Exception:
                pass

    mode = _resolve_mode(input_path, mode)
    stem = output_stem if output_stem else Path(input_path).stem
    t0 = time.time()

    results: dict = {
        "mode": mode,
        "slides": [],
        "slides_pdf": None,
        "segments": [],
        "matched": [],
        "note": None,
        "transcript": None,
        "slides_dir": None,
    }

    do_slides = mode in ("both", "slides")
    do_whisper = mode in ("both", "whisper")

    bar = "=" * 55
    print(f"\n{bar}\n MODE: {mode.upper():<10}  input: {Path(input_path).name}\n{bar}")

    # ── Stage 1 + 2: 슬라이드 감지 + PDF ───────────────────────────────
    if do_slides:
        print(f"\n{bar}\n Stage 1  슬라이드 세그멘테이션\n{bar}")
        _emit("Stage 1 · Detecting slides", 0.05)
        slides = stage1_segment.run(input_path, cfg)
        results["slides"] = slides

        print(f"\n{bar}\n Stage 2  슬라이드 PDF\n{bar}")
        _emit("Stage 2 · Building slide PDF", 0.30)
        results["slides_pdf"] = stage2_pdf.run(slides, cfg, stem=stem) or None
    else:
        slides = []

    # ── Stage 3 + 4: 오디오 추출 + STT ────────────────────────────────
    segments: list[dict] = []
    if do_whisper:
        is_audio = Path(input_path).suffix.lower() in AUDIO_EXTS
        if is_audio:
            wav_path = input_path
            print(f"\n{bar}\n Stage 3  (오디오 입력 — 추출 생략)\n{bar}")
        else:
            print(f"\n{bar}\n Stage 3  오디오 추출\n{bar}")
            _emit("Stage 3 · Extracting audio", 0.40)
            wav_path = stage3_audio.run(input_path, cfg)

        print(f"\n{bar}\n Stage 4  Whisper STT\n{bar}")
        _emit("Stage 4 · Whisper transcribing (this may take a while)", 0.45)
        segments = stage4_stt.run(wav_path, cfg)
        results["segments"] = segments

    # ── Stage 5: 매칭 (모드별 분기) ────────────────────────────────────
    print(f"\n{bar}\n Stage 5  타임스탬프 매칭 / 정렬\n{bar}")
    _emit("Stage 5 · Matching timestamps", 0.85)
    if mode == "slides":
        # 슬라이드는 있지만 text 는 비움
        matched = [dict(s, text="") for s in slides]
        print(f"[Stage 5] slides 모드 — {len(matched)}개 슬라이드, 텍스트 없음")
    elif mode == "whisper":
        matched = stage5_match.run([], segments)
    else:
        matched = stage5_match.run(slides, segments)
    results["matched"] = matched

    # ── Stage 6: 노트 출력 ────────────────────────────────────────────
    print(f"\n{bar}\n Stage 6  노트 내보내기\n{bar}")
    _emit("Stage 6 · Exporting note", 0.95)
    note_path = stage6_export.run(matched, cfg, stem=stem)
    results["note"] = note_path

    # transcript / slides_dir 경로 추적 (UI 표시용)
    out_dir = cfg["paths"]["output_dir"]
    transcript_path = os.path.join(out_dir, f"{stem}-transcript.txt")
    if os.path.isfile(transcript_path):
        results["transcript"] = transcript_path
    slides_dir = os.path.join(out_dir, "slides")
    if os.path.isdir(slides_dir):
        results["slides_dir"] = slides_dir

    elapsed = time.time() - t0
    print(f"\n{bar}\n Done  ({mode})  total {elapsed:.1f}s")
    if results.get("slides_pdf"):
        print(f"  Slide PDF  : {results['slides_pdf']}")
    if results.get("note"):
        print(f"  Note       : {results['note']}")
    if results.get("transcript"):
        print(f"  Transcript : {results['transcript']}")
    print(bar + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="SlideScribe: 강의 영상/오디오 → 구조화된 노트"
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="하나 이상의 영상/오디오 파일 경로"
    )
    parser.add_argument(
        "--config", default="config.yaml", metavar="PATH",
        help="config.yaml 경로 (기본: config.yaml)"
    )
    parser.add_argument(
        "--mode", choices=list(MODES), default=None,
        help="실행 모드: both | slides | whisper (기본: config.yaml 의 default_mode)"
    )
    parser.add_argument(
        "--format", choices=["html", "pdf", "markdown"], default=None,
        help="출력 포맷 (기본: config.yaml)"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.format:
        cfg["export"]["format"] = args.format
    mode = args.mode or cfg.get("pipeline", {}).get("default_mode", "both")

    total = len(args.inputs)
    failed: list[str] = []

    for i, src in enumerate(args.inputs, 1):
        print(f"\n{'#'*55}\n  Processing {i} / {total}: {src}\n{'#'*55}")
        try:
            run_pipeline(src, cfg, mode=mode)
        except FileNotFoundError as e:
            print(f"\n[Error] {e}", file=sys.stderr)
            failed.append(src)
        except KeyboardInterrupt:
            print("\n[Interrupted] 사용자에 의해 중단됨.")
            sys.exit(0)
        except Exception as e:
            print(f"\n[Error] {src}: {e}", file=sys.stderr)
            failed.append(src)

    if total > 1:
        print(f"\n{'='*55}")
        print(f" Batch done: {total - len(failed)}/{total} succeeded")
        if failed:
            print(f" Failed: {', '.join(failed)}")
        print("=" * 55)


if __name__ == "__main__":
    main()
