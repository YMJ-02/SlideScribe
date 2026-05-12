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

  /* 본문 grid: 모드별 컬럼 구성 */
  .page-body {{
    display: grid;
    overflow: hidden;
  }}
  .mode-both     .page-body {{ grid-template-columns: 3fr 1fr; }}
  .mode-slides   .page-body {{ grid-template-columns: 1fr; }}
  .mode-whisper  .page-body {{ grid-template-columns: 1fr; }}

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
    has_any_text = any(s.get("text", "").strip() for s in matched)
    has_any_frame = any(os.path.isfile(s.get("frame_path", "")) for s in matched)

    pages = []
    for slide in matched:
        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])
        text = slide.get("text", "").strip()
        fp = slide.get("frame_path", "")
        slide_num = slide['idx'] + 1

        # 트랜스크립트 컬럼 — text 가 한 슬라이드라도 있으면 표시
        if has_any_text:
            transcript_html = (
                f'<div class="transcript">{text}</div>'
                if text else
                '<div class="transcript no-text">(해당 구간 음성 없음)</div>'
            )
            transcript_block = f"""
      <div class="transcript-panel">
        <div class="transcript-label">Transcript</div>
        {transcript_html}
      </div>"""
        else:
            transcript_block = ""

        # 슬라이드 컬럼 — frame_path 가 한 슬라이드라도 있으면 표시
        if has_any_frame:
            img_html = (
                f'<img src="data:image/jpeg;base64,{_img_to_b64(fp)}" alt="슬라이드 {slide_num}">'
                if fp and os.path.isfile(fp) else
                '<div class="no-slide">(슬라이드 이미지 없음)</div>'
            )
            slide_block = f'<div class="slide-panel">{img_html}</div>'
        else:
            slide_block = ""

        # 모드별 grid 변형
        if has_any_text and has_any_frame:
            page_class = "note-page mode-both"
        elif has_any_frame:
            page_class = "note-page mode-slides"
        else:
            page_class = "note-page mode-whisper"

        pages.append(f"""
  <div class="{page_class}">
    <div class="page-header">
      <span class="slide-num">슬라이드 {slide_num}</span>
      <span class="slide-time">{t_s} ~ {t_e}</span>
    </div>
    <div class="page-body">
      {slide_block}
      {transcript_block}
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
    has_any_text = any(s.get("text", "").strip() for s in matched)
    has_any_frame = any(os.path.isfile(s.get("frame_path", "")) for s in matched)

    lines = ["# 강의 노트\n"]
    for slide in matched:
        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])
        text = slide.get("text", "").strip()
        fp = slide.get("frame_path", "")

        lines.append(f"---\n\n## 슬라이드 {slide['idx']+1}  `{t_s} ~ {t_e}`\n")
        if has_any_frame and fp and os.path.isfile(fp):
            img_rel = os.path.relpath(fp, os.path.dirname(out_path))
            lines.append(f"![슬라이드 {slide['idx']+1}]({img_rel})\n\n")
        if has_any_text:
            body = text or "*(해당 구간 음성 없음)*"
            lines.append(f"> **Transcript**\n>\n> {body.replace(chr(10), chr(10) + '> ')}\n\n")

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
    """모드별 레이아웃:
       both    : 396×210 가로 — 좌(슬라이드) | 우(스크립트)
       slides  : 297×210 가로 — 슬라이드만
       whisper : 210×297 세로 — 스크립트만
    """
    from fpdf import FPDF

    has_any_text = any(s.get("text", "").strip() for s in matched)
    has_any_frame = any(os.path.isfile(s.get("frame_path", "")) for s in matched)

    pdf = FPDF(unit="mm")
    pdf.set_auto_page_break(auto=False)

    font_path = _find_korean_font()
    if font_path:
        pdf.add_font("Korean", "", font_path)
        body_font = "Korean"
    else:
        print("[Stage 6] 한국어 폰트를 찾지 못했습니다. 텍스트가 깨질 수 있습니다.")
        body_font = "Helvetica"

    if has_any_frame and has_any_text:
        PAGE_W, PAGE_H = 396, 210
    elif has_any_frame:
        PAGE_W, PAGE_H = 297, 210
    else:
        PAGE_W, PAGE_H = 210, 297

    MARGIN = 8
    HDR_H = 7
    CONTENT_Y = MARGIN + HDR_H + 2

    if has_any_frame and has_any_text:
        SLIDE_W = 277
        DIV_X = MARGIN + SLIDE_W + 4
        SCRIPT_X = DIV_X + 4
        SCRIPT_W = PAGE_W - SCRIPT_X - MARGIN
    elif has_any_frame:
        SLIDE_W = PAGE_W - 2 * MARGIN
        DIV_X = SCRIPT_X = SCRIPT_W = 0
    else:
        SLIDE_W = 0
        DIV_X = 0
        SCRIPT_X = MARGIN
        SCRIPT_W = PAGE_W - 2 * MARGIN

    for slide in matched:
        pdf.add_page(format=(PAGE_W, PAGE_H))

        t_s = _fmt_time(slide["t_start"])
        t_e = _fmt_time(slide["t_end"])

        # 헤더 바
        pdf.set_fill_color(26, 26, 46)
        pdf.rect(0, 0, PAGE_W, HDR_H + 2, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(MARGIN, 1)
        pdf.cell(PAGE_W - 2 * MARGIN, 5,
                 f"Slide {slide['idx']+1}  [{t_s} ~ {t_e}]", ln=False)
        pdf.set_text_color(0, 0, 0)

        # 슬라이드 이미지
        fp = slide.get("frame_path", "")
        if has_any_frame and fp and os.path.isfile(fp):
            pdf.image(fp, x=MARGIN, y=CONTENT_Y, w=SLIDE_W)

        # 스크립트
        if has_any_text:
            if has_any_frame:
                pdf.set_draw_color(200, 200, 200)
                pdf.line(DIV_X, MARGIN, DIV_X, PAGE_H - MARGIN)
            pdf.set_xy(SCRIPT_X, CONTENT_Y)
            pdf.set_font(body_font, size=8)
            text = slide.get("text", "").strip() or "(해당 구간 음성 없음)"
            pdf.multi_cell(SCRIPT_W, 4.5, text)

    pdf.output(out_path)


# ── 항상 생성되는 독립 출력물 ──────────────────────────────────

def _export_transcript(matched: list[dict], out_dir: str, stem: str = "lecture_note") -> str | None:
    """타임스탬프 포함 전체 텍스트를 <stem>-transcript.txt로 저장.

    어떤 슬라이드에도 text 가 없으면 (slides-only 모드) 생성하지 않고 None 반환.
    """
    if not any(s.get("text", "").strip() for s in matched):
        return None
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


def _export_slide_images(matched: list[dict], out_dir: str) -> str | None:
    """슬라이드 이미지를 output/<stem>-slides/ 폴더에 복사.

    어떤 슬라이드에도 frame_path 가 없으면 (whisper-only 모드) None 반환.
    """
    if not any(os.path.isfile(s.get("frame_path", "")) for s in matched):
        return None
    import shutil
    slides_dir = os.path.join(out_dir, "slides")
    Path(slides_dir).mkdir(parents=True, exist_ok=True)
    copied = 0
    for slide in matched:
        src = slide.get("frame_path", "")
        if src and os.path.isfile(src):
            t_s = _fmt_time(slide["t_start"]).replace(":", "-")
            dst = os.path.join(slides_dir, f"slide_{slide['idx']:03d}_{t_s}.jpg")
            shutil.copy2(src, dst)
            copied += 1
    print(f"[Stage 6] 슬라이드 이미지: {slides_dir}/ ({copied}장)")
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
