"""UI 문자열 번역 (SlideScribe).

Usage:
    from i18n import t
    label = t("upload_label", lang)
"""

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title":            "SlideScribe",
        "tagline":          "Lecture video → structured notes, in one pass.",
        "subtitle":         "Drop a video or audio file. Pick a mode. We do the rest.",
        "upload_label":     "Lecture file",
        "upload_hint":      "Video (mp4, mkv, mov, avi, webm) or audio (mp3, wav, m4a, aac, flac)",
        "mode_label":       "Mode",
        "mode_both":        "Slides + Transcript",
        "mode_slides":      "Slides only",
        "mode_whisper":     "Transcript only",
        "mode_hint_both":   "Detect slides AND transcribe audio with Whisper (slowest, most complete).",
        "mode_hint_slides": "Detect slides only — skip Whisper transcription. Fastest.",
        "mode_hint_whisper":"Transcribe audio only — skip slide detection.",
        "format_label":     "Output format",
        "params_slide":     "Slide detection",
        "params_whisper":   "Transcription",
        "sensitivity_label":"Detection sensitivity  (lower = more slides detected)",
        "merge_label":      "Merge similar slides  (higher = fewer near-duplicates)",
        "sample_rate_label":"Sample rate (fps) — higher catches faster cuts",
        "min_dur_label":    "Minimum slide duration (sec)",
        "whisper_label":    "Transcription language",
        "run_btn":          "Generate",
        "status_label":     "Status",
        "result_label":     "Result",
        "download_label":   "Download (ZIP)",
        "error_no_file":    "Please upload a video or audio file first.",
        "done_msg":         "✓ {name}  →  {slides} slides / {segs} segments",
        "err_msg":          "✗ {name}  ERROR: {err}",
    },
    "ko": {
        "title":            "SlideScribe",
        "tagline":          "강의 영상 → 구조화된 노트, 한 번에.",
        "subtitle":         "영상이나 오디오 파일을 올리고 모드만 선택하세요.",
        "upload_label":     "강의 파일",
        "upload_hint":      "영상(mp4, mkv, mov, avi, webm) 또는 오디오(mp3, wav, m4a, aac, flac)",
        "mode_label":       "모드",
        "mode_both":        "슬라이드 + 스크립트",
        "mode_slides":      "슬라이드만",
        "mode_whisper":     "스크립트만",
        "mode_hint_both":   "슬라이드 감지 + Whisper 전사 (가장 느리지만 가장 풍부함).",
        "mode_hint_slides": "슬라이드만 추출. Whisper 생략 → 가장 빠름.",
        "mode_hint_whisper":"음성 전사만. 슬라이드 감지 생략.",
        "format_label":     "출력 포맷",
        "params_slide":     "슬라이드 감지",
        "params_whisper":   "음성 인식",
        "sensitivity_label":"감지 민감도  (낮을수록 더 많이 감지)",
        "merge_label":      "유사 슬라이드 병합  (높을수록 적극 병합)",
        "sample_rate_label":"샘플링 속도 (fps) — 높을수록 빠른 컷도 잡음",
        "min_dur_label":    "슬라이드 최소 지속 시간 (초)",
        "whisper_label":    "전사 언어",
        "run_btn":          "생성 시작",
        "status_label":     "상태",
        "result_label":     "결과",
        "download_label":   "다운로드 (ZIP)",
        "error_no_file":    "파일을 먼저 업로드해 주세요.",
        "done_msg":         "✓ {name}  →  슬라이드 {slides}개 / 세그먼트 {segs}개",
        "err_msg":          "✗ {name}  오류: {err}",
    },
}

# Whisper 언어 옵션: 표시명 → faster-whisper 언어 코드 (None = auto)
WHISPER_LANGUAGES: list[tuple[str, str | None]] = [
    ("Auto-detect", None),
    ("한국어",       "ko"),
    ("English",     "en"),
    ("日本語",       "ja"),
    ("中文",         "zh"),
    ("Français",    "fr"),
    ("Deutsch",     "de"),
    ("Español",     "es"),
    ("Português",   "pt"),
    ("Русский",     "ru"),
]

WHISPER_DISPLAY_NAMES = [label for label, _ in WHISPER_LANGUAGES]
WHISPER_CODE_MAP = {label: code for label, code in WHISPER_LANGUAGES}


# 모드 표시명 (UI) → 내부 키
def mode_choices(lang: str) -> list[tuple[str, str]]:
    return [
        (t("mode_both",    lang), "both"),
        (t("mode_slides",  lang), "slides"),
        (t("mode_whisper", lang), "whisper"),
    ]


def t(key: str, lang: str = "ko") -> str:
    return STRINGS.get(lang, STRINGS["ko"]).get(key, key)
