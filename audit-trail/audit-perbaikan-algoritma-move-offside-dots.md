# Audit & Rancang Bangun: Isolasi Reposisi Titik Offside (Anti-Pergeseran Titik Valid)

**Tanggal:** 2026-11-02  
**Objek Investigasi:** Modul Pemrosesan Spasial (`s02_repair_geotagging.py`, `s03_perhitungan_muatan.py`, `move_failed.py`)  
**Masalah Kritis:** Seluruh titik bangunan (~44.000 titik) mengalami pergeseran koordinat (`flag_position = 1`), padahal hanya **10.034 titik** yang berstatus `OFFSIDE` terhadap home poligon SLS-nya. Titik yang sudah valid di dalam poligon ikut tercemar dan bergeser.

---

## 1. Hasil Deep Scan: 4 Akar Masalah (Root Causes)

Setelah menelusuri alur kode bawaan pada pipeline `01-move offside dots`, ditemukan 4 cacat logika fatal yang menyebabkan titik valid ikut bergeser:

### Akar Masalah 1: Agregasi Median Buta di `s02_repair_geotagging.py` (Baris 438–460)
- **Kode Bermasalah:**
  ```python
  median_coord = (
      joined
      .groupby("unique_bang")
      .agg({"geotag_latitude": "median", "geotag_longitude": "median"})
      .reset_index()
      .rename(columns={"geotag_latitude": "latitude_edited", "geotag_longitude": "longitude_edited"})
  )
  joined = joined.merge(median_coord, on="unique_bang", how="left")
  ```
- **Dampak Fatal:**  
  Pengembang terdahulu berasumsi bahwa bangunan dengan banyak keluarga harus disatukan ke koordinat median. Namun, agregasi ini dijalankan secara **global ke seluruh baris**, tanpa memfilter `flag_repair == 1`.
  Jika sebuah bangunan memiliki lebih dari 1 geotag survei (misal 2 keluarga), koordinat kedua titik tersebut langsung digantikan oleh nilai median sintetik. Titik yang semula valid berada di dalam poligon home SLS berubah koordinatnya.

### Akar Masalah 2: Penimpaan Geometri Fisik secara Global di `s02_repair_geotagging.py` (Baris 505–508)
- **Kode Bermasalah:**
  ```python
  joined["geometry"] = gpd.points_from_xy(
      joined["longitude_edited"],
      joined["latitude_edited"]
  )
  ```
- **Dampak Fatal:**  
  Geometri spasial SHAPELY dari **SEMUA TITIK** digantikan dengan `longitude_edited` dan `latitude_edited`. Karena titik valid sudah tercemar oleh nilai median pada langkah sebelumnya, geometri aslinya hilang ditimpa koordinat median.

### Akar Masalah 3: Penandaan `flag_position = 1` Tanpa Toleransi di `s03_perhitungan_muatan.py` (Baris 735–749)
- **Kode Bermasalah:**
  ```python
  gs_internal["flag_position"] = np.where(
      (gs_internal["latitude_origin"] == gs_internal["latitude_edited"]) &
      (gs_internal["longitude_origin"] == gs_internal["longitude_edited"]),
      0,
      1
  )
  ```
- **Dampak Fatal:**  
  Karena koordinat edited tercemar oleh nilai median, kondisi `latitude_origin == latitude_edited` bernilai `False` pada hampir seluruh titik kabupaten. Seluruh dataset dicap `flag_position = 1` seolah-olah seluruh titik digeser oleh operator.

### Akar Masalah 4: `flag_position = 1` Hardcoded pada `move_failed.py` (Baris 179)
- **Kode Bermasalah:**
  ```python
  props["flag_position"] = 1
  ```
- **Dampak Fatal:**  
  Skrip menetapkan `flag_position = 1` secara membabi buta tanpa mengecek apakah titik tersebut benar-benar digeser atau sudah berada di dalam poligon (`already_inside`).

---

## 2. Prinsip Rekayasa Baru: Immutabilitas Titik Valid (Zero-Touch)

> [!CRITICAL]
> **Hukum Mutlak Validasi Spasial:**
> 1. Titik dengan status `flag_repair == 0` (berada di dalam home poligon `level_6_full_code` / `idsubsls_origin`) berstatus **IMMUTABLE (HARAM DISENTUH)**.
> 2. `latitude_edited` dan `geotag_latitude` pada titik valid **WAJIB 100% SAMA** dengan `latitude_origin` mentah.
> 3. `longitude_edited` dan `geotag_longitude` pada titik valid **WAJIB 100% SAMA** dengan `longitude_origin` mentah.
> 4. `flag_position` pada titik valid **WAJIB bernilai 0**.
> 5. **Hanya 10.034 titik yang berstatus `flag_repair == 1` (`OFFSIDE`)** yang boleh diproses oleh algoritma interpolasi maupun reposisi poligon.

---

## 3. Rencana Perbaikan Kode Komprehensif

### A. Perbaikan pada `01-move offside dots/00 - module/s02_repair_geotagging.py`
1. **Isolasi Median Hanya untuk Bangunan yang Memiliki Titik Offside:**
   Nilai median hanya boleh dihitung dari titik-titik valid di dalam bangunan yang sama jika ada titik offside, DAN **tidak boleh menimpa** nilai titik yang berstatus `flag_repair == 0`.
2. **Klausul Guard pada Titik Valid:**
   ```python
   # Titik valid (INSIDE) mempertahankan koordinat mentahnya 100%
   is_inside = (joined["flag_repair"] == 0)
   joined.loc[is_inside, "latitude_edited"] = joined.loc[is_inside, "geotag_latitude"]
   joined.loc[is_inside, "longitude_edited"] = joined.loc[is_inside, "geotag_longitude"]
   joined.loc[is_inside, "repair_status"] = "original_inside"

   # Hanya titik offside (flag_repair == 1) yang dihitung koordinat barunya
   repair_idx = joined["flag_repair"] == 1
   for idx, row in joined[repair_idx].iterrows():
       lat_new, lon_new, status = find_repair_coordinate(row, valid_points, gdf_poly)
       joined.at[idx, "latitude_edited"] = lat_new
       joined.at[idx, "longitude_edited"] = lon_new
       joined.at[idx, "repair_status"] = status
   ```

### B. Perbaikan pada `01-move offside dots/00 - module/s03_perhitungan_muatan.py`
Kunci `flag_position` berdasarkan status riil:
```python
# flag_position hanya boleh 1 jika koordinat benar-benar berpindah melebihi toleransi spasial (> 0.5 meter)
# DAN titik tersebut memang semula berstatus offside
lat_diff = np.abs(gs_internal["latitude_origin"] - gs_internal["latitude_edited"])
lon_diff = np.abs(gs_internal["longitude_origin"] - gs_internal["longitude_edited"])
moved_mask = (lat_diff > 1e-6) | (lon_diff > 1e-6)

gs_internal["flag_position"] = np.where(moved_mask, 1, 0)
```

### C. Perbaikan pada `01-move offside dots/module/move_failed.py`
Hanya set `flag_position = 1` bila titik benar-benar berpindah posisi (bukan `already_inside`):
```python
if method == "already_inside":
    props["flag_position"] = 0
else:
    props["flag_position"] = 1
```

### D. Perbaikan pada `01-move offside dots/module/extract_failed.py`
Pastikan filter ekstraksi secara presisi hanya menyaring:
- Titik dengan `flag_repair == 1` ATAU `status == 'OFFSIDE'`
- Mengabaikan seluruh titik dengan `flag_repair == 0`.

---

## 4. Matriks Verifikasi Target Pasca-Perbaikan

| Indikator Validasi | Kondisi Rusak Saat Ini | Target Pasca-Perbaikan | Status |
|---|---|---|---|
| **Total Titik Kabupaten** | ~44.000 titik | ~44.000 titik | Tetap |
| **Titik Bergeser (`flag_position = 1`)** | ~44.000 titik (100%) | **Tepat 10.034 titik** | Siap Diterapkan |
| **Titik Asli Tidak Bergeser (`flag_position = 0`)** | 0 titik (0%) | **~34.000 titik (Sisa)** | Siap Diterapkan |
| **Koordinat Titik Valid (`flag_repair = 0`)** | Berubah ke Median | **Identik 100% Data Mentah** | Siap Diterapkan |

---

## 5. Tahapan Eksekusi Step-by-Step

- [x] **Step 1**: Terapkan klausul guard immutabilitas titik valid di [`01-move offside dots/00 - module/s02_repair_geotagging.py`](file:///c:/laragon/www/wilkerstat-checker/01-move%20offside%20dots/00%20-%20module/s02_repair_geotagging.py) (menghapus agregasi median global & mengunci koordinat `flag_repair == 0`).
- [x] **Step 2**: Perbaiki logika kalkulasi `flag_position` pada [`01-move offside dots/00 - module/s03_perhitungan_muatan.py`](file:///c:/laragon/www/wilkerstat-checker/01-move%20offside%20dots/00%20-%20module/s03_perhitungan_muatan.py) (toleransi spasial `1e-6` & guard mutlak `flag_repair == 0` -> `flag_position = 0`).
- [x] **Step 3**: Perbaiki penandaan `flag_position` kondisional di [`01-move offside dots/module/move_failed.py`](file:///c:/laragon/www/wilkerstat-checker/01-move%20offside%20dots/module/move_failed.py) (`already_inside` -> `flag_position = 0`).
- [x] **Step 4**: Sediakan skrip uji kering mandiri di [`dry_run.py`](file:///c:/laragon/www/wilkerstat-checker/dry_run.py) untuk menghitung titik INSIDE vs OFFSIDE tanpa mengubah berkas.
- [ ] **Step 5**: Pengguna mengeksekusi pipeline pemrosesan ulang via `rtk python "01-move offside dots/run.py"` dan verifikasi hasil.

