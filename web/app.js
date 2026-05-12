// SlideScribe — frontend logic (vanilla JS, no framework)
'use strict';

// ── i18n strings ───────────────────────────────────────────
const STRINGS = {
  en: {
    tagline:               'Lecture video → structured notes, in one pass.',
    section_upload:        'Upload',
    section_mode:          'Mode',
    section_slide_params:  'Slide detection',
    section_whisper_params:'Transcription',
    upload_title:          'Drop a video or audio file',
    upload_sub:            'or click to browse — MP4, MKV, MOV, WAV, M4A…',
    mode_both:             'Slides + Transcript',
    mode_slides:           'Slides only',
    mode_whisper:          'Transcript only',
    mode_hint_both:        'Detect slides AND transcribe audio with Whisper. Most complete (slower).',
    mode_hint_slides:      'Detect slides only — skip Whisper transcription. Fastest.',
    mode_hint_whisper:     'Transcribe audio only — skip slide detection.',
    sensitivity_label:     'Sensitivity (lower = more slides)',
    merge_label:           'Merge similar slides (higher = fewer near-dupes)',
    sample_rate_label:     'Sample rate (fps)',
    min_dur_label:         'Min slide duration (s)',
    whisper_lang_label:    'Language',
    format_label:          'Export format',
    lang_auto:             'Auto-detect',
    run_btn:               'Generate',
    error_no_file:         'Please drop a video or audio file first.',
    result_done:           'DONE',
    result_error:          'ERROR',
    download_btn:          'Download ZIP',
    starting:              'Starting…',
    uploading:             'Uploading…',
  },
  ko: {
    tagline:               '강의 영상 → 구조화된 노트, 한 번에.',
    section_upload:        '업로드',
    section_mode:          '모드',
    section_slide_params:  '슬라이드 감지',
    section_whisper_params:'음성 인식',
    upload_title:          '영상이나 오디오 파일을 드롭하세요',
    upload_sub:            '또는 클릭해서 선택 — MP4, MKV, MOV, WAV, M4A…',
    mode_both:             '슬라이드 + 스크립트',
    mode_slides:           '슬라이드만',
    mode_whisper:          '스크립트만',
    mode_hint_both:        '슬라이드 감지 + Whisper 전사. 가장 풍부함 (느림).',
    mode_hint_slides:      '슬라이드만 추출. Whisper 생략 — 가장 빠름.',
    mode_hint_whisper:     '음성 전사만. 슬라이드 감지 생략.',
    sensitivity_label:     '감지 민감도 (낮을수록 더 많이)',
    merge_label:           '유사 슬라이드 병합 (높을수록 적극 병합)',
    sample_rate_label:     '샘플링 속도 (fps)',
    min_dur_label:         '최소 지속 시간 (초)',
    whisper_lang_label:    '언어',
    format_label:          '출력 포맷',
    lang_auto:             '자동 감지',
    run_btn:               '생성 시작',
    error_no_file:         '파일을 먼저 업로드해 주세요.',
    result_done:           '완료',
    result_error:          '오류',
    download_btn:          'ZIP 다운로드',
    starting:              '시작하는 중…',
    uploading:             '업로드 중…',
  },
};

// ── State ──────────────────────────────────────────────────
const state = {
  files: [],
  mode: 'both',
  format: 'html',
  lang: 'en',
  jobId: null,
  pollTimer: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function t(key) {
  const dict = STRINGS[state.lang] || STRINGS.en;
  return dict[key] || key;
}

function applyI18n() {
  document.body.setAttribute('data-lang', state.lang);
  $$('[data-i18n]').forEach((el) => {
    const key = el.dataset.i18n;
    if (!key) return;
    el.textContent = t(key);
  });
}

function escapeHtml(s) {
  return String(s).replace(/[<>&"']/g, (c) => ({
    '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function fmtBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  if (b < 1024 * 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`;
  return `${(b / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

// ── Language toggle ────────────────────────────────────────
$$('.hero-lang button').forEach((b) => {
  b.addEventListener('click', () => {
    state.lang = b.dataset.lang;
    $$('.hero-lang button').forEach((x) => x.classList.toggle('active', x === b));
    applyI18n();
    renderFileList(); // re-render with current state (no text dep but for consistency)
  });
});

// ── File upload (drag-drop + click + keyboard) ─────────────
const dropzone = $('#dropzone');
const fileInput = $('#file-input');
const fileList = $('#file-list');

function addFiles(items) {
  for (const f of items) state.files.push(f);
  renderFileList();
}

function renderFileList() {
  fileList.innerHTML = '';
  state.files.forEach((f, i) => {
    const row = document.createElement('div');
    row.className = 'file-row';
    row.innerHTML = `
      <div class="file-row-icon">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
      </div>
      <div class="file-row-name">${escapeHtml(f.name)}</div>
      <div class="file-row-size">${fmtBytes(f.size)}</div>
      <button class="file-row-remove" data-i="${i}" aria-label="Remove ${escapeHtml(f.name)}">×</button>
    `;
    fileList.appendChild(row);
  });
  $$('.file-row-remove').forEach((b) => {
    b.addEventListener('click', () => {
      const i = parseInt(b.dataset.i, 10);
      state.files.splice(i, 1);
      renderFileList();
    });
  });
}

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
});

['dragenter', 'dragover'].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add('dragover');
  })
);
['dragleave', 'drop'].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('dragover');
  })
);
dropzone.addEventListener('drop', (e) => {
  if (e.dataTransfer && e.dataTransfer.files) addFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', (e) => {
  if (e.target.files) addFiles(e.target.files);
  fileInput.value = ''; // allow re-adding same file later
});

// ── Mode segmented control ─────────────────────────────────
$$('#mode-segmented button').forEach((b) => {
  b.addEventListener('click', () => {
    state.mode = b.dataset.mode;
    $$('#mode-segmented button').forEach((x) => {
      const on = x === b;
      x.classList.toggle('active', on);
      x.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    updatePanelVisibility();
    updateModeHint();
  });
});

function updatePanelVisibility() {
  $('#slide-params-section').classList.toggle('hidden', state.mode === 'whisper');
  $('#whisper-params-section').classList.toggle('hidden', state.mode === 'slides');
}

function updateModeHint() {
  const el = $('#mode-hint');
  el.textContent = t(`mode_hint_${state.mode}`);
  el.style.animation = 'none';
  // force reflow then re-trigger animation
  void el.offsetWidth;
  el.style.animation = '';
}

// ── Format segmented ───────────────────────────────────────
$$('#format-segmented button').forEach((b) => {
  b.addEventListener('click', () => {
    state.format = b.dataset.fmt;
    $$('#format-segmented button').forEach((x) => x.classList.toggle('active', x === b));
  });
});

// ── Slider values ──────────────────────────────────────────
[
  ['sensitivity', (v) => v.toFixed(1)],
  ['merge_score', (v) => v.toFixed(3)],
  ['sample_rate', (v) => v.toFixed(1)],
  ['min_dur',     (v) => v.toFixed(1)],
].forEach(([id, fmt]) => {
  const slider = $(`#${id}`);
  const value = $(`#${id}-val`);
  const update = () => { value.textContent = fmt(parseFloat(slider.value)); };
  slider.addEventListener('input', update);
  update();
});

// ── Submit ─────────────────────────────────────────────────
const runBtn = $('#run-btn');
runBtn.addEventListener('click', async () => {
  if (state.files.length === 0) {
    flashDropzone();
    setStatus(t('error_no_file'), true);
    return;
  }

  runBtn.disabled = true;
  hideResult();
  showProgress(t('uploading'), 0.02);

  const fd = new FormData();
  state.files.forEach((f) => fd.append('files', f, f.name));
  fd.append('mode', state.mode);
  fd.append('format', state.format);
  fd.append('sensitivity',   $('#sensitivity').value);
  fd.append('merge_score',   $('#merge_score').value);
  fd.append('sample_rate',   $('#sample_rate').value);
  fd.append('min_slide_sec', $('#min_dur').value);
  fd.append('whisper_lang',  $('#whisper-lang').value);

  try {
    const r = await fetch('/api/run', { method: 'POST', body: fd });
    if (!r.ok) {
      const txt = await r.text();
      throw new Error(`HTTP ${r.status}: ${txt}`);
    }
    const j = await r.json();
    if (j.error) throw new Error(j.error);
    state.jobId = j.job_id;
    showProgress(t('starting'), 0.05);
    startPolling();
  } catch (e) {
    runBtn.disabled = false;
    hideProgress();
    setStatus(String(e.message || e), true);
  }
});

function flashDropzone() {
  dropzone.classList.add('dragover');
  setTimeout(() => dropzone.classList.remove('dragover'), 350);
}

function startPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(pollOnce, 700);
  pollOnce();
}

async function pollOnce() {
  if (!state.jobId) return;
  try {
    const r = await fetch(`/api/jobs/${state.jobId}`);
    if (!r.ok) return;
    const j = await r.json();
    showProgress(j.message || '', j.progress || 0);
    if (j.status === 'done' || j.status === 'error') {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      runBtn.disabled = false;
      hideProgress();
      if (j.status === 'done') {
        showResult(j.summary || '', false);
      } else {
        showResult(j.message || 'Pipeline error', true);
      }
    }
  } catch (e) {
    /* network transient — keep polling */
  }
}

function showProgress(msg, frac) {
  $('#progress-panel').classList.add('show');
  $('#progress-title').textContent = msg || '';
  const pct = Math.max(0, Math.min(100, frac * 100));
  $('#progress-fill').style.width = `${pct}%`;
  $('#progress-pct').textContent = `${pct.toFixed(0)}%`;
}

function hideProgress() {
  $('#progress-panel').classList.remove('show');
}

function showResult(text, isError) {
  const panel = $('#result-panel');
  const title = $('#result-title');
  const summary = $('#result-summary');
  const link = $('#download-link');

  title.textContent = isError ? t('result_error') : t('result_done');
  title.classList.toggle('is-error', isError);
  summary.textContent = text;

  if (!isError && state.jobId) {
    link.href = `/api/jobs/${state.jobId}/download`;
    link.style.display = '';
  } else {
    link.style.display = 'none';
  }
  panel.classList.add('show');
}

function hideResult() {
  $('#result-panel').classList.remove('show');
}

function setStatus(msg, isError) {
  showResult(msg, !!isError);
}

// ── Init ───────────────────────────────────────────────────
applyI18n();
updatePanelVisibility();
updateModeHint();
