/* ===== upload.js — Upload forms + polling ===== */
(function () {
    'use strict';

    const POLL_INTERVAL = 1500;

    function bindForm(formId, statusId) {
        const form = document.getElementById(formId);
        if (!form) return;
        const statusEl = document.getElementById(statusId);
        const uploadType = form.dataset.type;
        const dropZone = form.querySelector('.drop-zone');
        const fileInput = form.querySelector('input[type="file"]');
        const filenameEl = form.querySelector('.drop-zone-filename');
        const textEl = form.querySelector('.drop-zone-text');

        function updateFilename(name) {
            if (filenameEl && textEl) {
                if (name) {
                    filenameEl.textContent = name;
                    filenameEl.style.display = 'inline-block';
                    textEl.style.display = 'none';
                } else {
                    filenameEl.style.display = 'none';
                    textEl.style.display = 'inline-block';
                }
            }
        }

        if (dropZone && fileInput) {
            ['dragenter', 'dragover'].forEach(evt => {
                dropZone.addEventListener(evt, e => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.add('dragover');
                });
            });

            ['dragleave', 'drop'].forEach(evt => {
                dropZone.addEventListener(evt, e => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.remove('dragover');
                });
            });

            dropZone.addEventListener('drop', e => {
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    fileInput.files = e.dataTransfer.files;
                    updateFilename(e.dataTransfer.files[0].name);
                }
            });

            fileInput.addEventListener('change', () => {
                if (fileInput.files && fileInput.files.length > 0) {
                    updateFilename(fileInput.files[0].name);
                } else {
                    updateFilename(null);
                }
            });
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files.length) return;

            const fd = new FormData();
            fd.append('file', fileInput.files[0]);
            fd.append('upload_type', uploadType);

            statusEl.className = 'upload-status status-processing';
            statusEl.textContent = '⏳ Mengunggah...';
            form.querySelector('button').disabled = true;

            try {
                const res = await fetch('/api/upload', { method: 'POST', body: fd });
                const data = await res.json();

                if (data.error) {
                    statusEl.className = 'upload-status status-rejected';
                    statusEl.textContent = '✗ ' + data.error;
                    form.querySelector('button').disabled = false;
                    return;
                }

                statusEl.className = 'upload-status status-processing';
                statusEl.textContent = '⏳ Memproses validasi...';
                if (window.GlobalWorker) {
                    window.GlobalWorker.trackTask(data.task_id, fileInput.files[0].name, uploadType);
                }
                pollStatus(data.task_id, statusEl, form.querySelector('button'));

            } catch (err) {
                statusEl.className = 'upload-status status-rejected';
                statusEl.textContent = '✗ Gagal terhubung ke server.';
                form.querySelector('button').disabled = false;
            }
        });
    }

    function pollStatus(taskId, statusEl, btn) {
        const iv = setInterval(async () => {
            try {
                const res = await fetch(`/api/upload/status/${taskId}`);
                const data = await res.json();

                if (data.status === 'done') {
                    clearInterval(iv);
                    btn.disabled = false;
                    const result = data.result;
                    if (result && result.accepted === false) {
                        statusEl.className = 'upload-status status-rejected';
                        statusEl.textContent = '✗ Ditolak';
                    } else {
                        statusEl.className = 'upload-status status-done';
                        statusEl.textContent = '✓ Selesai';
                    }
                    renderUploadResult(data.result);

                } else if (data.status === 'error') {
                    clearInterval(iv);
                    btn.disabled = false;
                    statusEl.className = 'upload-status status-rejected';
                    statusEl.textContent = '✗ Error: ' + (data.error || 'unknown');
                }
            } catch (err) {
                // network hiccup, keep polling
            }
        }, POLL_INTERVAL);
    }

    function renderUploadResult(result) {
        if (!result) return;
        const container = document.getElementById('uploadResult');
        const content = document.getElementById('uploadResultContent');
        container.style.display = 'block';

        let html = '';

        if (result.accepted === false) {
            html += '<h3 style="color:var(--danger);margin-bottom:12px;">❌ File Ditolak</h3>';
            (result.reject_reasons || []).forEach(r => {
                html += `<div class="error-item">✗ ${escHtml(r)}</div>`;
            });
        } else {
            html += '<h3 style="color:var(--success);margin-bottom:12px;">✅ Upload Berhasil</h3>';

            // Stats
            if (result.stats) {
                const s = result.stats;
                html += `<div class="result-stats">
                    <div class="result-stat"><span class="val">${s.new || 0}</span> baru</div>
                    <div class="result-stat"><span class="val">${s.updated || 0}</span> diperbarui</div>
                    <div class="result-stat"><span class="val">${s.unchanged || 0}</span> tidak berubah</div>
                </div>`;
            }

            // Warnings
            if (result.warnings && result.warnings.length) {
                html += `<h4 style="margin:12px 0 6px;color:var(--warning)">⚠ Peringatan (${result.warnings.length})</h4>`;
                result.warnings.forEach(w => {
                    html += `<div class="warn-item">${escHtml(w.message)}</div>`;
                });
            }

            // Notes
            if (result.notes && result.notes.length) {
                html += `<h4 style="margin:12px 0 6px;color:var(--info)">ℹ Catatan (${result.notes.length})</h4>`;
                result.notes.forEach(n => {
                    html += `<div class="note-item">${escHtml(n.message)}</div>`;
                });
            }
        }

        content.innerHTML = html;
        container.scrollIntoView({ behavior: 'smooth' });
    }

    function escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // Bind all forms
    bindForm('formMasterShape', 'statusMasterShape');
    bindForm('formMasterDot', 'statusMasterDot');
    bindForm('formShape', 'statusShape');
    bindForm('formDot', 'statusDot');

    // Pre-fill petugas filter from URL
    const urlParams = new URLSearchParams(window.location.search);
})();

