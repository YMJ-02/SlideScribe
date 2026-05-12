# 슬라이드 감지 (Stage 1) — 다중 시그널 적응형

## 핵심 문제
1. 교수 필기 → 같은 슬라이드인데 SSIM 이 천천히 떨어진다 (오탐 위험).
2. 비슷한 템플릿의 슬라이드 (제목만 다름) → SSIM 이 0.92 정도라 missed.
3. 1 fps 샘플링이면 빠른 전환 사이의 슬라이드가 통째로 사라진다.
4. `min_slide_sec` 미만 전환을 **버려버리는** 기존 로직 → 실제 전환 손실.

## 알고리즘
### 1. 빠른 샘플링
`cv2.VideoCapture.grab()` 으로 불필요한 디코드를 건너뛰고
`cv2.VideoCapture.retrieve()` 로 샘플 프레임만 디코드. 기본 2 fps.

### 2. 4-신호 change_score (0~1)
```
score = 0.45·SSIM_dist + 0.30·dHash_hamming + 0.20·hist_chi2 + 0.05·edge_delta
```
- **SSIM** (160×90 그레이): 구조적 유사도
- **dHash** (8×8 difference hash): 압축 노이즈에 강건, 작은 콘텐츠 변화
- **HSV 히스토그램** (12×12 H,S): 테마/배경 색 변화
- **에지 밀도 변화**: 다이어그램 ↔ 빈 슬라이드 전환

### 3. 적응형 임계값
```
threshold_i = max(min_floor, median(window) + k · MAD(window) · 1.4826)
```
- `k = sensitivity` (config) — 낮을수록 더 민감
- rolling window = 20초 분량 샘플
- MAD 는 outlier 에 강건한 분산 추정치

### 4. 비최대 억제 (NMS)
같은 전환의 인접 중복 검출 → 점수 최대 인덱스만 유지.

### 5. 사후 병합
- 인접 슬라이드 change_score < `merge_score` 면 병합.
- 짧은 슬라이드 (`< min_slide_sec`) 는 **버리지 않고** 더 유사한 이웃에 흡수.

### 6. 대표 프레임 선택
- 슬라이드의 50%~95% 구간에서 후보 추출.
- Laplacian 분산 (선명도) 최대인 프레임을 저장.

## config.yaml 파라미터
```yaml
slide_detection:
  frame_sample_rate: 2.0     # fps, 높을수록 빠른 컷도 잡음
  sensitivity: 2.5           # k 값, 낮을수록 더 민감 (1.5~4.0)
  merge_score: 0.07          # 사후 병합 임계값 (0.02~0.20)
  min_slide_sec: 2.0         # 최소 지속 시간 (짧으면 이웃에 흡수)
  min_score_floor: 0.08      # 적응형 임계값의 절대 하한
```

## 튜닝 가이드
- **놓치는 슬라이드가 많다** → `sensitivity` 를 2.5 → 2.0 으로 낮춤.
- **같은 슬라이드가 두 번으로 쪼개진다** → `merge_score` 를 0.07 → 0.10 으로 높임.
- **빠른 컷이 통째로 사라진다** → `frame_sample_rate` 를 2.0 → 3.0 으로 높임.
- **짧은 슬라이드를 보존하고 싶다** → `min_slide_sec` 를 2.0 → 0.5 로 낮춤.
