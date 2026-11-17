# DEEP RESEARCH AUDIT: AKAR MASALAH TITIK TERSERET KE UTARA
**Berkas Kasus**: `c:\laragon\www\wilkerstat-checker\audit-trail\audit akar masalah titik terseret utara.md`  
**Objek Analisis**: Titik `ecf36d42-5fa9-44b9-8ad0-b2e5f3057397`, RT 008 Desa Tanta Hulu (`idsls: 63090500170008`)  
**Tingkat Keyakinan**: [certain] (Berdasarkan pembacaan kode sumber spasial, data batas poligon, dan jejak eksekusi pipeline)

---

## 1. The Uncomfortable Truth (Fakta Kritis)
[certain] Titik ditarik ke utara bukan karena data poligon tidak valid, melainkan karena **arsitektur kode di 4 modul pipeline memiliki cacat logika berantai (cascading bug)**:
1. Pemuat poligon (`load_polygons`) tidak pernah melakukan `unary_union` pada poligon SLS yang memiliki banyak SubSLS.
2. Tahap 3 (`s03_perhitungan_muatan.py`) membuang atribut `flag_repair` dari berkas master GeoJSON.
3. Tahap 4 (`extract_failed.py`) memvonis titik valid sebagai titik gagal karena mengevaluasi titik terhadap poligon parsial (hanya separuh poligon yang terindeks).
4. Tahap 5 (`move_failed.py`) memproyeksikan titik ke SubSLS 02 (poligon utara) padahal koordinat aslinya berada di SubSLS 01 (poligon selatan), yang mana keduanya berada di RT 008 yang sama.

---

## 2. Bedah Forensik Kasus Titik `ecf36d42-5fa9-44b9-8ad0-b2e5f3057397`

### A. Geometri Poligon RT 008 (`63090500170008`)
Di berkas peta Wilkerstat (`final_sls_251_6309050017.geojson` / `slsmentah fixed-2025sm1.geojson`), RT 008 terdiri dari **2 bagian SubSLS terpisah**:
* **SubSLS 01 (`6309050017000801`, GID: 307408)**: Terletak di sisi **SELATAN** (rentang Latitude: `-2.1864` s.d. `-2.1918`).
* **SubSLS 02 (`6309050017000802`, GID: 307410)**: Terletak di sisi **UTARA** (rentang Latitude: `-2.1826` s.d. `-2.1864`).

### B. Posisi Spasial Titik Masalah
* Koordinat fisik titik berada di sisi **SELATAN** (di dalam poligon SubSLS 01 / GID 307408).
* Namun pada atribut hasil sensus/geotagging petugas lapangan, titik tersebut diberi kode beban tugas:
  `level_6_full_code = "6309050017000802"` (SubSLS 02).
* Secara aturan operasional statistik BPS: Pemecahan SubSLS adalah batas beban kerja petugas, **bukan batas administrasi terlarang**. Titik di SubSLS 01 yang ditugaskan di SubSLS 02 adalah sah dan valid di dalam RT 008. Titik ini **tidak boleh digeser**.

---

## 3. Anatomi Kerusakan Berantai di Pipeline (Cascade Failure)

```
[Tahap 2: s02_repair_geotagging]
  -> Titik dievaluasi cocok di tingkat SLS (14-digit: 63090500170008).
  -> Diberi flag_repair = 0 (INSIDE, koordinat dipertahankan asli).
           ↓
[Tahap 3: s03_perhitungan_muatan]
  -> Kolom 'flag_repair' & 'is_inside_home' terhapus dari daftar kolom gs_upload.
  -> Master final_landmark_6309_se_2026.geojson diekspor tanpa status proteksi.
           ↓
[Tahap 4: extract_failed.py]
  -> Membaca final_landmark_6309_se_2026.geojson (flag_repair tidak ada).
  -> Menggunakan _load_polygon_map() dengan keterbatasan non-union:
     poly_map["63090500170008"] hanya menyimpan poligon SubSLS pertama.
  -> Poligon selatan (SubSLS 01) tidak terdaftar di tingkat SLS.
  -> Titik divonis OFFSIDE dan diekstrak ke failed.geojson.
           ↓
[Tahap 5: move_failed.py]
  -> target_id diambil dari level_6_full_code ("6309050017000802", Poligon UTARA).
  -> Karena poligon selatan tidak di-union ke SLS, titik dianggap di luar.
  -> interior_projection menarik titik ratusan meter ke UTARA masuk ke SubSLS 02.
           ↓
[Tahap 6: sync_final_landmark.py]
  -> Titik yang tergeser menimpa master final_landmark_6309_se_2026.geojson.
  -> Dampak: Titik sah berpindah posisi secara keliru.
```

---

## 4. Rincian Cacat Kode Spesifik

### Bug 1: Cacat Kamus Poligon Non-Union di `extract_failed.py`, `move_failed.py`, dan `dry_run.py`
Kode:
```python
# module/extract_failed.py & module/move_failed.py & dry_run.py
idsub = str(props.get("idsubsls") or "").strip()
idsls = str(props.get("idsls") or "").strip()

if idsub:
    poly_map[idsub] = geom
if idsls and idsls not in poly_map:
    poly_map[idsls] = geom
```
**Analisis Cacat**:
`if idsls and idsls not in poly_map:` memastikan bahwa hanya poligon SubSLS **pertama** yang tersimpan di kamus untuk `idsls`. Poligon SubSLS berikutnya diabaikan. Untuk RT 008, jika SubSLS 02 dibaca lebih dulu, maka `poly_map["63090500170008"]` hanya berisi SubSLS 02 (Utara). Area SubSLS 01 (Selatan) tidak terakomodasi di tingkat SLS.

### Bug 2: Penghilangan Atribut Proteksi di `s03_perhitungan_muatan.py`
Kode:
```python
# 00 - module/s03_perhitungan_muatan.py line 756-777
gs_upload = gs_internal[
    [
        "id_assignment",
        "unique_bang",
        "flag_position",
        "level_6_full_code",
        "idsubsls_261",
        "latitude_origin",
        "longitude_origin",
        "latitude_edited",
        "longitude_edited",
        "no_bang",
        "kode_bang_value",
        "kk",
        "btt",
        "bku",
        "bttk",
        "bbtt_nonusaha",
        "usaha",
        "geometry"
    ]
].copy()
```
**Analisis Cacat**:
`flag_repair` dibuang sehingga modul downstream (Tahap 4 `extract_failed.py`) tidak mendeteksi bahwa titik tersebut sebenarnya sudah divalidasi sebagai titik valid `flag_repair == 0`.

### Bug 3: Proyeksi Membuta ke SubSLS di `move_failed.py`
Kode:
```python
# module/move_failed.py line 101-139
target_id = str(props.get("level_6_full_code") or ...).strip()
poly = poly_map.get(target_id) # Mengambil SubSLS 02 (Utara)
...
inward_poly = poly.buffer(-0.00005)
p1, _ = nearest_points(inward_poly, curr_pt)
new_pt = candidate # Titik diseret ke utara
```
**Analisis Cacat**:
`target_id` dipaksa ke SubSLS 16-digit. Batas acuan utama seharusnya adalah **Home SLS 14-digit yang telah di-union**. Jika titik sudah di dalam Home SLS 14-digit, reposisi **wajib dibatalkan** (`new_pt = curr_pt`).

---

## 5. Rencana Perbaikan Sistematis (Action Plan)

1. **Fix 1 — Pemuat Poligon Wajib Spatial Union**:
   Di `extract_failed.py`, `move_failed.py`, dan `dry_run.py`, kumpulkan seluruh poligon per-`idsls` ke dalam list, lalu lakukan:
   ```python
   from shapely.ops import unary_union
   # Untuk setiap idsls:
   sls_poly_map[idsls] = unary_union(list_geoms)
   ```
2. **Fix 2 — Pertahankan Kolom `flag_repair` di `s03_perhitungan_muatan.py`**:
   Masukkan `flag_repair` ke dalam schema `gs_upload` agar status kelolosan dari Tahap 2 tidak hilang saat ekspor ke `final_landmark_6309_se_2026.geojson`.
3. **Fix 3 — Immutability Guard Tingkat SLS 14-Digit di `move_failed.py`**:
   Sebelum memproyeksikan titik ke poligon SubSLS, periksa apakah titik berada di dalam `sls_poly_union[home_id[:14]]`. Jika ya:
   `new_pt = curr_pt`, `method = "already_inside_home_sls"`, koordinat tidak diubah.
4. **Fix 4 — Reset Koordinat ke Origin**:
   Untuk titik-titik yang sempat tergeser ke utara, pulihkan koordinat dari `latitude_origin` dan `longitude_origin`.
5. **Fix 5 — Whitelist Mutlak Model 3 & Multi-part SLS di `s02_repair_geotagging.py`**:
   - Jika `flag_repair == 0` dari Model 3, titik dikunci kebal evaluasi dan dijamin `flag_repair = 0`, `is_inside_home = True`, koordinat dipertahankan.
   - `repair_idx` hanya memproses titik dengan `flag_repair == 1` dari Model 3 (tepat 10.034 titik).
   - Pengambilan poligon target di `find_repair_coordinate` menerapkan `unary_union` untuk menyatukan multi-part poligon SubSLS dan SLS 14-digit.
   - Kolom `flag_position` dikomputasi konsisten (0 jika koordinat tidak digeser, 1 jika digeser).

---

## 6. Audit Lanjutan: Kehilangan Kolom Mentah Asli (Raw Schema Loss)

### A. Akar Masalah
[certain] Berkas final kehilangan kolom mentah asli karena dua pemangkasan:
1. Di `s02_repair_geotagging.py` baris 769-812: Fungsi `refactor_fields` menyaring kolom menggunakan whitelist `final_columns`. Kolom CAPI asli (`nama_usaha_bang`, `geotag_accuracy`, `ada_keluarga_value`, `count_usaha`, `ada_bang_usaha_value`, `level_6_name`, `flag_psls`, `fid`) dibuang.
2. Di `s03_perhitungan_muatan.py` baris 799-826: Modul mengekspor `final_landmark` hanya dengan whitelist `upload_cols` format Ground Segment BPS (`kk`, `btt`, `bku`, `bttk`, `bbtt_nonusaha`, `usaha`, `idsubsls_261`), bukan skema asli masukan pengguna.

### B. Dampak
Mustahil memulihkan skema kolom hanya dengan mengubah nama kolom pada berkas final, karena data atribut pada kolom mentah yang dibuang sudah hilang permanen dari berkas final.

### C. Solusi Perbaikan Kode (Step-by-Step)
1. **Langkah 1 (`s02_repair_geotagging.py`)**: Pertahankan seluruh kolom asli masukan (`input_cols`). Kolom baru dari pipeline ditambahkan tanpa menghapus satu pun kolom asli.
2. **Langkah 2 (`s03_perhitungan_muatan.py`)**: Saat mengekspor `final_landmark_6309_se_2026.geojson`, gunakan skema kolom asli masukan yang diperbarui koordinatnya (`geometry`, `geotag_latitude`, `geotag_longitude`), bukan skema muatan GS.

