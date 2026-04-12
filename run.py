"""CLI entry point: python run.py <video_path> [--config config.yaml] [--format html]

Runs the full SlideScribe pipeline:
  Stage 1 (Segmentation)
    ├─ Stage 2 (Slide PDF)
    └─ Stage 3 (Audio Extraction)
         └─ Stage 4 (Whisper STT)
              └─ Stage 5 (Timestamp Matching)
                   └─ Stage 6 (Note Export)
"""

import argparse
import os
import sys
import time
import yaml

from stages import stage1_segment
from stages import stage2_pdf
from stages import stage3_audio
from stages import stage4_stt
from stages import stage5_match
from stages import stage6_export


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline(video_path: str, cfg: dict) -> dict:
    """Run the full pipeline. Returns a dict of stage results."""
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

    from pathlib import Path as _Path
    stem = _Path(video_path).stem   # e.g. "lecture_week3"

    t0 = time.time()
    results = {}

    # ── Stage 1: Slide Segmentation ─────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 1 / 6  Slide Segmentation")
    print("="*55)
    slides = stage1_segment.run(video_path, cfg)
    results["slides"] = slides

    # ── Stage 2: Slide PDF ───────────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 2 / 6  Slide PDF")
    print("="*55)
    pdf_path = stage2_pdf.run(slides, cfg, stem=stem)
    results["slides_pdf"] = pdf_path

    # ── Stage 3: Audio Extraction ────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 3 / 6  Audio Extraction")
    print("="*55)
    wav_path = stage3_audio.run(video_path, cfg)
    results["wav"] = wav_path

    # ── Stage 4: Whisper STT ─────────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 4 / 6  Whisper STT")
    print("="*55)
    segments = stage4_stt.run(wav_path, cfg)
    results["segments"] = segments

    # ── Stage 5: Timestamp Matching ──────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 5 / 6  Timestamp Matching")
    print("="*55)
    matched = stage5_match.run(slides, segments)
    results["matched"] = matched

    # ── Stage 6: Note Export ─────────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 6 / 6  Note Export")
    print("="*55)
    note_path = stage6_export.run(matched, cfg, stem=stem)
    results["note"] = note_path

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f" Done  total time: {elapsed:.1f}s")
    print(f"  Slide PDF  : {pdf_path}")
    print(f"  Note       : {note_path}")
    print("="*55 + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="SlideScribe: turn a lecture video into a structured note"
    )
    parser.add_argument("video", help="path to the input video file")
    parser.add_argument(
        "--config", default="config.yaml", metavar="PATH",
        help="path to config.yaml (default: config.yaml)"
    )
    parser.add_argument(
        "--format", choices=["html", "pdf", "markdown"], default=None,
        help="output format (default: value in config.yaml)"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.format:
        cfg["export"]["format"] = args.format

    try:
        run_pipeline(args.video, cfg)
    except FileNotFoundError as e:
        print(f"\n[Error] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Interrupted] Pipeline stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
