# Audit Akses & Ekspor Data Gabungan Hasil Upload Petugas

**Tanggal:** 2026-11-02  
**Tujuan:** Memetakan lokasi unduh (*download*) seluruh data gabungan hasil unggahan petugas (poligon SLS dan titik muatan landmark) dalam format murni GeoJSON, menghapus dependensi ekspor GPKG, dan menyediakan tombol fisik di web.

---

## 1. Lokasi Unduh Hasil Pembaruan (GeoJSON)

### A. Titik Muatan Landmark Gabungan (Dot)
- **Antarmuka Web:** Menu [`/issues`](file:///c:/laragon/www/wilkerstat-checker/issues) -> tombol **`⬇ Titik GeoJSON`**
- **Tautan Langsung:** `http://localhost:11750/api/export/dot_geojson`
- **Nama Berkas Unduhan:** `titik_gabungan.geojson`
- **Isi Berkas:** Seluruh titik hasil gabungan semua petugas dengan kolom atribut asli, koordinat termutakhir, serta kolom validasi: `assignment_id`, `idsubsls_origin`, `flag_repair`, `flag_position`, `jarak_m`, dan `status`.
- **Status GPKG:** Fitur unduh `dot_gpkg` telah **dimusnahkan** sepenuhnya.

---

### B. Poligon SLS Gabungan (Shape)
- **Antarmuka Web:** Menu [`/issues`](file:///c:/laragon/www/wilkerstat-checker/issues) -> tombol **`⬇ Poligon SLS GeoJSON`**
- **Tautan Langsung:** `http://localhost:11750/api/export/shape_geojson`
- **Nama Berkas Unduhan:** `sls_gabungan.geojson`
- **Isi Berkas:** Seluruh poligon SLS yang berhasil diunggah petugas dalam format FeatureCollection GeoJSON standar EPSG:4326.

---

### C. Laporan Isu Spasial
- Poligon Overlap: `http://localhost:11750/api/export/overlap_geojson`
- Poligon Gap: `http://localhost:11750/api/export/gap_geojson`
- Poligon Multipart: `http://localhost:11750/api/export/multipart_geojson`
- Titik Offside (XLSX): `http://localhost:11750/api/export/dot_offside?format=xlsx`
- Titik Wajib Perbaikan (XLSX): `http://localhost:11750/api/export/dot_flag_repair?format=xlsx`

---

## 2. Status Implementasi

| Fitur | Status | Detail Implementasi |
|---|---|---|
| **Ekspor Titik GeoJSON** | Selesai | Endpoint `/api/export/dot_geojson` & tombol `⬇ Titik GeoJSON` di `/issues` |
| **Ekspor Poligon SLS GeoJSON** | Selesai | Endpoint `/api/export/shape_geojson` & tombol `⬇ Poligon SLS GeoJSON` di `/issues` |
| **Pemusnahan GPKG Export** | Selesai | Penghapusan handler `dot_gpkg` di backend & pembersihan tombol di frontend |


