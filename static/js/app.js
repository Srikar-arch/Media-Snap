/* ===== State ===== */
let currentMode = 'video';
let currentQuality = '1080';
let currentJobId = null;
let pollInterval = null;

/* ===== Mode & Quality ===== */
function setMode(mode) {
  currentMode = mode;
  document.getElementById('btnVideo').classList.toggle('active', mode === 'video');
  document.getElementById('btnAudio').classList.toggle('active', mode === 'audio');
  const qRow = document.getElementById('qualityRow');
  qRow.style.display = mode === 'video' ? 'flex' : 'none';
  // Update dl button text if info is showing
  const txt = document.getElementById('dlBtnText');
  if (txt) txt.textContent = mode === 'audio' ? 'Download MP3' : 'Download MP4';
}

function setQuality(btn) {
  document.querySelectorAll('.q-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentQuality = btn.dataset.q;
}

/* ===== Clipboard ===== */
async function pasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    document.getElementById('urlInput').value = text;
    showToast('✅ Pasted from clipboard', 'success');
  } catch {
    showToast('Could not read clipboard — please paste manually', 'error');
  }
}

/* ===== Fetch Info ===== */
async function fetchInfo() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) { showToast('Please paste a video URL first', 'error'); return; }

  const btn = document.getElementById('fetchBtn');
  btn.disabled = true;
  btn.querySelector('.btn-text').textContent = 'Analysing…';
  hideAll();

  try {
    const res = await fetch('/api/info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();

    if (data.error) {
      showToast('Error: ' + data.error.substring(0, 120), 'error');
    } else {
      populateInfoCard(data);
      document.getElementById('infoCard').classList.remove('hidden');
    }
  } catch (e) {
    showToast('Network error. Make sure the server is running.', 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-text').textContent = 'Analyse';
  }
}

function populateInfoCard(data) {
  document.getElementById('infoThumb').src = data.thumbnail || '';
  document.getElementById('infoTitle').textContent = data.title || 'Unknown';
  document.getElementById('infoUploader').textContent = data.uploader || '';
  document.getElementById('infoDuration').textContent = data.duration ? `⏱ ${data.duration}` : '';
  document.getElementById('infoPlatform').textContent = (data.platform || '').toUpperCase();
  const txt = document.getElementById('dlBtnText');
  if (txt) txt.textContent = currentMode === 'audio' ? 'Download MP3' : 'Download MP4';
}

/* ===== Start Download ===== */
async function startDownload() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) return;

  const dlBtn = document.getElementById('downloadBtn');
  dlBtn.disabled = true;
  dlBtn.querySelector('.dl-text').textContent = 'Starting…';

  try {
    const videoTitle = document.getElementById('infoTitle').textContent || 'download';
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, mode: currentMode, quality: currentQuality, title: videoTitle })
    });
    const data = await res.json();

    if (data.error) {
      showToast('Error: ' + data.error, 'error');
      dlBtn.disabled = false;
      dlBtn.querySelector('.dl-text').textContent = currentMode === 'audio' ? 'Download MP3' : 'Download MP4';
      return;
    }

    currentJobId = data.job_id;
    document.getElementById('infoCard').classList.add('hidden');
    const progCard = document.getElementById('progressCard');
    progCard.classList.remove('hidden');
    setProgressLabel('⏳ Downloading... please wait');
    startPolling(data.job_id);

  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
    dlBtn.disabled = false;
  }
}

/* ===== Polling ===== */
function startPolling(jobId) {
  if (pollInterval) clearInterval(pollInterval);

  let fakeProgress = 0;
  const bar = document.getElementById('progressBar');

  pollInterval = setInterval(async () => {
    // Animate fake progress up to 90%
    if (fakeProgress < 85) {
      fakeProgress += Math.random() * 3;
      bar.style.width = Math.min(fakeProgress, 85) + '%';
    }

    try {
      const res = await fetch(`/api/status/${jobId}`);
      const data = await res.json();

      if (data.status === 'done') {
        clearInterval(pollInterval);
        bar.style.width = '100%';
        setProgressLabel('✅ Ready! Downloading to your device…');
        triggerFileDownload(jobId);
      } else if (data.status === 'error') {
        clearInterval(pollInterval);
        document.getElementById('progressCard').classList.add('hidden');
        showToast('Download failed: ' + (data.error || 'Unknown error'), 'error');
        resetUI();
      }
    } catch {}
  }, 1500);
}

function setProgressLabel(text) {
  document.getElementById('progressLabel').textContent = text;
}

/* ===== Trigger File Download ===== */
function triggerFileDownload(jobId) {
  const a = document.createElement('a');
  a.href = `/api/file/${jobId}`;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  setTimeout(() => {
    document.getElementById('progressCard').classList.add('hidden');
    showToast('🎉 Download complete!', 'success');
    resetUI();
  }, 3000);
}

/* ===== Reset ===== */
function resetUI() {
  if (pollInterval) clearInterval(pollInterval);
  currentJobId = null;
  document.getElementById('infoCard').classList.add('hidden');
  document.getElementById('progressCard').classList.add('hidden');
  document.getElementById('urlInput').value = '';
  document.getElementById('downloadBtn').disabled = false;
  document.getElementById('downloadBtn').querySelector('.dl-text').textContent =
    currentMode === 'audio' ? 'Download MP3' : 'Download MP4';
  document.getElementById('progressBar').style.width = '0%';
}

function hideAll() {
  document.getElementById('infoCard').classList.add('hidden');
  document.getElementById('progressCard').classList.add('hidden');
}

/* ===== Toast ===== */
let toastTimer = null;
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 4000);
}

/* ===== Keyboard support ===== */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('urlInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') fetchInfo();
  });

  // Auto-detect paste
  document.getElementById('urlInput').addEventListener('paste', () => {
    setTimeout(fetchInfo, 200);
  });

  setMode('video');
});
