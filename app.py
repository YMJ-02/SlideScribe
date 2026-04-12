"""Gradio UI entry point: python app.py

Runs the SlideScribe note generation UI on localhost.
"""

import os
import yaml
import gradio as gr

from run import load_config, run_pipeline, AUDIO_EXTS
from i18n import t, WHISPER_DISPLAY_NAMES, WHISPER_CODE_MAP


def _run_for_gradio(
    video_file,
    fmt: str,
    scene_threshold: float,
    ssim_threshold: float,
    whisper_lang: str,
    ui_lang: str,
    progress=gr.Progress(track_tqdm=True),
) -> tuple[str, str, str, str]:
    lang = "en" if ui_lang == "English" else "ko"

    if video_file is None:
        return t("error_no_file", lang), None, None, None

    video_path = video_file if isinstance(video_file, str) else video_file.name
    from pathlib import Path as _Path
    stem = _Path(video_path).stem

    cfg = load_config()
    cfg["export"]["format"] = fmt
    cfg["slide_detection"]["slide_change_threshold"] = scene_threshold
    cfg["slide_detection"]["ssim_merge_threshold"] = ssim_threshold
    # Whisper language: map display name → code (None = auto)
    cfg["stt"]["language"] = WHISPER_CODE_MAP.get(whisper_lang, "auto") or "auto"

    try:
        from stages import stage1_segment, stage2_pdf, stage3_audio
        from stages import stage4_stt, stage5_match, stage6_export

        from pathlib import Path as _Path
        is_audio = _Path(video_path).suffix.lower() in AUDIO_EXTS

        progress(0.00, desc="Starting…")

        if is_audio:
            slides = []
            pdf_path = None
            wav_path = video_path                      # skip Stage 3
            progress(0.10, desc="Audio input — skipping slide detection")
        else:
            progress(0.05, desc="Stage 1/6 — Detecting slide transitions")
            slides = stage1_segment.run(video_path, cfg)

            progress(0.25, desc="Stage 2/6 — Exporting slide PDF")
            pdf_path = stage2_pdf.run(slides, cfg, stem=stem)

            progress(0.35, desc="Stage 3/6 — Extracting audio")
            wav_path = stage3_audio.run(video_path, cfg)

        progress(0.45, desc="Stage 4/6 — Transcribing with Whisper (this may take a while…)")
        segments = stage4_stt.run(wav_path, cfg)

        progress(0.82, desc="Stage 5/6 — Matching timestamps")
        matched = stage5_match.run(slides, segments)

        progress(0.92, desc="Stage 6/6 — Generating note")
        note_path = stage6_export.run(matched, cfg, stem=stem)

        progress(1.00, desc="Done!")

        out_dir = cfg["paths"]["output_dir"]
        transcript_path = os.path.join(out_dir, f"{stem}-transcript.txt")
        msg = t("done_msg", lang).format(
            slides=len(slides), segs=len(segments),
            note=note_path, pdf=pdf_path,
            transcript=transcript_path, slides_dir=out_dir,
        )
        return msg, note_path, pdf_path, transcript_path
    except Exception as e:
        return t("error_prefix", lang) + str(e), None, None, None


def build_ui() -> gr.Blocks:
    cfg = load_config() if os.path.isfile("config.yaml") else {}
    sd = cfg.get("slide_detection", {})
    default_threshold = sd.get("slide_change_threshold", 0.90)
    default_ssim = sd.get("ssim_merge_threshold", 0.85)
    default_fmt = cfg.get("export", {}).get("format", "html")
    default_whisper = "Auto-detect"

    with gr.Blocks(title="SlideScribe") as demo:
        # ── UI language toggle (top-right) ───────────────────────────
        with gr.Row():
            gr.Markdown("## SlideScribe")
            ui_lang = gr.Radio(
                choices=["한국어", "English"],
                value="한국어",
                label="UI Language",
                scale=0,
            )

        title_md   = gr.Markdown(t("subtitle", "ko"))

        with gr.Row():
            with gr.Column(scale=2):
                video_input = gr.File(
                    label=t("upload_label", "ko"),
                    file_types=[
                        ".mp4", ".avi", ".mkv", ".mov", ".webm",   # video
                        ".mp3", ".wav", ".m4a", ".aac", ".flac",   # audio
                    ],
                )
                fmt_radio = gr.Radio(
                    choices=["html", "pdf", "markdown"],
                    value=default_fmt,
                    label=t("format_label", "ko"),
                )
                whisper_dd = gr.Dropdown(
                    choices=WHISPER_DISPLAY_NAMES,
                    value=default_whisper,
                    label=t("whisper_label", "ko"),
                )

            with gr.Column(scale=1):
                params_md = gr.Markdown(t("params_header", "ko"))
                scene_slider = gr.Slider(
                    minimum=0.70, maximum=0.99, step=0.01,
                    value=default_threshold,
                    label=t("threshold_label", "ko"),
                )
                ssim_slider = gr.Slider(
                    minimum=0.5, maximum=1.0, step=0.01,
                    value=default_ssim,
                    label=t("merge_label", "ko"),
                )

        run_btn = gr.Button(t("run_btn", "ko"), variant="primary")
        status_box = gr.Textbox(label=t("status_label", "ko"), lines=4, interactive=False)

        with gr.Row():
            note_out       = gr.File(label=t("note_label", "ko"))
            pdf_out        = gr.File(label=t("pdf_label", "ko"))
            transcript_out = gr.File(label=t("transcript_label", "ko"))

        # ── UI language switch updates all labels ────────────────────
        def _switch_lang(lang_choice):
            lang = "en" if lang_choice == "English" else "ko"
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
                gr.update(label=t("note_label", lang)),
                gr.update(label=t("pdf_label", lang)),
                gr.update(label=t("transcript_label", lang)),
            )

        ui_lang.change(
            fn=_switch_lang,
            inputs=[ui_lang],
            outputs=[
                title_md, video_input, fmt_radio, whisper_dd,
                params_md, scene_slider, ssim_slider,
                run_btn, status_box, note_out, pdf_out, transcript_out,
            ],
        )

        run_btn.click(
            fn=_run_for_gradio,
            inputs=[video_input, fmt_radio, scene_slider, ssim_slider, whisper_dd, ui_lang],
            outputs=[status_box, note_out, pdf_out, transcript_out],
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
