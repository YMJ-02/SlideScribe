# 파이프라인 워크플로우

## 전체 흐름
```
[영상 파일]
    │
    ▼
Stage 1: 슬라이드 세그멘테이션  (stages/stage1_segment.py)
    │   PySceneDetect 하드컷 감지 → SSIM 후처리 병합
    │   출력: [(slide_idx, t_start, t_end, frame_path)]
    │
    ├──▶ Stage 2: PDF 생성        (stages/stage2_pdf.py)
    │        각 슬라이드 마지막 프레임 → fpdf2로 PDF
    │
    └──▶ Stage 3: 오디오 추출    (stages/stage3_audio.py)
             ffmpeg → 16kHz mono WAV
             ▼
         Stage 4: Whisper STT    (stages/stage4_stt.py)
             faster-whisper large-v3, language="ko"
             출력: [(start, end, text)]
             ▼
         Stage 5: 타임스탬프 매칭 (stages/stage5_match.py)
             슬라이드 타임라인 ↔ STT 세그먼트 매핑
             경계 처리: 세그먼트 시작 시각 기준 귀속
             ▼
         Stage 6: 노트 생성      (stages/stage6_export.py)
             출력 포맷: HTML(기본) / PDF / Markdown
             HTML은 이미지 base64 임베드 (단일 파일)
```

## Stage 간 데이터 계약
```python
# Stage 1 출력 → Stage 2, 5 입력
slides: list[dict] = [
    {"idx": 0, "t_start": 0.0, "t_end": 203.5, "frame_path": "tmp/slide_0.jpg"},
    ...
]

# Stage 4 출력 → Stage 5 입력
segments: list[dict] = [
    {"start": 12.3, "end": 18.7, "text": "이 부분이 핵심입니다"},
    ...
]
```
