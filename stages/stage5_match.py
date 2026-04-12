"""Stage 5: 타임스탬프 매칭

슬라이드 타임라인 ↔ STT 세그먼트 매핑.
귀속 기준: 세그먼트 start 시각이 속하는 슬라이드.

입력:
    slides:   list[dict]  (Stage 1 출력)
    segments: list[dict]  (Stage 4 출력)

출력: list[dict] — slides에 "text" 필드 추가
    [
        {"idx": 0, "t_start": 0.0, "t_end": 60.0, "frame_path": "...", "text": "..."},
        ...
    ]
"""

import bisect


def run(slides: list[dict], segments: list[dict]) -> list[dict]:
    """STT 세그먼트를 슬라이드에 귀속.

    알고리즘:
        slides를 t_start 기준 정렬 후 bisect_right로 O(log n) 탐색.
        세그먼트 start가 슬라이드 경계 이전이면 0번 슬라이드에 귀속.

    Args:
        slides:   Stage 1 출력 (t_start 기준 정렬되어 있다고 가정)
        segments: Stage 4 출력

    Returns:
        matched: slides 딕셔너리 복사본에 "text" 필드 추가한 list
    """
    if not slides:
        # 오디오 전용 입력: 슬라이드 없이 전체 텍스트를 단일 항목으로 반환
        full_text = " ".join(s["text"] for s in segments if s.get("text"))
        t_end = max((s["end"] for s in segments), default=0.0)
        print(f"[Stage 5] 슬라이드 없음 → 전체 텍스트를 단일 항목으로 처리 ({len(segments)}개 세그먼트)")
        return [{"idx": 0, "t_start": 0.0, "t_end": t_end, "frame_path": "", "text": full_text}]

    # 각 슬라이드에 빈 텍스트 버퍼 준비
    matched: list[dict] = [dict(s, text="") for s in slides]
    t_starts = [s["t_start"] for s in matched]  # 이미 정렬되어 있음

    for seg in segments:
        # bisect_right: seg.start 보다 큰 첫 번째 t_start의 인덱스
        # - 1 → seg.start 이하인 마지막 슬라이드
        i = bisect.bisect_right(t_starts, seg["start"]) - 1
        i = max(0, min(i, len(matched) - 1))
        text = seg["text"]
        if text:
            matched[i]["text"] += (" " if matched[i]["text"] else "") + text

    assigned = sum(1 for s in matched if s["text"])
    print(f"[Stage 5] {len(segments)}개 세그먼트 → {assigned}/{len(matched)}개 슬라이드에 텍스트 귀속")
    return matched


# ── 단독 실행 테스트 ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage: python stage5_match.py <stage1_json> <stage4_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        slides = json.load(f)
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        segments = json.load(f)

    result = run(slides, segments)

    print(f"\n{'='*50}")
    print(f"Stage 5 완료: {len(result)}개 슬라이드")
    print('='*50)
    for s in result:
        preview = (s["text"][:60] + "...") if len(s["text"]) > 60 else s["text"] or "(없음)"
        print(f"  [{s['idx']:3d}] {s['t_start']:7.1f}s ~ {s['t_end']:7.1f}s  |  {preview}")

    out_json = "stage5_output.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_json}")
