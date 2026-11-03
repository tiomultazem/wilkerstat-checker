/* ===== home.js — Dashboard + Full Map (merged) ===== */
(function () {
    'use strict';

    let statsData = null;
    let petugasColours = {};
    let currentTab = 'poligon';
    let currentPolyMode = 'progress';
    let currentDotMode = 'progress';
    let expandedPetugasSet = new Set();

    // Map state
    let map = null;
    let shapesGeoJSON = null;
    let colourBy = 'petugas';
    let colourMaps = {};
    // Dropdown checklist state
    let ddState = { kec: [], desa: [], sls: [] };

    // ---- Tab switching ----
    document.querySelectorAll('.tab-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-pill').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            currentTab = btn.dataset.tab;
            document.getElementById(`tab-${currentTab}`).classList.add('active');
            renderBars();
        });
    });

    // ---- Mode switching ----
    document.querySelectorAll('#modePoly .mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#modePoly .mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPolyMode = btn.dataset.mode;
            renderBars();
        });
    });
    document.querySelectorAll('#modeDot .mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#modeDot .mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentDotMode = btn.dataset.mode;
            renderBars();
        });
    });

    // ---- Load stats ----
    async function loadStats() {
        const [statsRes, coloursRes] = await Promise.all([
            fetch('/api/petugas/stats'),
            fetch('/api/colours/petugas'),
        ]);
        statsData = await statsRes.json();
        petugasColours = await coloursRes.json();
        renderBars();
    }

    function updateTopStrip(html, pct) {
        const summaryEl = document.getElementById('topSummary');
        const barEl = document.getElementById('topProgressBar');
        if (summaryEl) summaryEl.innerHTML = html;
        if (barEl) {
            const safePct = typeof pct === 'number' && !isNaN(pct) ? Math.min(Math.max(pct, 0), 100) : 0;
            barEl.style.width = safePct + '%';
        }
    }

    function renderBars() {
        if (!statsData) return;
        if (currentTab === 'poligon') renderPolyBars();
        else renderDotBars();
    }

    function renderPolyBars() {
        const { stats, petugas_targets, master_shape_total, unassigned_shape_count } = statsData;
        const mode = currentPolyMode;
        const container = document.getElementById('polyBars');

        const allPetugas = new Set([
            ...Object.keys(stats),
            ...Object.keys(petugas_targets || {})
        ]);

        let rows = [];
        let totalUpload = 0, totalIssue = 0;
        const realTarget = master_shape_total || 0;

        allPetugas.forEach(p => {
            if (p === '(tanpa petugas)') return;
            const s = stats[p] || {};
            const target = (petugas_targets || {})[p] || realTarget;
            const upload = s.upload_shape || 0;
            const val = mode === 'progress' ? upload
                : mode === 'multipart' ? (s.multipart || 0)
                : mode === 'gap' ? (s.gap || s.gap_count || 0)
                : mode === 'duplicate' ? (s.duplicate_idsubsls || 0)
                : (s.overlap || s.overlap_count || 0);
            totalUpload += upload;
            totalIssue += val;
            rows.push({ petugas: p, val, target, upload });
        });

        // Tambah bar SLS Belum Diupload jika mode progress
        const unassigned = unassigned_shape_count || 0;
        if (mode === 'progress' && unassigned > 0) {
            rows.push({
                petugas: '(Belum Diupload)',
                val: unassigned,
                target: realTarget,
                upload: unassigned,
                isUnassigned: true
            });
        }

        rows.sort((a, b) => b.val - a.val);
        const maxVal = Math.max(...rows.map(r => r.val), 1);

        // Update Top Progress Strip
        const pct = realTarget > 0 ? Math.round(totalUpload / realTarget * 100) : 0;
        if (mode === 'progress') {
            updateTopStrip(`
                <span>Terupload: <strong>${totalUpload}</strong></span>
                <span>Target: <strong>${realTarget || '?'}</strong></span>
                <span class="badge-pct">${pct}% Beres</span>
            `, pct);
        } else {
            const label = mode === 'multipart' ? 'Multipart'
                : mode === 'gap' ? 'Gap'
                : mode === 'duplicate' ? 'Duplikat IDSUBSLS'
                : 'Overlap';
            updateTopStrip(`
                <span>Mode: <strong>${label}</strong></span>
                <span>Total Isu: <strong>${totalIssue.toFixed(1)}</strong></span>
            `, 0);
        }

        container.innerHTML = '';
        rows.forEach(({ petugas, val, target, upload, isUnassigned }) => {
            const isGrey = !isUnassigned && (upload === 0);
            const pctVal = mode === 'progress'
                ? (target > 0 ? Math.min(val / target * 100, 100) : 0)
                : (maxVal > 0 ? val / maxVal * 100 : 0);

            const labelText = isGrey
                ? `0 / ${target} (Belum upload)`
                : mode === 'progress'
                ? `${upload}${target ? ' / ' + target : ''}`
                : (val % 1 === 0 ? val.toString() : val.toFixed(3).replace(/\.?0+$/, ''));

            const barColour = (isUnassigned || isGrey) ? '#94a3b8'
                : mode === 'progress' ? (petugasColours[petugas] || '#2563eb')
                : mode === 'multipart' ? '#f59e0b'
                : mode === 'gap' ? '#6366f1'
                : mode === 'duplicate' ? '#c026d3'
                : '#ef4444';

            const dotStyle = `display:inline-block;width:8px;height:8px;border-radius:50%;background:${(isUnassigned || isGrey) ? '#94a3b8' : (petugasColours[petugas] || '#94a3b8')};margin-right:6px;flex-shrink:0`;
            const row = document.createElement('div');
            row.className = 'petugas-bar-row' + (isGrey ? ' is-unsubmitted' : '');
            row.innerHTML = `
                <div class="bar-header">
                    <span class="bar-name"><span style="${dotStyle}"></span>${escHtml(petugas)}</span>
                    <span class="bar-label">${escHtml(labelText)}<span class="bar-toggle-icon">▾</span></span>
                </div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:${pctVal}%;background:${barColour}"></div>
                </div>
                <div class="petugas-error-dropdown"></div>
            `;
            row.addEventListener('click', () => {
                togglePetugasCard(row, petugas, 'shape', mode, isGrey);
            });
            container.appendChild(row);
            if (expandedPetugasSet.has(petugas)) {
                setTimeout(() => togglePetugasCard(row, petugas, 'shape', mode, isGrey), 0);
            }
        });
    }

    function renderDotBars() {
        const { stats, dot_targets, master_dot_total, dot_total } = statsData;
        const mode = currentDotMode;
        const container = document.getElementById('dotBars');

        const allPetugas = new Set([
            ...Object.keys(stats),
            ...Object.keys(dot_targets || {})
        ]);

        let rows = [];
        let totalInside = 0, totalOffside = 0, totalTarget = 0;

        allPetugas.forEach(p => {
            const s = stats[p] || {};
            const target = (dot_targets || {})[p] || 0;
            const inside = s.dot_inside || 0;
            const offside = s.offside || 0;
            const val = mode === 'progress' ? inside
                : mode === 'offside' ? offside
                : (s.flag_position || 0);
            totalInside += inside;
            totalOffside += offside;
            totalTarget += target;
            rows.push({ petugas: p, val, target, inside, offside });
        });

        rows.sort((a, b) => b.val - a.val);
        const maxVal = Math.max(...rows.map(r => r.val), 1);

        const total = totalTarget || statsData.dot_total || master_dot_total || 0;
        const pct = total > 0 ? Math.round(totalInside / total * 100) : 0;

        if (mode === 'progress') {
            updateTopStrip(`
                <span>Sudah INSIDE: <strong>${totalInside}</strong></span>
                <span>Masih Offside: <strong>${totalOffside}</strong></span>
                <span>Total Titik: <strong>${total}</strong></span>
                <span class="badge-pct">${pct}% Beres</span>
            `, pct);
        } else {
            const label = mode === 'offside' ? 'Masih Offside' : 'Sudah Digeser';
            const sumVal = rows.reduce((a, r) => a + r.val, 0);
            updateTopStrip(`
                <span>Mode: <strong>${label}</strong></span>
                <span>Total: <strong>${sumVal}</strong></span>
            `, 0);
        }

        container.innerHTML = '';
        rows.forEach(({ petugas, val, target, inside, offside }) => {
            const isGrey = (inside === 0 && offside === 0);
            const pctVal = mode === 'progress'
                ? (target > 0 ? Math.min(inside / target * 100, 100) : 0)
                : (maxVal > 0 ? val / maxVal * 100 : 0);

            const labelText = isGrey
                ? `0 / ${target} (Belum upload)`
                : mode === 'progress'
                ? `${inside} dalam / ${offside} offside${target ? ' (total: ' + target + ')' : ''}`
                : val.toString();

            const barColour = isGrey ? '#94a3b8'
                : mode === 'progress' ? (petugasColours[petugas] || '#2563eb')
                : mode === 'offside' ? '#ef4444'
                : '#10b981';

            const dotStyle = `display:inline-block;width:8px;height:8px;border-radius:50%;background:${isGrey ? '#94a3b8' : (petugasColours[petugas] || '#94a3b8')};margin-right:6px;flex-shrink:0`;
            const row = document.createElement('div');
            row.className = 'petugas-bar-row' + (isGrey ? ' is-unsubmitted' : '');
            row.innerHTML = `
                <div class="bar-header">
                    <span class="bar-name"><span style="${dotStyle}"></span>${escHtml(petugas)}</span>
                    <span class="bar-label">${escHtml(labelText)}<span class="bar-toggle-icon">▾</span></span>
                </div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:${pctVal}%;background:${barColour}"></div>
                </div>
                <div class="petugas-error-dropdown"></div>
            `;
            row.addEventListener('click', () => {
                togglePetugasCard(row, petugas, 'dot', mode, isGrey);
            });
            container.appendChild(row);
            if (expandedPetugasSet.has(petugas)) {
                setTimeout(() => togglePetugasCard(row, petugas, 'dot', mode, isGrey), 0);
            }
        });
    }

    let highlightMarker = null;
    let slsBlinkTimer = null;

    function ensureHighlightLayers() {
        if (!map.getSource('highlight-shape')) {
            map.addSource('highlight-shape', {
                type: 'geojson',
                data: { type: 'FeatureCollection', features: [] }
            });
            map.addLayer({
                id: 'highlight-shape-fill',
                type: 'fill',
                source: 'highlight-shape',
                paint: {
                    'fill-color': '#f59e0b',
                    'fill-opacity': 0.7
                }
            });
            map.addLayer({
                id: 'highlight-shape-outline',
                type: 'line',
                source: 'highlight-shape',
                paint: {
                    'line-color': '#d97706',
                    'line-width': 3.5
                }
            });
        }
    }

    function blinkHighlightSLS(idsubsls) {
        if (!map) return;
        ensureHighlightLayers();

        if (slsBlinkTimer) {
            clearInterval(slsBlinkTimer);
            slsBlinkTimer = null;
        }

        let feat = null;
        if (shapesGeoJSON && shapesGeoJSON.features) {
            feat = shapesGeoJSON.features.find(f => f.properties && f.properties.idsubsls === idsubsls);
        }

        const src = map.getSource('highlight-shape');
        if (!src) return;

        if (feat) {
            src.setData({ type: 'FeatureCollection', features: [feat] });
        }

        let ticks = 0;
        slsBlinkTimer = setInterval(() => {
            ticks++;
            const isVisible = (ticks % 2 === 0);
            if (map.getLayer('highlight-shape-fill')) {
                map.setPaintProperty('highlight-shape-fill', 'fill-opacity', isVisible ? 0.7 : 0.05);
            }
            if (map.getLayer('highlight-shape-outline')) {
                map.setPaintProperty('highlight-shape-outline', 'line-opacity', isVisible ? 1.0 : 0.1);
            }

            if (ticks >= 10) { // 10 x 300ms = 3000ms = 3 detik
                clearInterval(slsBlinkTimer);
                slsBlinkTimer = null;
                src.setData({ type: 'FeatureCollection', features: [] });
            }
        }, 300);
    }

    function focusErrorOnMap(item) {
        if (!map) return;
        if (highlightMarker) {
            highlightMarker.remove();
            highlightMarker = null;
        }

        if (item.bbox && Array.isArray(item.bbox) && item.bbox.length === 4) {
            const [minx, miny, maxx, maxy] = item.bbox;
            if (!isNaN(minx) && !isNaN(miny) && !isNaN(maxx) && !isNaN(maxy)) {
                map.fitBounds([[minx, miny], [maxx, maxy]], {
                    padding: 80,
                    maxZoom: 18,
                    duration: 1000
                });
            }
        } else if (item.lon != null && item.lat != null) {
            map.flyTo({
                center: [item.lon, item.lat],
                zoom: 17,
                essential: true,
                duration: 1000
            });
        }

        // SLS upload: gunakan highlight berkedip 3 detik tanpa pinpoint marker
        if (item.category === 'shape' && item.issue_type === 'SLS') {
            blinkHighlightSLS(item.target_id);
            return;
        }

        if (item.issue_type === 'duplicate_idsubsls' || item.issue_type === 'duplicate') {
            blinkHighlightSLS(item.target_id);
        }

        if (item.lon != null && item.lat != null) {
            const isOk = item.issue_type === 'INSIDE';
            const isDup = item.issue_type && (item.issue_type.includes('duplicate') || item.issue_type === 'duplicate_idsubsls');
            const markerColor = isOk ? '#2563eb' : (isDup ? '#c026d3' : '#ef4444');
            const popupHtml = `
                <div style="font-size:12px; line-height:1.4;">
                    <div style="font-weight:700; color:${markerColor}; margin-bottom:2px;">[${escHtml(item.issue_type)}]</div>
                    <div style="font-weight:600;">${escHtml(item.label)}</div>
                    ${item.jarak_m != null ? `<div style="font-size:11px; color:#64748b;">Jarak: ${item.jarak_m} m</div>` : ''}
                </div>
            `;
            highlightMarker = new maplibregl.Marker({ color: markerColor })
                .setLngLat([item.lon, item.lat])
                .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(popupHtml))
                .addTo(map);
            highlightMarker.togglePopup();
        }
    }

    async function togglePetugasCard(row, petugas, category, mode, isGrey) {
        const isExpanded = row.classList.contains('expanded');

        if (isExpanded) {
            row.classList.remove('expanded');
            expandedPetugasSet.delete(petugas);
            return;
        }

        row.classList.add('expanded');
        expandedPetugasSet.add(petugas);
        const dropdown = row.querySelector('.petugas-error-dropdown');
        if (!dropdown) return;
        dropdown.onclick = (e) => e.stopPropagation();

        if (isGrey) {
            dropdown.innerHTML = `<div class="error-empty-msg">Petugas ini belum mengunggah data apa pun.</div>`;
            return;
        }

        const isProgress = (mode === 'progress' || mode === 'status');
        dropdown.innerHTML = `
            <div class="dropdown-search-box">
                <input type="text" class="dropdown-search-input" placeholder="🔍 Cari (contoh: jaro rt 002)..." />
            </div>
            <div class="error-list-container">
                <div class="error-empty-msg">${isProgress ? (petugas === '(Belum Diupload)' ? '⏳ Memuat daftar SLS belum diupload...' : '⏳ Memuat daftar hasil upload...') : '⏳ Memuat detail error...'}</div>
            </div>
        `;

        const searchInput = dropdown.querySelector('.dropdown-search-input');
        const listContainer = dropdown.querySelector('.error-list-container');

        searchInput.addEventListener('click', (e) => e.stopPropagation());

        let page = 1;
        let searchQuery = '';
        let debounceTimer = null;

        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchQuery = e.target.value.trim();
                page = 1;
                loadPage(1);
            }, 250);
        });

        async function loadPage(p) {
            try {
                let url = `/api/petugas/${encodeURIComponent(petugas)}/errors?category=${category}&mode=${encodeURIComponent(mode)}&page=${p}&per_page=50`;
                if (searchQuery) url += `&q=${encodeURIComponent(searchQuery)}`;
                const res = await fetch(url);
                const data = await res.json();
                renderErrorList(data, p);
            } catch (err) {
                listContainer.innerHTML = `<div class="error-empty-msg" style="color:#ef4444;">Gagal memuat: ${escHtml(err.message)}</div>`;
            }
        }

        function renderErrorList(data, p) {
            if (p === 1) listContainer.innerHTML = '';
            if (!data.items || data.items.length === 0) {
                if (p === 1) {
                    const emptyMsg = searchQuery
                        ? `Tidak ada data yang cocok dengan "${escHtml(searchQuery)}".`
                        : (isProgress
                            ? (category === 'shape' ? (petugas === '(Belum Diupload)' ? 'Semua SLS master sudah terupload.' : 'Belum ada poligon SLS terupload.') : 'Belum ada titik terupload.')
                            : '✅ Tidak ada isu ditemukan.');
                    listContainer.innerHTML = `<div class="error-empty-msg">${emptyMsg}</div>`;
                }
                return;
            }

            let scrollBox = listContainer.querySelector('.error-list-scroll');
            if (!scrollBox) {
                scrollBox = document.createElement('div');
                scrollBox.className = 'error-list-scroll';
                listContainer.appendChild(scrollBox);
            }

            data.items.forEach(item => {
                const el = document.createElement('div');
                el.className = 'error-list-item';
                const badgeClass = item.issue_type ? item.issue_type.toLowerCase().split(' ')[0] : 'sls';
                el.innerHTML = `
                    <div style="display:flex;align-items:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        <span class="error-badge ${escHtml(badgeClass)}">${escHtml(item.issue_type)}</span>
                        <span style="overflow:hidden;text-overflow:ellipsis;" title="${escHtml(item.label)}">${escHtml(item.label)}</span>
                    </div>
                    <span style="font-size:10px;color:#64748b;margin-left:6px;flex-shrink:0;">${item.jarak_m != null ? item.jarak_m + 'm' : '📍'}</span>
                `;
                el.addEventListener('click', (e) => {
                    e.stopPropagation();
                    focusErrorOnMap(item);
                });
                scrollBox.appendChild(el);
            });

            const oldBtn = listContainer.querySelector('.btn-more-errors');
            if (oldBtn) oldBtn.remove();

            if (data.has_more) {
                const btn = document.createElement('button');
                btn.className = 'btn-more-errors';
                btn.innerHTML = `Muat 50 lebih (${data.items.length * p} dari ${data.total}) ↓`;
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    page++;
                    loadPage(page);
                });
                listContainer.appendChild(btn);
            }
        }

        loadPage(page);
    }

    // ================================================================
    //  DROPDOWN CHECKLIST
    // ================================================================
    window.toggleDropdown = function (id) {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('open');
    };

    function buildCheckPanel(panelId, items, stateKey, onChange) {
        const panel = document.getElementById(panelId);
        panel.innerHTML = '';
        items.forEach(({ value, label }) => {
            const checked = ddState[stateKey].includes(value);
            const id = `chk_${stateKey}_${value.replace(/\s/g, '_')}`;
            const div = document.createElement('label');
            div.className = 'dd-item';
            div.innerHTML = `<input type="checkbox" id="${id}" value="${escHtml(value)}" ${checked ? 'checked' : ''}> ${escHtml(label)}`;
            div.querySelector('input').addEventListener('change', e => {
                if (e.target.checked) {
                    if (!ddState[stateKey].includes(value)) ddState[stateKey].push(value);
                } else {
                    ddState[stateKey] = ddState[stateKey].filter(v => v !== value);
                }
                updateTriggerLabel(stateKey);
                if (onChange) onChange();
            });
            panel.appendChild(div);
        });
    }

    function updateTriggerLabel(stateKey) {
        const ddId = stateKey === 'kec' ? 'ddKec' : stateKey === 'desa' ? 'ddDesa' : 'ddSLS';
        const el = document.getElementById(ddId);
        const trigger = el.querySelector('.dd-trigger');
        const count = ddState[stateKey].length;
        const placeholder = stateKey === 'kec' ? 'kecamatan' : stateKey === 'desa' ? 'desa' : 'SLS';
        trigger.innerHTML = (count > 0 ? `${count} ${placeholder} dipilih` : `Pilih ${placeholder}…`) + ' <span class="dd-arrow">▾</span>';
    }

    async function loadFiltersUI() {
        const res = await fetch('/api/filters');
        const data = await res.json();

        buildCheckPanel('ddKecPanel', data.kecamatan.map(k => ({ value: k, label: k })), 'kec', null);
        buildCheckPanel('ddDesaPanel', data.desa.map(d => ({ value: d.name, label: d.name })), 'desa', null);
        buildCheckPanel('ddSLSPanel', data.sls.map(s => ({ value: s.id, label: s.name })), 'sls', null);
    }

    // ================================================================
    //  MAP
    // ================================================================
    async function initMap() {
        const cfgRes = await fetch('/api/config');
        const cfg = await cfgRes.json();

        map = new maplibregl.Map({
            container: 'mainMap',
            attributionControl: false,
            style: {
                version: 8,
                glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
                sources: {
                    osm: {
                        type: 'raster',
                        tiles: [cfg.tile_url],
                        tileSize: 256,
                        attribution: cfg.tile_attribution,
                    }
                },
                layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
            },
            center: [115.0, -2.0],
            zoom: 6,
        });

        map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
        map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');
        map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');

        map.on('load', async () => {
            await loadFiltersUI();
            await loadMasterShapes(cfg);
            await loadShapes(cfg);
            setupLayerToggles();
            // Auto-load dots
            await toggleDotsLayer(true);
        });
    }

    async function loadMasterShapes(cfg) {
        const res = await fetch('/api/master/shapes/geojson');
        const data = await res.json();
        if (!data.features || data.features.length === 0) return;
        map.addSource('master-shapes', { type: 'geojson', data });
        map.addLayer({ id: 'master-shapes-fill', type: 'fill', source: 'master-shapes', paint: { 'fill-color': '#94a3b8', 'fill-opacity': 0.12 } });
        map.addLayer({ id: 'master-shapes-outline', type: 'line', source: 'master-shapes', paint: { 'line-color': '#94a3b8', 'line-width': 0.5, 'line-dasharray': [2, 2] } });
    }

    async function loadShapes(cfg) {
        const [shapesRes, kecColRes, desaColRes, slsColRes, petugasColRes] = await Promise.all([
            fetch('/api/shapes/geojson'),
            fetch('/api/colours/kec'),
            fetch('/api/colours/desa'),
            fetch('/api/colours/sls'),
            fetch('/api/colours/petugas'),
        ]);

        shapesGeoJSON = await shapesRes.json();
        colourMaps.kec = await kecColRes.json();
        colourMaps.desa = await desaColRes.json();
        colourMaps.sls = await slsColRes.json();
        colourMaps.petugas = await petugasColRes.json();

        if (!map.getSource('shapes')) {
            map.addSource('shapes', { type: 'geojson', data: shapesGeoJSON });
        }
        addShapeLayers(cfg);
        fitToData();
        setupHover();
        applyColour();
    }

    function addShapeLayers(cfg) {
        if (!map.getLayer('shapes-fill')) {
            map.addLayer({ id: 'shapes-fill', type: 'fill', source: 'shapes', paint: { 'fill-color': '#2563eb', 'fill-opacity': 0.4 } });
        }
        if (!map.getLayer('shapes-outline')) {
            map.addLayer({ id: 'shapes-outline', type: 'line', source: 'shapes', paint: { 'line-color': '#1e293b', 'line-width': 0.8 } });
        }
        if (!map.getLayer('shapes-label')) {
            const minZoom = (cfg && cfg.label_min_zoom != null) ? cfg.label_min_zoom : 11;
            map.addLayer({
                id: 'shapes-label', type: 'symbol', source: 'shapes',
                minzoom: minZoom,
                layout: {
                    'text-field': ['concat', ['get', 'nmdesa'], ' - ', ['get', 'nmsls'], ' [', ['get', 'kdsubsls'], ']'],
                    'text-size': [
                        'interpolate', ['linear'], ['zoom'],
                        11, 9,
                        13, 11,
                        16, 13
                    ],
                    'text-allow-overlap': false,
                    'text-optional': true,
                    'symbol-placement': 'point',
                },
                paint: {
                    'text-color': '#0f172a',
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 2.0
                }
            });
        }
    }

    function applyColour() {
        if (!map.getLayer('shapes-fill') || !shapesGeoJSON) return;
        const propMap = { kec: 'nmkec', desa: 'nmdesa', sls: 'idsubsls', petugas: 'petugas' };
        const prop = propMap[colourBy];
        const cmap = colourMaps[colourBy] || {};
        const vals = [...new Set(shapesGeoJSON.features.map(f => f.properties[prop]).filter(Boolean))];
        if (vals.length === 0) return;
        const expr = ['match', ['get', prop]];
        vals.forEach(v => { expr.push(v); expr.push(cmap[v] || '#94a3b8'); });
        expr.push('#94a3b8');
        map.setPaintProperty('shapes-fill', 'fill-color', expr);
    }

    function applyDisplayFilter() {
        if (!shapesGeoJSON) return;
        const kecs = ddState.kec;
        const desas = ddState.desa;
        const slss = ddState.sls;
        const filtered = {
            type: 'FeatureCollection',
            features: shapesGeoJSON.features.filter(f => {
                const p = f.properties;
                if (kecs.length && !kecs.includes(p.nmkec)) return false;
                if (desas.length && !desas.includes(p.nmdesa)) return false;
                if (slss.length && !slss.includes(p.idsubsls)) return false;
                return true;
            })
        };
        map.getSource('shapes').setData(filtered);
        applyColour();
    }

    function resetDisplayFilter() {
        ddState = { kec: [], desa: [], sls: [] };
        ['kec', 'desa', 'sls'].forEach(k => updateTriggerLabel(k));
        // Uncheck all checkboxes
        document.querySelectorAll('.dd-item input[type=checkbox]').forEach(cb => cb.checked = false);
        if (shapesGeoJSON) map.getSource('shapes').setData(shapesGeoJSON);
        applyColour();
    }

    function setupHover() {
        let popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
        let hoverTimer = null;
        map.on('mousemove', 'shapes-fill', e => {
            map.getCanvas().style.cursor = 'pointer';
            clearTimeout(hoverTimer);
            hoverTimer = setTimeout(() => {
                const p = e.features[0].properties;
                popup.setLngLat(e.lngLat).setHTML(`
                    <div class="popup-row"><span>Kecamatan:</span> ${p.nmkec || '-'}</div>
                    <div class="popup-row"><span>Desa:</span> ${p.nmdesa || '-'}</div>
                    <div class="popup-row"><span>SLS:</span> ${p.nmsls || '-'}</div>
                    <div class="popup-row"><span>Petugas:</span> ${p.petugas || '-'}</div>
                `).addTo(map);
            }, 150);
        });
        map.on('mouseleave', 'shapes-fill', () => {
            map.getCanvas().style.cursor = '';
            clearTimeout(hoverTimer);
            popup.remove();
        });
    }

    async function toggleDotsLayer(show) {
        const sourceId = 'dots';
        if (show) {
            const res = await fetch('/api/dots/geojson');
            const data = await res.json();
            if (!map.getSource(sourceId)) {
                map.addSource(sourceId, { type: 'geojson', data, cluster: false });
            } else {
                map.getSource(sourceId).setData(data);
            }
            if (!map.getLayer('dots-circle')) {
                map.addLayer({
                    id: 'dots-circle', type: 'circle', source: sourceId,
                    paint: {
                        'circle-radius': [
                            'interpolate', ['linear'], ['zoom'],
                            8, 1.5,
                            12, 2.5,
                            15, 4,
                            18, 5
                        ],
                        'circle-color': ['match', ['get', 'status'],
                            'INSIDE', '#16a34a',
                            'OFFSIDE', '#dc2626',
                            'MENUNGGU_SHAPE', '#94a3b8',
                            '#f59e0b'
                        ],
                        'circle-stroke-width': [
                            'interpolate', ['linear'], ['zoom'],
                            12, 0,
                            15, 1
                        ],
                        'circle-stroke-color': '#ffffff',
                        'circle-opacity': 0.85,
                    }
                });
                let dotPopup = new maplibregl.Popup();
                map.on('click', 'dots-circle', e => {
                    const p = e.features[0].properties;
                    dotPopup.setLngLat(e.lngLat).setHTML(`
                        <strong>${p.assignment_id}</strong><br>
                        Status: <b>${p.status}</b><br>
                        idsubsls: ${p.idsubsls_origin || '-'}<br>
                        Jarak: ${p.jarak_m != null ? p.jarak_m + ' m' : '-'}
                    `).addTo(map);
                });
            } else {
                ['dots-cluster', 'dots-cluster-count', 'dots-circle'].forEach(id => {
                    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'visible');
                });
            }
        } else {
            ['dots-cluster', 'dots-cluster-count', 'dots-circle'].forEach(id => {
                if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none');
            });
        }
    }

    async function toggleIssueLayer(type, show, colour) {
        const sourceId = `issues-${type}`;
        const layerId = `issues-${type}-fill`;
        const outlineId = `issues-${type}-outline`;
        if (show) {
            const res = await fetch(`/api/issues/geojson?type=${type}`);
            const data = await res.json();
            if (!map.getSource(sourceId)) {
                map.addSource(sourceId, { type: 'geojson', data });
            } else {
                map.getSource(sourceId).setData(data);
            }
            if (!map.getLayer(layerId)) {
                map.addLayer({ id: layerId, type: 'fill', source: sourceId, paint: { 'fill-color': colour, 'fill-opacity': 0.5 } });
                map.addLayer({ id: outlineId, type: 'line', source: sourceId, paint: { 'line-color': colour, 'line-width': 2 } });
            } else {
                map.setLayoutProperty(layerId, 'visibility', 'visible');
                map.setLayoutProperty(outlineId, 'visibility', 'visible');
            }
        } else {
            if (map.getLayer(layerId)) {
                map.setLayoutProperty(layerId, 'visibility', 'none');
                map.setLayoutProperty(outlineId, 'visibility', 'none');
            }
        }
    }

    function setupLayerToggles() {
        document.getElementById('layerMultipart').addEventListener('change', e => toggleIssueLayer('multipart', e.target.checked, '#f59e0b'));
        document.getElementById('layerGap').addEventListener('change', e => toggleIssueLayer('gap', e.target.checked, '#6366f1'));
        document.getElementById('layerOverlap').addEventListener('change', e => toggleIssueLayer('overlap', e.target.checked, '#ef4444'));
        const layerDup = document.getElementById('layerDuplicate');
        if (layerDup) {
            layerDup.addEventListener('change', e => toggleIssueLayer('duplicate_idsubsls', e.target.checked, '#c026d3'));
        }
        document.getElementById('layerDots').addEventListener('change', e => toggleDotsLayer(e.target.checked));
    }

    function fitToData() {
        if (!shapesGeoJSON || !shapesGeoJSON.features.length) return;
        const bounds = new maplibregl.LngLatBounds();
        shapesGeoJSON.features.forEach(f => getAllCoords(f.geometry).forEach(c => bounds.extend(c)));
        if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 40 });
    }

    function getAllCoords(geometry) {
        const coords = [];
        const recurse = c => { if (typeof c[0] === 'number') coords.push(c); else c.forEach(recurse); };
        recurse(geometry.coordinates);
        return coords;
    }

    function escHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function showToast(msg, type = 'info') {
        let toast = document.querySelector('.global-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'global-toast';
            document.body.appendChild(toast);
        }
        toast.className = 'global-toast' + (type === 'error' ? ' toast-error' : type === 'success' ? ' toast-success' : '');
        toast.textContent = msg;
        toast.style.display = 'block';
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.transition = 'opacity 0.4s ease';
            toast.style.opacity = '0';
            setTimeout(() => { toast.style.display = 'none'; }, 400);
        }, 3000);
    }

    // ---- Event listeners ----
    document.getElementById('btnApplyFilter').addEventListener('click', applyDisplayFilter);
    document.getElementById('btnClearFilter').addEventListener('click', resetDisplayFilter);
    document.getElementById('btnFitData').addEventListener('click', fitToData);

    const btnRecheckTopo = document.getElementById('btnRecheckTopology');
    if (btnRecheckTopo) {
        btnRecheckTopo.addEventListener('click', async () => {
            btnRecheckTopo.disabled = true;
            const origHtml = btnRecheckTopo.innerHTML;
            btnRecheckTopo.innerHTML = '<span>⏳</span> Menghitung topologi...';
            showToast('Menjalankan rekalkulasi topologi di latar belakang...', 'info');
            try {
                const res = await fetch('/api/admin/recheck-topology');
                const d = await res.json();
                showToast(d.message || 'Pengecekan topologi selesai.', 'success');
                setTimeout(async () => {
                    await loadStats();
                    ['multipart', 'gap', 'overlap', 'duplicate_idsubsls'].forEach(type => {
                        const chk = document.getElementById(`layer${type === 'duplicate_idsubsls' ? 'Duplicate' : type.charAt(0).toUpperCase() + type.slice(1)}`);
                        if (chk && chk.checked) {
                            toggleIssueLayer(type, true, type === 'multipart' ? '#f59e0b' : type === 'gap' ? '#6366f1' : type === 'overlap' ? '#ef4444' : '#c026d3');
                        }
                    });
                }, 1500);
            } catch (err) {
                showToast('Gagal memicu recheck topologi: ' + err.message, 'error');
            } finally {
                setTimeout(() => {
                    btnRecheckTopo.disabled = false;
                    btnRecheckTopo.innerHTML = origHtml;
                }, 2000);
            }
        });
    }

    const btnRecheckDots = document.getElementById('btnRecheckDots');
    if (btnRecheckDots) {
        btnRecheckDots.addEventListener('click', async () => {
            btnRecheckDots.disabled = true;
            const origHtml = btnRecheckDots.innerHTML;
            btnRecheckDots.innerHTML = '<span>⏳</span> Memeriksa titik...';
            showToast('Menjalankan rekalkulasi titik di latar belakang...', 'info');
            try {
                const res = await fetch('/api/admin/recheck-dots', { method: 'POST' });
                const d = await res.json();
                showToast(d.message || 'Recheck titik selesai.', 'success');
                setTimeout(async () => {
                    await loadStats();
                    const dotChk = document.getElementById('layerDots');
                    if (dotChk && dotChk.checked) {
                        await toggleDotsLayer(true);
                    }
                }, 1500);
            } catch (err) {
                showToast('Gagal memicu recheck titik: ' + err.message, 'error');
            } finally {
                setTimeout(() => {
                    btnRecheckDots.disabled = false;
                    btnRecheckDots.innerHTML = origHtml;
                }, 2000);
            }
        });
    }

    document.querySelectorAll('input[name="colourBy"]').forEach(radio => {
        radio.addEventListener('change', async () => {
            colourBy = radio.value;
            // Reload colour map jika belum ada
            if (!colourMaps[colourBy] || Object.keys(colourMaps[colourBy]).length === 0) {
                const r = await fetch(`/api/colours/${colourBy}`);
                colourMaps[colourBy] = await r.json();
            }
            applyColour();
        });
    });

    // Init
    loadStats();
    initMap();
    setInterval(loadStats, 30000);
})();
