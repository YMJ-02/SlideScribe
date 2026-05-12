"""Gradio UI entry point: python app.py

visionOS-inspired UI for SlideScribe.
모드 선택 (both / slides / whisper) + 슬라이드 감지 파라미터 노출.
"""

from __future__ import annotations

import os
import site
import sys
import tempfile
import zipfile
from pathlib import Path

import gradio as gr


# ── CUDA DLL paths on Windows (자동 주입) ────────────────────────────
def _inject_cuda_paths() -> None:
    if sys.platform != "win32":
        return
    for sp in site.getsitepackages():
        for lib in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_runtime/bin"]:
            dll_path = os.path.join(sp, lib.replace("/", os.sep))
            if os.path.isdir(dll_path) and dll_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")


_inject_cuda_paths()

from run import load_config, run_pipeline, AUDIO_EXTS, MODES  # noqa: E402
from i18n import t, WHISPER_DISPLAY_NAMES, WHISPER_CODE_MAP   # noqa: E402


# ── visionOS-flavored CSS ──────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root, .gradio-container {
  --vs-ink: #FFFFFF;
  --vs-ink-2: rgba(255,255,255,.78);
  --vs-ink-3: rgba(255,255,255,.55);
  --vs-ink-4: rgba(255,255,255,.32);
  --vs-glass: rgba(255,255,255,.12);
  --vs-glass-strong: rgba(255,255,255,.20);
  --vs-border: rgba(255,255,255,.24);
  --vs-border-soft: rgba(255,255,255,.12);
  --vs-accent: #5AB6FF;
  --vs-accent-2: #FF8A4C;
  --vs-danger: #FF6A6A;
  --vs-ok: #7CE3A6;
}

/* ── Page background ─────────────────────────────────────────── */
html, body, .gradio-container, gradio-app {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Pretendard",
               "Apple SD Gothic Neo", system-ui, sans-serif !important;
  color: var(--vs-ink) !important;
  letter-spacing: -0.01em;
  -webkit-font-smoothing: antialiased;
}

gradio-app, .gradio-container {
  background:
    radial-gradient(1200px 800px at 18% 12%, #6e7a55 0%, transparent 55%),
    radial-gradient(1000px 700px at 82% 22%, #2f3a30 0%, transparent 60%),
    radial-gradient(900px 700px at 18% 88%, #c25a1f 0%, transparent 55%),
    radial-gradient(700px 600px at 82% 80%, #2a3a3b 0%, transparent 55%),
    linear-gradient(180deg, #4d5b3f 0%, #2c3530 60%, #1c2220 100%) !important;
  background-attachment: fixed !important;
  min-height: 100vh;
}

.gradio-container { max-width: 1180px !important; padding: 32px 24px !important; }

/* ── Hero / title bar ────────────────────────────────────────── */
.vs-hero {
  display: flex; align-items: center; justify-content: space-between;
  gap: 24px; padding: 22px 28px; margin-bottom: 24px;
  background: var(--vs-glass);
  border: 1px solid var(--vs-border);
  border-radius: 32px;
  -webkit-backdrop-filter: blur(40px) saturate(150%);
  backdrop-filter: blur(40px) saturate(150%);
  box-shadow: 0 0 0 1px rgba(255,255,255,.10) inset,
              0 24px 60px -10px rgba(0,0,0,.45);
}
.vs-hero h1 {
  font-size: 28px; font-weight: 600; margin: 0;
  background: linear-gradient(120deg, #fff 0%, #cfe4ff 60%, #ffd1b3 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.vs-hero p { margin: 4px 0 0; color: var(--vs-ink-3); font-size: 14px; }
.vs-hero .vs-logo {
  width: 52px; height: 52px; border-radius: 16px;
  background: linear-gradient(135deg, #5AB6FF 0%, #B16CFF 50%, #FF8A4C 100%);
  box-shadow: 0 12px 30px -6px rgba(90,182,255,.45);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 22px; color: #0c1014;
}

/* ── Generic glass panels ───────────────────────────────────── */
.block, .form, .panel,
.gr-box, .gr-form, .gr-panel,
.gr-block, .gr-group {
  background: var(--vs-glass) !important;
  border: 1px solid var(--vs-border-soft) !important;
  backdrop-filter: blur(30px) saturate(140%) !important;
  -webkit-backdrop-filter: blur(30px) saturate(140%) !important;
  border-radius: 22px !important;
  color: var(--vs-ink) !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,.06) inset,
              0 18px 40px -16px rgba(0,0,0,.45);
}

.gr-block .gr-block { background: transparent !important; border: 0 !important; box-shadow: none !important; }

/* Labels */
label, .label-wrap, .label, .gradio-container label, .gradio-container .label-wrap {
  color: var(--vs-ink-2) !important;
  font-weight: 500 !important;
  font-size: 13px !important;
}

/* ── Inputs ──────────────────────────────────────────────────── */
input[type="text"], input[type="number"], textarea, select,
.gr-text-input, .gr-textbox textarea, .gr-textbox input {
  background: rgba(255,255,255,.08) !important;
  border: 1px solid var(--vs-border-soft) !important;
  border-radius: 14px !important;
  color: var(--vs-ink) !important;
  padding: 10px 14px !important;
}
input[type="text"]:focus, input[type="number"]:focus, textarea:focus, select:focus,
.gr-text-input:focus, .gr-textbox textarea:focus, .gr-textbox input:focus {
  border-color: var(--vs-accent) !important;
  box-shadow: 0 0 0 4px rgba(90,182,255,.18) !important;
  outline: none !important;
}

/* ── File upload area ────────────────────────────────────────── */
.gr-file, [data-testid="file"], .file-preview, .file-upload {
  background: rgba(255,255,255,.06) !important;
  border: 1.5px dashed var(--vs-border) !important;
  border-radius: 22px !important;
  color: var(--vs-ink-2) !important;
}
.gr-file:hover, [data-testid="file"]:hover { border-color: var(--vs-accent) !important; }

/* ── Radio buttons → pill group ──────────────────────────────── */
.gr-radio, [data-testid="radio"], .wrap.svelte-1ipelgc {
  background: rgba(255,255,255,.06) !important;
  border-radius: 999px !important;
  padding: 4px !important;
  border: 1px solid var(--vs-border-soft) !important;
  display: inline-flex !important;
  gap: 4px !important;
}
.gr-radio label, [data-testid="radio"] label {
  background: transparent !important;
  border: 0 !important;
  border-radius: 999px !important;
  padding: 8px 16px !important;
  color: var(--vs-ink-3) !important;
  cursor: pointer !important;
  transition: all .18s ease !important;
}
.gr-radio label:has(input:checked),
[data-testid="radio"] label:has(input:checked),
.gr-radio label.selected,
[data-testid="radio"] label.selected {
  background: var(--vs-glass-strong) !important;
  color: var(--vs-ink) !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,.22) inset,
              0 6px 16px rgba(0,0,0,.25) !important;
}
.gr-radio input[type="radio"], [data-testid="radio"] input[type="radio"] { display: none !important; }

/* ── Sliders ─────────────────────────────────────────────────── */
input[type="range"] {
  -webkit-appearance: none; appearance: none;
  height: 6px; border-radius: 999px;
  background: rgba(255,255,255,.16) !important;
  outline: none;
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 20px; height: 20px; border-radius: 999px;
  background: #fff;
  box-shadow: 0 4px 10px rgba(0,0,0,.3);
  cursor: pointer;
}

/* ── Primary button ──────────────────────────────────────────── */
button.primary, button.gr-button-primary, .gr-button.primary,
button[variant="primary"], .lg.primary {
  background: linear-gradient(135deg, #5AB6FF 0%, #6e8cff 100%) !important;
  border: 0 !important;
  border-radius: 999px !important;
  color: #0c1014 !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  padding: 14px 28px !important;
  box-shadow: 0 12px 28px -8px rgba(90,182,255,.55),
              0 0 0 1px rgba(255,255,255,.20) inset !important;
  transition: transform .15s ease, box-shadow .15s ease !important;
}
button.primary:hover, button.gr-button-primary:hover, .gr-button.primary:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 18px 36px -8px rgba(90,182,255,.65),
              0 0 0 1px rgba(255,255,255,.28) inset !important;
}

/* ── Secondary/utility buttons ───────────────────────────────── */
button.secondary, .gr-button-secondary, button:not(.primary):not(.gr-button-primary) {
  background: var(--vs-glass-strong) !important;
  border: 1px solid var(--vs-border) !important;
  border-radius: 999px !important;
  color: var(--vs-ink) !important;
}

/* ── Dropdown ────────────────────────────────────────────────── */
.gr-dropdown, .dropdown {
  background: rgba(255,255,255,.08) !important;
  border: 1px solid var(--vs-border-soft) !important;
  border-radius: 14px !important;
  color: var(--vs-ink) !important;
}

/* ── Progress / status text ──────────────────────────────────── */
.progress-text, .progress-level, .meta-text {
  color: var(--vs-ink-2) !important;
}

/* ── Tab bar (mode chips) ────────────────────────────────────── */
.vs-mode-hint {
  margin-top: 6px;
  font-size: 13px;
  color: var(--vs-ink-3);
  padding: 10px 14px;
  background: rgba(255,255,255,.05);
  border-radius: 12px;
  border: 1px solid var(--vs-border-soft);
}

/* ── Markdown text (subtitle, hints) ─────────────────────────── */
.gradio-container .prose, .gradio-container .markdown, .gradio-container .md {
  color: var(--vs-ink-2) !important;
}
.gradio-container .prose h1, .gradio-container .prose h2, .gradio-container .prose h3 {
  color: var(--vs-ink) !important;
  font-weight: 600 !important;
}

/* ── Scrollbars ──────────────────────────────────────────────── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.18); border-radius: 5px; }
::-webkit-scrollbar-track { background: transparent; }

/* ── Footer / footer-style note ──────────────────────────────── */
.vs-footer {
  text-align: center; margin-top: 28px;
  color: var(--vs-ink-4); font-size: 12px;
}

/* ── Group spacing tweaks ────────────────────────────────────── */
.gradio-container .gap-4, .gradio-container .gap-2 { gap: 14px !important; }
.gradio-container .row { gap: 16px !important; }

/* Lift cards on hover */
.lift { transition: transform .25s ease, box-shadow .25s ease; }
.lift:hover { transform: translateY(-2px); box-shadow: 0 30px 60px -10px rgba(0,0,0,.45); }
"""


# ── 헤더 HTML ─────────────────────────────────────────────────────
def _hero_html(lang: str) -> str:
    title = t("title", lang)
    tagline = t("tagline", lang)
    subtitle = t("subtitle", lang)
    return f"""
<div class="vs-hero">
  <div style="display:flex; align-items:center; gap:18px;">
    <div class="vs-logo">S</div>
    <div>
      <h1>{title}</h1>
      <p>{tagline} · <span style="color:var(--vs-ink-4)">{subtitle}</span></p>
    </div>
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <span style="color:var(--vs-ink-3); font-size:13px;">v0.2</span>
  </div>
</div>
"""


# ── 실행 함수 (Gradio 콜백) ────────────────────────────────────────
def _build_cfg(
    fmt: str,
    sensitivity: float,
    merge_score: float,
    sample_rate: float,
    min_slide_sec: float,
    whisper_lang_label: str,
) -> dict:
    cfg = load_config()
    cfg["export"]["format"] = fmt
    cfg["slide_detection"]["sensitivity"] = float(sensitivity)
    cfg["slide_detection"]["merge_score"] = float(merge_score)
    cfg["slide_detection"]["frame_sample_rate"] = float(sample_rate)
    cfg["slide_detection"]["min_slide_sec"] = float(min_slide_sec)
    cfg["stt"]["language"] = WHISPER_CODE_MAP.get(whisper_lang_label, "auto") or "auto"
    return cfg


def _mode_value_from_label(label: str, lang: str) -> str:
    """UI 라벨을 내부 모드 키로 변환."""
    table = {
        t("mode_both",    lang): "both",
        t("mode_slides",  lang): "slides",
        t("mode_whisper", lang): "whisper",
    }
    return table.get(label, "both")


def _run_for_gradio(
    files,
    mode_label: str,
    fmt: str,
    sensitivity: float,
    merge_score: float,
    sample_rate: float,
    min_slide_sec: float,
    whisper_lang: str,
    ui_lang_label: str,
    progress=gr.Progress(track_tqdm=True),
):
    lang = "en" if ui_lang_label == "English" else "ko"

    if not files:
        return t("error_no_file", lang), None

    if not isinstance(files, list):
        files = [files]
    paths = [f if isinstance(f, str) else f.name for f in files]
    mode = _mode_value_from_label(mode_label, lang)

    cfg = _build_cfg(fmt, sensitivity, merge_score, sample_rate, min_slide_sec, whisper_lang)

    total = len(paths)
    collected: list[str] = []
    status_lines: list[str] = []

    for idx, src in enumerate(paths, 1):
        name = Path(src).name
        desc_prefix = f"[{idx}/{total}] {name}"
        try:
            progress((idx - 1) / total, desc=f"{desc_prefix} — start ({mode})")
            res = run_pipeline(src, cfg, mode=mode)
            for p in (res.get("note"), res.get("slides_pdf"), res.get("transcript")):
                if p and os.path.isfile(p):
                    collected.append(p)
            status_lines.append(
                t("done_msg", lang).format(
                    name=name,
                    slides=len(res.get("slides", [])),
                    segs=len(res.get("segments", [])),
                )
            )
        except Exception as e:
            status_lines.append(t("err_msg", lang).format(name=name, err=str(e)))

    progress(1.0, desc="Done!")

    if not collected:
        return "\n".join(status_lines), None

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        seen: set[str] = set()
        for p in collected:
            if p in seen:
                continue
            seen.add(p)
            zf.write(p, arcname=os.path.basename(p))

    return "\n".join(status_lines), tmp.name


# ── UI ────────────────────────────────────────────────────────────
def build_ui() -> gr.Blocks:
    cfg = load_config() if os.path.isfile("config.yaml") else {}
    sd = cfg.get("slide_detection", {})
    default_mode_key = cfg.get("pipeline", {}).get("default_mode", "both")
    default_fmt = cfg.get("export", {}).get("format", "html")
    default_sensitivity = float(sd.get("sensitivity", 2.5))
    default_merge = float(sd.get("merge_score", 0.07))
    default_rate = float(sd.get("frame_sample_rate", 2.0))
    default_mindur = float(sd.get("min_slide_sec", 2.0))

    init_lang = "en"
    mode_label_map = {
        "both":    t("mode_both",    init_lang),
        "slides":  t("mode_slides",  init_lang),
        "whisper": t("mode_whisper", init_lang),
    }
    default_mode_label = mode_label_map.get(default_mode_key, mode_label_map["both"])

    with gr.Blocks(title="SlideScribe", css=CUSTOM_CSS, theme=gr.themes.Base()) as demo:
        # ── 헤더 ────────────────────────────────────────────
        with gr.Row():
            hero = gr.HTML(_hero_html(init_lang))
        with gr.Row():
            ui_lang = gr.Radio(
                choices=["English", "한국어"],
                value="English",
                label="Language",
                interactive=True,
            )

        # ── 모드 선택 ───────────────────────────────────────
        with gr.Group(elem_classes=["lift"]):
            mode_radio = gr.Radio(
                choices=[mode_label_map["both"], mode_label_map["slides"], mode_label_map["whisper"]],
                value=default_mode_label,
                label=t("mode_label", init_lang),
                interactive=True,
            )
            mode_hint = gr.HTML(
                f"<div class='vs-mode-hint'>{t('mode_hint_both', init_lang)}</div>"
            )

        # ── 파일 업로드 ─────────────────────────────────────
        with gr.Group(elem_classes=["lift"]):
            files = gr.File(
                label=t("upload_label", init_lang),
                file_count="multiple",
                file_types=[
                    ".mp4", ".avi", ".mkv", ".mov", ".webm",
                    ".mp3", ".wav", ".m4a", ".aac", ".flac",
                ],
            )
            upload_hint = gr.Markdown(
                f"<div style='color:var(--vs-ink-4); font-size:12px;'>{t('upload_hint', init_lang)}</div>"
            )

        # ── 파라미터 패널 ───────────────────────────────────
        with gr.Row():
            # 슬라이드 감지 파라미터
            with gr.Group(elem_classes=["lift"]) as slide_params:
                params_slide_md = gr.Markdown(f"### {t('params_slide', init_lang)}")
                sensitivity_slider = gr.Slider(
                    minimum=1.5, maximum=4.0, step=0.1,
                    value=default_sensitivity,
                    label=t("sensitivity_label", init_lang),
                )
                merge_slider = gr.Slider(
                    minimum=0.02, maximum=0.20, step=0.005,
                    value=default_merge,
                    label=t("merge_label", init_lang),
                )
                sample_rate_slider = gr.Slider(
                    minimum=1.0, maximum=5.0, step=0.5,
                    value=default_rate,
                    label=t("sample_rate_label", init_lang),
                )
                min_dur_slider = gr.Slider(
                    minimum=0.5, maximum=10.0, step=0.5,
                    value=default_mindur,
                    label=t("min_dur_label", init_lang),
                )

            # 전사 파라미터
            with gr.Group(elem_classes=["lift"]) as whisper_params:
                params_whisper_md = gr.Markdown(f"### {t('params_whisper', init_lang)}")
                whisper_dd = gr.Dropdown(
                    choices=WHISPER_DISPLAY_NAMES,
                    value="Auto-detect",
                    label=t("whisper_label", init_lang),
                )
                fmt_radio = gr.Radio(
                    choices=["html", "pdf", "markdown"],
                    value=default_fmt,
                    label=t("format_label", init_lang),
                )

        # ── 실행 ────────────────────────────────────────────
        run_btn = gr.Button(t("run_btn", init_lang), variant="primary", size="lg")

        # ── 출력 ────────────────────────────────────────────
        with gr.Group(elem_classes=["lift"]):
            status_box = gr.Textbox(
                label=t("status_label", init_lang),
                lines=6, interactive=False,
            )
        zip_out = gr.File(label=t("download_label", init_lang))

        gr.HTML("<div class='vs-footer'>SlideScribe · faster-whisper + adaptive slide detection</div>")

        # ── 콜백: 언어 전환 (모드는 첫 옵션 "both" 로 리셋) ─
        def _switch_lang(lang_choice):
            lang = "en" if lang_choice == "English" else "ko"
            new_labels = [
                t("mode_both",    lang),
                t("mode_slides",  lang),
                t("mode_whisper", lang),
            ]
            return (
                _hero_html(lang),
                gr.update(choices=new_labels, value=new_labels[0], label=t("mode_label", lang)),
                f"<div class='vs-mode-hint'>{t('mode_hint_both', lang)}</div>",
                gr.update(visible=True),   # slide_params
                gr.update(visible=True),   # whisper_params
                gr.update(label=t("upload_label", lang)),
                f"<div style='color:var(--vs-ink-4); font-size:12px;'>{t('upload_hint', lang)}</div>",
                f"### {t('params_slide', lang)}",
                gr.update(label=t("sensitivity_label", lang)),
                gr.update(label=t("merge_label", lang)),
                gr.update(label=t("sample_rate_label", lang)),
                gr.update(label=t("min_dur_label", lang)),
                f"### {t('params_whisper', lang)}",
                gr.update(label=t("whisper_label", lang)),
                gr.update(label=t("format_label", lang)),
                gr.update(value=t("run_btn", lang)),
                gr.update(label=t("status_label", lang)),
                gr.update(label=t("download_label", lang)),
            )

        ui_lang.change(
            fn=_switch_lang,
            inputs=[ui_lang],
            outputs=[
                hero, mode_radio, mode_hint,
                slide_params, whisper_params,
                files, upload_hint,
                params_slide_md, sensitivity_slider, merge_slider, sample_rate_slider, min_dur_slider,
                params_whisper_md, whisper_dd, fmt_radio,
                run_btn, status_box, zip_out,
            ],
        )

        # ── 콜백: 모드 변경 → 힌트 + 패널 가시성 토글 ─────
        def _on_mode_change(mode_label, lang_choice):
            lang = "en" if lang_choice == "English" else "ko"
            mode = _mode_value_from_label(mode_label, lang)
            hint_key = {
                "both": "mode_hint_both",
                "slides": "mode_hint_slides",
                "whisper": "mode_hint_whisper",
            }[mode]
            slide_visible = mode in ("both", "slides")
            whisper_visible = mode in ("both", "whisper")
            return (
                f"<div class='vs-mode-hint'>{t(hint_key, lang)}</div>",
                gr.update(visible=slide_visible),
                gr.update(visible=whisper_visible),
            )

        mode_radio.change(
            fn=_on_mode_change,
            inputs=[mode_radio, ui_lang],
            outputs=[mode_hint, slide_params, whisper_params],
        )

        # ── 실행 ────────────────────────────────────────────
        run_btn.click(
            fn=_run_for_gradio,
            inputs=[
                files, mode_radio, fmt_radio,
                sensitivity_slider, merge_slider, sample_rate_slider, min_dur_slider,
                whisper_dd, ui_lang,
            ],
            outputs=[status_box, zip_out],
        )

    return demo


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SlideScribe Gradio UI")
    parser.add_argument("--share", action="store_true", help="Public Gradio share link")
    parser.add_argument("--port", type=int, default=7860, help="Local port (default: 7860)")
    args = parser.parse_args()

    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=args.port, share=args.share)
