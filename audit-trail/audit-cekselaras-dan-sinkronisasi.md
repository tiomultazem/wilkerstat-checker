# Audit Verifikasi Keselarasan Skema & Sinkronisasi Titik Spasial

**Tanggal:** 2026-10-31  
**Target Analisis:** 
1. `00-identify dots/titik sebelum identifikasi.geojson` (Data Mentah Geotagging Awal)
2. `01-move offside dots/03 - final/final_landmark_6309_se_2026.geojson` (Dataset Master Muatan Kabupaten)
3. `01-move offside dots/moved_failed.geojson` (Subset Titik Gagal yang Sudah Diposisikan INSIDE)

---

## 1. Koreksi Gap Asumsi & Hakikat Dataset

> [!CRITICAL]
> **Koreksi Asumsi Jumlah Baris:**  
> `moved_failed.geojson` **TIDAK AKAN PERNAH** memiliki jumlah baris yang sama dengan `final_landmark_6309_se_2026.geojson` atau `titik sebelum identifikasi.geojson`.
> - `titik sebelum identifikasi.geojson`: Berisi seluruh titik bangunan se-kabupaten (~44.000 titik).
> - `final_landmark_6309_se_2026.geojson`: Berisi seluruh titik bangunan se-kabupaten hasil proses modul muatan (~44.000 titik), namun masih menyisakan titik-titik yang posisinya OFFSIDE/gagal diolah oleh algoritma QGIS tahap awal.
> - `moved_failed.geojson`: Merupakan **subset khusus** (~845 titik) dari titik-titik yang berstatus gagal/offside yang telah ditarik paksa ke dalam poligon rumah asalnya (`INSIDE`).
> 
> Maka dari itu, penggabungan tidak dilakukan secara append (tambah baris), melainkan **Replace by Key (`assignment_id`)**: memperbarui koordinat dan atribut 845 titik bermasalah yang ada di dalam `final_landmark` dengan koordinat valid dari `moved_failed`.

---

## 2. Matriks Perbandingan Kolom Antar-Dataset

| Kolom | Titik Mentah (`00`) | Final Landmark (`01`) | Moved Failed (`01`) | Kategori & Perlakuan |
|---|:---:|:---:|:---:|---|
| `assignment_id` / `id_assignment` | Ada (`assignment_id`) | Ada (keduanya) | Ada (keduanya) | **Primary Key** — Wajib identik 100% |
| `unique_bang` | Ada | Ada | Ada | Wajib identik |
| `no_bang` | Ada | Ada | Ada | Wajib identik |
| `kode_bang_value` | Ada | Ada | Ada | Wajib identik |
| `latitude_origin` | - | Ada | Ada | Diambil dari `geotag_latitude` mentah |
| `longitude_origin` | - | Ada | Ada | Diambil dari `geotag_longitude` mentah |
| `latitude_edited` | - | Ada (Algoritma) | Ada (Reposisi) | Berubah; **Wajib NOT NULL** |
| `longitude_edited` | - | Ada (Algoritma) | Ada (Reposisi) | Berubah; **Wajib NOT NULL** |
| `geotag_latitude` | Ada (Mentah) | Ada (Sinkronisasi) | Ada (Sinkronisasi) | Kompatibilitas Model3; **NOT NULL** |
| `geotag_longitude` | Ada (Mentah) | Ada (Sinkronisasi) | Ada (Sinkronisasi) | Kompatibilitas Model3; **NOT NULL** |
| `level_6_full_code` | Ada | Ada | Ada | Kunci evaluasi Model3; **NOT NULL** |
| `idsubsls_origin` | - | Ada | Ada | Kloning dari `level_6_full_code`; **NOT NULL** |
| `idsubsls_edited` | - | Ada | Ada | SLS penempelan hasil intersect |
| `flag_position` | - | Ada (`0`/`1`) | Ada (`1`) | Indikator titik tergeser |
| `kk`, `btt`, `bku`, `bttk`, `bbtt_nonusaha`, `usaha` | - | Ada (Muatan) | Ada (Muatan) | Tetap dipertahankan dari master final |
| `flag_repair`, `status`, `jarak_m`, `repair_method` | - | - | Ada (Diagnostik) | Hanya metadata recovery di `moved_failed` |

---

## 3. Desain Logika `cekselaras.py`

Skrip `cekselaras.py` dirancang untuk berjalan di direktori root dengan 4 tugas audit dan 1 tugas eksekusi sinkronisasi:

### A. Uji 1: Keselarasan Kolom (Schema Check)
- Memeriksa kelengkapan kolom wajib Model3 (`level_6_full_code`, `geotag_latitude`, `geotag_longitude`, `idsubsls_origin`).
- Mendeteksi kolom yang hilang atau inkonsisten antar ketiga dataset.

### B. Uji 2: Keselarasan Nilai Statis (Integrity Check)
- Memverifikasi apakah nilai identitas (`assignment_id`, `no_bang`, `kode_bang_value`, `unique_bang`, `latitude_origin`, `longitude_origin`) pada `final_landmark` dan `moved_failed` cocok dengan nilai aslinya di `titik sebelum identifikasi.geojson`.

### C. Uji 3: Uji Nilai Kosong pada Kolom Algoritma (Nullity Check)
- Memastikan tidak ada nilai `NULL` atau string kosong pada:
  - `latitude_edited` dan `longitude_edited`
  - `geotag_latitude` dan `geotag_longitude`
  - `level_6_full_code` dan `idsubsls_origin`
  - `flag_position`

### D. Uji 4: Audit Jumlah Baris & Titik Offside
- Menghitung total baris dataset mentah vs final landmark.
- Mendeteksi berapa titik di `final_landmark` yang assignment_id-nya ada di `moved_failed`.
- Memvalidasi bahwa seluruh subset `moved_failed` terpetakan secara utuh ke `final_landmark`.

### E. Eksekusi Penggabungan (Replace In-Place)
- Jika opsi sinkronisasi diaktifkan:
  1. Melakukan replace titik di `final_landmark` yang cocok dengan `moved_failed`:
     - Memperbarui geometri `coordinates` titik.
     - Memperbarui `latitude_edited`, `longitude_edited`, `geotag_latitude`, `geotag_longitude`.
     - Mengubah `flag_position = 1`.
     - Memastikan `level_6_full_code` dan `idsubsls_origin` terisi kode SLS asal.
     - Mempertahankan kolom muatan (`kk`, `btt`, dll.).
  2. Menyimpan hasil terpadu ke `01-move offside dots/03 - final/final_landmark_6309_se_2026.geojson` (dengan backup berkas asli bertanda `.bak`).

---

## 4. Rencana Tahapan Eksekusi Step-by-Step

- [x] **Step 1**: Tulis skrip [`cekselaras.py`](file:///c:/laragon/www/wilkerstat-checker/cekselaras.py) di root sesuai spesifikasi audit.
- [ ] **Step 2**: Pengguna menjalankan audit pemeriksaan keselarasan via terminal:
  ```cmd
  rtk python cekselaras.py --check
  ```
- [ ] **Step 3**: Jika hasil uji valid dan bebas anomali, pengguna menjalankan sinkronisasi replacement:
  ```cmd
  rtk python cekselaras.py --sync
  ```
- [ ] **Step 4**: Validasi ulang hasil output menggunakan QGIS Model3 untuk menjamin `flag_repair = 0` (100% INSIDE).

