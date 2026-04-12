"""CLI entry point: python run.py <video_path> [--config config.yaml] [--format html]

Runs the full SlideScribe pipeline:
  Video input → Stages 1-6 (segmentation + STT + note export)
  Audio input → Stage 4 only (STT) → transcript-only note
"""

import argparse
import os
import sys
import time
import yaml
from pathlib import Path

from stages import stage1_segment
from stages import stage2_pdf
from stages import stage3_audio
from stages import stage4_stt
from stages import stage5_match
from stages import stage6_export

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline(input_path: str, cfg: dict) -> dict:
    """Run the pipeline. Branches on audio vs. video input.

    Returns a dict of stage results.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {input_path}")

    stem = Path(input_path).stem
    ext = Path(input_path).suffix.lower()
    t0 = time.time()
    results = {}

    if ext in AUDIO_EXTS:
        # ── Audio-only pipeline (Stage 3 skipped) ───────────────────
        print("\n" + "="*55)
        print(f" Audio input detected ({ext}) — skipping slide segmentation")
        print("="*55)

        print("\n Stage 4 / 4  Whisper STT")
        print("="*55)
        segments = stage4_stt.run(input_path, cfg)
        results["segments"] = segments
        results["slides"] = []

        print("\n Stage 5 / 4  Timestamp Matching")
        print("="*55)
        matched = stage5_match.run([], segments)
        results["matched"] = matched

        print("\n Stage 6 / 4  Note Export")
        print("="*55)
        note_path = stage6_export.run(matched, cfg, stem=stem)
        results["note"] = note_path
        results["slides_pdf"] = None

    else:
        # ── Full video pipeline ──────────────────────────────────────
        print("\n" + "="*55)
        print(" Stage 1 / 6  Slide Segmentation")
        print("="*55)
        slides = stage1_segment.run(input_path, cfg)
        results["slides"] = slides

        print("\n" + "="*55)
        print(" Stage 2 / 6  Slide PDF")
        print("="*55)
        pdf_path = stage2_pdf.run(slides, cfg, stem=stem)
        results["slides_pdf"] = pdf_path

        print("\n" + "="*55)
        print(" Stage 3 / 6  Audio Extraction")
        print("="*55)
        wav_path = stage3_audio.run(input_path, cfg)
        results["wav"] = wav_path

        print("\n" + "="*55)
        print(" Stage 4 / 6  Whisper STT")
        print("="*55)
        segments = stage4_stt.run(wav_path, cfg)
        results["segments"] = segments

        print("\n" + "="*55)
        print(" Stage 5 / 6  Timestamp Matching")
        print("="*55)
        matched = stage5_match.run(slides, segments)
        results["matched"] = matched

        print("\n" + "="*55)
        print(" Stage 6 / 6  Note Export")
        print("="*55)
        note_path = stage6_export.run(matched, cfg, stem=stem)
        results["note"] = note_path

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f" Done  total time: {elapsed:.1f}s")
    if results.get("slides_pdf"):
        print(f"  Slide PDF  : {results['slides_pdf']}")
    print(f"  Note       : {results['note']}")
    print("="*55 + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="SlideScribe: turn a lecture video (or audio) into a structured note"
    )
    parser.add_argument("video", help="path to the input video or audio file")
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
