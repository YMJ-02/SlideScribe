"""Stage 1: 슬라이드 세그멘테이션 (개선판)

기존 단일-SSIM 임계값 방식이 놓치던 슬라이드를 잡기 위한 재설계.

알고리즘 개요
─────────────
1. cap.grab() + cap.retrieve() 로 빠르게 N fps 샘플링 (기본 2 fps).
   - grab() 은 디코드를 건너뛰므로 무관 프레임을 빠르게 통과한다.
2. 각 샘플마다 가벼운 다중 시그널 추출:
     · SSIM (구조)        : 텍스트 레이아웃 변화 민감
     · dHash hamming      : 압축 노이즈에 강건, 작은 콘텐츠 변화 감지
     · HSV 색히스토그램   : 테마/배경 변화 감지
     · 에지 밀도 변화량   : 다이어그램 / 슬라이드 골격 변화 감지
3. 4가지 정규화 후 가중합 → "change score" (0~1)
4. **적응형 임계값**: rolling median + k·MAD
   - 콘텐츠 밀도 (가만히 있는 슬라이드 vs 필기 진행 중) 차이에 자동 적응
   - "낮으면 더 민감" 슬라이더 = k 값 (기본 2.5)
5. 비최대 억제(non-max suppression)로 같은 전환의 중복 검출 제거
6. 검출된 모든 전환을 슬라이드로 빌드 (짧은 슬라이드도 일단 유지)
7. **사후 병합**: 인접 슬라이드가 너무 유사하면 병합
8. **최소 지속시간 강제**: 짧은 슬라이드는 *버리지 않고* 유사도가 높은 이웃에 합침
9. 각 슬라이드에서 대표 프레임 1장 선택 (선명도 최대 - Laplacian 분산)

핵심 변경점
─────────
- min_slide_sec 보다 짧은 전환을 무시 → 짧으면 *병합* 하도록 변경
  (실제 전환을 잃지 않음)
- 단일 SSIM → 4-신호 가중합으로 미세 변화 감지
- 고정 임계값 → 적응형 임계값으로 콘텐츠별 자동 조정

출력 계약은 동일:
    slides: list[dict] = [
        {"idx": 0, "t_start": 0.0, "t_end": 60.3, "frame_path": ".tmp/slide_0.jpg"},
        ...
    ]
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
import yaml
from skimage.metrics import structural_similarity as ssim


# ── 유틸 ──────────────────────────────────────────────────────────────

def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fmt_time(sec: float) -> str:
    s = int(sec)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ── 특징 추출 ────────────────────────────────────────────────────────

_WORK_W, _WORK_H = 160, 90   # 다운스케일 작업 해상도
_DHASH_SIZE = 8              # 8x8 difference hash → 64 bits
_HIST_BINS = (12, 12)        # HSV (H, S) 히스토그램 bin 수


@dataclass
class Feature:
    """샘플 하나에 대한 변화 검출용 특징 묶음 (~ 수 KB)."""
    gray: np.ndarray            # uint8 (H, W)
    dhash: np.ndarray           # uint8 (64,) 비트 시퀀스
    hist: np.ndarray            # float32 (H_bins*S_bins,) 정규화 히스토그램
    edge_density: float         # 0~1 에지 픽셀 비율


def _extract_feature(frame_bgr: np.ndarray) -> Feature:
    small = cv2.resize(frame_bgr, (_WORK_W, _WORK_H), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    # dHash: 9x8 그레이 다운스케일 후 인접 픽셀 비교
    h_small = cv2.resize(gray, (_DHASH_SIZE + 1, _DHASH_SIZE), interpolation=cv2.INTER_AREA)
    dhash = (h_small[:, 1:] > h_small[:, :-1]).astype(np.uint8).flatten()

    # HSV (H, S) 히스토그램 → L1 정규화
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, list(_HIST_BINS), [0, 180, 0, 256])
    cv2.normalize(hist, hist, alpha=1.0, norm_type=cv2.NORM_L1)
    hist = hist.flatten().astype(np.float32)

    # 에지 밀도
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)

    return Feature(gray=gray, dhash=dhash, hist=hist, edge_density=edge_density)


def _change_score(a: Feature, b: Feature) -> float:
    """4-신호 가중합 (0~1, 클수록 큰 변화)."""
    # 1) SSIM 거리
    score, _ = ssim(a.gray, b.gray, full=True, data_range=255)
    ssim_dist = max(0.0, 1.0 - float(score))

    # 2) dHash hamming / 64
    hamming = float(np.sum(a.dhash != b.dhash)) / 64.0

    # 3) 히스토그램 카이제곱 거리 (경험적 정규화)
    chi = float(cv2.compareHist(a.hist, b.hist, cv2.HISTCMP_CHISQR))
    hist_norm = min(1.0, chi / 4.0)

    # 4) 에지 밀도 변화량 (큰 다이어그램 → 빈 슬라이드 등)
    edge_delta = min(1.0, abs(a.edge_density - b.edge_density) * 6.0)

    return 0.45 * ssim_dist + 0.30 * hamming + 0.20 * hist_norm + 0.05 * edge_delta


# ── 비디오 샘플링 ────────────────────────────────────────────────────

def _iter_samples(video_path: str, sample_rate: float):
    """grab() 으로 빠르게 건너뛰며 sample_rate fps로 프레임 산출.

    Yields: (t_sec, frame_idx, frame_bgr)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    skip = max(1, int(round(fps / sample_rate)))

    try:
        frame_idx = 0
        while True:
            ok = cap.grab()
            if not ok:
                break
            if frame_idx % skip == 0:
                ret, frame = cap.retrieve()
                if not ret:
                    break
                yield frame_idx / fps, frame_idx, frame
            frame_idx += 1
            if total_frames and frame_idx > total_frames + skip:
                break
    finally:
        cap.release()


# ── 전환점 탐지 (적응형 임계값) ──────────────────────────────────────

def _detect_transitions(
    scores: np.ndarray,
    k: float = 2.5,
    window: int = 30,
    min_threshold: float = 0.08,
    nms_dist: int = 1,
) -> list[int]:
    """rolling median + k·MAD 로 적응형 임계값 후, 비최대 억제.

    Returns: scores 인덱스 (samples[i]와 samples[i+1] 사이 전환).
    """
    n = len(scores)
    if n == 0:
        return []

    candidates: list[int] = []
    for i in range(n):
        lo = max(0, i - window // 2)
        hi = min(n, i + window // 2 + 1)
        # 자기 자신 제외한 주변 통계
        nbrs = np.concatenate([scores[lo:i], scores[i + 1:hi]])
        if nbrs.size == 0:
            continue
        med = float(np.median(nbrs))
        mad = float(np.median(np.abs(nbrs - med))) + 1e-6
        # MAD ≈ std / 1.4826
        threshold = max(min_threshold, med + k * mad * 1.4826)
        if scores[i] >= threshold:
            candidates.append(i)

    if not candidates:
        return []

    # 비최대 억제: nms_dist 이내의 후보들 중 가장 큰 점수만 유지
    final = [candidates[0]]
    for idx in candidates[1:]:
        if idx - final[-1] <= nms_dist:
            if scores[idx] > scores[final[-1]]:
                final[-1] = idx
        else:
            final.append(idx)
    return final


# ── 슬라이드 빌드 + 사후 병합 ────────────────────────────────────────

def _build_slides(
    timestamps: list[float],
    features: list[Feature],
    transitions: list[int],
    total_sec: float,
) -> list[dict]:
    """transitions: scores 인덱스 (samples[i]와 samples[i+1] 사이 전환)."""
    n = len(timestamps)
    starts_idx = [0] + [t + 1 for t in transitions]
    ends_idx = [t + 1 for t in transitions] + [n]

    slides: list[dict] = []
    for s, e in zip(starts_idx, ends_idx):
        if s >= e or s >= n:
            continue
        t_start = timestamps[s]
        # 다음 슬라이드 시작 = 현 슬라이드 종료
        t_end = timestamps[e] if e < n else total_sec
        # 대표 특징: 슬라이드의 80% 지점 (필기 완료 후, 다음 전환 직전)
        rep = s + max(0, (e - s) * 4 // 5)
        rep = min(rep, e - 1)
        slides.append({
            "_sample_lo": s,
            "_sample_hi": e,
            "_rep_idx": rep,
            "_feature": features[rep],
            "t_start": float(t_start),
            "t_end": float(t_end),
        })
    return slides


def _merge_similar_adjacent(
    slides: list[dict],
    merge_score: float,
) -> list[dict]:
    """이웃 슬라이드 change_score < merge_score 이면 병합."""
    if len(slides) <= 1:
        return slides
    out = [slides[0]]
    for cur in slides[1:]:
        prev = out[-1]
        s = _change_score(prev["_feature"], cur["_feature"])
        if s < merge_score:
            prev["_sample_hi"] = cur["_sample_hi"]
            prev["_rep_idx"] = cur["_rep_idx"]
            prev["_feature"] = cur["_feature"]
            prev["t_end"] = cur["t_end"]
        else:
            out.append(cur)
    return out


def _enforce_min_duration(
    slides: list[dict],
    min_sec: float,
) -> list[dict]:
    """짧은 슬라이드를 더 유사한 이웃과 병합 (버리지 않음)."""
    if len(slides) <= 1:
        return slides
    changed = True
    while changed and len(slides) > 1:
        changed = False
        durations = [s["t_end"] - s["t_start"] for s in slides]
        # 가장 짧은 인덱스
        i = int(np.argmin(durations))
        if durations[i] >= min_sec:
            break

        # 어느 쪽 이웃과 병합?
        if i == 0:
            target = 1
        elif i == len(slides) - 1:
            target = len(slides) - 2
        else:
            left = _change_score(slides[i - 1]["_feature"], slides[i]["_feature"])
            right = _change_score(slides[i]["_feature"], slides[i + 1]["_feature"])
            target = i - 1 if left <= right else i + 1

        lo, hi = sorted([i, target])
        merged = {
            "_sample_lo": slides[lo]["_sample_lo"],
            "_sample_hi": slides[hi]["_sample_hi"],
            # 뒤쪽 슬라이드의 대표 프레임 사용 (필기 완성 우선)
            "_rep_idx": slides[hi]["_rep_idx"],
            "_feature": slides[hi]["_feature"],
            "t_start": slides[lo]["t_start"],
            "t_end": slides[hi]["t_end"],
        }
        slides = slides[:lo] + [merged] + slides[hi + 1:]
        changed = True
    return slides


# ── 대표 프레임 픽 ───────────────────────────────────────────────────

def _pick_representative_frame(
    video_path: str,
    sample_frame_indices: list[int],
    slide: dict,
    candidates_per_slide: int = 6,
) -> np.ndarray | None:
    """슬라이드 구간 안에서 가장 선명한 프레임을 골라 반환.

    여러 후보를 Laplacian 분산(선명도) 으로 비교.
    """
    s, e = slide["_sample_lo"], slide["_sample_hi"]
    if s >= e:
        return None
    # 슬라이드의 50% ~ 95% 지점에서 후보 추출 (필기 완성 영역)
    lo = s + (e - s) // 2
    hi = e - 1
    if hi < lo:
        hi = lo
    if hi == lo:
        cand_indices = [lo]
    else:
        cand_indices = list(np.linspace(lo, hi, num=min(candidates_per_slide, hi - lo + 1), dtype=int))

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    best_frame: np.ndarray | None = None
    best_sharp = -1.0
    try:
        for ci in cand_indices:
            if ci >= len(sample_frame_indices):
                continue
            fi = sample_frame_indices[ci]
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if sharp > best_sharp:
                best_sharp = sharp
                best_frame = frame
    finally:
        cap.release()
    return best_frame


# ── 메인 진입점 ──────────────────────────────────────────────────────

def run(video_path: str, cfg: dict | None = None) -> list[dict]:
    """다중 시그널 + 적응형 임계값 기반 슬라이드 세그멘테이션.

    Args:
        video_path: 입력 영상 경로
        cfg:        config.yaml dict

    Returns:
        slides: list[dict] — idx, t_start, t_end, frame_path
    """
    if cfg is None:
        cfg = _load_config()

    sd = cfg.get("slide_detection", {})
    sample_rate: float = float(sd.get("frame_sample_rate", 2.0))
    sensitivity: float = float(sd.get("sensitivity", 2.5))      # k 값. 낮을수록 민감
    merge_score: float = float(sd.get("merge_score", 0.07))     # 사후 병합 임계값
    min_slide_sec: float = float(sd.get("min_slide_sec", 2.0))
    min_threshold: float = float(sd.get("min_score_floor", 0.08))
    tmp_dir: str = cfg["paths"]["tmp_dir"]

    # 구버전 키 (slide_change_threshold, ssim_merge_threshold) 호환:
    # 이미 사용하지 않지만 cfg 검증 실패를 방지하기 위해 무시한다.

    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"영상을 열 수 없습니다: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_sec = total_frames / fps if total_frames else 0.0
    cap.release()

    print(f"[Stage 1] 영상 길이 {_fmt_time(total_sec)} | FPS {fps:.1f} | "
          f"샘플 {sample_rate} fps | 민감도 k={sensitivity:.2f}")

    # ── 1) 샘플링 + 특징 추출 ───────────────────────────────────────
    timestamps: list[float] = []
    frame_indices: list[int] = []
    features: list[Feature] = []

    for t, fi, frame in _iter_samples(video_path, sample_rate):
        timestamps.append(t)
        frame_indices.append(fi)
        features.append(_extract_feature(frame))

    n_samples = len(features)
    if n_samples == 0:
        print("[Stage 1] 샘플 0개 — 빈 결과 반환")
        return []
    print(f"[Stage 1] 샘플 {n_samples}개 특징 추출 완료")

    # ── 2) 인접 샘플 change_score 계산 ──────────────────────────────
    scores = np.zeros(n_samples - 1, dtype=np.float32)
    for i in range(n_samples - 1):
        scores[i] = _change_score(features[i], features[i + 1])

    # ── 3) 적응형 임계값 + NMS 로 전환점 탐지 ───────────────────────
    transitions = _detect_transitions(
        scores,
        k=sensitivity,
        window=max(10, int(sample_rate * 20)),  # 20초 분량 윈도우
        min_threshold=min_threshold,
        nms_dist=1,
    )
    print(f"[Stage 1] 1차 전환 후보 {len(transitions)}개 (적응형 임계값)")

    # ── 4) 슬라이드 빌드 ────────────────────────────────────────────
    slides = _build_slides(timestamps, features, transitions, total_sec)
    print(f"[Stage 1] 빌드된 슬라이드 {len(slides)}개")

    # ── 5) 인접 유사 슬라이드 병합 ──────────────────────────────────
    slides = _merge_similar_adjacent(slides, merge_score=merge_score)
    print(f"[Stage 1] 유사 이웃 병합 후 {len(slides)}개")

    # ── 6) 최소 지속시간 강제 (짧은 슬라이드를 버리지 않고 합침) ────
    slides = _enforce_min_duration(slides, min_sec=min_slide_sec)
    print(f"[Stage 1] 최소 지속시간({min_slide_sec}s) 적용 후 {len(slides)}개")

    # ── 7) 대표 프레임 추출 & 저장 ──────────────────────────────────
    out: list[dict] = []
    for idx, s in enumerate(slides):
        frame = _pick_representative_frame(video_path, frame_indices, s)
        if frame is None:
            # 마지막 안전망: 샘플 특징에서 대표 인덱스의 그레이는 있지만 원본 프레임은 없음
            # → 그 인덱스의 원본 프레임을 다시 한 번 시도
            cap = cv2.VideoCapture(video_path)
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_indices[s["_rep_idx"]])
                ok, frame = cap.read()
            finally:
                cap.release()
            if not ok or frame is None:
                continue

        frame_path = os.path.join(tmp_dir, f"slide_{idx}.jpg")
        cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])

        dur = s["t_end"] - s["t_start"]
        print(f"  [{idx:3d}] {_fmt_time(s['t_start'])} ~ {_fmt_time(s['t_end'])}  "
              f"({dur:.1f}s)  → {frame_path}")

        out.append({
            "idx": idx,
            "t_start": round(s["t_start"], 3),
            "t_end": round(s["t_end"], 3),
            "frame_path": frame_path,
        })

    print(f"[Stage 1] 최종 슬라이드 {len(out)}개")
    return out


# ── 단독 실행 테스트 ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python stage1_segment.py <video_path> [config_path]")
        sys.exit(1)

    video = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    result = run(video, cfg)

    print(f"\n{'='*50}")
    print(f"Stage 1 완료: {len(result)}개 슬라이드")
    print('='*50)

    out_json = os.path.join(cfg["paths"]["tmp_dir"], "stage1_output.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_json}")
