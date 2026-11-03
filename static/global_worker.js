/**
 * WilkerStat Checker — Global Background Worker Tracker
 * Memantau task background di seluruh halaman via localStorage & API
 */
(function() {
    'use strict';

    const STORAGE_KEY = 'wilkerstat_active_tasks';
    const POLL_INTERVAL = 2500;
    let pollTimer = null;

    function getTasks() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    function saveTasks(tasks) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
        } catch (e) {}
    }

    function trackTask(taskId, filename, uploadType) {
        const tasks = getTasks().filter(t => t.id !== taskId);
        tasks.push({
            id: taskId,
            filename: filename || 'File',
            type: uploadType || '',
            start: Date.now()
        });
        saveTasks(tasks);
        updateUI();
        startPolling();
    }

    function removeTask(taskId) {
        const tasks = getTasks().filter(t => t.id !== taskId);
        saveTasks(tasks);
        updateUI();
        if (tasks.length === 0 && pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    function showToast(title, message, isError) {
        let container = document.getElementById('globalToastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'globalToastContainer';
            container.className = 'global-toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'global-toast ' + (isError ? 'toast-error' : 'toast-success');
        toast.innerHTML = `
            <div style="font-weight:600;margin-bottom:2px;">${title}</div>
            <div style="font-size:0.82rem;color:var(--text-muted,#475569);">${message}</div>
        `;
        toast.onclick = () => {
            window.location.href = '/history';
        };

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 6000);
    }

    function updateUI() {
        const tasks = getTasks();
        const badge = document.getElementById('globalWorkerBadge');
        const text = document.getElementById('globalWorkerText');

        if (!badge) return;

        if (tasks.length > 0) {
            badge.style.display = 'inline-flex';
            if (text) {
                const current = tasks[0];
                text.textContent = tasks.length === 1 
                    ? `Memproses ${current.filename}...`
                    : `Memproses ${tasks.length} file...`;
            }
        } else {
            badge.style.display = 'none';
        }
    }

    async function checkTasks() {
        const tasks = getTasks();
        if (tasks.length === 0) {
            // Cek juga ke server apakah ada task aktif di background yang tidak ada di localStorage
            try {
                const res = await fetch('/api/worker/active');
                const data = await res.json();
                if (data.active && data.tasks && data.tasks.length > 0) {
                    const badge = document.getElementById('globalWorkerBadge');
                    const text = document.getElementById('globalWorkerText');
                    if (badge) {
                        badge.style.display = 'inline-flex';
                        if (text) text.textContent = `Memproses ${data.tasks[0].filename}...`;
                    }
                } else {
                    updateUI();
                }
            } catch (e) {}
            return;
        }

        for (const t of tasks) {
            try {
                const res = await fetch(`/api/upload/status/${t.id}`);
                if (!res.ok) {
                    if (res.status === 404) removeTask(t.id);
                    continue;
                }
                const data = await res.json();

                if (data.status === 'done') {
                    removeTask(t.id);
                    const acc = data.result && data.result.accepted !== false;
                    showToast(
                        acc ? '✅ Validasi Selesai' : '❌ File Ditolak',
                        `${t.filename}: ${acc ? 'Data berhasil dimuat.' : 'Klik untuk melihat riwayat.'}`,
                        !acc
                    );
                } else if (data.status === 'error') {
                    removeTask(t.id);
                    showToast('❌ Gagal Memproses', `${t.filename}: ${data.error || 'Terjadi kesalahan'}`, true);
                }
            } catch (e) {
                // Network error, coba lagi nanti
            }
        }
        updateUI();
    }

    function startPolling() {
        if (!pollTimer) {
            pollTimer = setInterval(checkTasks, POLL_INTERVAL);
        }
        checkTasks();
    }

    // Export API
    window.GlobalWorker = {
        trackTask,
        removeTask,
        getTasks
    };

    // Reusable server-synced datetime formatter
    window.formatServerTime = function (ts) {
        if (!ts) return '-';
        const tz = (document.body && document.body.dataset.serverTz) ? document.body.dataset.serverTz : 'WITA';
        const clean = String(ts).replace('T', ' ').trim();
        const m = clean.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
        if (m) {
            const [, y, mo, d, h, mi] = m;
            return `${d}/${mo}/${y} ${h}:${mi} ${tz}`;
        }
        return `${clean.slice(0, 16)} ${tz}`;
    };

    // Auto-init on page load
    document.addEventListener('DOMContentLoaded', () => {
        updateUI();
        startPolling();
    });
})();

