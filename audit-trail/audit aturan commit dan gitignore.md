# AUDIT & KEBIJAKAN: ATURAN COMMIT DAN STRUKTUR .GITIGNORE

- **Lokasi Berkas**: `c:\laragon\www\wilkerstat-checker\audit-trail\audit aturan commit dan gitignore.md`
- **Tanggal Audit**: 2026-11-05
- **Tingkat Keyakinan**: [certain] (Berdasarkan audit langsung berkas `.gitignore` eksisting dan standar version control spasial BPS/Git)

---

## 1. The Uncomfortable Truth (Fakta Kritis & Anomali Eksisting)

[certain] `.gitignore` Anda saat ini memiliki kecacatan fatal:
1. **`audit-trail/` diblokir di baris 70**: Seluruh dokumen audit arsitektur yang kita buat justru diabaikan oleh Git. Jika Anda menjalankan `git commit`, seluruh rekam jejak keputusan teknis ini tidak akan pernah tersimpan di repositori.
2. **Skrip spasial terancam terisolasi**: Folder `00-identify dots/` dan `01-move offside dots/` memuat skrip produksi penting (`bridge_repair.py`, `dissolve_wilkerstat.py`), namun bercampur dengan puluhan megabyte data spasial mentah (`.geojson`). Pendekatan yang benar adalah mengecualikan datanya (`*.geojson`), bukan mematikan pelacakan skripnya.

---

## 2. Matriks Keputusan: Apa yang WAJIB Dicommit vs DILARANG Dicommit

### A. WAJIB DICOMMIT (Source of Truth, Logika, Konfigurasi, & Dokumentasi)

| Kategori | Pola Jalur / Berkas | Alasan Teknis |
| :--- | :--- | :--- |
| **Aplikasi Web Core** | `app/**/*.py` | Kode backend Flask, validasi topologi, routing, dan skema database. |
| **Frontend Web** | `templates/**/*.html`, `static/**/*.js`, `static/**/*.css`, `static/vendor/**/*` | Antarmuka dashboard, library MapLibre lokal, dan visualisasi progres. |
| **Skrip Otomasi Spasial** | `00-identify dots/*.py`, `01-move offside dots/*.py`, `scripts/**/*.py` | Logika transformasi data, jembatan Model 2, dan algoritma dissolve. |
| **Dokumentasi & Audit** | `README.md`, `audit-trail/**/*.md` | Spesifikasi operasional sistem dan rekam jejak audit regulasi. |
| **Dependensi & Template** | `requirements.txt`, `pyproject.toml`, `.env.example` | Standar instalasi lingkungan replikatif tanpa membocorkan kredensial. |
| **Peluncur Server LAN** | `install.bat`, `run.bat` | Skrip instalasi otomatis dan eksekusi satu klik untuk petugas. |
| **Penjaga Folder Kosong** | `data/.gitkeep`, `uploads/.gitkeep` | Memastikan struktur direktori runtime tetap ada saat repo di-clone. |

---

### B. DILARANG DICOMMIT (Wajib Masuk `.gitignore`)

| Kategori | Pola Ekstensi / Direktori | Risiko Bila Tercommit |
| :--- | :--- | :--- |
| **Data Vektor Raksasa** | `*.geojson`, `*.gpkg`, `*.shp`, `*.dbf`, `*.shx`, `*.prj`, `*.cpg` | Menyebabkan *repo bloat* (ratusan MB), melanggar batas 100MB GitHub, membuat `git clone/pull` sangat lambat. |
| **Basis Data Runtime** | `data/*.db`, `data/*.sqlite`, `*.sqlite3` | Konflik merge biner, merusak integritas basis data antar PC koordinator, potensi kebocoran data operasional. |
| **Unggahan Petugas** | `data/uploads/*`, `data/cache/*`, `data/temp/*` | Data dinamis sementara per sesi petugas yang tidak boleh mengotori riwayat kode. |
| **Kredensial & Secrets** | `.env`, `.env.local`, `.env.*.local` | Kebocoran kunci rahasia, token, atau konfigurasi lokal PC. |
| **Python Bytecode** | `__pycache__/`, `*.py[cod]`, `*$py.class` | Sampah kompilasi lokal yang spesifik per arsitektur CPU/versi interpreter. |
| **Virtual Environment** | `venv/`, `.venv/`, `env/`, `ENV/` | Puluhan ribu file pustaka pihak ketiga yang wajib dipasang via `pip install`, bukan via Git. |
| **Sampah Sistem Operasi** | `Thumbs.db`, `desktop.ini`, `.DS_Store` | Berkas metadata eksplorer Windows/macOS yang tidak relevan dengan aplikasi. |
| **Konfigurasi IDE Lokal** | `.vscode/`, `.idea/`, `*.swp` | Preferensi editor individu yang memicu konflik konfigurasi personal. |
| **Log & Debug Dumps** | `*.log`, `*.tmp`, `*.bak` | Berkas log transaksi runtime yang berubah terus menerus setiap detik. |
| **Salinan Repo Asing** | `Pengolahan-Wilkerstat-SE2026-main/`, `artifacts/` | Ekstraksi zip repositori lain atau artefak sementara yang bukan bagian modul inti. |

---

## 3. Rekomendasi Berkas `.gitignore` Baku (Production-Ready)

Berikut isi lengkap `.gitignore` yang telah diperbaiki: mengeluarkan `audit-trail/` dari blacklist dan mengisolasi berkas spasial biner secara ketat:

```gitignore
# =============================================================================
# WILKERSTAT-CHECKER .GITIGNORE (PRODUCTION)
# =============================================================================

# 1. Byte-compiled / Optimized Python files
__pycache__/
*.py[cod]
*$py.class
*.pyo
*.pyd
.Python

# 2. Virtual Environments
venv/
env/
.venv/
ENV/

# 3. Environment Variables & Secrets (JANGAN PERNAH COMMIT)
.env
.env.local
.env.*.local
!.env.example

# 4. Database, Uploads, dan File Runtime
data/*
!data/.gitkeep
uploads/*
!uploads/.gitkeep
*.db
*.sqlite
*.sqlite3
*.log
*.tmp
*.bak

# 5. Data Geospasial & Model QGIS (Gunakan penyimpanan lokal, bukan Git)
*.geojson
*.gpkg
*.shp
*.shx
*.dbf
*.prj
*.cpg
*.zip
*.model3
*.qgs~
*.qgz~

# 6. Gambar Hasil Render Sementara (Kecualikan aset statis web)
*.png
!static/**/*.png
!assets/**/*.png

# 7. Testing & Coverage
.pytest_cache/
.coverage
htmlcov/

# 8. Operating System Files
.DS_Store
Thumbs.db
ehthumbs.db
desktop.ini

# 9. IDE & Code Editor Files
.vscode/
.idea/
*.swp
*.swo

# 10. Packaging & Distribution
dist/
build/
*.egg-info/

# 11. Direktori Eksternal / Non-Modul
Pengolahan-Wilkerstat-SE2026-main/
artifacts/
jupyter.bat
organize.bat
scripts/organize.bat
```

---

## 4. Status Prosedural

Sesuai aturan kerja tahap demi tahap:
1. Dokumen audit ini telah dicatat resmi di `audit-trail/audit aturan commit dan gitignore.md`.
2. Menunggu konfirmasi Anda untuk memperbarui berkas `.gitignore` sesuai rekomendasi di atas.

