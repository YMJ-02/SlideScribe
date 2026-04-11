"""CLI 진입점: python run.py <video_path> [--config config.yaml] [--format html]

파이프라인 전체 실행:
  Stage 1 (세그멘테이션)
    ├─ Stage 2 (슬라이드 PDF)
    └─ Stage 3 (오디오 추출)
         └─ Stage 4 (Whisper STT)
              └─ Stage 5 (타임스탬프 매칭)
                   └─ Stage 6 (노트 생성)
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
    """파이프라인 전체 실행. 각 Stage 결과를 반환."""
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

    t0 = time.time()
    results = {}

    # ── Stage 1: 슬라이드 세그멘테이션 ─────────────────────────────
    print("\n" + "="*55)
    print(" Stage 1 / 6  슬라이드 세그멘테이션")
    print("="*55)
    slides = stage1_segment.run(video_path, cfg)
    results["slides"] = slides

    # ── Stage 2: 슬라이드 PDF (Stage 1과 독립) ──────────────────────
    print("\n" + "="*55)
    print(" Stage 2 / 6  슬라이드 PDF 생성")
    print("="*55)
    pdf_path = stage2_pdf.run(slides, cfg)
    results["slides_pdf"] = pdf_path

    # ── Stage 3: 오디오 추출 ────────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 3 / 6  오디오 추출")
    print("="*55)
    wav_path = stage3_audio.run(video_path, cfg)
    results["wav"] = wav_path

    # ── Stage 4: Whisper STT ────────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 4 / 6  Whisper STT")
    print("="*55)
    segments = stage4_stt.run(wav_path, cfg)
    results["segments"] = segments

    # ── Stage 5: 타임스탬프 매칭 ────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 5 / 6  타임스탬프 매칭")
    print("="*55)
    matched = stage5_match.run(slides, segments)
    results["matched"] = matched

    # ── Stage 6: 노트 생성 ──────────────────────────────────────────
    print("\n" + "="*55)
    print(" Stage 6 / 6  노트 생성")
    print("="*55)
    note_path = stage6_export.run(matched, cfg)
    results["note"] = note_path

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f" 완료  총 소요 시간: {elapsed:.1f}초")
    print(f"  슬라이드 PDF : {pdf_path}")
    print(f"  강의 노트    : {note_path}")
    print("="*55 + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="lecture-note-gen: 강의 영상 → 슬라이드 노트 자동 생성"
    )
    parser.add_argument("video", help="입력 영상 파일 경로")
    parser.add_argument(
        "--config", default="config.yaml", metavar="PATH",
        help="config.yaml 경로 (기본: config.yaml)"
    )
    parser.add_argument(
        "--format", choices=["html", "pdf", "markdown"], default=None,
        help="출력 포맷 (기본: config.yaml의 export.format)"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    # CLI --format 플래그가 있으면 config 오버라이드
    if args.format:
        cfg["export"]["format"] = args.format

    try:
        run_pipeline(args.video, cfg)
    except FileNotFoundError as e:
        print(f"\n[오류] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[중단] 사용자 요청으로 파이프라인을 중단했습니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()
