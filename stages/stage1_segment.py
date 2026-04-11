"""Stage 1: 슬라이드 세그멘테이션

SSIM 기반 프레임 샘플링으로 슬라이드 전환 감지.
PySceneDetect ContentDetector는 강의 영상의 부드러운 전환(페이드 등)을
잡지 못하는 경우가 많아 제거하고, 직접 샘플링 방식으로 대체.

알고리즘:
  1. frame_sample_rate (기본 1fps) 간격으로 프레임 샘플링
  2. 연속 샘플 간 SSIM < slide_change_threshold → 슬라이드 전환 후보
  3. min_slide_sec 미만 구간은 무시 (오탐 방지)
  4. 인접 슬라이드 SSIM >= ssim_merge_threshold → 병합

출력 계약 (workflow.md):
    slides: list[dict] = [
        {"idx": 0, "t_start": 0.0, "t_end": 60.3, "frame_path": ".tmp/slide_0.jpg"},
        ...
    ]
"""

import os
import cv2
import yaml
import numpy as np
from pathlib import Path
from skimage.metrics import structural_similarity as ssim


def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """두 BGR 이미지 간 SSIM 계산 (grayscale 변환 후)."""
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    if gray1.shape != gray2.shape:
        gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
    score, _ = ssim(gray1, gray2, full=True, data_range=255)
    return float(score)


def _fmt_time(sec: float) -> str:
    s = int(sec)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def run(video_path: str, cfg: dict | None = None) -> list[dict]:
    """SSIM 샘플링 기반 슬라이드 세그멘테이션.

    Args:
        video_path: 입력 영상 경로
        cfg:        config.yaml dict

    Returns:
        slides: list[dict] — idx, t_start, t_end, frame_path
    """
    if cfg is None:
        cfg = _load_config()

    sd_cfg = cfg["slide_detection"]
    change_threshold: float = sd_cfg.get("slide_change_threshold", 0.90)
    merge_threshold: float = sd_cfg.get("ssim_merge_threshold", 0.85)
    sample_rate: float = sd_cfg.get("frame_sample_rate", 1)
    min_slide_sec: float = sd_cfg.get("min_slide_sec", 3.0)
    tmp_dir: str = cfg["paths"]["tmp_dir"]

    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps: float = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_sec: float = total_frames / fps
    sample_step: int = max(1, int(fps / sample_rate))

    print(f"[Stage 1] 영상: {_fmt_time(total_sec)}  FPS:{fps:.1f}  "
          f"샘플 간격:{sample_step}f ({1/sample_rate:.1f}초)")

    # ── 1단계: SSIM 샘플링으로 슬라이드 전환 감지 ───────────────────
    raw: list[tuple[float, float, np.ndarray]] = []  # (t_start, t_end, last_frame)
    prev_frame: np.ndarray | None = None
    seg_start: float = 0.0
    seg_last: np.ndarray | None = None

    for fi in range(0, total_frames, sample_step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ret, frame = cap.read()
        if not ret:
            break
        t = fi / fps

        if prev_frame is None:
            prev_frame = frame
            seg_start = t
            seg_last = frame
            continue

        score = _compute_ssim(prev_frame, frame)
        seg_dur = t - seg_start

        if score < change_threshold and seg_dur >= min_slide_sec:
            raw.append((seg_start, t, seg_last))
            print(f"  [{_fmt_time(seg_start)} ~ {_fmt_time(t)}]  SSIM={score:.3f}  → 전환")
            seg_start = t

        prev_frame = frame
        seg_last = frame

    cap.release()

    # 마지막 구간 추가
    if seg_last is not None:
        raw.append((seg_start, total_sec, seg_last))

    print(f"[Stage 1] 전환 감지 후 {len(raw)}개 구간")

    if not raw:
        return []

    # ── 2단계: 인접 구간 SSIM 병합 ──────────────────────────────────
    merged: list[tuple[float, float, np.ndarray]] = []
    cur_start, cur_end, cur_frame = raw[0]

    for t_start, t_end, frame in raw[1:]:
        score = _compute_ssim(cur_frame, frame)
        if score >= merge_threshold:
            cur_end = t_end
            cur_frame = frame   # 마지막 프레임(필기 완성 상태)으로 갱신
        else:
            merged.append((cur_start, cur_end, cur_frame))
            cur_start, cur_end, cur_frame = t_start, t_end, frame

    merged.append((cur_start, cur_end, cur_frame))
    print(f"[Stage 1] 병합 후 {len(merged)}개 슬라이드")

    # ── 3단계: 프레임 저장 및 출력 구성 ────────────────────────────
    slides: list[dict] = []
    for idx, (t_start, t_end, frame) in enumerate(merged):
        frame_path = os.path.join(tmp_dir, f"slide_{idx}.jpg")
        cv2.imwrite(frame_path, frame)
        slides.append({
            "idx": idx,
            "t_start": round(t_start, 3),
            "t_end": round(t_end, 3),
            "frame_path": frame_path,
        })

    return slides


# ── 단독 실행 테스트 ──────────────────────────────────────────────────
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
    for s in result:
        dur = s["t_end"] - s["t_start"]
        print(f"  [{s['idx']:3d}] {_fmt_time(s['t_start'])} ~ {_fmt_time(s['t_end'])}"
              f"  ({dur:.1f}s)  → {s['frame_path']}")

    out_json = os.path.join(cfg["paths"]["tmp_dir"], "stage1_output.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_json}")
