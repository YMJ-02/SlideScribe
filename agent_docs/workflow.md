# 파이프라인 워크플로우

## 모드별 실행 경로

### `both` (기본, video 입력)
```
[Video]
  ├─ Stage 1  슬라이드 세그멘테이션 (다중 시그널 + 적응형 임계값)
  │     ↓ slides = [{idx, t_start, t_end, frame_path}]
  ├─ Stage 2  슬라이드 PDF (이미지 nodes)
  ├─ Stage 3  ffmpeg 16 kHz mono WAV 추출
  ├─ Stage 4  Whisper STT  → segments = [{start, end, text}]
  ├─ Stage 5  bisect 매칭  → matched = slides + text
  └─ Stage 6  HTML / PDF / Markdown 노트 + transcript.txt + slides/
```

### `slides` (Whisper 생략, 빠른 슬라이드 추출만)
```
[Video]
  ├─ Stage 1  슬라이드 세그멘테이션
  ├─ Stage 2  슬라이드 PDF
  ├─ Stage 5  matched = [dict(s, text="") for s in slides]
  └─ Stage 6  슬라이드만 들어간 노트 (transcript.txt 생성 안 됨)
```

### `whisper` (슬라이드 감지 생략, 전사만)
```
[Video|Audio]
  ├─ Stage 3  (오디오 입력이면 스킵)
  ├─ Stage 4  Whisper STT
  ├─ Stage 5  matched = 단일 항목 (전체 텍스트)
  └─ Stage 6  텍스트만 들어간 노트 + transcript.txt
```

오디오 파일이 입력되면 자동으로 `whisper` 모드로 강제 전환된다.

## Stage 간 데이터 계약

```python
# Stage 1 출력 → Stage 2, 5 입력
slides: list[dict] = [
    {"idx": 0, "t_start": 0.0, "t_end": 203.5, "frame_path": ".tmp/slide_0.jpg"},
    ...
]

# Stage 4 출력 → Stage 5 입력
segments: list[dict] = [
    {"start": 12.3, "end": 18.7, "text": "이 부분이 핵심입니다"},
    ...
]

# Stage 5 출력 → Stage 6 입력
matched: list[dict] = [
    {"idx": 0, "t_start": 0.0, "t_end": 203.5, "frame_path": "...", "text": "..."},
    ...
]
```

## Stage 6 자동 모드 감지
- 어떤 슬라이드도 `text` 가 없으면 → 슬라이드만 렌더링 (transcript.txt 생성 안 됨).
- 어떤 슬라이드도 `frame_path` 가 없으면 → 텍스트만 렌더링 (slides/ 디렉터리 생성 안 됨).
- 둘 다 있으면 → 좌(슬라이드) | 우(전사) 2단 페이지.
