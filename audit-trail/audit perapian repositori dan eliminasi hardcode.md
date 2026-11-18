# AUDIT & RENCANA PERAPIAN REPOSITORI (DECLUTTERING & DE-HARDCODING)

- **Lokasi Berkas**: `c:\laragon\www\wilkerstat-checker\audit-trail\audit perapian repositori dan eliminasi hardcode.md`
- **Tanggal Audit**: 2026-11-05
- **Tingkat Keyakinan**: [certain] (Berdasarkan audit menyeluruh terhadap struktur berkas, skrip Python, dan alur kerja Git)

---

## 1. The Uncomfortable Truth (Fakta Kritis & Hasil Deep Scan)

[certain] Repositori Anda menumpuk residu dari 3 fase pengembangan yang berbeda:
1. **Residu Pipeline Lama di `01-move offside dots/`**:
   - `failed.geojson` (~10MB) dan `moved_failed.geojson` (~13MB) adalah artefak temporer warisan pipeline 6-tahap yang kini telah sepenuhnya digantikan oleh `bridge_repair.py`.
   - Folder `01 - data/`, `03 - final/`, serta notebook `01-pengolahan_titik_muatan.ipynb` menjadi tumpukan sampah yang membingungkan alur kerja utama.
2. **Ketiadaan Konfirmasi pada Skrip Destruktif**:
   - `scripts/clear_dots.py` sebelumnya langsung mengeksekusi `DELETE FROM dot` tanpa konfirmasi interaktif sama sekali.
3. **Residu Batch di Root**:
   - Berkas `organize.bat`, `scripts/organize.bat`, dan `jupyter.bat` adalah sisa skrip ad-hoc lokal yang tidak layak dipush ke repositori publik.
4. **Residu Berkas Berjudul Kasar**:
   - `audit-trail/audit gagal geser titik bangsat.md` masih tersisa di pohon Git dan wajib dihapus via `git rm`.

---

## 2. Status Eliminasi Hardcode (100% Selesai)

| Modul | Status Sebelum | Status Sesudah (Final) |
| :--- | :--- | :--- |
| `00-identify dots/dissolve_wilkerstat.py` | Mengunci kode `6309`, nama file Tabalong, dan EPSG 32650. | **100% Dinamis**: CLI interaktif, auto-deteksi kode wilayah dari data, auto-deteksi zona UTM se-Indonesia (EPSG 32646 s.d. 32754), dan nama output dinamis. |
| `01-move offside dots/bridge_repair.py` | Mengunci path `titik hasil identifikasi.geojson` dan `slsmentah fixed-2025sm1.geojson`. | **100% Dinamis**: CLI interaktif + flags `--dots`, `--poly`, `--out`, `--buffer`, auto-deteksi file geojson terdekat, dan toleransi buffer yang dapat diatur. |
| `scripts/clear_dots.py` | Langsung menghapus seluruh data tabel titik di database. | **Dilengkapi Safety Guard**: Konfirmasi interaktif eksplisit `(y/N)` sebelum mengeksekusi penghapusan database. |
| `scripts/split.py` | Default splitting `nmkec`. | **Mendukung CLI Argument & Prompt Interaktif**: Mendukung path relatif/absolut. |

---

## 3. Rencana Perapian Repositori (Matriks Tindakan)

### A. Tindakan Pembersihan Berkas Residu & Sampah

| Berkas / Direktori | Tindakan Rekomendasi | Justifikasi Teknis |
| :--- | :--- | :--- |
| `audit-trail/audit gagal geser titik bangsat.md` | **Hapus via Git** (`git rm`) | Berkas telah digantikan oleh `audit akar masalah titik terseret utara.md` dan judul kasarnya dilarang masuk repositori. |
| `01-move offside dots/failed.geojson` | **Hapus / Ignore** | Berkas intermediat lama (~10MB) yang tidak lagi digunakan oleh `bridge_repair.py`. |
| `01-move offside dots/moved_failed.geojson` | **Hapus / Ignore** | Berkas luaran lama (~13MB) yang digantikan oleh `titik_siap_model2.geojson`. |
| `01-move offside dots/log.txt` | **Hapus / Masuk .gitignore** | Log runtime lokal. |
| `organize.bat` & `scripts/organize.bat` | **Hapus** | Skrip sekali-pakai migrasi folder yang fungsinya sudah tuntas. |
| `01-move offside dots/module/` & `run.py` | **Pindahkan ke `01-move offside dots/legacy/`** | Memisahkan mesin modern (`bridge_repair.py`) dari modul warisan 6-tahap agar root folder 01 bersih. |

---

### B. Tindakan Integrasi Logo & Favicon Web

| Komponen | Status Saat Ini | Tindakan Koreksi |
| :--- | :--- | :--- |
| `static/logo.png` | Tidak ada | Salin `assets/logo.png` ke `static/logo.png` agar dapat diakses Flask. |
| `static/favicon.ico` | Tidak ada (404) | Konversi atau salin `assets/favicon.ico` (atau `logo.png`) ke `static/favicon.ico`. |
| `templates/base.html` (Navbar) | Teks emoji `🗺️` | Ubah menjadi `<img src="{{ url_for('static', filename='logo.png') }}">` dengan CSS rapi. |
| `templates/base.html` (Favicon) | 404 Not Found | Hubungkan link favicon ke `static/favicon.ico` dan `static/logo.png`. |

---

## 4. Struktur Bersih Target (Production Clean Tree)

```text
wilkerstat-checker/
│
├── [ENTRY POINT & WEB ENGINE]
│   ├── run.py / run.bat / install.bat / download_vendor.bat
│   ├── shape_col.csv / dot_col.csv / requirements.txt
│   ├── .env.example / .gitignore / README.md
│   ├── app/                       # Logika backend Flask terisolasi
│   ├── static/                    # CSS, JS, Vendor, logo.png, favicon.ico
│   ├── templates/                 # HTML templates
│   ├── data/                      # Database operasional SQLite
│   └── assets/                    # Master logo & identitas grafis
│
├── 00-identify dots/              # [MODUL TAHAP 0: MODEL 1 & PELEBURAN]
│   ├── README.md
│   ├── 01 Identifikasi Titik.model3
│   └── dissolve_wilkerstat.py     # 100% Dinamis se-Indonesia
│
├── 01-move offside dots/          # [MODUL TAHAP 1: REPOSISI TITIK]
│   ├── README.md
│   ├── bridge_repair.py           # Mesin utama 100% dinamis (CLI + Prompt)
│   └── legacy/                    # Modul warisan 6-tahap (diarsipkan)
│
├── audit-trail/                   # [REKAM JEJAK ARSITEKTUR / ADR]
│   ├── README.md
│   ├── audit aturan commit dan gitignore.md
│   ├── audit peleburan sls ke desa dan kecamatan.md
│   ├── audit akar masalah titik terseret utara.md
│   ├── audit perapian repositori dan eliminasi hardcode.md
│   ├── audit-restrukturisasi-folder.md
│   └── audit-fitur-baru.md
│
└── scripts/                       # [UTILITAS PEMELIHARAAN]
    ├── README.md
    ├── clear_dots.py              # Dilengkapi konfirmasi interaktif
    └── split.py                   # Mendukung CLI argument & prompt
```

