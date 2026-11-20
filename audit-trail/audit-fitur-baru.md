# Audit Fitur Baru — WilkerStat Checker
**Dibuat:** 2026-10-30

---

## Fitur 1: Label Peta "nmdesa - nmsls [kdsubsls]"

### Deskripsi
Tambahkan label teks pada setiap poligon SLS di peta dengan format:
```
{nmdesa} - {nmsls} [{kdsubsls}]
```
Contoh: `LANO - RT 004 [00]`

### Masalah Utama
Label naif (satu label per fitur) akan **saling bertumpuk** saat zoom out karena jumlah SLS sangat banyak.

### Solusi yang Direkomendasikan
Gunakan **Leaflet.markercluster** atau pendekatan **zoom-level-gated label** — label hanya muncul mulai zoom level tertentu (konfigurasi via `config.LABEL_MIN_ZOOM`, sudah ada di `config.py` default 14).

#### Implementasi di `map.html` / JS:
```js
// Hanya render label bila zoom >= LABEL_MIN_ZOOM
map.on('zoomend', function () {
    const z = map.getZoom();
    shapeLayer.eachLayer(function (layer) {
        if (z >= LABEL_MIN_ZOOM) {
            layer.bindTooltip(
                layer.feature.properties.nmdesa + ' - ' +
                layer.feature.properties.nmsls + ' [' +
                layer.feature.properties.kdsubsls + ']',
                { permanent: true, direction: 'center', className: 'sls-label' }
            ).openTooltip();
        } else {
            layer.unbindTooltip();
        }
    });
});
```

#### CSS tambahan:
```css
.sls-label {
    background: transparent;
    border: none;
    box-shadow: none;
    font-size: 10px;
    font-weight: 600;
    color: #111;
    text-shadow: 0 0 3px #fff, 0 0 3px #fff;
    white-space: nowrap;
    pointer-events: none;
}
```

### File yang Diubah
- `templates/map.html` — logika JS zoom-gated label
- `static/css/` — class `.sls-label`

---

## Fitur 2: Progres Per-Petugas — Dropdown Error + Fokus Peta

### Deskripsi
Card progres bar tiap petugas (termasuk petugas abu-abu / belum upload):
- **Klik card** → expand dropdown list error detail
- **Klik item error** → peta langsung pan + zoom ke lokasi geometri error tersebut

### Pertanyaan: Apakah Berat?

#### Untuk Shape (poligon) — **Tidak berat**
- Jumlah SLS seluruh Tabalong: ratusan, bukan jutaan
- Data error (multipart, gap, overlap) tersimpan di tabel `issue` dengan `geom_wkb`
- Cukup lazy-load: dropdown hanya fetch error list saat diklik (1 request per petugas)

#### Untuk Titik (dot) — **Berpotensi Berat** bila ratusan ribu
- Titik offside + digeser bisa puluhan ribu baris
- Render semua sekaligus = **berat di browser**

### Solusi yang Tidak Berat untuk Titik

**Opsi A: Virtualized List (paling ringan)**
- Render hanya baris yang terlihat di viewport dropdown (virtual scroll)
- Library: `clusterize.js` (ringan ~3KB) atau implementasi manual
- Data tetap diambil sekaligus, tapi DOM tidak dibuat semua

**Opsi B: Paginated Error List (paling mudah diimplementasi)**
- Dropdown menampilkan 50 item per halaman
- Tombol "Muat lebih" / pagination sederhana
- Tidak butuh library tambahan

**Opsi C: Cluster Point di Peta (direkomendasikan dikombinasi)**
- Error titik dicluster di peta (`Leaflet.markercluster`)
- Dropdown hanya tampilkan summary per desa/kecamatan, bukan per titik
- Klik item dropdown → zoom ke area kecamatan/desa, bukan titik individual

> [!IMPORTANT]
> **Rekomendasi**: Kombinasi **Opsi B + C** — dropdown paginated 50/halaman untuk list, titik di peta dicluster. Klik item error → fly ke centroid area terkait, bukan titik individual (menghindari render ribuan marker sekaligus).

### Arsitektur API yang Diusulkan

#### Endpoint baru:
```
GET /api/petugas/list
→ [{petugas, status, shape_count, error_count, dot_count, offside_count, ...}]
  Termasuk petugas yang belum ada data (status: "belum_upload")

GET /api/petugas/<nama>/errors?type=shape&page=1&per_page=50
→ [{issue_type, target_id, nmdesa, nmsls, lat, lon, detail}, ...]

GET /api/petugas/<nama>/errors?type=dot&page=1&per_page=50
→ [{assignment_id, nmdesa, nmsls, flag_repair, flag_position, lat, lon}, ...]
```

#### Koordinat centroid untuk fly-to:
- Shape error → ambil centroid dari `geom_wkb` (Shapely `wkb.loads(geom_wkb).centroid`)
- Dot error → gunakan `latitude_edited`, `longitude_edited`

### Daftar Petugas "Abu-abu" (Belum Upload)
Perlu data referensi daftar petugas resmi yang diharapkan upload. Simpan di:
- Tabel baru `petugas_master (nama TEXT PRIMARY KEY, kecamatan TEXT)`, atau
- File konfigurasi `petugas.csv` di root project

Petugas yang ada di `petugas_master` tapi belum ada di `shape.petugas` → tampil abu-abu dengan progres 0%.

### UI Card Progres yang Diusulkan

```
┌─────────────────────────────────────────────┐
│ 👤 liza                          [▼ 12 error]│
│ ████████░░░░ 68%                            │
│ Shape: 340 | Gap: 3 | Overlap: 2 | Multi: 1 │
│ Titik: 1.240 | Offside: 6 | Digeser: 0     │
├─────────────────────────────────────────────┤ ← expand saat diklik
│  ⚠ [multipart] LANO - RT 004 [00]          │ ← klik → fly to
│  ⚠ [gap] JARO - RT 001 [00]               │
│  ⚠ [overlap] SOLAN - RT 002 [00]          │
│  ● [offside] MASINGAI I - RT 003 [00]      │
│  ... [Muat 50 lebih ↓]                      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 👤 (petugas baru)                  [abu-abu] │
│ ░░░░░░░░░░░░ 0% — belum upload             │
└─────────────────────────────────────────────┘
```

### File yang Diubah
| File | Perubahan |
|------|-----------|
| `database.py` | Tambah tabel `petugas_master`, query centroid |
| `app.py` | Endpoint `/api/petugas/list` dan `/api/petugas/<nama>/errors` |
| `templates/home.html` / halaman baru | Card progres + dropdown JS |
| `spatial.py` | Helper `geom_centroid(geom_wkb)` → (lat, lon) |
| `petugas.csv` *(baru)* | Daftar petugas referensi |

---

## Prioritas & Ketergantungan

| No | Fitur | Estimasi | Ketergantungan |
|----|-------|----------|----------------|
| 1 | Label zoom-gated | Rendah | Tidak ada |
| 2a | Card petugas abu-abu | Rendah | `petugas.csv` harus ada dulu |
| 2b | Dropdown error list (shape) | Sedang | API endpoint baru |
| 2c | Fly-to per error | Rendah | Centroid dari `geom_wkb` |
| 2d | Dot error paginated | Sedang | — |
| 2e | Cluster dot di peta | Sedang | Leaflet.markercluster |

---

## Revisi Dropdown: Pemisahan Konten Mode Progres vs Mode Error

### Latar Belakang & Masalah
Sebelumnya, dropdown pada kartu progres menampilkan seluruh error gabungan tanpa mempedulikan tab mode yang aktif. Pada mode **Upload/Status**, dropdown harus menampilkan daftar poligon/titik hasil unggahan petugas tersebut, dan saat diklik langsung melakukan zoom/fokus ke poligon atau titik tersebut di peta. Sementara pada mode error (`multipart`, `gap`, `overlap`, `offside`, `moved`), dropdown menampilkan daftar isu spesifik sesuai mode.

### Solusi Teknis
1. **API Endpoint `/api/petugas/<petugas>/errors`**:
   - Mendukung parameter `mode` (`progress`, `multipart`, `gap`, `overlap`, `offside`, `moved`).
   - Jika `category=shape` dan `mode=progress`: Query dari tabel `shape`, mengembalikan poligon hasil upload petugas dengan `bbox`, `centroid`, dan label `{nmdesa} - {nmsls} [{kdsubsls}]`.
   - Jika `category=shape` dan `mode in ('multipart', 'gap', 'overlap')`: Query dari tabel `issue` terfilter jenis isu tersebut.
   - Jika `category=dot` dan `mode=progress`: Query dari tabel `dot`, mengembalikan titik hasil upload petugas dengan koordinat `lat`/`lon` dan status (`INSIDE`/`OFFSIDE`).
   - Jika `category=dot` dan `mode in ('offside', 'moved')`: Query dari tabel `dot` terfilter `flag_repair=1` atau `flag_position=1`.
2. **Frontend UI (`static/home.js`)**:
   - `togglePetugasCard`: Mengirimkan parameter `mode` saat ini ke backend API.
   - Mode `progress`: Menampilkan badge `SLS` (poligon) atau status `INSIDE`/`OFFSIDE` (titik); saat diklik memfokuskan peta (`fitBounds`/`flyTo`) ke poligon/titik tersebut.
   - Mode error: Menampilkan badge error spesifik sesuai mode yang dipilih.
3. **Penyelarasan CSS (`static/style.css`)**:
   - Tambah styling badge `SLS` (`.error-badge.sls`) dan `INSIDE` (`.error-badge.inside`).

---

## Revisi Fokus SLS Upload: Highlight Berkedip 3 Detik (Tanpa Pinpoint)

### Latar Belakang & Masalah
Saat poligon hasil upload diklik pada dropdown, penanda berupa pinpoint marker merah/biru mengganggu pandangan poligon SLS. Diinginkan efek visual berupa poligon itu sendiri yang di-highlight dan berkedip (blinking) selama 3 detik tanpa adanya icon pinpoint.

### Solusi Teknis
1. **Highlight Layer Dinamis di MapLibre GL**:
   - Menambahkan layer vektor `highlight-shape-fill` dan `highlight-shape-outline` menggunakan source dinamis `highlight-shape`.
   - Warna highlight: amber cerah (`#f59e0b` / outline `#d97706`).
2. **Efek Kedip 3 Detik**:
   - Animasi berbasis interval 300ms sebanyak 10 siklus (total 3 detik).
   - Setelah 3 detik, interval dibersihkan dan source dikosongkan secara otomatis.
   - Tidak merender `maplibregl.Marker` (pinpoint) untuk item bertipe `SLS`.

---

## Revisi Label Peta & Kolom Pencarian Dropdown

### 1. Perbaikan Label Peta Tidak Muncul
- **Penyebab**: Konfigurasi MapLibre GL raster style sebelumnya tidak mendefinisikan URL `glyphs` (font PBF). Engine MapLibre GL menolak me-render layer `symbol` bertipe teks tanpa properti glyphs. Selain itu batas `minzoom` default 14 terlalu dekat untuk tampilan umum.
- **Perbaikan**:
  - Menambahkan endpoint glyphs publik: `https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf` pada inisialisasi MapLibre GL di `static/home.js` dan `static/map.js`.
  - Menurunkan `LABEL_MIN_ZOOM` ke level 11 di `config.py`.
  - Mengaktifkan collision detection bawaan GPU (`'text-allow-overlap': false`, `'text-optional': true`) dan interpolasi ukuran teks dinamis (zoom 11: 9px s.d. zoom 16: 13px) sehingga label terlihat di level kecamatan/desa tanpa saling bertumpuk.

### 2. Kolom Pencarian Dropdown (Contains Match in All Columns)
- **Implementasi Backend (`app.py`)**:
  - Endpoint `/api/petugas/<petugas>/errors` menerima parameter `q`.
  - Melakukan pencarian substring peka-spasi (case-insensitive `LIKE '%q%'`) terhadap seluruh atribut yang digabung: nama desa, nama SLS, kode sub-SLS, ID, dan status.
  - Pencarian "jaro rt 002" akan cocok dengan poligon desa Jaro RT 002, sedangkan "jaro rt002" tidak akan cocok jika tidak dipisahkan spasi.
- **Implementasi Frontend (`static/home.js` & `static/style.css`)**:
  - Menambahkan input pencarian di bagian atas dropdown kartu petugas dengan debounce 250ms.




