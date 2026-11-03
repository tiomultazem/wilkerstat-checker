/* ===== history.js ===== */
(function () {
    'use strict';

    function formatTime(ts) {
        if (window.formatServerTime) return window.formatServerTime(ts);
        if (!ts) return '-';
        const tz = (document.body && document.body.dataset.serverTz) ? document.body.dataset.serverTz : 'WITA';
        const clean = String(ts).replace('T', ' ').trim();
        const m = clean.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
        if (m) {
            const [, y, mo, d, h, mi] = m;
            return `${d}/${mo}/${y} ${h}:${mi} ${tz}`;
        }
        return `${clean.slice(0, 16)} ${tz}`;
    }

    async function loadHistory() {
        const res = await fetch('/api/upload/log');
        const data = await res.json();
        const tbody = document.getElementById('historyBody');
        const logs = data.logs || [];

        if (!logs.length) {
            tbody.innerHTML = '<tr><td colspan="10" class="loading-msg">Belum ada riwayat upload.</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(log => {
            const badgeClass = log.status === 'done' ? 'badge-done'
                : log.status === 'rejected' ? 'badge-rejected'
                : log.status === 'processing' ? 'badge-processing'
                : 'badge-note';

            const summary = log.summary || {};
            const warnCount = (summary.warnings || []).length;
            const noteCount = (summary.notes || []).length;
            const errorTxt = (summary.reject_reasons || []).join('; ').slice(0, 60);

            return `<tr>
                <td>${escHtml(formatTime(log.ts))}</td>
                <td>${escHtml(log.hostname || log.ip || '-')}</td>
                <td title="${escHtml(log.filename || '')}">${escHtml((log.filename || '-').slice(-30))}</td>
                <td>${escHtml(uploadTypeLabel(log.upload_type))}</td>
                <td>${log.record_count || 0}</td>
                <td>${log.new_count || 0}</td>
                <td>${log.updated_count || 0}</td>
                <td>${log.unchanged_count || 0}</td>
                <td><span class="badge ${badgeClass}">${escHtml(log.status)}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="showDetail(${log.id})">Lihat</button>
                </td>
            </tr>`;
        }).join('');

        // Store for modal detail
        window._historyLogs = {};
        logs.forEach(l => { window._historyLogs[l.id] = l; });
    }

    function uploadTypeLabel(t) {
        return { master_shape: 'Master Poligon', master_dot: 'Master Titik', shape: 'Shape', dot: 'Titik' }[t] || t;
    }

    window.showDetail = function (id) {
        const log = window._historyLogs[id];
        if (!log) return;
        const summary = log.summary || {};
        document.getElementById('modalTitle').textContent = `Upload #${id} — ${log.filename}`;

        let html = `<div style="margin-bottom:10px;font-size:12px;color:var(--text-muted)">Waktu Upload: <b style="color:var(--text)">${escHtml(formatTime(log.ts))}</b></div>
        <div class="result-stats">
            <div class="result-stat"><span class="val">${log.new_count || 0}</span> baru</div>
            <div class="result-stat"><span class="val">${log.updated_count || 0}</span> update</div>
            <div class="result-stat"><span class="val">${log.unchanged_count || 0}</span> sama</div>
        </div>`;

        if (summary.error) {
            html += `<h4 style="color:var(--danger);margin:12px 0 6px">💥 Galat Sistem (Internal)</h4>`;
            html += `<div class="error-item" style="font-family:monospace;white-space:pre-wrap;word-break:break-all;">${escHtml(summary.error)}</div>`;
        }
        if (summary.traceback) {
            html += `<details style="margin-top:6px;"><summary style="cursor:pointer;color:var(--text-muted);font-size:12px;">Lihat Traceback</summary><pre style="background:var(--bg-card);padding:8px;border-radius:4px;font-size:11px;overflow-x:auto;white-space:pre-wrap;">${escHtml(summary.traceback)}</pre></details>`;
        }
        if (summary.reject_reasons && summary.reject_reasons.length) {
            html += `<h4 style="color:var(--danger);margin:12px 0 6px">❌ Alasan Tolak</h4>`;
            summary.reject_reasons.forEach(r => { html += `<div class="error-item">${escHtml(r)}</div>`; });
        }
        if (summary.warnings && summary.warnings.length) {
            html += `<h4 style="color:var(--warning);margin:12px 0 6px">⚠ Peringatan (${summary.warnings.length})</h4>`;
            summary.warnings.slice(0, 30).forEach(w => { html += `<div class="warn-item">${escHtml(w.message)}</div>`; });
            if (summary.warnings.length > 30) html += `<div class="note-item">dan ${summary.warnings.length - 30} peringatan lainnya...</div>`;
        }
        if (summary.notes && summary.notes.length) {
            html += `<h4 style="color:var(--info);margin:12px 0 6px">ℹ Catatan (${summary.notes.length})</h4>`;
            summary.notes.forEach(n => { html += `<div class="note-item">${escHtml(n.message)}</div>`; });
        }

        document.getElementById('modalBody').innerHTML = html;
        document.getElementById('modalOverlay').style.display = 'flex';
    };

    document.getElementById('modalClose').addEventListener('click', () => {
        document.getElementById('modalOverlay').style.display = 'none';
    });
    document.getElementById('modalOverlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) e.currentTarget.style.display = 'none';
    });

    // Trend chart using canvas (no lib)
    async function loadTrend() {
        const res = await fetch('/api/snapshots');
        const data = await res.json();
        const snapshots = (data.snapshots || []).reverse().slice(-30);
        if (!snapshots.length) return;

        const canvas = document.getElementById('trendCanvas');
        const ctx = canvas.getContext('2d');
        const W = canvas.offsetWidth;
        const H = canvas.offsetHeight;
        canvas.width = W;
        canvas.height = H;

        // Collect all petugas
        const allPetugas = new Set();
        snapshots.forEach(s => Object.keys(s.data).forEach(p => allPetugas.add(p)));
        const petugasList = [...allPetugas];

        const colours = [
            '#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed',
            '#0891b2', '#be185d', '#065f46', '#92400e', '#1e3a5f',
        ];

        const labels = snapshots.map(s => s.ts.slice(5, 16));
        const pad = { l: 50, r: 20, t: 20, b: 40 };
        const chartW = W - pad.l - pad.r;
        const chartH = H - pad.t - pad.b;

        // Find max value
        let maxVal = 1;
        snapshots.forEach(s => {
            petugasList.forEach(p => {
                const v = (s.data[p] || {}).upload_shape || 0;
                if (v > maxVal) maxVal = v;
            });
        });

        ctx.clearRect(0, 0, W, H);

        // Grid lines
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i++) {
            const y = pad.t + chartH - (i / 5) * chartH;
            ctx.beginPath();
            ctx.moveTo(pad.l, y);
            ctx.lineTo(pad.l + chartW, y);
            ctx.stroke();
            ctx.fillStyle = '#94a3b8';
            ctx.font = '11px Segoe UI';
            ctx.textAlign = 'right';
            ctx.fillText(Math.round(i / 5 * maxVal), pad.l - 4, y + 4);
        }

        // X labels
        const step = Math.max(1, Math.floor(labels.length / 8));
        labels.forEach((lbl, i) => {
            if (i % step !== 0) return;
            const x = pad.l + (i / Math.max(labels.length - 1, 1)) * chartW;
            ctx.fillStyle = '#94a3b8';
            ctx.font = '10px Segoe UI';
            ctx.textAlign = 'center';
            ctx.fillText(lbl, x, H - pad.b + 14);
        });

        // Lines per petugas
        petugasList.forEach((p, pi) => {
            ctx.strokeStyle = colours[pi % colours.length];
            ctx.lineWidth = 2;
            ctx.beginPath();
            snapshots.forEach((s, i) => {
                const v = (s.data[p] || {}).upload_shape || 0;
                const x = pad.l + (i / Math.max(snapshots.length - 1, 1)) * chartW;
                const y = pad.t + chartH - (v / maxVal) * chartH;
                i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            });
            ctx.stroke();
        });
    }

    function escHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    loadHistory();
    loadTrend();
})();

