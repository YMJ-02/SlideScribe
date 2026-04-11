# lecture-note-gen

## 스택
Python 3.11+, faster-whisper, opencv-python-headless, scenedetect, scikit-image, fpdf2, Gradio

## 환경
- GPU: RTX 2070 (VRAM 8GB), CUDA 필수
- 시스템 의존성: ffmpeg (PATH 등록 필요)
- 패키지 매니저: pip + requirements.txt

## 구조
- `stages/`     파이프라인 Stage 1~6 모듈
- `app.py`      Gradio UI 진입점
- `run.py`      CLI 진입점
- `config.yaml` 파라미터 (SSIM threshold, 모델명 등)
- `output/`     생성된 노트 저장

## 명령어
```
pip install -r requirements.txt   # 의존성 설치
python app.py                     # UI 실행 (localhost)
python run.py <video_path>        # CLI 실행
```

## 문서
상세 가이드는 `agent_docs/` 참조
