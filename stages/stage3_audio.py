"""Stage 3: 오디오 추출

ffmpeg로 영상에서 16kHz mono WAV 추출.
faster-whisper 입력 포맷에 맞춤.

입력: video_path: str
출력: str  — WAV 파일 경로 (.tmp/audio.wav)
"""

import os
import shutil
import subprocess
import yaml
from pathlib import Path

# winget / choco / scoop 등 패키지 매니저가 설치하는 일반적인 ffmpeg 위치
_FFMPEG_SEARCH_DIRS = [
    # winget (Gyan.FFmpeg)
    Path.home() / "AppData/Local/Microsoft/WinGet/Packages",
    # Chocolatey
    Path("C:/ProgramData/chocolatey/bin"),
    # Scoop
    Path.home() / "scoop/shims",
    Path.home() / "scoop/apps/ffmpeg/current/bin",
    # 직접 설치 관례 경로
    Path("C:/ffmpeg/bin"),
    Path("C:/Program Files/ffmpeg/bin"),
]


def _find_ffmpeg() -> str:
    """ffmpeg 실행 파일 경로 탐색. 우선순위: PATH → 알려진 설치 경로."""
    # 1) 현재 PATH에서 탐색
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 2) 알려진 디렉터리에서 직접 탐색
    for base in _FFMPEG_SEARCH_DIRS:
        if not base.exists():
            continue
        # winget은 패키지명 하위에 bin/ffmpeg.exe 구조
        for candidate in base.rglob("ffmpeg.exe"):
            return str(candidate)

    raise RuntimeError(
        "ffmpeg를 찾을 수 없습니다.\n"
        "설치: winget install Gyan.FFmpeg  (또는 https://ffmpeg.org/download.html)\n"
        "설치 후 새 터미널에서 실행하거나, PATH에 ffmpeg bin 폴더를 등록하세요."
    )


def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(video_path: str, cfg: dict | None = None) -> str:
    """영상에서 16kHz mono WAV 추출.

    Args:
        video_path: 입력 영상 경로
        cfg:        config.yaml dict

    Returns:
        WAV 파일 경로
    """
    if cfg is None:
        cfg = _load_config()

    tmp_dir: str = cfg["paths"]["tmp_dir"]
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    wav_path = os.path.join(tmp_dir, "audio.wav")
    ffmpeg = _find_ffmpeg()
    print(f"[Stage 3] 오디오 추출 중: {video_path}  (ffmpeg: {ffmpeg})")

    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vn",           # 영상 트랙 제외
        "-ac", "1",      # mono
        "-ar", "16000",  # 16kHz (Whisper 최적)
        "-f", "wav",
        wav_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"[Stage 3] ffmpeg 오류:\n{err}")

    size_mb = os.path.getsize(wav_path) / (1024 ** 2)
    print(f"[Stage 3] 추출 완료: {wav_path}  ({size_mb:.1f} MB)")
    return wav_path


# ── 단독 실행 테스트 ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python stage3_audio.py <video_path> [config_path]")
        sys.exit(1)

    video = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    wav = run(video, cfg)
    print(f"\nWAV 경로: {wav}")
