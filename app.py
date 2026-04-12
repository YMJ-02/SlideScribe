"""Gradio UI entry point: python app.py

Runs the SlideScribe note generation UI on localhost.
"""

import os
import sys
import yaml
import gradio as gr

from run import load_config, run_pipeline


def _run_for_gradio(
    video_file,
    fmt: str,
    scene_threshold: float,
    ssim_threshold: float,
    progress=gr.Progress(track_tqdm=True),
) -> tuple[str, str, str, str]:
    """Gradio button click handler.

    Returns:
        (status message, note file path, slide PDF path, transcript path)
    """
    if video_file is None:
        return "영상 파일을 업로드해 주세요.", None, None, None

    video_path = video_file if isinstance(video_file, str) else video_file.name

    cfg = load_config()
    cfg["export"]["format"] = fmt
    cfg["slide_detection"]["slide_change_threshold"] = scene_threshold
    cfg["slide_detection"]["ssim_merge_threshold"] = ssim_threshold

    try:
        from stages import stage1_segment, stage2_pdf, stage3_audio
        from stages import stage4_stt, stage5_match, stage6_export

        progress(0.00, desc="Starting…")

        progress(0.05, desc="Stage 1/6 — Detecting slide transitions")
        slides = stage1_segment.run(video_path, cfg)

        progress(0.25, desc="Stage 2/6 — Exporting slide PDF")
        pdf_path = stage2_pdf.run(slides, cfg)

        progress(0.35, desc="Stage 3/6 — Extracting audio")
        wav_path = stage3_audio.run(video_path, cfg)

        progress(0.45, desc="Stage 4/6 — Transcribing with Whisper (this may take a while…)")
        segments = stage4_stt.run(wav_path, cfg)

        progress(0.82, desc="Stage 5/6 — Matching timestamps")
        matched = stage5_match.run(slides, segments)

        progress(0.92, desc="Stage 6/6 — Generating note")
        note_path = stage6_export.run(matched, cfg)

        progress(1.00, desc="Done!")

        out_dir = cfg["paths"]["output_dir"]
        transcript_path = os.path.join(out_dir, "transcript.txt")
        msg = (
            f"완료!  슬라이드 {len(slides)}개 / STT 세그먼트 {len(segments)}개\n"
            f"강의 노트: {note_path}\n"
            f"슬라이드 PDF: {pdf_path}\n"
            f"트랜스크립트: {transcript_path}  |  슬라이드 이미지: {out_dir}/slides/"
        )
        return msg, note_path, pdf_path, transcript_path
    except Exception as e:
        return f"오류 발생:\n{e}", None, None, None


def build_ui() -> gr.Blocks:
    cfg = load_config() if os.path.isfile("config.yaml") else {}
    sd = cfg.get("slide_detection", {})
    default_threshold = sd.get("slide_change_threshold", 0.90)
    default_ssim = sd.get("ssim_merge_threshold", 0.85)
    default_fmt = cfg.get("export", {}).get("format", "html")

    with gr.Blocks(title="SlideScribe") as demo:
        gr.Markdown("# 강의 노트 자동 생성\n영상을 업로드하면 슬라이드 세그멘테이션 + STT → 강의 노트를 생성합니다.")

        with gr.Row():
            with gr.Column(scale=2):
                video_input = gr.File(
                    label="강의 영상 업로드",
                    file_types=[".mp4", ".avi", ".mkv", ".mov", ".webm"],
                )
                fmt_radio = gr.Radio(
                    choices=["html", "pdf", "markdown"],
                    value=default_fmt,
                    label="출력 포맷",
                )

            with gr.Column(scale=1):
                gr.Markdown("### 슬라이드 감지 파라미터")
                scene_slider = gr.Slider(
                    minimum=0.70, maximum=0.99, step=0.01,
                    value=default_threshold,
                    label="슬라이드 전환 감도 (낮을수록 더 많이 감지)",
                )
                ssim_slider = gr.Slider(
                    minimum=0.5, maximum=1.0, step=0.01,
                    value=default_ssim,
                    label="ssim_merge_threshold (높을수록 적극 병합)",
                )

        run_btn = gr.Button("노트 생성 시작", variant="primary")

        status_box = gr.Textbox(label="진행 상황 / 결과", lines=4, interactive=False)

        with gr.Row():
            note_out       = gr.File(label="강의 노트 다운로드")
            pdf_out        = gr.File(label="슬라이드 PDF 다운로드")
            transcript_out = gr.File(label="트랜스크립트 다운로드 (transcript.txt)")

        run_btn.click(
            fn=_run_for_gradio,
            inputs=[video_input, fmt_radio, scene_slider, ssim_slider],
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
