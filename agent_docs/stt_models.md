# STT 모델 옵션

## 기본 설정 (RTX 2070 최적)
```python
from faster_whisper import WhisperModel

model = WhisperModel(
    "large-v3",
    device="cuda",
    compute_type="float16"   # 2070은 float16 권장
)
segments, _ = model.transcribe(
    "audio.wav",
    language="ko",
    beam_size=5,
    batch_size=8             # VRAM 여유 있으므로 8 사용
)
```

## 모델 선택 기준
| 모델 | VRAM | 속도 | 한국어 정확도 |
|---|---|---|---|
| large-v3 (기본) | ~4.5GB | 빠름 | ★★★★☆ |
| Whisper-Large-v3-turbo-STT-Zeroth-KO-v2 | ~5GB | 보통 | ★★★★★ |
| medium | ~2GB | 매우 빠름 | ★★★☆☆ |

HuggingFace 한국어 특화 모델 사용 시:
```python
# config.yaml에서 model_name 변경
model_name: "o0dimplz0o/Whisper-Large-v3-turbo-STT-Zeroth-KO-v2"
```

## 모델 캐시 위치
최초 실행 시 `~/.cache/huggingface/` 자동 다운로드
이후 오프라인 실행 가능
