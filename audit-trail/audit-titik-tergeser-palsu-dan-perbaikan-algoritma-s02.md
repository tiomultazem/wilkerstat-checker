# AUDIT INVESTIGASI DAN PERBAIKAN ALGORITMA REPOSISI SPASIAL (s02)

**Tanggal**: 2026-11-02  
**Status**: SELESAI DIPERBAIKI  
**Modul Target**: [`01-move offside dots/00 - module/s02_repair_geotagging.py`](file:///c:/laragon/www/wilkerstat-checker/01-move%20offside%20dots/00%20-%20module/s02_repair_geotagging.py)  

---

## 1. Identitas Kasus Temuan Lapangan
- **ID Titik (assignment_id)**: `ecf36d42-5fa9-44b9-8ad0-b2e5f3057397`
- **Posisi Fisik Nyata**: Berada di dalam batas poligon:
  - `gid`: `307408`
  - `idsls`: `63090500170008` (RT 008, Desa TANTA HULU, Kec. TANTA)
  - `idsubsls`: `6309050017000801` (SubSLS 01)
- **Gejala Masalah**: Titik tersebut secara nyata sudah berada di dalam poligon RT 008, namun oleh algoritma reposisi digeser jauh ke utara ("ke atas") menuju poligon SubSLS tetangga (`6309050017000802`).

---

## 2. Akar Masalah Teknis (Root Causes)

### A. Mismatch Granularitas 16-Digit SubSLS vs 14-Digit SLS
Pada data BPS Wilkerstat, satu SLS (14-digit, contoh `63090500170008`) dapat memiliki pecahan SubSLS (16-digit, contoh `...0801` dan `...0802`).
Pada algoritma lama di [`s02_repair_geotagging.py`](file:///c:/laragon/www/wilkerstat-checker/01-move%20offside%20dots/00%20-%20module/s02_repair_geotagging.py#L408-L414):
```python
joined["flag_repair"] = np.where(
    joined["idsubsls_overlay"].astype(str) == joined["level_6_full_code"].astype(str),
    0,
    1
)
```
Evaluasi hanya mencocokkan string 16-digit SubSLS secara kaku. Jika pencacah lapangan mencatat `level_6_full_code = ...0802` tetapi secara fisik berdiri di bagian `...0801`, algoritma memvonis titik tersebut offside (`flag_repair = 1`). Akibatnya, titik yang sah berada di RT 008 dipaksa ditarik masuk ke poligon `...0802` yang posisinya berada jauh di utara.

### B. Ketiadaan Guard Klausul Spasial pada Fungsi Reposisi
Fungsi `find_repair_coordinate()` langsung mencari poligon target berdasarkan string `target_subsls = str(row["level_6_full_code"])` dan menghitung posisi baru (interpolasi / pergeseran) tanpa memeriksa terlebih dahulu apakah koordinat mentah asli titik tersebut sudah berada di dalam batas home poligonnya.

### C. Kegagalan Predikat Spasial `within` pada Batas Garis Poligon
Penggunaan `gpd.sjoin(..., predicate="within")` pada geometri batas menyebabkan titik-titik yang terletak tepat pada garis tepi (boundary/vertex) poligon menghasilkan nilai `idsubsls_overlay = NaN`. Nilai `NaN` ini menyebabkan titik divonis offside secara palsu.

### D. Kelemahan Fallback `centroid` pada Poligon Non-Konveks
Pada kondisi tidak ada titik tetangga untuk interpolasi, algoritma lama menggunakan `poly.centroid`. Pada poligon multipolygon, berbentuk bulan sabit, huruf U, atau memanjang lekuk, titik centroid secara geometris dapat jatuh di luar badan poligon.

---

## 3. Rincian Perbaikan Algoritma yang Diterapkan

1. **Perlindungan Hirarki Ganda (Dual-Level SLS & SubSLS Guard)**:
   - Evaluasi kesesuaian spasial memeriksa kecocokan pada tingkat SubSLS (16-digit) **ATAU** kesesuaian pada tingkat home SLS (14-digit: `idsls_overlay == level_5_full_code` atau `overlay[:14] == home[:14]`).
   - Jika titik berada di dalam poligon mana pun yang merupakan bagian dari home SLS-nya, titik berstatus `flag_repair = 0` (**HARAM DIGESER**).

2. **Penggantian Predikat Spasial ke `intersects` & Resolusi Titik Batas**:
   - Mengganti `predicate="within"` menjadi `predicate="intersects"` agar titik di garis batas tetap terdeteksi.
   - Melakukan deduplikasi hasil `sjoin` dengan memprioritaskan baris yang cocok dengan home SLS/SubSLS titik tersebut.

3. **Immutable Guard pada `find_repair_coordinate()`**:
   - Sebelum melakukan perhitungan apa pun, fungsi memverifikasi geometri asli:
     ```python
     if poly.contains(raw_pt) or poly.intersects(raw_pt):
         return (row["geotag_latitude"], row["geotag_longitude"], "already_inside_home")
     ```
   - Titik yang sudah berada di dalam batas dijamin 100% mempertahankan koordinat aslinya.

4. **Fallback Topologis `representative_point()`**:
   - Seluruh fallback penggantian koordinat yang semula menggunakan `poly.centroid` diubah menjadi `poly.representative_point()`. Metode ini menjamin secara matematis bahwa titik pengganti selalu berada di dalam interior poligon.

5. **Koreksi Kolom pada `refactor_fields()`**:
   - Memperbaiki komparasi `flag_repair_sls` agar membandingkan `idsls_overlay` dengan `level_5_full_code` asli, bukan membandingkan kolom titik dengan dirinya sendiri.

