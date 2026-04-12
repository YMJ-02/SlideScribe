"""Stage 4: Whisper STT

faster-whisper로 한국어 음성 인식.
RTX 2070 기준: large-v3, float16, batch_size=8 권장.

입력: wav_path: str
출력: list[dict]  — [{"start": 12.3, "end": 18.7, "text": "..."}]
"""

import os
import site
import sys
import yaml

# HuggingFace 캐시 심볼릭 링크 경고 억제 (Windows Developer Mode 미활성 환경)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def _register_cuda_dlls() -> None:
    """pip install nvidia-cublas-cu12 등으로 설치된 CUDA DLL 경로를
    os.environ['PATH'] 앞에 추가해 ctranslate2가 로드할 수 있게 함.
    ctranslate2는 import 시점에 DLL을 로드하므로 최상단에서 호출해야 함.
    비-Windows 또는 nvidia 패키지 미설치 환경에서는 무해하게 종료.
    """
    if sys.platform != "win32":
        return
    extra: list[str] = []
    for sp in site.getsitepackages():
        nvidia_base = os.path.join(sp, "nvidia")
        if not os.path.isdir(nvidia_base):
            continue
        for pkg in os.listdir(nvidia_base):
            bin_dir = os.path.join(nvidia_base, pkg, "bin")
            if os.path.isdir(bin_dir):
                extra.append(bin_dir)
    if extra:
        os.environ["PATH"] = os.pathsep.join(extra) + os.pathsep + os.environ.get("PATH", "")


_register_cuda_dlls()


def _load_model(model_name: str, device: str, compute_type: str):
    """WhisperModel 로드. CUDA 초기화 실패 시 CPU/int8로 자동 fallback."""
    from faster_whisper import WhisperModel

    def _try(dev, ct):
        print(f"[Stage 4] 모델 로딩: {model_name}  device={dev}  compute={ct}")
        return WhisperModel(model_name, device=dev, compute_type=ct)

    if device == "cuda":
        try:
            return _try(device, compute_type)
        except Exception as e:
            # cublas/cuDNN DLL 없거나 CUDA 미지원 환경
            print(f"[Stage 4] CUDA 초기화 실패 ({e.__class__.__name__}: {e})")
            print("[Stage 4] CPU / int8 모드로 fallback합니다 (속도 느림)")
            return _try("cpu", "int8")
    return _try(device, compute_type)


def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(wav_path: str, cfg: dict | None = None) -> list[dict]:
    """Whisper STT 실행.

    batch_size > 1 이면 BatchedInferencePipeline 사용 (속도 향상).
    BatchedInferencePipeline 미지원 환경에서는 자동 fallback.

    Args:
        wav_path: 입력 WAV 파일 경로
        cfg:      config.yaml dict

    Returns:
        segments: list[dict] with keys start, end, text
    """
    if cfg is None:
        cfg = _load_config()

    stt_cfg = cfg["stt"]
    model_name: str = stt_cfg["model_name"]
    device: str = stt_cfg["device"]
    compute_type: str = stt_cfg["compute_type"]
    language_cfg: str = stt_cfg.get("language", "auto")
    # "auto" → None (faster-whisper auto-detect)
    language: str | None = None if language_cfg == "auto" else language_cfg
    beam_size: int = stt_cfg["beam_size"]
    batch_size: int = stt_cfg.get("batch_size", 1)

    from faster_whisper import WhisperModel

    model = _load_model(model_name, device, compute_type)

    transcribe_kwargs = dict(language=language, beam_size=beam_size)

    if batch_size > 1:
        try:
            from faster_whisper import BatchedInferencePipeline
            pipeline = BatchedInferencePipeline(model=model)
            print(f"[Stage 4] BatchedInferencePipeline 사용 (batch_size={batch_size})")
            raw_segments, info = pipeline.transcribe(
                wav_path, batch_size=batch_size, **transcribe_kwargs,
            )
        except (ImportError, TypeError):
            print("[Stage 4] BatchedInferencePipeline 미지원 → 일반 모드로 fallback")
            raw_segments, info = model.transcribe(wav_path, **transcribe_kwargs)
    else:
        raw_segments, info = model.transcribe(wav_path, **transcribe_kwargs)

    print(f"[Stage 4] 감지 언어: {info.language}  (확률 {info.language_probability:.2%})")
    print("[Stage 4] 전사 중...")

    segments: list[dict] = []
    for seg in raw_segments:
        segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
        })

    print(f"[Stage 4] 완료: {len(segments)}개 세그먼트")
    return segments


# ── 단독 실행 테스트 ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python stage4_stt.py <wav_path> [config_path]")
        sys.exit(1)

    wav = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    result = run(wav, cfg)

    print(f"\n{'='*50}")
    print(f"Stage 4 완료: {len(result)}개 세그먼트")
    print('='*50)
    for s in result[:10]:
        print(f"  [{s['start']:7.2f} ~ {s['end']:7.2f}]  {s['text'][:60]}")
    if len(result) > 10:
        print(f"  ... 이하 {len(result)-10}개 생략")

    out_json = "stage4_output.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_json}")
