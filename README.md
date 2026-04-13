<div align="center">

# 🎓 SlideScribe

**Turn any lecture video into a structured, readable note — automatically.**

[![version](https://img.shields.io/badge/version-0.1.1-blue?style=flat-square)](https://github.com/YMJ-02/SlideScribe/releases)
[![license](https://img.shields.io/github/license/YMJ-02/SlideScribe?style=flat-square&color=green)](https://github.com/YMJ-02/SlideScribe/blob/master/LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/YMJ-02/SlideScribe/ci.yml?branch=master&style=flat-square&label=CI&logo=github-actions&logoColor=white)](https://github.com/YMJ-02/SlideScribe/actions/workflows/ci.yml)

</div>

---

Most tools give you a raw transcript. SlideScribe gives you a structured note — each slide paired with what was actually said about it.

Drop in a lecture video. Get back a paginated document with every slide matched to its spoken content, ready to read or export.

---

## Example Note Preview

![Example Note Preview](docs/preview.png)

---

## How It Works

```
Video / Audio file
  ↓
  Slide segmentation (SSIM-based)   ← skipped for audio-only input
  ↓
  Audio extraction + Whisper STT
  ↓
  Timestamp matching (slide ↔ transcript)
  ↓
  Export → HTML / PDF / Markdown
```

---

## Project Structure

```
SlideScribe/
├── app.py              # Gradio web UI entry point
├── run.py              # CLI entry point
├── install.bat         # Windows one-click setup script
├── config.yaml         # Configuration file
├── i18n.py             # UI language strings (EN / KO)
├── requirements.txt    # Python dependencies
├── stages/             # Pipeline stages (1–6)
│   ├── stage1_segment.py
│   ├── stage2_pdf.py
│   ├── stage3_audio.py
│   ├── stage4_stt.py
│   ├── stage5_match.py
│   └── stage6_export.py
└── output/             # Generated outputs (created at runtime)
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

### Clone and install

**Windows (recommended)**
```bat
git clone https://github.com/YMJ-02/SlideScribe.git
cd SlideScribe
install.bat
```
`install.bat` installs all Python dependencies, CUDA libraries, and registers DLL paths automatically.

**macOS / Linux**
```bash
git clone https://github.com/YMJ-02/SlideScribe.git
cd SlideScribe
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

1. Upload one or more video/audio files (`.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`, `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`)
2. Choose output format (`html`, `pdf`, `markdown`)
3. Select Whisper language or leave on Auto-detect
4. Adjust slide detection parameters if needed
5. Click **Generate Note**
6. Download the ZIP containing notes, slide PDFs, and transcripts

### Option B — CLI

```bash
# Single file
python run.py lecture.mp4

# Multiple files
python run.py lecture1.mp4 lecture2.mp4 lecture3.mp4

# With options
python run.py lecture.mp4 --format markdown
python run.py lecture.mp4 --config my_config.yaml --format pdf
```

### Gradio public link (for sharing / demo)

```bash
python app.py --share
# → Running on public URL: https://xxxx.gradio.live
```

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
  language: "auto"               # Language code or "auto" for auto-detect
  batch_size: 8                  # Chunks processed per GPU batch (lower if VRAM is limited)

export:
  format: "html"                 # Output format: html | pdf | markdown
  embed_images: true             # Embed slide images as base64 in HTML

paths:
  output_dir: "output"
  tmp_dir: ".tmp"
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Developer

| Item | Detail |
|------|--------|
| GitHub | [@YMJ-02](https://github.com/YMJ-02) |
| Repository | https://github.com/YMJ-02/SlideScribe |

---

## Bug Reports

Open an issue at https://github.com/YMJ-02/SlideScribe/issues.

When reporting a bug, include:
- OS and Python version
- GPU model (or CPU-only flag)
- The exact command or UI steps used
- Full error traceback from the terminal

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
|---------|------|---------|
| 0.1.1 | 2026-04-13 | Auto CUDA PATH injection, `install.bat`, batch processing, audio input, UI language toggle (EN/KO), Whisper language selector, progress display, `--share` flag |
| 0.1.0 | 2026-04-12 | Initial release. 6-stage pipeline. Gradio UI + CLI. |

---

## FAQ

**Q. The program crashes immediately with `No module named 'cv2'`.**  
A. Run `pip install -r requirements.txt` again. If it still fails, try `pip install opencv-python-headless`.

**Q. `Library cublas64_12.dll is not found` error on Windows.**  
A. Run `install.bat` — it installs CUDA libraries and registers DLL paths automatically. If you installed manually, run `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`.

**Q. Whisper model download takes too long or fails.**  
A. `faster-whisper` downloads the model on first run (~1–3 GB). A stable internet connection is required. The model is cached after the first download. On Windows, enabling Developer Mode fixes symlink-related cache issues.

**Q. Running on CPU is extremely slow.**  
A. Set `model_name: "small"` or `"base"` in `config.yaml` and set `compute_type: "int8"`.

**Q. `ffmpeg` not found error.**  
A. Install `ffmpeg` and ensure it is in your system `PATH`. Verify with `ffmpeg -version` in a terminal.

**Q. Output note is empty or has very few segments.**  
A. Lower `slide_change_threshold` (e.g., `0.80`) and `min_slide_sec` (e.g., `1.0`). Also verify the video has audible speech.

**Q. CUDA out of memory.**  
A. Lower `batch_size` in `config.yaml` (e.g., `4`), or use a smaller model (`medium` or `small`), or switch to `device: "cpu"`.

---

# 🎓 SlideScribe (한국어)

대부분의 도구는 원시 트랜스크립트를 낸다. SlideScribe는 구조화된 노트를 낸다 — 각 슬라이드에 실제로 한 말이 매칭된 형태로.

강의 영상을 넣으면 슬라이드마다 트랜스크립트가 연결된 페이지 형태의 노트가 자동으로 만들어집니다.

---

## 작동 방식

```
영상 / 오디오 파일
  ↓
  슬라이드 세그멘테이션 (SSIM 기반)   ← 오디오 입력 시 생략
  ↓
  오디오 추출 + Whisper STT
  ↓
  타임스탬프 매칭 (슬라이드 ↔ 트랜스크립트)
  ↓
  내보내기 → HTML / PDF / Markdown
```

---

## 설치 방법

### 요구 사항

- Python 3.10 이상
- NVIDIA GPU 권장 — `faster-whisper` GPU 모드에는 CUDA 11.8 이상 필요
- CPU 전용도 가능하나 STT 처리 속도가 매우 느림
- `ffmpeg` 설치 후 PATH에 등록 필요

### Windows (원클릭 설치)

```bat
git clone https://github.com/YMJ-02/SlideScribe.git
cd SlideScribe
install.bat
```

`install.bat`이 Python 패키지, CUDA 라이브러리, DLL 경로를 자동으로 설치합니다.

### macOS / Linux

```bash
git clone https://github.com/YMJ-02/SlideScribe.git
cd SlideScribe
pip install -r requirements.txt
```

---

## 사용법

### 방법 A — Gradio 웹 UI

```bash
python app.py
```

브라우저에서 `http://localhost:7860` 접속.

1. 영상/오디오 파일 업로드 (여러 개 동시 가능)
2. 출력 포맷 선택
3. Whisper 언어 선택 (기본: 자동 감지)
4. **Generate Note** 클릭
5. ZIP 파일로 노트, 슬라이드 PDF, 트랜스크립트 다운로드

### 방법 B — CLI

```bash
python run.py lecture.mp4
python run.py lecture1.mp4 lecture2.mp4 lecture3.mp4
python run.py lecture.mp4 --format markdown
```

---

## 버전 및 업데이트 정보

| 버전 | 날짜 | 내용 |
|------|------|------|
| 0.1.1 | 2026-04-13 | CUDA 자동 PATH 주입, `install.bat`, 배치 처리, 오디오 입력, UI 언어 토글, Whisper 언어 선택, 진행률 표시, `--share` 플래그 |
| 0.1.0 | 2026-04-12 | 최초 릴리즈. 6단계 파이프라인. Gradio UI + CLI. |

---

## FAQ

**Q. `Library cublas64_12.dll is not found` 오류.**  
A. `install.bat` 실행 — CUDA 라이브러리 설치 및 DLL 경로를 자동 등록합니다. 수동 설치 시 `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`.

**Q. Whisper 모델 다운로드가 너무 오래 걸리거나 0%에서 멈춰 있음.**  
A. Windows에서 `개인 정보 및 보안 → 개발자용 → 개발자 모드 ON` 후 재부팅하면 심볼릭 링크 문제가 해결됩니다.

**Q. CUDA out of memory 오류.**  
A. `config.yaml`에서 `batch_size` 낙추기 (예: `4`), 또는 더 작은 모델 (`medium`/`small`) 사용.

**Q. 실행하자마자 `No module named 'cv2'` 오류.**  
A. `pip install -r requirements.txt` 다시 실행. 실패 시 `pip install opencv-python-headless`.

**Q. `ffmpeg` not found 오류.**  
A. `ffmpeg` 설치 후 PATH 등록. `ffmpeg -version`으로 확인.

**Q. 출력 노트가 비어있거나 세그먼트가 거의 없음.**  
A. `slide_change_threshold` 낙추기 (예: `0.80`), `min_slide_sec` 줄이기 (예: `1.0`).
