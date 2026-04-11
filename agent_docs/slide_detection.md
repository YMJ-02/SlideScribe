# 슬라이드 감지 튜닝 가이드

## 핵심 문제
교수님 필기 → 같은 슬라이드인데 프레임이 계속 변함
→ 단순 프레임 비교로는 오탐 다수 발생

## 2단계 전략

### 1단계: PySceneDetect (하드컷 감지)
```python
from scenedetect import detect, ContentDetector
scenes = detect(video_path, ContentDetector(threshold=27.0))
```
- threshold 기본값: 27.0 (낮을수록 민감)
- 슬라이드 전환(하드컷)에 최적화됨
- 필기는 감지하지 않음 → 의도된 동작

### 2단계: SSIM 후처리 (유사 슬라이드 병합)
```python
from skimage.metrics import structural_similarity as ssim
# ssim > 0.85 이면 동일 슬라이드로 간주하여 병합
```
- 임계값: config.yaml의 `ssim_merge_threshold` (기본 0.85)

### 대표 프레임 선택
- 각 scene의 **마지막 프레임** 사용
- 이유: 필기가 가장 완성된 상태 = 최대 정보량

## config.yaml 파라미터
```yaml
slide_detection:
  scene_threshold: 27.0      # 낮추면 더 민감
  ssim_merge_threshold: 0.85 # 높이면 더 적극적으로 병합
  frame_sample_rate: 2       # 초당 샘플링 프레임 수
```
