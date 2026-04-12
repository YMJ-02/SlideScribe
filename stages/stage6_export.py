"""Stage 6: 강의 노트 생성

matched 데이터(Stage 5 출력)를 HTML / PDF / Markdown으로 출력.
HTML: 이미지 base64 임베드 → 단일 파일로 배포 가능.
      레이아웃: 좌측 슬라이드 | 우측 스크립트 (2열)
PDF:  fpdf2 기반, 한국어 폰트 자동 탐색.
      레이아웃: 좌측 슬라이드 | 우측 스크립트 (A4 가로)
Markdown: 이미지 파일 경로 참조.

입력: matched: list[dict]  (Stage 5 출력 — idx, t_start, t_end, frame_path, text)
출력: str  — 생성된 노트 파일 경로
"""

import os
import base64
import yaml
from pathlib import Path


# ── 유틸 ─────────────────────────────────────────────────────

def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fmt_time(seconds: float) -> str:
    """수 → HH:MM:SS (또는 MM:SS)."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def _img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── HTML 내보내기 ─────────────────────────────────────────────────

_HTML_STYLE = """
  * { box-sizing: border-box; }
  body {
    font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
    max-width: 1200px; margin: 0 auto; padding: 24px;
    background: #f5f5f5; color: #222;
  }
  h1 { text-align: center; color: #1a1a2e; margin-bottom: 40px; }

  /* 슬라이드 하나 = 카드 */
  .slide-section {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 32px;
    box-shadow: 0 2px 6px rgba(0,0,0,.06);
  }

  /* 헤더 줄 (Slide N + 타임코드) */
  .slide-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #ececec;
  }
  .slide-num  { font-size: 1.05em; font-weight: bold; color: #1a1a2e; }
  .slide-time { font-size: 0.88em; color: #888; }

  /* 주 콘텐츠: 좌(슬라이드) + 우(스크립트) */
  .slide-body {
    display: grid;
    grid-template-columns: 3fr 1.3fr;
    gap: 20px;
    align-items: start;
  }

  /* 좌측 슬라이드 영역 */
  .slide-panel img {
    width: 100%;
    height: auto;
    display: block;
    border: 1px solid #ddd;
    border-radius: 4px;
  }

  /* 우측 스크립트 영역 */
  .transcript-panel {
    border-left: 2px solid #e8e8e8;
    padding-left: 16px;
    min-height: 60px;
  }
  .transcript-label {
    font-size: 0.78em;
    font-weight: bold;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
  }
  .transcript {
    line-height: 1.85;
    font-size: 0.93em;
    white-space: pre-wrap;
    color: #333;
  }
  .no-text { color: #bbb; font-style: italic; font-size: 0.88em; }

  /* 맸 끄 인쇄 시: 하나당 새 페이지 */
  @media print {
    .slide-section { page-break-after: always; box-shadow: none; }
  }
"""


def _export_html(matched: list[dict], out_path: str) -> None:
    sections = []
    for slide in matched:
        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])
        b64 = _img_to_b64(slide["frame_path"])
        text = slide.get("text", "").strip()
        transcript_html = (
            f'<div class="transcript">{text}</div>'
            if text else
            '<div class="transcript no-text">(해당 구간 음성 없음)</div>'
        )
        sections.append(f"""
  <div class="slide-section">
    <div class="slide-header">
      <span class="slide-num">슬라이드 {slide['idx'] + 1}</span>
      <span class="slide-time">{t_s} ~ {t_e}</span>
    </div>
    <div class="slide-body">
      <div class="slide-panel">
        <img src="data:image/jpeg;base64,{b64}" alt="슬라이드 {slide['idx']+1}">
      </div>
      <div class="transcript-panel">
        <div class="transcript-label">Transcript</div>
        {transcript_html}
      </div>
    </div>
  </div>""")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>강의 노트</title>
  <style>{_HTML_STYLE}</style>
</head>
<body>
  <h1>강의 노트</h1>
{''.join(sections)}
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


# ── Markdown 내보내기 ───────────────────────────────────────────────

def _export_markdown(matched: list[dict], out_path: str) -> None:
    lines = ["# 강의 노트\n"]
    for slide in matched:
        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])
        text = slide.get("text", "").strip() or "*(해당 구간 음성 없음)*"
        img_rel = os.path.relpath(slide["frame_path"], os.path.dirname(out_path))
        lines.append(f"---\n\n## 슬라이드 {slide['idx']+1}  `{t_s} ~ {t_e}`\n")
        lines.append(f"![슬라이드 {slide['idx']+1}]({img_rel})\n\n")
        lines.append(f"> **Transcript**\n>\n> {text.replace(chr(10), chr(10) + '> ')}\n\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── PDF 내보내기 ────────────────────────────────────────────────

_KOREAN_FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/NanumGothic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Regular.otf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


def _find_korean_font() -> str | None:
    for path in _KOREAN_FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def _export_pdf(matched: list[dict], out_path: str) -> None:
    """A4 가로(landscape) 기준: 좌측 슬라이드 / 우측 스크립트."""
    from fpdf import FPDF

    # 가로 A4: 297 × 210 mm
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)

    font_path = _find_korean_font()
    if font_path:
        pdf.add_font("Korean", "", font_path)
        body_font = "Korean"
    else:
        print("[Stage 6] 한국어 폴트를 찾지 못했습니다. 텍스트가 깨질 수 있습니다.")
        body_font = "Helvetica"

    # 레이아웃 상수 (mm)
    PAGE_W, PAGE_H = 297, 210
    MARGIN = 10
    SLIDE_W = 190          # 좌측 슬라이드 열 폭
    SCRIPT_X = MARGIN + SLIDE_W + 6   # 우측 스크립트 시작 X
    SCRIPT_W = PAGE_W - SCRIPT_X - MARGIN  # 우측 열 폭

    for slide in matched:
        pdf.add_page()

        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])
        label = f"Slide {slide['idx']+1}  [{t_s} ~ {t_e}]"

        # ─ 헤더 ─
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_xy(MARGIN, MARGIN)
        pdf.cell(SLIDE_W, 6, label, ln=False)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(SCRIPT_X, MARGIN)
        pdf.cell(SCRIPT_W, 6, "Transcript", ln=False)

        y_content = MARGIN + 8  # 헤더 아래에서 콘텐츠 시작

        # ─ 좌측: 슬라이드 이미지 ─
        SLIDE_H = SLIDE_W * 9 / 16   # 16:9 비율
        if os.path.isfile(slide["frame_path"]):
            pdf.image(slide["frame_path"], x=MARGIN, y=y_content, w=SLIDE_W)

        # ─ 구분선 ─
        line_x = SCRIPT_X - 3
        pdf.set_draw_color(200, 200, 200)
        pdf.line(line_x, MARGIN, line_x, PAGE_H - MARGIN)

        # ─ 우측: 스크립트 텍스트 ─
        pdf.set_xy(SCRIPT_X, y_content)
        pdf.set_font(body_font, size=8)
        text = slide.get("text", "").strip() or "(해당 구간 음성 없음)"
        pdf.multi_cell(SCRIPT_W, 5, text)

    pdf.output(out_path)


# ── 항상 생성되는 독립 출력물 ──────────────────────────────────

def _export_transcript(matched: list[dict], out_dir: str) -> str:
    """타임스탬프 포함 전체 텍스트를 transcript.txt로 저장."""
    out_path = os.path.join(out_dir, "transcript.txt")
    lines = []
    for slide in matched:
        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])
        text = slide.get("text", "").strip()
        lines.append(f"[{t_s} ~ {t_e}] 슬라이드 {slide['idx'] + 1}")
        lines.append(text if text else "(음성 없음)")
        lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Stage 6] 트랜스크립트: {out_path}")
    return out_path


def _export_slide_images(matched: list[dict], out_dir: str) -> str:
    """슬라이드 이미지를 output/slides/ 폴더에 복사."""
    import shutil
    slides_dir = os.path.join(out_dir, "slides")
    Path(slides_dir).mkdir(parents=True, exist_ok=True)
    for slide in matched:
        src = slide["frame_path"]
        if os.path.isfile(src):
            t_s = _fmt_time(slide["t_start"]).replace(":", "-")
            dst = os.path.join(slides_dir, f"slide_{slide['idx']:03d}_{t_s}.jpg")
            shutil.copy2(src, dst)
    print(f"[Stage 6] 슬라이드 이미지: {slides_dir}/ ({len(matched)}장)")
    return slides_dir


# ── 메인 진입점 ───────────────────────────────────────────────────

def run(matched: list[dict], cfg: dict | None = None) -> str:
    """강의 노트 파일 생성.

    Args:
        matched: Stage 5 출력
        cfg:     config.yaml dict

    Returns:
        생성된 파일 경로
    """
    if cfg is None:
        cfg = _load_config()

    export_cfg = cfg["export"]
    fmt: str = export_cfg.get("format", "html").lower()
    out_dir: str = cfg["paths"]["output_dir"]
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    transcript_path = _export_transcript(matched, out_dir)
    slides_dir = _export_slide_images(matched, out_dir)

    ext_map = {"html": "html", "pdf": "pdf", "markdown": "md"}
    ext = ext_map.get(fmt, "html")
    out_path = os.path.join(out_dir, f"lecture_note.{ext}")

    print(f"[Stage 6] 강의 노트 생성 중 (포맷: {fmt})")

    if fmt == "html":
        _export_html(matched, out_path)
    elif fmt == "pdf":
        _export_pdf(matched, out_path)
    elif fmt in ("markdown", "md"):
        _export_markdown(matched, out_path)
    else:
        raise ValueError(f"지원하지 않는 포맷: {fmt}  (html | pdf | markdown)")

    size_kb = os.path.getsize(out_path) / 1024
    print(f"[Stage 6] 저장 완료: {out_path}  ({size_kb:.1f} KB)")
    return out_path


# ── 단독 실행 테스트 ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python stage6_export.py <stage5_json> [config_path]")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        matched = json.load(f)

    config_path = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    result = run(matched, cfg)
    print(f"\n노트 경로: {result}")
