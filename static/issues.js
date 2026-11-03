/* ===== issues.js ===== */
(function () {
    'use strict';

    let allIssues = [];
    let petugasList = [];

    async function loadPetugas() {
        try {
            const res = await fetch('/api/filters');
            const data = await res.json();
            petugasList = data.petugas || [];
            const sel = document.getElementById('filterPetugas');
            petugasList.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p;
                opt.textContent = p;
                sel.appendChild(opt);
            });
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('petugas')) sel.value = urlParams.get('petugas');
        } catch (e) {
            console.error('Failed to load petugas', e);
        }
    }

    function applyClientSearch() {
        const search = document.getElementById('searchInput').value.trim().toLowerCase();
        const filtered = search
            ? allIssues.filter(i => (i.target_id || '').toLowerCase().includes(search)
                || JSON.stringify(i.detail || '').toLowerCase().includes(search))
            : allIssues;

        document.getElementById('issueCount').textContent = `${filtered.length} masalah ditemukan`;
        renderTable(filtered);
    }

    async function loadIssues() {
        document.getElementById('issuesLoading').style.display = 'block';
        document.getElementById('issueCount').textContent = '';
        document.getElementById('issuesTable').innerHTML = '';

        const type = document.getElementById('filterType').value;
        const petugas = document.getElementById('filterPetugas').value;

        let url = '/api/issues?';
        if (type) url += `type=${encodeURIComponent(type)}&`;
        if (petugas) url += `petugas=${encodeURIComponent(petugas)}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            allIssues = data.issues || [];
        } catch (e) {
            allIssues = [];
        } finally {
            document.getElementById('issuesLoading').style.display = 'none';
        }

        applyClientSearch();
    }

    function renderTable(issues) {
        if (!issues.length) {
            document.getElementById('issuesTable').innerHTML = '<p class="loading-msg">Tidak ada masalah ditemukan.</p>';
            return;
        }

        const tz = (document.body && document.body.dataset.serverTz) ? document.body.dataset.serverTz : '';
        const tzLabel = tz ? ` (${tz})` : '';

        let html = `<table class="data-table">
            <thead><tr>
                <th>Jenis</th>
                <th>Target ID</th>
                <th>Petugas</th>
                <th>Severity</th>
                <th>Waktu${tzLabel}</th>
                <th>Detail</th>
                <th>Aksi</th>
            </tr></thead>
            <tbody>`;

        issues.forEach(issue => {
            const detail = issue.detail || {};
            const badgeClass = issue.severity === 'warning' ? 'badge-warning'
                : issue.severity === 'note' ? 'badge-note' : 'badge-error';

            let detailStr = '';
            if (issue.issue_type === 'multipart') {
                detailStr = `${detail.num_parts || '?'} bagian`;
            } else if (issue.issue_type === 'overlap' || issue.issue_type === 'gap') {
                detailStr = `${(detail.area_m2 || 0).toFixed(2)} m²`;
                if (detail.scope) detailStr += ` · ${detail.scope}`;
            } else if (issue.issue_type === 'null_col') {
                detailStr = `${detail.count || '?'} sel kosong di kolom ${detail.column || '?'}`;
            } else if (issue.issue_type === 'dot_offside') {
                detailStr = `Jarak: ${detail.jarak_m != null ? detail.jarak_m + ' m' : '?'}`;
            } else {
                detailStr = JSON.stringify(detail).slice(0, 80);
            }

            const actionBtn = issue.issue_type === 'multipart'
                ? `<button class="btn btn-sm ${issue.severity === 'note' ? 'btn-confirm confirmed' : 'btn-confirm'}"
                    data-id="${escHtml(issue.target_id || '')}"
                    data-confirmed="${issue.severity === 'note' ? '1' : '0'}"
                    onclick="toggleMultipartConfirm(this)">
                    ${issue.severity === 'note' ? '✓ Sah' : 'Tandai Sah'}
                </button>` : '';

            html += `<tr>
                <td>${escHtml(issue.issue_type)}</td>
                <td><code>${escHtml(issue.target_id || '-')}</code></td>
                <td>${escHtml(issue.petugas || '-')}</td>
                <td><span class="badge ${badgeClass}">${escHtml(issue.severity)}</span></td>
                <td>${escHtml(window.formatServerTime ? window.formatServerTime(issue.created_at) : (issue.created_at || '').slice(0, 16))}</td>
                <td>${escHtml(detailStr)}</td>
                <td>${actionBtn}</td>
            </tr>`;
        });

        html += '</tbody></table>';
        document.getElementById('issuesTable').innerHTML = html;
    }

    window.toggleMultipartConfirm = async function (btn) {
        const idsubsls = btn.dataset.id;
        const currentlyConfirmed = btn.dataset.confirmed === '1';
        const newConfirmed = !currentlyConfirmed;

        const res = await fetch('/api/multipart/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idsubsls, confirm: newConfirmed })
        });

        if (res.ok) {
            btn.dataset.confirmed = newConfirmed ? '1' : '0';
            btn.textContent = newConfirmed ? '✓ Sah' : 'Tandai Sah';
            btn.className = `btn btn-sm btn-confirm${newConfirmed ? ' confirmed' : ''}`;
        }
    };

    window.exportIssues = function (type) {
        const petugas = document.getElementById('filterPetugas').value;
        const isGeo = type.endsWith('_geojson');
        let url = `/api/export/${type}`;
        const params = [];
        if (petugas) params.push(`petugas=${encodeURIComponent(petugas)}`);
        if (!isGeo) params.push('format=xlsx');
        if (params.length) url += '?' + params.join('&');
        window.location.href = url;
    };

    function escHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Read URL params
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('type')) document.getElementById('filterType').value = urlParams.get('type');

    // Live reactive event listeners
    document.getElementById('filterType').addEventListener('change', loadIssues);
    document.getElementById('filterPetugas').addEventListener('change', loadIssues);

    let searchDebounceTimer = null;
    document.getElementById('searchInput').addEventListener('input', () => {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(applyClientSearch, 200);
    });

    document.getElementById('btnReset').addEventListener('click', () => {
        document.getElementById('filterType').value = '';
        document.getElementById('filterPetugas').value = '';
        document.getElementById('searchInput').value = '';
        loadIssues();
    });

    loadPetugas().then(loadIssues);
})();

