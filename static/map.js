/* ===== map.js — Full interactive map page ===== */
(function () {
    'use strict';

    let map = null;
    let shapesGeoJSON = null;
    let colourBy = 'petugas';
    let colourMaps = {};
    let filterState = { kec: [], desa: [], sls: [] };
    let activeLayerToggles = { multipart: false, gap: false, overlap: false, dots: false };

    // ---- Init map ----
    async function initMap() {
        const cfgRes = await fetch('/api/config');
        const cfg = await cfgRes.json();

        map = new maplibregl.Map({
            container: 'mainMap',
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

        map.addControl(new maplibregl.NavigationControl(), 'top-right');
        map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');

        map.on('load', async () => {
            await loadFiltersUI();
            await loadMasterShapes();
            await loadShapes(cfg);
            setupLayerToggles(cfg);
        });
    }

    // ---- Load filter options ----
    async function loadFiltersUI() {
        const res = await fetch('/api/filters');
        const data = await res.json();

        populateMultiSelect('filterKec', data.kecamatan.map(k => ({ value: k, label: k })));
        populateMultiSelect('filterDesa', data.desa.map(d => ({ value: d.name, label: d.name })));
        populateMultiSelect('filterSLS', data.sls.map(s => ({ value: s.id, label: s.name })));

        // Cascade: kec changes → refresh desa/sls options
        document.getElementById('filterKec').addEventListener('change', async () => {
            const kec = getMultiSelectValues('filterKec');
            const q = kec.map(k => `kec=${encodeURIComponent(k)}`).join('&');
            const r = await fetch(`/api/filters?${q}`);
            const d = await r.json();
            populateMultiSelect('filterDesa', d.desa.map(x => ({ value: x.name, label: x.name })));
            populateMultiSelect('filterSLS', d.sls.map(x => ({ value: x.id, label: x.name })));
        });
    }

    function populateMultiSelect(id, options) {
        const el = document.getElementById(id);
        el.innerHTML = options.map(o => `<option value="${escHtml(o.value)}">${escHtml(o.label)}</option>`).join('');
    }

    function getMultiSelectValues(id) {
        const el = document.getElementById(id);
        return Array.from(el.selectedOptions).map(o => o.value);
    }

    // ---- Load master shapes (gray background layer) ----
    async function loadMasterShapes() {
        const res = await fetch('/api/master/shapes/geojson');
        const data = await res.json();
        if (!data.features || data.features.length === 0) return;

        map.addSource('master-shapes', { type: 'geojson', data });
        map.addLayer({
            id: 'master-shapes-fill',
            type: 'fill',
            source: 'master-shapes',
            paint: { 'fill-color': '#94a3b8', 'fill-opacity': 0.12 }
        });
        map.addLayer({
            id: 'master-shapes-outline',
            type: 'line',
            source: 'master-shapes',
            paint: { 'line-color': '#94a3b8', 'line-width': 0.5, 'line-dasharray': [2, 2] }
        });
    }

    // ---- Load shapes ----
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
            map.addLayer({
                id: 'shapes-fill',
                type: 'fill',
                source: 'shapes',
                paint: { 'fill-color': '#2563eb', 'fill-opacity': 0.4 }
            });
        }
        if (!map.getLayer('shapes-outline')) {
            map.addLayer({
                id: 'shapes-outline',
                type: 'line',
                source: 'shapes',
                paint: { 'line-color': '#1e293b', 'line-width': 0.8 }
            });
        }
        if (!map.getLayer('shapes-label')) {
            const minZoom = (cfg && cfg.label_min_zoom != null) ? cfg.label_min_zoom : 11;
            map.addLayer({
                id: 'shapes-label',
                type: 'symbol',
                source: 'shapes',
                minzoom: minZoom,
                layout: {
                    'text-field': ['concat',
                        ['get', 'nmdesa'], ' - ', ['get', 'nmsls'], ' [', ['get', 'kdsubsls'], ']'
                    ],
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
                    'text-halo-width': 2.0,
                }
            });
        }
    }

    function applyColour() {
        if (!map.getLayer('shapes-fill')) return;
        const propMap = { kec: 'nmkec', desa: 'nmdesa', sls: 'idsubsls', petugas: 'petugas' };
        const prop = propMap[colourBy];
        const cmap = colourMaps[colourBy] || {};

        if (!shapesGeoJSON || !shapesGeoJSON.features) return;
        const vals = [...new Set(shapesGeoJSON.features.map(f => f.properties[prop]).filter(Boolean))];
        if (vals.length === 0) return;

        const expr = ['match', ['get', prop]];
        vals.forEach(v => { expr.push(v); expr.push(cmap[v] || '#94a3b8'); });
        expr.push('#94a3b8');

        map.setPaintProperty('shapes-fill', 'fill-color', expr);
    }

    function applyDisplayFilter() {
        const kecs = getMultiSelectValues('filterKec');
        const desas = getMultiSelectValues('filterDesa');
        const slss = getMultiSelectValues('filterSLS');

        if (!shapesGeoJSON) return;

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
        if (shapesGeoJSON) map.getSource('shapes').setData(shapesGeoJSON);
        applyColour();
        document.getElementById('filterKec').selectedIndex = -1;
        document.getElementById('filterDesa').selectedIndex = -1;
        document.getElementById('filterSLS').selectedIndex = -1;
    }

    // ---- Hover popup ----
    function setupHover() {
        let popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
        let hoverTimer = null;

        map.on('mousemove', 'shapes-fill', (e) => {
            map.getCanvas().style.cursor = 'pointer';
            clearTimeout(hoverTimer);
            hoverTimer = setTimeout(() => {
                const props = e.features[0].properties;
                popup.setLngLat(e.lngLat)
                    .setHTML(`
                        <div class="popup-row"><span>Kecamatan:</span> ${props.nmkec || '-'}</div>
                        <div class="popup-row"><span>Desa:</span> ${props.nmdesa || '-'}</div>
                        <div class="popup-row"><span>SLS:</span> ${props.nmsls || '-'}</div>
                        <div class="popup-row"><span>KdSubSLS:</span> ${props.kdsubsls || '-'}</div>
                        <div class="popup-row"><span>Petugas:</span> ${props.petugas || '-'}</div>
                    `)
                    .addTo(map);
            }, 150);
        });

        map.on('mouseleave', 'shapes-fill', () => {
            map.getCanvas().style.cursor = '';
            clearTimeout(hoverTimer);
            popup.remove();
        });
    }

    // ---- Layer toggles ----
    function setupLayerToggles(cfg) {
        document.getElementById('layerMultipart').addEventListener('change', async (e) => {
            await toggleIssueLayer('multipart', e.target.checked, '#f59e0b');
        });
        document.getElementById('layerGap').addEventListener('change', async (e) => {
            await toggleIssueLayer('gap', e.target.checked, '#6366f1');
        });
        document.getElementById('layerOverlap').addEventListener('change', async (e) => {
            await toggleIssueLayer('overlap', e.target.checked, '#ef4444');
        });
        document.getElementById('layerDots').addEventListener('change', async (e) => {
            await toggleDotsLayer(e.target.checked);
        });
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
                map.addLayer({
                    id: layerId,
                    type: 'fill',
                    source: sourceId,
                    paint: { 'fill-color': colour, 'fill-opacity': 0.5 }
                });
                map.addLayer({
                    id: outlineId,
                    type: 'line',
                    source: sourceId,
                    paint: { 'line-color': colour, 'line-width': 2 }
                });

                // Popup on issue click
                let popup = new maplibregl.Popup();
                map.on('click', layerId, (e) => {
                    const props = e.features[0].properties;
                    let detail = props.detail || props;
                    if (typeof detail === 'string') {
                        try { detail = JSON.parse(detail); } catch (err) { detail = {}; }
                    }
                    const content = `<strong>${type.toUpperCase()}</strong><br>
                        Luas: ${props.area_m2 ? props.area_m2.toFixed(2) + ' m²' : '-'}<br>
                        Petugas: ${props.petugas || '-'}`;
                    popup.setLngLat(e.lngLat).setHTML(content).addTo(map);
                });
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

    async function toggleDotsLayer(show) {
        const sourceId = 'dots';
        const layerId = 'dots-circle';

        if (show) {
            const res = await fetch('/api/dots/geojson');
            const data = await res.json();

            if (!map.getSource(sourceId)) {
                map.addSource(sourceId, { type: 'geojson', data, cluster: false });
            } else {
                map.getSource(sourceId).setData(data);
            }

            if (!map.getLayer(layerId)) {
                // Individual dots without clustering
                map.addLayer({
                    id: layerId,
                    type: 'circle',
                    source: sourceId,
                    paint: {
                        'circle-radius': [
                            'interpolate', ['linear'], ['zoom'],
                            8, 1.5,
                            12, 2.5,
                            15, 4,
                            18, 5
                        ],
                        'circle-color': [
                            'match', ['get', 'status'],
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

                // Dot popup
                let dotPopup = new maplibregl.Popup();
                map.on('click', layerId, (e) => {
                    const props = e.features[0].properties;
                    dotPopup.setLngLat(e.lngLat).setHTML(`
                        <strong>${props.assignment_id}</strong><br>
                        Status: ${props.status}<br>
                        idsubsls: ${props.idsubsls_origin || '-'}<br>
                        Jarak: ${props.jarak_m != null ? props.jarak_m + ' m' : '-'}
                    `).addTo(map);
                });
            } else {
                ['dots-cluster', 'dots-cluster-count', layerId].forEach(id => {
                    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'visible');
                });
            }
        } else {
            ['dots-cluster', 'dots-cluster-count', 'dots-circle'].forEach(id => {
                if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none');
            });
        }
    }

    // ---- Fit to data ----
    function fitToData() {
        if (!shapesGeoJSON || !shapesGeoJSON.features.length) return;
        const bounds = new maplibregl.LngLatBounds();
        shapesGeoJSON.features.forEach(f => {
            getAllCoords(f.geometry).forEach(c => bounds.extend(c));
        });
        if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 40 });
    }

    function getAllCoords(geometry) {
        const coords = [];
        const recurse = (c) => {
            if (typeof c[0] === 'number') coords.push(c);
            else c.forEach(recurse);
        };
        recurse(geometry.coordinates);
        return coords;
    }

    function escHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // ---- Event listeners ----
    document.getElementById('btnApplyFilter').addEventListener('click', applyDisplayFilter);
    document.getElementById('btnClearFilter').addEventListener('click', resetDisplayFilter);
    document.getElementById('btnFitData').addEventListener('click', fitToData);

    document.querySelectorAll('input[name="colourBy"]').forEach(radio => {
        radio.addEventListener('change', () => {
            colourBy = radio.value;
            applyColour();
        });
    });

    initMap();
})();

