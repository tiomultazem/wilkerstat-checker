# AUDIT STANDARISASI SKEMA OUTPUT FINAL (ACUAN: dot_col.csv)
**Berkas Kasus**: `audit-trail/audit standardisasi skema dot_col.md`  
**Objek Analisis**: Berkas master final landmark (`final_landmark_6309_se_2026.geojson`)  
**Tingkat Keyakinan**: [certain] (Berdasarkan dokumen spesifikasi baku `dot_col.csv`)

---

## 1. The Uncomfortable Truth (Fakta Pahit)
[certain] Berkas final membengkak dari ~50 MB menjadi 135,5 MB karena penumpukan **25 kolom duplikat/sampah internal** dan **presisi koordinat berlebih (16-17 digit desimal)**.  
Daftar baku yang benar pada [dot_col.csv](file:///c:/laragon/www/wilkerstat-checker/dot_col.csv) menetapkan **tepat 22 atribut (+ 1 kolom geometry)**. Semua kolom di luar daftar tersebut adalah sampah residu pipeline yang wajib dimusnahkan.

---

## 2. Pemetaan Eliminasi & Penyelarasan Kolom

### A. 22 Kolom Resmi Sesuai `dot_col.csv`
| No | Nama Kolom Baku | Tipe Data | Sumber / Aturan Mapping |
|---|---|---|---|
| 1 | `assignment_id` | String | `assignment_id` (singkirkan `id_assignment`) |
| 2 | `flag_repair` | Integer | `flag_repair` (0 = Inside, 1 = Offside) |
| 3 | `flag_position` | Integer | `flag_position` (0 = Asli, 1 = Bergeser) |
| 4 | `idsubsls_origin` | String | Asal: `level_6_full_code` (16 digit) |
| 5 | `idsubsls_edited` | String | Asal: `idsubsls_261` / `idsubsls` overlay peta |
| 6 | `latitude_origin` | Decimal | Latitude mentah awal (dibulatkan 8 desimal) |
| 7 | `longitude_origin` | Decimal | Longitude mentah awal (dibulatkan 8 desimal) |
| 8 | `latitude_edited` | Decimal | Latitude final hasil edit/asli (dibulatkan 8 desimal) |
| 9 | `longitude_edited` | Decimal | Longitude final hasil edit/asli (dibulatkan 8 desimal) |
| 10 | `no_bang` | Integer | `no_bang` |
| 11 | `kode_bang_value` | Integer | `kode_bang_value` |
| 12 | `kdprov` | String | `kdprov` |
| 13 | `nmprov` | String | `nmprov` |
| 14 | `kdkab` | String | `kdkab` |
| 15 | `nmkab` | String | `nmkab` |
| 16 | `kdkec` | String | `kdkec` |
| 17 | `nmkec` | String | `nmkec` |
| 18 | `kddesa` | String | `kddesa` |
| 19 | `nmdesa` | String | `nmdesa` |
| 20 | `idsls` | String | `idsls` (14 digit) |
| 21 | `nmsls` | String | `nmsls` (Nama SLS peta) |
| 22 | `sls` | String | Asal: `level_6_name` / `sls` (Nama SLS titik) |
| - | `geometry` | Point | Koordinat final [longitude_edited, latitude_edited] (8 desimal) |

### B. Daftar 25 Kolom Sampah yang Dimusnahkan
1. `id_assignment` (duplikat `assignment_id`)
2. `unique_bang`
3. `level_6_full_code` (sudah jadi `idsubsls_origin`)
4. `level_5_full_code` (duplikat `idsls`)
5. `idsubsls` (sudah jadi `idsubsls_edited`)
6. `idsubsls_261` (sudah jadi `idsubsls_edited`)
7. `idsls_overlay`
8. `geotag_latitude` (duplikat `latitude_edited`)
9. `geotag_longitude` (duplikat `longitude_edited`)
10. `geotag_accuracy`
11. `no_bang_clean`
12. `no_bang_str`
13. `flag_repair_initial`
14. `flag_repair_sls`
15. `flag_psls`
16. `is_inside_home`
17. `repair_status`
18. `ec_keluarga`
19. `ada_keluarga_value`
20. `kk`
21. `btt`
22. `bku`
23. `bttk`
24. `bbtt` / `bbtt_nonusaha`
25. `count_usaha` / `jumlah_usaha_ditemukan` / `usaha` / `nama_usaha_bang` / `status`

---

## 3. Optimasi Ukuran Berkas
1. **Penyusutan Jumlah Kolom**: Menghapus 25 kunci JSON per titik untuk 104.216 titik menghemat ~55 MB teks JSON.
2. **Pembulatan Koordinat 8 Desimal**: Memangkas float dari 17 digit menjadi 8 digit (`round(x, 8)`) menjaga ketelitian spasial tingkat milimeter (< 1 mm) sekaligus menghemat ~25 MB teks JSON.
3. **Estimasi Ukuran Final**: Berkas turun dari **135,5 MB** menjadi **~38 MB** tanpa kehilangan 1 bit pun informasi spasial valid.

