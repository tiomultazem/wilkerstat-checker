# AUDIT FORENSIK: AKAR PENYEBAB ANOMALI 9.856 TITIK
## Mengapa `level_6_full_code` Berbeda dengan `idsubsls_origin`?

- **Lokasi Berkas**: `c:\laragon\www\wilkerstat-checker\audit-trail\audit anomali 9856 level 6 vs idsubsls origin.md`
- **Tanggal Audit**: 2026-11-03
- **Tingkat Keyakinan**: [certain] (Berdasarkan audit forensik XML QGIS Model 3, skema GeoJSON mentah, dan alur transformasi pipeline)

---

## 1. The Uncomfortable Truth (Fakta Pahit)

[certain] Asumsi bahwa algoritma reposisi atau AI sengaja mengubah/mengotak-atik identitas SLS titik adalah **KELIRU**. 

Akar masalah 9.856 ketidaksesuaian ini berakar dari **kesalahan fatal pada formula QGIS Model 3 (`01 Identifikasi Titik.model3`) yang dibuat sejak awal**:
1. Di data mentah survei lapangan (`titik sebelum identifikasi.geojson`), **kolom `idsubsls_origin` TIDAK PERNAH ADA**. Identitas SLS rumah tangga asli hanya ada di kolom `level_6_full_code`.
2. QGIS Model 3 membuat kolom baru bernama `idsubsls_origin`, namun mengisinya dengan formula:
   ```xml
   coalesce("idsubsls", "idsls")
   ```
   Formula ini mengambil **kode poligon peta Wilkerstat tempat titik jatuh (overlay)**, BUKAN kode identitas rumah tangga asli!
3. Jika sebuah titik jatuh di RT/SubSLS sebelah (offside sebanyak 9.856 titik), Model 3 mencatat:
   - `level_6_full_code`: kode SLS asli lapangan (misal: `6309060008000602`)
   - `idsubsls_origin`: kode poligon tetangga tempat titik melenceng (misal: `6309060008000603`)
4. Pada pipeline Tahap 3 lama (`s03_perhitungan_muatan.py`), saat mengekspor 22 kolom baku sesuai `dot_col.csv`:
   - Kolom `level_6_full_code` dibuang karena tidak terdaftar di `dot_col.csv`.
   - Kolom `idsubsls_origin` diambil langsung dari atribut masukan (yang sudah terlanjur berisi kode poligon tetangga dari Model 3).
5. Akibatnya, pada `final_landmark_6309_se_2026.geojson`, 9.856 titik tersebut membawa kode poligon tetangga, bukan kode SLS rumah tangga aslinya.

---

## 2. Bukti Forensik Tak Terbantahkan (Hard Evidence)

### A. Data Mentah Lapangan: `titik sebelum identifikasi.geojson`
Pada berkas mentah sebelum masuk Model 3, kolom `idsubsls_origin` **sama sekali belum eksis**:
```json
{
  "assignment_id": "8a047aaa-8a27-464a-82c6-f33cfd39c8ba",
  "level_6_full_code": "6309060008000602",
  "level_6_name": "RT 006",
  "no_bang": "0082"
}
```

### B. Cacat Formula di `01 Identifikasi Titik.model3` (Baris 306–312)
Model 3 mendefinisikan pembuatan field `idsubsls_origin` sebagai berikut:
```xml
<Option type="Map">
  <Option type="QString" name="expression" value="coalesce(&quot;idsubsls&quot;, &quot;idsls&quot;)"/>
  <Option type="int" name="length" value="0"/>
  <Option type="QString" name="name" value="idsubsls_origin"/>
  <Option type="int" name="precision" value="0"/>
  <Option type="int" name="type" value="10"/>
</Option>
```
> **Catatan Kritis**: Di Model 3, `idsubsls` dan `idsls` adalah atribut yang berasal dari layer **Poligon SLS** (hasil spatial overlay). Memberi nama field tersebut `idsubsls_origin` adalah kontradiksi semantik, karena isinya adalah poligon overlay (`idsubsls_edited`), bukan SLS asal (`idsubsls_origin`).

### C. Hasil Model 3 di `titik hasil identifikasi.geojson`
Pada berkas keluaran Model 3, dualisme nilai ini mulai muncul secara permanen pada 9.856 fitur:
```json
{
  "assignment_id": "8a047aaa-8a27-464a-82c6-f33cfd39c8ba",
  "level_6_full_code": "6309060008000602",   <-- Identitas SLS ASLI survei
  "idsubsls_origin":   "6309060008000603",   <-- Poligon tetangga dari Model 3!
  "flag_repair": 1
}
```

---

## 3. Matriks Perbandingan 5 Sampel Anomali

| assignment_id | Mentah Awal (`level_6_full_code`) | Model 3 (`level_6_full_code`) | Model 3 (`idsubsls_origin` hasil overlay) | Final Landmark (`idsubsls_origin`) | Keterangan Anomali |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `8a047aaa-8a27-464a-82c6-f33cfd39c8ba` | `6309060008000602` | `6309060008000602` | `6309060008000603` | `6309060008000603` | Model 3 menimpa origin dengan poligon SubSLS 03 |
| `d66c1a86-ec68-4d01-ade8-b7232ca83c9b` | `6309081002000700` | `6309081002000700` | `6309081002000400` | `6309081002000400` | Model 3 menimpa origin dengan poligon RT 04 |
| `e55ff47a-4199-4c4f-b3b5-b7dfc6df5d63` | `6309070001000300` | `6309070001000300` | `6309070001000901` | `6309070001000901` | Model 3 menimpa origin dengan poligon RT 09 |
| `2683fff8-00c6-4c90-aadc-07b14f254e53` | `6309050017000201` | `6309050017000201` | `6309050017000801` | `6309050017000801` | Model 3 menimpa origin dengan poligon RT 08 |
| `b6da54da-4451-4b8e-8232-aaf98399cc35` | `6309050017000801` | `6309050017000801` | `6309050017000602` | `6309050017000602` | Model 3 menimpa origin dengan poligon RT 06 |

---

## 4. Solusi Penyelesaian (Step-by-Step)

Untuk menyelesaikan anomali ini secara permanen tanpa merusak koordinat yang sudah 0% offside:

1. **Step 1 (Restorasi Identitas Master Final)**:
   Buat skrip pemulihan instan yang menyinkronkan nilai `idsubsls_origin` pada `final_landmark_6309_se_2026.geojson` langsung dari `level_6_full_code` data mentah (`titik sebelum identifikasi.geojson` atau `titik hasil identifikasi.geojson`).
2. **Step 2 (Koreksi Formula QGIS Model 3)**:
   Ubah ekspresi baris 307 di `00-identify dots/model/01 Identifikasi Titik.model3` menjadi:
   ```xml
   coalesce("level_6_full_code", "idsubsls_origin", '')
   ```
   dan pastikan kolom poligon disimpan ke `idsubsls_edited` bukan `idsubsls_origin`.
3. **Step 3 (Verifikasi Ulang Keselarasan)**:
   Jalankan kembali modul verifikasi `cekselaras.py --compare` untuk memastikan 104.216 titik 100% selaras identik (0 anomali).

---

## 5. Keputusan Arsitektur: Preservasi Kolom Wajib QGIS Model 2

Berdasarkan kebutuhan input pada QGIS Model 2 (`00-identify dots/Model/02 Pengecekan Titik.model3`), seluruh tahapan pemrosesan **Step 1 hingga Step 6 DILARANG menghapus atribut** yang dibutuhkan oleh Model 2.

### Daftar Kolom yang Wajib Bertahan di Step 1–6:
1. **Atribut Spasial & Evaluasi Logika**:
   - `level_6_full_code` (Kunci evaluasi: `"level_6_full_code" = "idsubsls"`)
   - `idsubsls_origin` (Kode identitas lapangan)
   - `latitude_origin` & `longitude_origin` (Kunci kalkulasi `flag_position`)
   - `flag_repair` & `flag_repair_initial` (Kunci kalkulasi `flag_edit_atr_repair`)
   - `assignment_id` (Kunci deduplikasi dan penggabungan)
2. **Atribut Muatan Lapangan**:
   - `unique_bang`, `flag_psls`, `no_bang`, `kode_bang_value`, `ada_keluarga_value`, `ada_bang_usaha_value`, `jumlah_usaha_ditemukan`, `kk`, `btt`, `bku`, `bttk`, `bbtt`, `usaha`, `nama_usaha_bang`.

> **Catatan Implementasi**: Seluruh berkas intermediate (`03-geotagging-edited/*.geojson`, `failed.geojson`, `moved_failed.geojson`, dan master pra-validasi) mempertahankan seluruh kolom di atas agar dapat langsung diproses oleh Model 2 tanpa terjadi *error* atau nilai kosong. Pemangkasan ke skema 22 kolom baku `dot_col.csv` hanya dilakukan saat ekspor produk pengiriman final pasca-validasi Model 2.

---

## 6. Analisis Forensik Kompatibilitas Alur Kerja Antara: Model 1 → Pipeline 1–6 → Model 2

Audit forensik terhadap kode XML [`00-identify dots/Model/02 Pengecekan Titik.model3`](file:///c:/laragon/www/wilkerstat-checker/00-identify%20dots/Model/02%20Pengecekan%20Titik.model3) membuktikan bahwa Model 2 **bukan sekadar validator pasif**, melainkan prosesor spasial aktif yang menghitung ulang status perbaikan dan atribusi titik.

### A. Dekonstruksi Formula Internal Model 2 (XML Forensics)
1. **Ekstraksi Koordinat Aktual (`native:refactorfields_1`)**:
   Model 2 mengekstrak koordinat lintang dan bujur langsung dari geometri fitur titik (`$y` dan `$x`) untuk mengisi `latitude_edited` dan `longitude_edited` ([Baris 312–324](file:///c:/laragon/www/wilkerstat-checker/00-identify%20dots/Model/02%20Pengecekan%20Titik.model3#L312-L324)).
2. **Spatial Join dengan Peta Wilkerstat (`native:joinattributesbylocation_1`)**:
   Model 2 menumpangsari titik terhadap `petawilkerstatlamalapangan` untuk mengambil kode poligon tempat titik berada saat ini (`idsubsls` dan `idsls`) ([Baris 73–158](file:///c:/laragon/www/wilkerstat-checker/00-identify%20dots/Model/02%20Pengecekan%20Titik.model3#L73-L158)).
3. **Deteksi Pergeseran Fisik Titik (`native:refactorfields_3`)**:
   ```xml
   <!-- Baris 479: Menghitung flag_position -->
   <Option type="QString" name="expression" value="if(&quot;latitude_origin&quot; = &quot;latitude_edited&quot;, 0, 1)"/>
   <Option type="QString" name="name" value="flag_position"/>
   ```
   Jika koordinat geometri baru berbeda dari `latitude_origin`, maka `flag_position` otomatis diset menjadi 1.
4. **Evaluasi Keberhasilan Reposisi (`native:refactorfields_3` & `refactorfields_4`)**:
   ```xml
   <!-- Baris 486: Evaluasi kesesuaian poligon baru terhadap SLS survei asli -->
   <Option type="QString" name="expression" value="if(&quot;level_6_full_code&quot; = &quot;idsubsls&quot;, 0, 1)"/>
   <Option type="QString" name="name" value="flag_repair_initial"/>

   <!-- Baris 813: Pembalikan status flag_repair dari 1 menjadi 0 -->
   <Option type="QString" name="expression" value="if(&quot;flag_repair&quot; = 1 AND &quot;flag_repair_initial&quot; = 0, 0, if(&quot;flag_repair_initial&quot; = 1 AND &quot;flag_edit_atr_repair&quot; = 0, 1, &quot;flag_repair&quot;))"/>
   <Option type="QString" name="name" value="flag_repair"/>
   ```
   > **Fakta Kunci**: Model 2 secara otomatis mengubah `flag_repair` dari 1 menjadi 0 HANYA jika koordinat fisik titik yang masuk sudah berada di dalam poligon yang kodenya sama persis dengan `level_6_full_code`.
5. **Deduplikasi Unik (`native:removeduplicatesbyattribute_1`)**:
   Model 2 menyaring seluruh titik keluaran menggunakan atribut kunci `assignment_id` ([Baris 1057](file:///c:/laragon/www/wilkerstat-checker/00-identify%20dots/Model/02%20Pengecekan%20Titik.model3#L1057)).

---

### B. Tiga Sumbatan Teknis Kritis Jika Pipeline Langsung Disambung ke Model 2

Bila alur antara tidak disesuaikan, sistem akan mengalami kegagalan fatal (*pipeline breakdown*):

| No | Komponen Sumbatan | Kondisi di Pipeline Saat Ini | Dampak Fatal pada Model 2 | Solusi Teknis Teruji |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Granularitas Berkas** | Data terpecah menjadi 131 berkas GeoJSON per desa (`01 - data/03-geotagging-edited/`) | Model 2 hanya menerima 1 layer input tunggal (`titikhasilpengolahan`). Pengguna harus menjalankan Model 2 secara manual sebanyak 131 kali! | Bangun modul konsolidasi yang menggabungkan 131 berkas desa menjadi 1 layer GeoJSON utuh (104.216 fitur). |
| **2** | **Cacat Pass-Through `idsubsls_origin`** | Model 1 mengisi `idsubsls_origin` dengan kode poligon tetangga (9.856 titik offside). | Model 2 ([Baris 291 & 827](file:///c:/laragon/www/wilkerstat-checker/00-identify%20dots/Model/02%20Pengecekan%20Titik.model3#L291)) hanya menyalin langsung nilai `idsubsls_origin` tanpa perbaikan. Akibatnya, 9.856 titik tetap membawa kode poligon cacat. | Pipeline wajib menimpa `idsubsls_origin = level_6_full_code` sebelum berkas diserahkan ke Model 2. |
| **3** | **Integritas Geometri vs Teks** | Sebagian skrip memodifikasi atribut teks `latitude_edited` tanpa menggeser objek geometri `Point(x, y)`. | Model 2 mengekstrak `$y` dan `$x` langsung dari geometri. Jika geometri titik tidak dipindahkan secara fisik, Model 2 memvonis titik tidak bergeser (`flag_position = 0`) dan tetap offside (`flag_repair = 1`). | Pastikan skrip reposisi (Step 2 & 5) meng-update array `geometry.coordinates = [lon_baru, lat_baru]`. |

---

## 7. Cetak Biru Alur Eksekusi Terintegrasi (Ready-to-Execute Blueprint)

Berikut adalah alur terpadu yang telah disederhanakan (menggantikan alur usang 6-tahap pemecahan 131 desa menjadi **1 Skrip Jembatan Tunggal Terpadu**):

```
[Data Mentah Lapangan] (104.216 titik) + [Peta Batas SLS Mentah Master Kab]
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 0: QGIS Model 1 (01 Identifikasi Titik.model3)         │
│ - Eksekusi resmi di QGIS                                    │
│ - Deteksi status awal titik offside (flag_repair = 1)       │
│ - Output: titik hasil identifikasi.geojson (30 kolom)       │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: Skrip Jembatan Tunggal Terpadu                      │
│ Berkas: 01-move offside dots/bridge_repair.py               │
│ - Masukan: titik hasil identifikasi.geojson + poligon master│
│ - Vectorized Spatial Snap: geser fisik koordinat titik      │
│   offside langsung ke interior poligon target (STRtree)     │
│ - KOREKSI MUTLAK: idsubsls_origin = level_6_full_code       │
│ - Preservasi penuh 21 kolom wajib input Model 2             │
│ - Output: titik_siap_model2.geojson (104.216 titik, 0% off) │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: Validasi & Atribusi Resmi QGIS Model 2              │
│ Masukan Model 2:                                            │
│   - titikhasilpengolahan = titik_siap_model2.geojson        │
│   - petawilkerstatlamalapangan = slsmentah fixed.geojson    │
│ Proses Komputasi Model 2:                                   │
│   - Ekstrak koordinat baru: latitude/longitude_edited ($y,$x│
│   - Deteksi flag_position (0=tetap, 1=tergeser)             │
│   - Spatial join: isi idsubsls_edited                       │
│   - Balikkan status flag_repair (seluruhnya menjadi 0)      │
│ Output QGIS: hasil_pengecekan_titik.geojson                 │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: Ekspor Akhir Standar BPS & Verifikasi Mutlak        │
│ 1. finalize_delivery.py:                                    │
│    - Pangkas hasil Model 2 ke skema baku 22 kolom dot_col   │
│    - Hitung rekapitulasi muatan (XLSX)                      │
│    - Output: final_landmark_6309_se_2026.geojson            │
│ 2. cekselaras.py --compare:                                 │
│    - Verifikasi 104.216 titik 100% selaras tanpa anomali.   │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Spesifikasi Teknis Skrip Jembatan Tunggal (`bridge_repair.py`)

Skrip ini menggantikan seluruh skrip usang (pemecahan 131 desa, `s02_repair_geotagging`, `extract_failed`, `move_failed`, dan `sync`).

### Kontrak Data Masukan & Keluaran:
* **Masukan Utama**:
  - `00-identify dots/titik hasil identifikasi.geojson` (Keluaran resmi Model 1).
  - `00-identify dots/slsmentah fixed-2025sm1.geojson` (Poligon Master Kabupaten).
* **Aturan Transformasi**:
  1. Muat seluruh titik dan poligon master dalam memori GeoDataFrame.
  2. Identifikasi titik *offside* (`flag_repair == 1` atau `"level_6_full_code" != "idsubsls"`).
  3. Lakukan reposisi spasial fisik vektor:
     - Target poligon diambil dari `level_6_full_code` (SubSLS) dengan fallback 14-digit pertama (SLS utuh jika SubSLS multipart/pecahan).
     - Proyeksikan koordinat titik masuk ke *interior ring* poligon target.
     - Perbarui fisik `geometry = Point(new_lon, new_lat)`.
  4. Lakukan penormalisasi atribut lapangan:
     ```python
     gdf["idsubsls_origin"] = gdf["level_6_full_code"]
     ```
  5. Pertahankan 21 kolom skema Model 1:
     - `assignment_id`, `unique_bang`, `flag_psls`, `flag_repair_initial`, `flag_repair`, `level_6_full_code`, `idsubsls_origin`, `latitude_origin`, `longitude_origin`, `no_bang`, `kode_bang_value`, `ada_keluarga_value`, `ada_bang_usaha_value`, `jumlah_usaha_ditemukan`, `kk`, `btt`, `bku`, `bttk`, `bbtt`, `usaha`, `nama_usaha_bang`.
* **Keluaran**:
  - Berkas: `00-identify dots/titik_siap_model2.geojson`
  - Total Fitur: Tepat **104.216 fitur**.
  - Siap di-load langsung ke QGIS sebagai layer input `titikhasilpengolahan` pada Model 2.



