# Audit Investigasi & Perbaikan: Status Upload Rejected (False Positive)

**Tanggal:** 2026-11-01  
**Gejala:**  
Pengguna mengunggah berkas melalui antarmuka `/upload`. Di layar muncul indikasi upload berhasil diterima server, namun saat diperiksa di halaman `/history` (Riwayat Upload), status tercatat **`rejected`** dan modal detail tidak memberikan penjelasan yang jelas, sehingga disangka sebagai *false positive*.

---

## 1. Hasil Deep Scan: 3 Akar Masalah Utama (Root Causes)

### Akar Masalah 1: `FileNotFoundError` pada Berkas Spesifikasi Kolom (`shape_col.csv` & `dot_col.csv`)
- **Fakta Teknis:**  
  Berkas [`shape_col.csv`](file:///c:/laragon/www/wilkerstat-checker/artifacts/shape_col.csv) dan [`dot_col.csv`](file:///c:/laragon/www/wilkerstat-checker/artifacts/dot_col.csv) berada di dalam folder `artifacts/`, bukan di root proyek (`BASE_DIR`).
- **Mekanisme Kegagalan:**  
  Saat fungsi validasi [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py) memanggil `load_shape_columns(config.SHAPE_COL_CSV)`, sistem mencari berkas di `c:\laragon\www\wilkerstat-checker\shape_col.csv`.  
  Karena berkas tidak ditemukan di lokasi tersebut, Python melempar `FileNotFoundError`.
- **Dampak pada Status:**  
  Blok `except Exception as e:` pada `_process_shape()` menangkap galat ini dan langsung mengeksekusi:
  ```python
  db.update_upload_log(conn, log_id, status="rejected",
                       summary={"error": str(e), "traceback": traceback.format_exc()})
  ```
  Ini bukan *false positive* dari data geospasial, melainkan **kegagalan eksekusi internal akibat path berkas CSV**.

### Akar Masalah 2: Bug Visualisasi Error pada Frontend (`static/history.js`)
- **Fakta Teknis:**  
  Pada berkas [`static/history.js`](file:///c:/laragon/www/wilkerstat-checker/static/history.js) baris 64-67:
  ```javascript
  if (summary.reject_reasons && summary.reject_reasons.length) {
      html += `<h4 style="color:var(--danger)">❌ Alasan Tolak</h4>`;
      summary.reject_reasons.forEach(r => { html += `<div class="error-item">${escHtml(r)}</div>`; });
  }
  ```
- **Mekanisme Kegagalan:**  
  Jika penolakan terjadi akibat *unhandled exception* (seperti `FileNotFoundError` atau galat GDAL), informasi disimpan di `summary.error` dan `summary.traceback`, bukan di `summary.reject_reasons`.
- **Dampak:**  
  Modal detail di `/history` tidak menampilkan teks error apa pun. Pengguna hanya melihat badge merah `rejected` tanpa alasan, sehingga menduga algoritma validasi keliru (*false positive*).

### Akar Masalah 3: Kekakuan Skema Kolom Wajib (*Rigid Column Schema*)
- **Fakta Teknis:**
  1. **Pada Validasi Shape (`validate_shape.py`):**  
     Spesifikasi `shape_col.csv` mewajibkan kolom `petugas` dan `gid` berstatus `not null`. Jika petugas mengunggah peta mentah SLS dari QGIS/BPS yang belum memiliki kolom `petugas`, sistem langsung menolaknya (`result.reject()`).
  2. **Pada Validasi Titik (`validate_dot.py`):**  
     Sistem secara kaku mencari kolom `assignment_id`. Jika berkas ekspor lapangan menggunakan penamaan alternatif seperti `id_assignment`, berkas langsung ditolak mentah-mentah.

---

## 2. Rencana Solusi & Perbaikan Komprehensif

### Solusi 1: Pemulihan Lokasi & Resolusi Dinamis Spesifikasi Kolom
1. Salin berkas `shape_col.csv` dan `dot_col.csv` dari `artifacts/` kembali ke direktori root.
2. Perbarui [`app/config.py`](file:///c:/laragon/www/wilkerstat-checker/app/config.py) dengan fungsi *fallback resolver* multi-jalur:
   ```python
   def _resolve_spec_file(filename):
       for p in [os.path.join(BASE_DIR, filename), os.path.join(BASE_DIR, "artifacts", filename)]:
           if os.path.isfile(p):
               return p
       return os.path.join(BASE_DIR, filename)

   SHAPE_COL_CSV = _resolve_spec_file("shape_col.csv")
   DOT_COL_CSV = _resolve_spec_file("dot_col.csv")
   ```

### Solusi 2: Perbaikan Penanganan Error di `static/history.js`
Tambahkan rendering untuk `summary.error` agar galat teknis transparan terlihat oleh pengguna:
```javascript
if (summary.error) {
    html += `<h4 style="color:var(--danger);margin:12px 0 6px">❌ Galat Sistem</h4>`;
    html += `<div class="error-item">${escHtml(summary.error)}</div>`;
}
```

### Solusi 3: Alias Toleran pada Engine Validasi
1. **Di `app/validate_dot.py`:**  
   Dukung alias `id_assignment` secara otomatis jika `assignment_id` tidak ada:
   ```python
   if "assignment_id" not in gdf.columns and "id_assignment" in gdf.columns:
       gdf["assignment_id"] = gdf["id_assignment"]
   ```
2. **Di `app/validate_shape.py`:**  
   Dukung alias `idsls` jika `idsubsls` tidak ditemukan. Jika kolom `petugas` kosong/hilang pada unggahan shape mandiri, berikan nilai default `(tanpa petugas)` daripada menolak seluruh berkas.

---

## 3. Matriks Tindakan Bertahap & Status Implementasi

- [x] **Step 1**: Sinkronisasi keberadaan berkas `shape_col.csv` dan `dot_col.csv` ke root dan perbarui resolver path di [`app/config.py`](file:///c:/laragon/www/wilkerstat-checker/app/config.py) dengan fallback multi-jalur.
- [x] **Step 2**: Perbarui [`static/history.js`](file:///c:/laragon/www/wilkerstat-checker/static/history.js) agar menampilkan rincian `summary.error` dan `summary.traceback` di modal riwayat.
- [x] **Step 3**: Terapkan *smart aliasing* pada [`app/validate_dot.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_dot.py) (`id_assignment` -> `assignment_id`) dan nilai bawaan `(tanpa petugas)` pada [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py).
- [ ] **Step 4**: Restart server Flask via `rtk run.bat` untuk memuat ulang kode dan worker baru.

