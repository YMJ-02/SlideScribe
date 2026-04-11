"""Stage 2: 슬라이드 프레임 → PDF

Stage 1 출력(slides)에서 각 슬라이드 마지막 프레임을 모아 PDF 생성.
텍스트 없이 순수 이미지 PDF (슬라이드 백업용).

입력: slides: list[dict]  (Stage 1 출력)
출력: str  — 생성된 PDF 파일 경로
"""

import os
import yaml
from pathlib import Path
from fpdf import FPDF


def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(slides: list[dict], cfg: dict | None = None) -> str:
    """슬라이드 프레임들을 A4 가로 PDF로 묶기.

    Args:
        slides: Stage 1 출력 list[dict]
        cfg:    config.yaml dict

    Returns:
        생성된 PDF 파일의 절대 경로
    """
    if cfg is None:
        cfg = _load_config()

    out_dir: str = cfg["paths"]["output_dir"]
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    pdf = FPDF(orientation="L", unit="mm", format="A4")  # 297×210 mm 가로
    pdf.set_auto_page_break(auto=False)

    print(f"[Stage 2] {len(slides)}개 슬라이드 → PDF 생성 중")
    for slide in slides:
        frame_path = slide["frame_path"]
        if not os.path.isfile(frame_path):
            print(f"  [경고] 프레임 파일 없음: {frame_path} → 스킵")
            continue
        pdf.add_page()
        # A4 가로 여백 없이 꽉 채우기
        pdf.image(frame_path, x=0, y=0, w=297, h=210)

    out_path = os.path.join(out_dir, "slides.pdf")
    pdf.output(out_path)
    print(f"[Stage 2] 저장 완료: {out_path}")
    return out_path


# ── 단독 실행 테스트 ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python stage2_pdf.py <stage1_json> [config_path]")
        print("  stage1_json: Stage 1이 생성한 .tmp/stage1_output.json 경로")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        slides = json.load(f)

    config_path = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    result = run(slides, cfg)
    print(f"\nPDF 경로: {result}")
