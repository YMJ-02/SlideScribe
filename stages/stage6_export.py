"""Stage 6: 강의 노트 생성

matched 데이터(Stage 5 출력)를 HTML / PDF / Markdown으로 출력.
HTML: 이미지 base64 임베드 → 단일 파일로 배포 가능.
      페이지 크기: A4 가로(297mm) + 1/3(99mm) × A4 세로(210mm)
      슬라이드 영역(3) | 스크립트 영역(1) — 한 페이지 고정
PDF:  fpdf2 기반, 한국어 폰트 자동 탐색.
      총 폭 396mm × 210mm 레이아웃
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

# A4 가로: 297mm × 210mm
# 스크립트 열: 297/3 ≈ 99mm 우측에 추가
# 총 페이지: 396mm × 210mm (1mm ≈ 3.7795px)
_PAGE_W_PX  = 1496   # 396mm
_PAGE_H_PX  = 794    # 210mm

_HTML_STYLE = """
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
    background: #e8e8e8;
    padding: 32px 24px;
    color: #222;
  }}

  h1 {{
    text-align: center;
    color: #1a1a2e;
    margin-bottom: 32px;
    font-size: 1.1em;
    letter-spacing: 0.05em;
  }}

  /* 한 페이지 = A4가로(297mm) + 1/3(99mm) × A4세로(210mm) */
  .note-page {{
    width: {w}px;
    height: {h}px;
    background: #fff;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    margin: 0 auto 40px auto;
    display: grid;
    grid-template-rows: 32px 1fr;
    overflow: hidden;
  }}

  /* 상단 헤더 바 */
  .page-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px;
    background: #1a1a2e;
    color: #fff;
  }}
  .page-header .slide-num  {{ font-size: 0.73em; font-weight: bold; letter-spacing: 0.04em; }}
  .page-header .slide-time {{ font-size: 0.70em; color: #aab; }}

  /* 본문: 슬라이드(3) + 스크립트(1) */
  .page-body {{
    display: grid;
    grid-template-columns: 3fr 1fr;
    overflow: hidden;
  }}

  /* 좌측 슬라이드 */
  .slide-panel {{
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f8f8f8;
    padding: 10px;
    overflow: hidden;
  }}
  .slide-panel img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    display: block;
    border: 1px solid #ddd;
  }}

  /* 우측 스크립트 */
  .transcript-panel {{
    border-left: 2px solid #e0e0e0;
    padding: 10px 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    background: #fff;
  }}
  .transcript-label {{
    font-size: 0.62em;
    font-weight: bold;
    color: #bbb;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 5px;
    flex-shrink: 0;
    border-bottom: 1px solid #f0f0f0;
    padding-bottom: 4px;
  }}
  .transcript {{
    font-size: 0.70em;
    line-height: 1.65;
    white-space: pre-wrap;
    color: #333;
    overflow: hidden;
    flex: 1;
  }}
  .no-text {{ color: #ccc; font-style: italic; font-size: 0.68em; }}

  /* 인쇄: 슬라이드당 새 페이지 */
  @media print {{
    body {{ background: #fff; padding: 0; }}
    h1 {{ display: none; }}
    .note-page {{
      width: 396mm;
      height: 210mm;
      page-break-after: always;
      box-shadow: none;
      border: none;
      margin: 0;
      border-radius: 0;
    }}
  }}
""".format(w=_PAGE_W_PX, h=_PAGE_H_PX)


def _export_html(matched: list[dict], out_path: str) -> None:
    pages = []
    for slide in matched:
        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])
        text = slide.get("text", "").strip()
        transcript_html = (
            f'<div class="transcript">{text}</div>'
            if text else
            '<div class="transcript no-text">(해당 구간 음성 없음)</div>'
        )
        # Audio-only input has no slide image
        fp = slide.get("frame_path", "")
        slide_num = slide['idx'] + 1
        img_html = (
            f'<img src="data:image/jpeg;base64,{_img_to_b64(fp)}" alt="슬라이드 {slide_num}">'
            if fp and os.path.isfile(fp) else
            '<div class="no-slide">(슬라이드 이미지 없음)</div>'
        )
        pages.append(f"""
  <div class="note-page">
    <div class="page-header">
      <span class="slide-num">슬라이드 {slide['idx'] + 1}</span>
      <span class="slide-time">{t_s} ~ {t_e}</span>
    </div>
    <div class="page-body">
      <div class="slide-panel">{img_html}</div>
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
{''.join(pages)}
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
    """A4 가로 기준 + 1/3 추가 폭: 좌측 슬라이드(297mm) / 우측 스크립트(99mm)."""
    from fpdf import FPDF

    # 코사 지정 페이지: 396mm × 210mm
    pdf = FPDF(unit="mm")
    pdf.set_auto_page_break(auto=False)

    font_path = _find_korean_font()
    if font_path:
        pdf.add_font("Korean", "", font_path)
        body_font = "Korean"
    else:
        print("[Stage 6] 한국어 폰트를 찾지 못했습니다. 텍스트가 깨질 수 있습니다.")
        body_font = "Helvetica"

    # 레이아웃 상수 (mm)
    PAGE_W  = 396   # A4가로(297) + 1/3(99)
    PAGE_H  = 210   # A4 세로
    MARGIN  = 8
    HDR_H   = 7     # 헤더 롭
    SLIDE_W = 277   # 297 - 2*margin = 281 중 슬라이드에 할당
    SLIDE_H = SLIDE_W * 9 / 16
    DIV_X   = MARGIN + SLIDE_W + 4   # 구분선 X
    SCRIPT_X = DIV_X + 4
    SCRIPT_W = PAGE_W - SCRIPT_X - MARGIN
    CONTENT_Y = MARGIN + HDR_H + 2

    for slide in matched:
        pdf.add_page(format=(PAGE_W, PAGE_H))

        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])

        # ─ 헤더 바 ─
        pdf.set_fill_color(26, 26, 46)
        pdf.rect(0, 0, PAGE_W, HDR_H + 2, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(MARGIN, 1)
        pdf.cell(SLIDE_W, 5, f"Slide {slide['idx']+1}  [{t_s} ~ {t_e}]", ln=False)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(SCRIPT_X, 1)
        pdf.cell(SCRIPT_W, 5, "Transcript", ln=False)
        pdf.set_text_color(0, 0, 0)

        # ─ 좌측: 슬라이드 이미지 ─
        if os.path.isfile(slide["frame_path"]):
            pdf.image(slide["frame_path"], x=MARGIN, y=CONTENT_Y, w=SLIDE_W)

        # ─ 구분선 ─
        pdf.set_draw_color(200, 200, 200)
        pdf.line(DIV_X, MARGIN, DIV_X, PAGE_H - MARGIN)

        # ─ 우측: 스크립트 ─
        pdf.set_xy(SCRIPT_X, CONTENT_Y)
        pdf.set_font(body_font, size=7)
        text = slide.get("text", "").strip() or "(해당 구간 음성 없음)"
        pdf.multi_cell(SCRIPT_W, 4.2, text)

    pdf.output(out_path)


# ── 항상 생성되는 독립 출력물 ──────────────────────────────────

def _export_transcript(matched: list[dict], out_dir: str, stem: str = "lecture_note") -> str:
    """타임스탬프 포함 전체 텍스트를 <stem>-transcript.txt로 저장."""
    out_path = os.path.join(out_dir, f"{stem}-transcript.txt")
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


# ── 메인 진입점 ─────────────────────────────────────────────────

def run(matched: list[dict], cfg: dict | None = None, stem: str = "lecture_note") -> str:
    """강의 노트 파일 생성.

    Args:
        matched: Stage 5 출력
        cfg:     config.yaml dict
        stem:    출력 파일명 기반 (입력 영상 stem). e.g. "lecture_week3"

    Returns:
        생성된 파일 경로
    """
    if cfg is None:
        cfg = _load_config()

    export_cfg = cfg["export"]
    fmt: str = export_cfg.get("format", "html").lower()
    out_dir: str = cfg["paths"]["output_dir"]
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    transcript_path = _export_transcript(matched, out_dir, stem=stem)
    slides_dir = _export_slide_images(matched, out_dir)

    ext_map = {"html": "html", "pdf": "pdf", "markdown": "md"}
    ext = ext_map.get(fmt, "html")
    out_path = os.path.join(out_dir, f"{stem}-note.{ext}")

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
