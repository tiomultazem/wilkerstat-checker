# Audit Perencanaan Restrukturisasi Direktori Proyek

**Tanggal:** 2026-10-31  
**Status:** Perencanaan & Verifikasi Ketergantungan (Menunggu Persetujuan)

---

## 1. Analisis Kebutuhan & Masalah Saat Ini

Akar masalah direktori saat ini adalah penumpukan berkas dari tiga domain kerja yang berbeda di direktori *root*:
1. **Aplikasi Web Monitoring LAN** (Flask, Waitress, database operasional, validasi).
2. **Model Analisis QGIS Tahap Awal** (Pemadanan spasial format mentah BPS).
3. **Pipeline Pemrosesan Skrip & Jupyter** (Batch perbaikan, algoritma vektor, dan recovery titik gagal).

Penumpukan ini menyebabkan:
- Kerancuan alur kerja (*workflow confusion*).
- Terjadinya berkas duplikat di root (`extract_failed.py` dan `extract-failed.py`).
- Berkas data besar (>20MB) berserakan di samping kode program web.

---

## 2. Pemetaan Struktur Target

```
wilkerstat-checker/
│
├── [ROOT] APLIKASI WEB MONITORING LAN (Tidak Berubah)
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── worker.py
│   ├── spatial.py
│   ├── validate_shape.py
│   ├── validate_dot.py
│   ├── colours.py
│   ├── col_loader.py
│   ├── tray.py
│   ├── license_manager.py
│   ├── run.py
│   ├── run.bat
│   ├── install.bat
│   ├── download_vendor.bat
│   ├── shape_col.csv
│   ├── dot_col.csv
│   ├── requirements.txt
│   ├── .env / .env.example
│   ├── .gitignore
│   ├── README.md
│   ├── knowledge.md
│   ├── static/
│   ├── templates/
│   ├── data/
│   └── assets/
│
├── 00-identify dots/                     <-- [BARU] TAHAP 1: MODEL & DATA MENTAH
│   ├── 01 Identifikasi Titik.model3       (Model pemrosesan QGIS)
│   ├── titik sebelum identifikasi.geojson (Data mentah geotagging awal)
│   ├── slsmentah fixed-2025sm1.geojson    (Peta acuan batas SLS se-kabupaten)
│   └── titik hasil identifikasi.geojson   (Output hasil run model3)
│
└── 01-move offside dots/                 <-- [BARU] TAHAP 2: PIPELINE REPAIR & RECOVERY
    ├── jupyter.bat                        (Launcher JupyterLab terisolasi)
    ├── split_data.py                      (Pemecah GeoJSON SLS & titik per desa)
    ├── 01-pengolahan_titik_muatan.ipynb   (Notebook utama eksekusi batch)
    ├── 00 - module/                       (Modul s02_repair & s03_muatan)
    │   ├── s02_repair_geotagging.py
    │   └── s03_perhitungan_muatan.py
    ├── 01 - data/                         (Data per-desa terbagi 131 desa)
    │   ├── 01-peta-251/
    │   ├── 02-geotagging/
    │   ├── 03-geotagging-edited/
    │   └── 05-master-261/
    ├── 03 - final/                        (Hasil terpadu landmark & muatan)
    │   └── final_landmark_6309_se_2026.geojson
    │
    │   # Modul Pemulihan Titik Gagal (Fallback Recovery)
    ├── extract_failed.py                  (Ekstraksi titik yang masih OFFSIDE)
    ├── move-failed.py                     (Reposisi otomatis titik gagal ke poligon)
    ├── failed.geojson                     (Daftar titik gagal hasil ekstraksi)
    └── moved_failed.geojson               (Hasil akhir titik yang sudah diposisikan INSIDE)
```

---

## 3. Matriks Pemindahan & Tindakan Berkas

| Berkas Asal | Direktori Tujuan | Tindakan / Penyesuaian Kritis |
|---|---|---|
| `01 Identifikasi Titik.model3` | `00-identify dots/` | Pindahkan langsung |
| `titik sebelum identifikasi.geojson` | `00-identify dots/` | Pindahkan langsung |
| `slsmentah fixed-2025sm1.geojson` | `00-identify dots/` | Pindahkan langsung; update path di `01-move offside dots` |
| `titik hasil identifikasi.geojson` | `00-identify dots/` | Pindahkan langsung |
| `Pengolahan-Wilkerstat-SE2026-main/*` | `01-move offside dots/` | Angkat seluruh isi folder ke dalam `01-move offside dots/` lalu hapus folder kosong `Pengolahan-Wilkerstat-SE2026-main` |
| `jupyter.bat` | `01-move offside dots/` | Update path venv parent `..\venv\Scripts\jupyter-lab.exe` |
| `split_data.py` | `01-move offside dots/` | Update default path input ke `..\00-identify dots\` |
| `extract_failed.py` | `01-move offside dots/` | Simpan sebagai skrip kanonikal |
| `extract-failed.py` | *Dihapus (Eliminasi)* | Duplikat dari `extract_failed.py` |
| `move-failed.py` | `01-move offside dots/` | Update default path input ke `..\00-identify dots\` |
| `failed.geojson` | `01-move offside dots/` | Pindahkan langsung |
| `moved_failed.geojson` | `01-move offside dots/` | Pindahkan langsung |

---

## 4. Dampak & Penyesuaian Path Kritis

> [!WARNING]
> Jika berkas dipindahkan tanpa memperbarui path relatif di dalamnya, skrip Python dan launcher akan mengalami `FileNotFoundError`.

### A. Penyesuaian `jupyter.bat`
Jupyter launcher berada di subfolder `01-move offside dots/`, sehingga pemanggilan virtual environment harus mengarah ke direktori induk:
```bat
call "..\venv\Scripts\activate.bat"
"..\venv\Scripts\jupyter-lab.exe" --notebook-dir="%~dp0"
```

### B. Penyesuaian Path pada `split_data.py`
Skrip ini membutuhkan masukan poligon dan titik dari folder `00-identify dots/`:
- Default poligon: `..\00-identify dots\slsmentah fixed-2025sm1.geojson`
- Default titik: `..\00-identify dots\titik hasil identifikasi.geojson`
- Target folder: direktori lokal `01 - data`

### C. Penyesuaian Path pada `01-pengolahan_titik_muatan.ipynb`
Di dalam notebook, baris rujukan poligon:
```python
wilkerstat_261_path = "../00-identify dots/slsmentah fixed-2025sm1.geojson"
```

### D. Penyesuaian Path pada `move-failed.py`
Rujukan master poligon diarahkan ke:
- `..\00-identify dots\slsmentah fixed-2025sm1.geojson` atau direktori split lokal `01 - data/01-peta-251`

---

## 5. Rencana Langkah Eksekusi (Step-by-Step)

1. **Langkah 1**: Buat folder `00-identify dots/` dan `01-move offside dots/`. *(Selesai)*
2. **Langkah 2**: Pindahkan berkas-berkas model3 dan GeoJSON mentah ke `00-identify dots/`. *(Selesai, tersisa 1 residu terproteksi)*
3. **Langkah 3**: Pindahkan isi `Pengolahan-Wilkerstat-SE2026-main/`, `split_data.py`, `jupyter.bat`, `move-failed.py`, `extract_failed.py`, dan GeoJSON terkait ke `01-move offside dots/`. Hapus duplikat `extract-failed.py`. *(Selesai, tersisa 1 residu terproteksi)*
4. **Langkah 4**: Perbarui seluruh path relatif di dalam skrip `jupyter.bat`, `split_data.py`, `move-failed.py`, dan notebook agar tidak rusak. *(Selesai)*
5. **Langkah 5**: Perbarui dokumentasi [`knowledge.md`](file:///c:/laragon/www/wilkerstat-checker/knowledge.md) dan [`.gitignore`](file:///c:/laragon/www/wilkerstat-checker/.gitignore) agar mencerminkan struktur baru. *(Selesai)*

---

## 7. Pembersihan Residu Berkas Ad-Hoc & Database Root

Ditemukan 5 berkas residual sekunder di direktori root:
1. `split.py`: Skrip utilitas lawas pemotong GeoJSON per kecamatan (`nmkec`). -> Dipindahkan ke `scripts/`.
2. `sync_final_landmark.py`: Skrip pipeline penyesuaian model3 dan sinkronisasi `moved_failed.geojson` ke master landmark. -> Dipindahkan ke `01-move offside dots/`. Path internal disesuaikan.
3. `clear_dots.py`: Skrip CLI pemeliharaan untuk mengosongkan tabel titik di basis data. -> Dipindahkan ke `scripts/`. Path internal disesuaikan.
4. `wilkerstat.db` & `data.db`: Berkas database SQLite yatim di root (database produksi aktif aplikasi adalah `data/wilkerstat.db`). -> Diamankan ke `data/legacy_backup/` agar tidak mengotori root.


### A. Diagnosa Residu di Root
Saat ini di *root* masih menyisakan 2 berkas GeoJSON dan 12 berkas Python:
1. `slsmentah fixed-2025sm1.geojson` (Peta batas kabupaten, tertahan di root karena proteksi berkas/sedang dibuka oleh aplikasi lain seperti QGIS).
2. `moved_failed.geojson` (Hasil titik perbaikan, tertahan di root karena proteksi berkas).
3. 12 Berkas Python Backend Web (`app.py`, `config.py`, `database.py`, `worker.py`, `spatial.py`, `validate_shape.py`, `validate_dot.py`, `colours.py`, `col_loader.py`, `tray.py`, `license_manager.py`, `run.py`).

### B. Target Arsitektur Bersih Root (Clean Layout)
Untuk mencapai kerapian maksimal di mana direktori *root* hanya menyisakan entry point dan konfigurasi esensial, seluruh backend web diisolasi ke dalam paket Python `app/`:

```
wilkerstat-checker/
│
├── [ENTRY POINT & KONFIGURASI ROOT]
│   ├── run.py                  # Satu-satunya berkas eksekusi Python di root
│   ├── run.bat                 # Launcher server LAN
│   ├── install.bat             # Inisialisasi virtualenv & dependensi
│   ├── download_vendor.bat     # Download vendor library (MapLibre)
│   ├── organize.bat            # Skrip batch utilitas migrasi
│   ├── shape_col.csv           # Spesifikasi kolom poligon acuan
│   ├── dot_col.csv             # Spesifikasi kolom titik acuan
│   ├── requirements.txt        # Daftar dependensi pustaka
│   ├── .env / .env.example     # Konfigurasi environment
│   ├── .gitignore              # Aturan repositori Git
│   ├── README.md               # Dokumentasi umum
│   ├── knowledge.md            # Dokumentasi arsitektur teknis
│   ├── static/                 # Aset frontend (CSS, JS)
│   ├── templates/              # Antarmuka Jinja2
│   ├── data/                   # Database SQLite operasional & arsip unggahan
│   └── audit-trail/            # Log audit teknis
│
├── app/                        # [BARU] Seluruh modul logika backend web terisolasi
│   ├── __init__.py             # Factory create_app()
│   ├── app.py                  # Controller routes & API endpoints
│   ├── config.py               # Parsing konfigurasi & resolve root BASE_DIR
│   ├── database.py             # SQLite WAL & isolasi transaksi
│   ├── worker.py               # Background task queue
│   ├── spatial.py              # Operasi spasial geospasial murni
│   ├── validate_shape.py       # Engine validasi poligon
│   ├── validate_dot.py         # Engine validasi titik
│   ├── colours.py              # Generator palet warna golden-angle
│   ├── col_loader.py           # Parser CSV skema
│   ├── tray.py                 # Systray Windows
│   └── license_manager.py      # Pengelola lisensi
│
├── 00-identify dots/           # Modul Model QGIS & Data Mentah
│   ├── 01 Identifikasi Titik.model3
│   ├── titik sebelum identifikasi.geojson
│   ├── slsmentah fixed-2025sm1.geojson   <-- dipindahkan dari root
│   └── titik hasil identifikasi.geojson
│
└── 01-move offside dots/       # Pipeline Perbaikan Vektor & Recovery Titik Gagal
    ├── jupyter.bat
    ├── split_data.py
    ├── 01-pengolahan_titik_muatan.ipynb
    ├── 00 - module/
    ├── 01 - data/
    ├── 03 - final/
    ├── extract_failed.py
    ├── move-failed.py
    ├── failed.geojson
    └── moved_failed.geojson             <-- dipindahkan dari root
```

### C. Analisis Dampak & Modifikasi Teknis Kritis
1. **Pergeseran Anchor Path di `config.py`**:
   `BASE_DIR` saat ini menggunakan `os.path.dirname(os.path.abspath(__file__))`. Jika `config.py` berada di dalam folder `app/`, `BASE_DIR` wajib dinaikkan satu tingkat:
   ```python
   BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   ```
   Hal ini menjamin rujukan `DATABASE_PATH`, `UPLOAD_DIR`, `shape_col.csv`, `dot_col.csv`, dan `.env` tetap mengarah tepat ke direktori root proyek.
2. **Path Folder Template & Static di `app.py`**:
   ```python
   app = Flask(__name__,
               template_folder=os.path.join(config.BASE_DIR, "templates"),
               static_folder=os.path.join(config.BASE_DIR, "static"))
   ```
3. **Penyelarasan Entry Point `run.py`**:
   ```python
   from app.app import create_app
   # atau
   from app import create_app
   ```
4. **Relokasi Residu Berkas GeoJSON**:
   Setelah software eksternal (QGIS/editor) ditutup:
   - Pindahkan `slsmentah fixed-2025sm1.geojson` -> `00-identify dots/`
   - Pindahkan `moved_failed.geojson` -> `01-move offside dots/`

### D. Tahapan Eksekusi Step-by-Step (Menunggu Konfirmasi Lanjut)
- **Step 1**: Buka proteksi berkas GeoJSON di root, lalu pindahkan ke direktori tujuannya.
- **Step 2**: Buat direktori `app/` dan pindahkan 11 modul Python backend ke dalamnya.
- **Step 3**: Refactor path resolving `BASE_DIR` pada `config.py` dan template/static binding pada `app.py`.
- **Step 4**: Refactor import references pada `run.py` dan antar-modul internal `app/`.
- **Step 5**: Verifikasi integritas impor dan launch test server.


