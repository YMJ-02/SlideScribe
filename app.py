"""Gradio UI entry point: python app.py

Runs the SlideScribe note generation UI on localhost.
"""

import os
import sys
import site
import zipfile
import tempfile
import yaml
import gradio as gr
from pathlib import Path

# ── Auto-inject CUDA DLL paths on Windows ────────────────────────────────────
def _inject_cuda_paths():
    """Add nvidia CUDA DLL directories to PATH so faster-whisper can find them."""
    if sys.platform != "win32":
        return
    for sp in site.getsitepackages():
        for lib in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_runtime/bin"]:
            dll_path = os.path.join(sp, lib.replace("/", os.sep))
            if os.path.isdir(dll_path) and dll_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")

_inject_cuda_paths()
# ─────────────────────────────────────────────────────────────────────────────

from run import load_config, run_pipeline, AUDIO_EXTS
from i18n import t, WHISPER_DISPLAY_NAMES, WHISPER_CODE_MAP


def _build_cfg(fmt, scene_threshold, ssim_threshold, whisper_lang):
    cfg = load_config()
    cfg["export"]["format"] = fmt
    cfg["slide_detection"]["slide_change_threshold"] = scene_threshold
    cfg["slide_detection"]["ssim_merge_threshold"] = ssim_threshold
    cfg["stt"]["language"] = WHISPER_CODE_MAP.get(whisper_lang, "auto") or "auto"
    return cfg


def _run_for_gradio(
    video_files,
    fmt: str,
    scene_threshold: float,
    ssim_threshold: float,
    whisper_lang: str,
    ui_lang: str,
    progress=gr.Progress(track_tqdm=True),
) -> tuple[str, str | None]:
    """Handles single or multiple file uploads.

    Returns:
        (status message, zip file path for download)
    """
    lang = "en" if ui_lang == "English" else "ko"

    if not video_files:
        return t("error_no_file", lang), None

    if not isinstance(video_files, list):
        video_files = [video_files]
    paths = [f if isinstance(f, str) else f.name for f in video_files]

    cfg = _build_cfg(fmt, scene_threshold, ssim_threshold, whisper_lang)
    total = len(paths)
    collected: list[str] = []
    status_lines: list[str] = []

    from stages import stage1_segment, stage2_pdf, stage3_audio
    from stages import stage4_stt, stage5_match, stage6_export

    for idx, video_path in enumerate(paths, 1):
        stem = Path(video_path).stem
        is_audio = Path(video_path).suffix.lower() in AUDIO_EXTS
        desc_prefix = f"[{idx}/{total}] {Path(video_path).name}"

        try:
            progress((idx - 1) / total, desc=f"{desc_prefix} — starting…")

            if is_audio:
                slides, pdf_path, wav_path = [], None, video_path
                progress((idx - 0.7) / total, desc=f"{desc_prefix} — audio input, skipping slide detection")
            else:
                progress((idx - 0.9) / total, desc=f"{desc_prefix} — Stage 1 slide detection")
                slides = stage1_segment.run(video_path, cfg)
                progress((idx - 0.75) / total, desc=f"{desc_prefix} — Stage 2 slide PDF")
                pdf_path = stage2_pdf.run(slides, cfg, stem=stem)
                progress((idx - 0.6) / total, desc=f"{desc_prefix} — Stage 3 audio extraction")
                wav_path = stage3_audio.run(video_path, cfg)

            progress((idx - 0.5) / total, desc=f"{desc_prefix} — Stage 4 Whisper STT…")
            segments = stage4_stt.run(wav_path, cfg)

            progress((idx - 0.2) / total, desc=f"{desc_prefix} — Stage 5 matching")
            matched = stage5_match.run(slides, segments)

            progress((idx - 0.1) / total, desc=f"{desc_prefix} — Stage 6 note export")
            note_path = stage6_export.run(matched, cfg, stem=stem)

            out_dir = cfg["paths"]["output_dir"]
            transcript_path = os.path.join(out_dir, f"{stem}-transcript.txt")

            for p in [note_path, pdf_path, transcript_path]:
                if p and os.path.isfile(p):
                    collected.append(p)

            status_lines.append(
                f"✓ {Path(video_path).name}  →  {len(slides)} slides / {len(segments)} segs"
            )

        except Exception as e:
            status_lines.append(f"✗ {Path(video_path).name}  ERROR: {e}")

    progress(1.0, desc="Done!")

    if not collected:
        return "\n".join(status_lines), None

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in collected:
            zf.write(p, arcname=os.path.basename(p))

    return "\n".join(status_lines), tmp.name


def build_ui() -> gr.Blocks:
    cfg = load_config() if os.path.isfile("config.yaml") else {}
    sd = cfg.get("slide_detection", {})
    default_threshold = sd.get("slide_change_threshold", 0.90)
    default_ssim = sd.get("ssim_merge_threshold", 0.85)
    default_fmt = cfg.get("export", {}).get("format", "html")
    default_whisper = "Auto-detect"

    with gr.Blocks(title="SlideScribe") as demo:
        with gr.Row():
            gr.Markdown("## SlideScribe")
            ui_lang = gr.Radio(
                choices=["English", "한국어"],
                value="English",
                label="UI Language",
                scale=0,
            )

        title_md = gr.Markdown(t("subtitle", "en"))

        with gr.Row():
            with gr.Column(scale=2):
                video_input = gr.File(
                    label=t("upload_label", "en"),
                    file_count="multiple",
                    file_types=[
                        ".mp4", ".avi", ".mkv", ".mov", ".webm",
                        ".mp3", ".wav", ".m4a", ".aac", ".flac",
                    ],
                )
                fmt_radio = gr.Radio(
                    choices=["html", "pdf", "markdown"],
                    value=default_fmt,
                    label=t("format_label", "en"),
                )
                whisper_dd = gr.Dropdown(
                    choices=WHISPER_DISPLAY_NAMES,
                    value=default_whisper,
                    label=t("whisper_label", "en"),
                )

            with gr.Column(scale=1):
                params_md = gr.Markdown(t("params_header", "en"))
                scene_slider = gr.Slider(
                    minimum=0.70, maximum=0.99, step=0.01,
                    value=default_threshold,
                    label=t("threshold_label", "en"),
                )
                ssim_slider = gr.Slider(
                    minimum=0.5, maximum=1.0, step=0.01,
                    value=default_ssim,
                    label=t("merge_label", "en"),
                )

        run_btn = gr.Button(t("run_btn", "en"), variant="primary")
        status_box = gr.Textbox(label=t("status_label", "en"), lines=6, interactive=False)
        zip_out = gr.File(label="Download results (ZIP)")

        def _switch_lang(lang_choice):
            lang = "en" if lang_choice == "English" else "ko"
            dl_label = "Download results (ZIP)" if lang == "en" else "결과 다운로드 (ZIP)"
            return (
                t("subtitle", lang),
                gr.update(label=t("upload_label", lang)),
                gr.update(label=t("format_label", lang)),
                gr.update(label=t("whisper_label", lang)),
                t("params_header", lang),
                gr.update(label=t("threshold_label", lang)),
                gr.update(label=t("merge_label", lang)),
                gr.update(value=t("run_btn", lang)),
                gr.update(label=t("status_label", lang)),
                gr.update(label=dl_label),
            )

        ui_lang.change(
            fn=_switch_lang,
            inputs=[ui_lang],
            outputs=[
                title_md, video_input, fmt_radio, whisper_dd,
                params_md, scene_slider, ssim_slider,
                run_btn, status_box, zip_out,
            ],
        )

        run_btn.click(
            fn=_run_for_gradio,
            inputs=[video_input, fmt_radio, scene_slider, ssim_slider, whisper_dd, ui_lang],
            outputs=[status_box, zip_out],
        )

    return demo


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SlideScribe Gradio UI")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio link")
    parser.add_argument("--port", type=int, default=7860, help="Local port (default: 7860)")
    args = parser.parse_args()

    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=args.port, share=args.share)
