# SlideScribe — Windows 설치본 빌드 가이드

소스 코드를 받아 직접 `python app.py` 로 실행하는 대신, **`SlideScribe-Setup-x.y.z.exe`** 한 개로 일반 윈도우 프로그램처럼 설치할 수 있도록 만드는 방법.

## 자동 빌드 (권장) — GitHub Actions

태그를 푸시하기만 하면 GitHub Actions 가 Windows 러너에서 자동으로 빌드하고 **Releases 페이지에 `.exe` 를 첨부**합니다.

```bash
# 로컬에서:
git tag v0.3.0
git push origin v0.3.0
```

푸시되면 `.github/workflows/release.yml` 이 트리거되어:
1. Windows 러너에서 Python · 의존성 · ffmpeg · Inno Setup 자동 설치
2. PyInstaller + Inno Setup 으로 `SlideScribe-Setup-0.3.0.exe` 빌드
3. `https://github.com/YMJ-02/SlideScribe/releases` 에 자동 게시 (한국어 설치 안내문 포함)

태그 없이 테스트하려면: Actions 탭 → **Build & Release** → **Run workflow** (`version_override` 입력). Release 는 안 만들고 Actions 의 artifact 로만 올라옴.

---

## 로컬 빌드 (대안)

최종 산출물:
- `dist/SlideScribe/SlideScribe.exe` — 폴더 통째로 복사해서 실행 가능한 portable 버전
- `dist/installer/SlideScribe-Setup-0.3.0.exe` — 설치 마법사 (Start Menu/Desktop 단축아이콘 + 제거 등록)

## 사전 준비

- Windows 10/11 64-bit
- **Python 3.10 ~ 3.13** + 프로젝트 의존성:
  ```cmd
  pip install -r requirements.txt
  pip install pyinstaller
  ```
- (설치 마법사를 만들려면) [Inno Setup 6](https://jrsoftware.org/isdl.php) — 설치 후 `iscc` 가 PATH 에 등록되어야 함

### (강력 권장) 번들 안에 함께 넣을 것들

| 파일 | 위치 | 설명 |
|---|---|---|
| `ffmpeg.exe` | `build/bin/ffmpeg.exe` | [Gyan ffmpeg release](https://www.gyan.dev/ffmpeg/builds/) 에서 `ffmpeg-release-essentials.zip` 받은 후 안에 들어있는 `bin/ffmpeg.exe` 만 복사. 없으면 사용자가 직접 ffmpeg 를 설치해야 한다. |
| `icon.ico` | `build/icon.ico` | 256×256 .ico (없으면 기본 파이썬 아이콘) |

## 빌드

저장소 루트에서:

```cmd
build\build.bat
```

스크립트가 자동으로:
1. PyInstaller 설치 여부 확인 (없으면 설치)
2. 이전 빌드 결과 삭제
3. `build/slidescribe.spec` 로 PyInstaller 실행 (수 분 소요)
4. `dist/SlideScribe/` 폴더에 결과 출력

수동으로 실행하려면:
```cmd
pyinstaller build\slidescribe.spec --clean --noconfirm
```

## 설치 마법사 만들기

```cmd
iscc build\installer.iss
```

결과: `dist\installer\SlideScribe-Setup-0.3.0.exe`

## 빌드 산출물 구조

```
dist/SlideScribe/
├── SlideScribe.exe            ← 사용자가 더블클릭하는 진입점
├── web/                       ← visionOS SPA (HTML/CSS/JS)
├── stages/                    ← 파이프라인 모듈
├── config.yaml                ← 기본 설정 (첫 실행 시 사용자 폴더로 복사)
├── bin/ffmpeg.exe             ← (있을 때만) 번들 ffmpeg
├── _internal/                 ← Python 런타임 + 의존성 DLL
└── …
```

## 사용자 데이터 위치

설치 후 프로그램은 `C:\Program Files\SlideScribe\` 에 있지만, 사용자별 데이터는 다음 위치에 저장됩니다:

```
%LOCALAPPDATA%\SlideScribe\
├── config.yaml                ← 첫 실행 시 자동 생성된 사용자 편집 가능 설정
├── output/                    ← 생성된 노트 / PDF / transcript
└── .tmp/                      ← 슬라이드 프레임 / 오디오 임시 파일
```

제거 시 프로그램 파일은 지워지지만 위 폴더는 **보존**됩니다. 완전히 지우려면 수동으로 삭제하세요.

## 빌드/설치 사이즈

| 구성 | 대략 크기 |
|---|---|
| PyInstaller 결과 (`dist/SlideScribe/`) | 700 MB ~ 1.2 GB |
| Inno Setup 설치 마법사 (.exe) | 300 ~ 500 MB (lzma2/ultra 압축) |
| 설치 후 디스크 사용 | 700 MB ~ 1.2 GB |
| **Whisper large-v3 모델 (첫 실행 시 다운로드)** | + 약 1.5 GB → `%USERPROFILE%\.cache\huggingface\` |

## 제외된 것 (의도적)

- **TensorFlow + PyKoSpacing**: PyKoSpacing 이 TensorFlow ~500 MB+ 를 끌고 들어와 설치본을 비대하게 만듦. 번들에서는 비활성. Whisper 자체의 한국어 인식은 그대로 동작하지만, 띄어쓰기 후처리는 적용되지 않음. (소스로 직접 실행할 때만 사용)
- **Whisper 모델 가중치**: 첫 전사 시 자동 다운로드 (~1.5 GB). 인터넷 필요.

## GPU (CUDA) 지원

빌드 시 `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12` 가 설치되어 있으면 spec 이 해당 DLL 들을 자동으로 번들에 포함합니다. 사용자 PC 에 별도로 CUDA Toolkit 을 깔지 않아도 RTX 시리즈에서 바로 GPU 모드로 동작.

CUDA 가 없거나 호환되지 않는 GPU 면 `stages/stage4_stt.py` 가 알아서 CPU/int8 로 fallback 합니다.

## 트러블슈팅

- **빌드는 성공했는데 실행하면 `ImportError`** → `slidescribe.spec` 의 `hiddenimports` 에 누락된 모듈을 추가하고 다시 빌드.
- **`ffmpeg not found`** 오류 → `build/bin/ffmpeg.exe` 를 넣지 않았거나, 사용자 PC PATH 에도 ffmpeg 가 없는 경우.
- **Python 3.13 으로 빌드 실패** → PyInstaller 6.10 이상이 필요. `pip install -U pyinstaller`.
- **첫 실행 시 Whisper 모델 다운로드가 멈춤** → HuggingFace 가 차단되었거나 회사 망에서 자주 발생. `HF_ENDPOINT` 환경변수로 미러를 설정하거나 사전 다운로드.

## 배포 흐름 요약

```
빌드 (개발자 PC, 1회)
  build\build.bat                → dist\SlideScribe\
  iscc build\installer.iss       → dist\installer\SlideScribe-Setup-0.3.0.exe

배포 (Setup.exe 공유)
  사용자가 Setup.exe 실행
  → 자동으로 Program Files 에 설치
  → Start Menu / Desktop 단축아이콘 생성
  → 더블클릭 → 콘솔 창 + 자동으로 브라우저 열림 → 사용
```
