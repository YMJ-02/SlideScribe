"""UI string translations for SlideScribe.

Usage:
    from i18n import t
    label = t("upload_label", lang)
"""

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title":            "# SlideScribe — Lecture Note Generator",
        "subtitle":         "Upload a lecture video to automatically segment slides, transcribe audio, and generate a structured note.",
        "upload_label":     "Upload lecture video",
        "format_label":     "Output format",
        "params_header":    "### Detection parameters",
        "threshold_label":  "Slide change sensitivity (lower = more splits)",
        "merge_label":      "SSIM merge threshold (higher = more merges)",
        "whisper_label":    "Transcription language",
        "run_btn":          "Generate Note",
        "status_label":     "Progress / Result",
        "note_label":       "Download lecture note",
        "pdf_label":        "Download slide PDF",
        "transcript_label": "Download transcript (transcript.txt)",
        "error_no_file":    "Please upload a video file.",
        "done_msg":         "Done!  {slides} slides / {segs} STT segments\nNote: {note}\nSlide PDF: {pdf}\nTranscript: {transcript}  |  Slide images: {slides_dir}/slides/",
        "error_prefix":     "Error:\n",
    },
    "ko": {
        "title":            "# SlideScribe — 강의 노트 자동 생성",
        "subtitle":         "영상을 업로드하면 슬라이드 세그멘테이션 + STT → 강의 노트를 생성합니다.",
        "upload_label":     "강의 영상 업로드",
        "format_label":     "출력 포맷",
        "params_header":    "### 슬라이드 감지 파라미터",
        "threshold_label":  "슬라이드 전환 감도 (낮을수록 더 많이 감지)",
        "merge_label":      "ssim_merge_threshold (높을수록 적극 병합)",
        "whisper_label":    "전사 언어",
        "run_btn":          "노트 생성 시작",
        "status_label":     "진행 상황 / 결과",
        "note_label":       "강의 노트 다운로드",
        "pdf_label":        "슬라이드 PDF 다운로드",
        "transcript_label": "트랜스크립트 다운로드 (transcript.txt)",
        "error_no_file":    "영상 파일을 업로드해 주세요.",
        "done_msg":         "완료!  슬라이드 {slides}개 / STT 세그먼트 {segs}개\n강의 노트: {note}\n슬라이드 PDF: {pdf}\n트랜스크립트: {transcript}  |  슬라이드 이미지: {slides_dir}/slides/",
        "error_prefix":     "오류 발생:\n",
    },
}

# Whisper language options: display label → faster-whisper language code (None = auto)
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


def t(key: str, lang: str = "ko") -> str:
    """Return the translated string for key in lang, falling back to 'ko'."""
    return STRINGS.get(lang, STRINGS["ko"]).get(key, key)
