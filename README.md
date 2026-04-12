# lecture-note-gen

Automatically generates lecture notes from a video file.
Detects slide transitions, transcribes audio via Whisper, and exports a structured note document.

---

## Project Structure

```
lecture-note/
├── app.py              # Gradio web UI entry point
├── run.py              # CLI entry point
├── config.yaml         # Configuration file
├── requirements.txt    # Python dependencies
├── stages/             # Pipeline stages (1–6)
│   ├── stage1_segment.py   # Slide segmentation (SSIM)
│   ├── stage2_pdf.py       # Slide PDF export
│   ├── stage3_audio.py     # Audio extraction
│   ├── stage4_stt.py       # Whisper STT
│   ├── stage5_match.py     # Timestamp matching
│   └── stage6_export.py    # Note generation
├── agent_docs/         # Internal agent documentation
└── output/             # Generated outputs (created at runtime)
```

**Pipeline flow:**

```
Stage 1 (Segmentation)
├─ Stage 2 (Slide PDF)
└─ Stage 3 (Audio Extraction)
     └─ Stage 4 (Whisper STT)
          └─ Stage 5 (Timestamp Matching)
               └─ Stage 6 (Note Export)
```

---

## Installation

### Requirements

- Python 3.10 or later
- NVIDIA GPU (recommended) — CUDA 11.8+ for `faster-whisper` GPU mode
- CPU-only is supported but significantly slower for STT
- `ffmpeg` must be installed and available in `PATH`

### Install ffmpeg

**Windows**
```
winget install ffmpeg
```
or download from https://ffmpeg.org/download.html and add to PATH manually.

**macOS**
```
brew install ffmpeg
```

**Linux (Ubuntu/Debian)**
```
sudo apt install ffmpeg
```

### Clone and install Python dependencies

```bash
git clone https://github.com/YMJ-02/lecture-note.git
cd lecture-note
pip install -r requirements.txt
```

> If you do not have a GPU, edit `config.yaml` before running:
> ```yaml
> stt:
>   device: "cpu"
>   compute_type: "int8"
> ```

---

## Usage

### Option A — Gradio Web UI

```bash
python app.py
```

Open `http://localhost:7860` in a browser.

1. Upload a video file (`.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`)
2. Choose an output format (`html`, `pdf`, `markdown`)
3. Adjust slide detection parameters if needed
4. Click **노트 생성 시작**
5. Download the generated note, slide PDF, and transcript

### Option B — CLI

```bash
python run.py <video_path>
```

Examples:
```bash
python run.py lecture.mp4
python run.py lecture.mp4 --format markdown
python run.py lecture.mp4 --config my_config.yaml --format pdf
```

Output files are written to `output/` by default.

### config.yaml reference

```yaml
slide_detection:
  slide_change_threshold: 0.90   # Lower = detects more transitions
  ssim_merge_threshold: 0.85     # Higher = merges more adjacent slides
  frame_sample_rate: 1           # Frames sampled per second
  min_slide_sec: 3.0             # Minimum slide duration in seconds

stt:
  model_name: "large-v3"         # Whisper model size (tiny/base/small/medium/large-v3)
  device: "cuda"                 # "cuda" or "cpu"
  compute_type: "float16"        # "float16" (GPU) or "int8" (CPU)
  language: "ko"                 # Language code

export:
  format: "html"                 # Output format: html | pdf | markdown
  embed_images: true             # Embed slide images as base64 in HTML

paths:
  output_dir: "output"
  tmp_dir: ".tmp"
```

---

## License

MIT License.

```
Copyright (c) 2026 YMJ-02

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## Developer

| Item | Detail |
|------|--------|
| GitHub | [@YMJ-02](https://github.com/YMJ-02) |
| Repository | https://github.com/YMJ-02/lecture-note |

---

## Bug Reports

Open an issue at https://github.com/YMJ-02/lecture-note/issues.

When reporting a bug, include:
- OS and Python version
- GPU model (or CPU-only flag)
- The exact command or UI steps used
- Full error traceback from the terminal

Common issues and fixes are listed in the FAQ section below.

---

## References

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2-based Whisper inference
- [OpenAI Whisper](https://github.com/openai/whisper) — Original Whisper model
- [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) — Scene/slide transition detection
- [scikit-image](https://scikit-image.org/) — SSIM computation
- [Gradio](https://www.gradio.app/) — Web UI framework
- [fpdf2](https://py-fpdf2.readthedocs.io/) — PDF generation

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 0.1.0 | 2026 | Initial local release. 6-stage pipeline. Gradio UI + CLI. |

---

## FAQ

**Q. The program crashes immediately with `No module named 'cv2'`.**  
A. Run `pip install -r requirements.txt` again. If it still fails, try `pip install opencv-python-headless`.

**Q. Whisper model download takes too long or fails.**  
A. `faster-whisper` downloads the model on first run (~1–3 GB depending on model size). A stable internet connection is required. The model is cached after the first download.

**Q. Running on CPU is extremely slow.**  
A. Set `model_name: "small"` or `"base"` in `config.yaml` and set `compute_type: "int8"`. Larger models on CPU are not practical for long videos.

**Q. `ffmpeg` not found error.**  
A. Install `ffmpeg` and ensure it is in your system `PATH`. Verify with `ffmpeg -version` in a terminal.

**Q. Output note is empty or has very few segments.**  
A. Lower `slide_change_threshold` (e.g., `0.80`) and `min_slide_sec` (e.g., `1.0`) in `config.yaml`. Also verify the video has audible speech.

**Q. CUDA out of memory.**  
A. Use a smaller model (`medium` or `small`) or switch to `device: "cpu"` with `compute_type: "int8"`.

---

---

# lecture-note-gen (한국어)

강의 영상에서 강의 노트를 자동으로 생성합니다.
슬라이드 전환 감지 → Whisper 음성 인식 → 구조화된 노트 문서 출력.

---

## 프로젝트 구성

```
lecture-note/
├── app.py              # Gradio 웹 UI 진입점
├── run.py              # CLI 진입점
├── config.yaml         # 설정 파일
├── requirements.txt    # Python 의존성 목록
├── stages/             # 파이프라인 단계 (1–6)
│   ├── stage1_segment.py   # 슬라이드 세그멘테이션 (SSIM)
│   ├── stage2_pdf.py       # 슬라이드 PDF 생성
│   ├── stage3_audio.py     # 오디오 추출
│   ├── stage4_stt.py       # Whisper STT
│   ├── stage5_match.py     # 타임스탬프 매칭
│   └── stage6_export.py    # 노트 생성
├── agent_docs/         # 내부 문서
└── output/             # 생성된 결과물 (실행 시 자동 생성)
```

**파이프라인 흐름:**

```
Stage 1 (세그멘테이션)
├─ Stage 2 (슬라이드 PDF)
└─ Stage 3 (오디오 추출)
     └─ Stage 4 (Whisper STT)
          └─ Stage 5 (타임스탬프 매칭)
               └─ Stage 6 (노트 생성)
```

---

## 설치 방법

### 요구 사항

- Python 3.10 이상
- NVIDIA GPU 권장 — `faster-whisper` GPU 모드에는 CUDA 11.8 이상 필요
- CPU 전용도 가능하나 STT 처리 속도가 매우 느림
- `ffmpeg` 설치 후 PATH에 등록 필요

### ffmpeg 설치

**Windows**
```
winget install ffmpeg
```

또는 https://ffmpeg.org/download.html 에서 다운로드 후 PATH에 수동 등록.

**macOS**
```
brew install ffmpeg
```

**Linux (Ubuntu/Debian)**
```
sudo apt install ffmpeg
```

### 저장소 클론 및 Python 패키지 설치

```bash
git clone https://github.com/YMJ-02/lecture-note.git
cd lecture-note
pip install -r requirements.txt
```

> GPU가 없는 경우, 실행 전에 `config.yaml`을 수정:
> ```yaml
> stt:
>   device: "cpu"
>   compute_type: "int8"
> ```

---

## 사용법

### 방법 A — Gradio 웹 UI

```bash
python app.py
```

브라우저에서 `http://localhost:7860` 접속.

1. 영상 파일 업로드 (`.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`)
2. 출력 포맷 선택 (`html`, `pdf`, `markdown`)
3. 필요 시 슬라이드 감지 파라미터 조정
4. **노트 생성 시작** 버튼 클릭
5. 강의 노트, 슬라이드 PDF, 트랜스크립트 다운로드

### 방법 B — CLI

```bash
python run.py <영상_파일_경로>
```

예시:
```bash
python run.py lecture.mp4
python run.py lecture.mp4 --format markdown
python run.py lecture.mp4 --config my_config.yaml --format pdf
```

결과물은 기본적으로 `output/` 폴더에 저장됨.

### config.yaml 옵션 설명

```yaml
slide_detection:
  slide_change_threshold: 0.90   # 낮을수록 슬라이드 전환을 더 많이 감지
  ssim_merge_threshold: 0.85     # 높을수록 인접 슬라이드를 적극 병합
  frame_sample_rate: 1           # 초당 샘플링 프레임 수
  min_slide_sec: 3.0             # 슬라이드 최소 지속 시간 (초)

stt:
  model_name: "large-v3"         # Whisper 모델 크기 (tiny/base/small/medium/large-v3)
  device: "cuda"                 # "cuda" 또는 "cpu"
  compute_type: "float16"        # GPU: "float16" / CPU: "int8"
  language: "ko"                 # 언어 코드

export:
  format: "html"                 # 출력 포맷: html | pdf | markdown
  embed_images: true             # HTML에 슬라이드 이미지 base64 임베드 여부

paths:
  output_dir: "output"
  tmp_dir: ".tmp"
```

---

## 저작권 및 사용권 정보

MIT 라이선스.

개인적·상업적 용도로 자유롭게 사용, 수정, 배포 가능. 단, 원본 저작권 표시 및 라이선스 고지를 유지해야 함.

---

## 프로그래머 정보

| 항목 | 내용 |
|------|------|
| GitHub | [@YMJ-02](https://github.com/YMJ-02) |
| 저장소 | https://github.com/YMJ-02/lecture-note |

---

## 버그 및 디버그

https://github.com/YMJ-02/lecture-note/issues 에서 이슈를 등록.

버그 보고 시 아래 정보를 포함:
- OS 및 Python 버전
- GPU 모델 (또는 CPU 전용 여부)
- 사용한 명령어 또는 UI 조작 단계
- 터미널 전체 에러 트레이스백

---

## 참고 및 출처

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2 기반 Whisper 추론 엔진
- [OpenAI Whisper](https://github.com/openai/whisper) — 원본 Whisper 모델
- [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) — 장면/슬라이드 전환 감지
- [scikit-image](https://scikit-image.org/) — SSIM 연산
- [Gradio](https://www.gradio.app/) — 웹 UI 프레임워크
- [fpdf2](https://py-fpdf2.readthedocs.io/) — PDF 생성

---

## 버전 및 업데이트 정보

| 버전 | 날짜 | 내용 |
|------|------|------|
| 0.1.0 | 2026 | 최초 로컬 릴리즈. 6단계 파이프라인. Gradio UI + CLI. |

---

## FAQ

**Q. 실행하자마자 `No module named 'cv2'` 오류가 뜸.**  
A. `pip install -r requirements.txt`를 다시 실행. 그래도 실패하면 `pip install opencv-python-headless` 직접 설치.

**Q. Whisper 모델 다운로드가 너무 오래 걸리거나 실패함.**  
A. `faster-whisper`는 첫 실행 시 모델을 자동 다운로드함 (모델 크기에 따라 1–3 GB). 안정적인 인터넷 연결이 필요하며, 이후 실행부터는 캐시에서 로드됨.

**Q. CPU로 실행하면 너무 느림.**  
A. `config.yaml`에서 `model_name: "small"` 또는 `"base"`로 변경하고 `compute_type: "int8"` 설정. 긴 영상에서 CPU로 large 모델 사용은 현실적으로 비실용적.

**Q. `ffmpeg` not found 오류.**  
A. `ffmpeg`를 설치하고 시스템 PATH에 등록. 터미널에서 `ffmpeg -version`으로 확인.

**Q. 출력 노트가 비어있거나 세그먼트가 거의 없음.**  
A. `config.yaml`에서 `slide_change_threshold`를 낮추고 (예: `0.80`), `min_slide_sec`도 줄여볼 것 (예: `1.0`). 영상에 음성이 제대로 녹음되어 있는지도 확인.

**Q. CUDA out of memory 오류.**  
A. 더 작은 모델 (`medium` 또는 `small`) 사용, 또는 `device: "cpu"` + `compute_type: "int8"` 으로 전환.
