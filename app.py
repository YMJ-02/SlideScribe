"""Gradio UI 진입점: python app.py

localhost에서 강의 노트 생성 UI 실행.
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
) -> tuple[str, str, str]:
    """Gradio 버튼 클릭 핸들러.

    Returns:
        (상태 메시지, 강의노트 파일 경로, 슬라이드PDF 파일 경로)
    """
    if video_file is None:
        return "영상 파일을 업로드해 주세요.", None, None

    # gr.File은 버전에 따라 경로 문자열 또는 객체를 반환
    video_path = video_file if isinstance(video_file, str) else video_file.name

    cfg = load_config()
    cfg["export"]["format"] = fmt
    cfg["slide_detection"]["slide_change_threshold"] = scene_threshold
    cfg["slide_detection"]["ssim_merge_threshold"] = ssim_threshold

    try:
        results = run_pipeline(video_path, cfg)
        note_path = results["note"]
        pdf_path = results["slides_pdf"]
        slides_n = len(results["slides"])
        segs_n = len(results["segments"])
        import os
        out_dir = cfg["paths"]["output_dir"]
        transcript_path = os.path.join(out_dir, "transcript.txt")
        msg = (
            f"완료!  슬라이드 {slides_n}개 / STT 세그먼트 {segs_n}개\n"
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

    with gr.Blocks(title="lecture-note-gen") as demo:
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
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
