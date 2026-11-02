# Paket Modul Backend Aplikasi: `app/`

Direktori ini memuat seluruh kode sumber inti (*backend logic*) aplikasi web monitoring LAN WilkerStat Checker SE2026.

---

## 1. Inventaris Modul & Tanggung Jawab

| Modul | Tanggung Jawab Arsitektural |
| :--- | :--- |
| `__init__.py` | Package initializer & ekspos fungsi factory `create_app()`. |
| `app.py` | Controller utama Flask: registrasi rute halaman (`/`, `/upload`, `/issues`, `/history`, `/map`), endpoint REST API, penanganan unggahan berkas, dan Sentinel guard lisensi. |
| `config.py` | Manajemen konfigurasi aplikasi; membaca variabel `.env`, menentukan port, batas unggahan (`MAX_CONTENT_LENGTH`), dan mendefinisikan jangkar direktori root `BASE_DIR`. |
| `database.py` | Abstraksi akses basis data SQLite dengan mode WAL (*Write-Ahead Logging*). Mengelola tabel `shape`, `dot`, `issue`, `upload_log`, dan palet warna petugas. |
| `worker.py` | Antrean tugas latar belakang (*in-memory background task queue*) berbasis thread terisolasi untuk memproses validasi file geospasial berukuran besar tanpa memblokir thread HTTP. |
| `spatial.py` | Mesin analisis topologi dan kalkulasi geometri Shapely: deteksi celah (*gap*), tumpang tindih (*overlap*), multipart, kalkulasi bounding box, dan titik berat (*centroid*). |
| `validate_shape.py` | Engine validasi berkas poligon SLS (GeoJSON): evaluasi struktur atribut wajib acuan `shape_col.csv`, normalisasi koordinat WGS84, dan komputasi topologi antar-petugas. |
| `validate_dot.py` | Engine validasi titik bangunan (*geotagging*): evaluasi kesesuaian atribut acuan `dot_col.csv`, uji spasial posisi fisik terhadap poligon SLS (`INSIDE` vs `OFFSIDE`), dan evaluasi status perbaikan (`flag_repair`, `flag_position`). |
| `colours.py` | Generator palet warna dinamis berbasis algoritma *golden-angle* untuk membedakan visualisasi poligon/titik tiap petugas secara konsisten dan kontras tinggi. |
| `col_loader.py` | Parser berkas spesifikasi kolom acuan dari `shape_col.csv` dan `dot_col.csv`. |
| `tray.py` | Integrasi antarmuka Windows System Tray via pustaka `pystray`: menyembunyikan konsol terminal ke area notifikasi taskbar, memotong pesan tombol close, dan menu klik kanan server. |
| `license_manager.py` | Modul pengamanan lisensi luring terikat perangkat (*hardware-bound offline licensing*); memvalidasi token berdasarkan signature SHA-256 dan Hardware ID (UUID/MAC). |

---

## 2. Pola Arsitektur

- **Clean Architecture Isolation**: Seluruh logika server diisolasi di dalam `app/`, sehingga direktori root proyek tetap bersih dan hanya memuat entry point (`run.py`, `run.bat`, `install.bat`) serta konfigurasi.
- **Root Resolving Guarantee**: Semua pembacaan jalur statis (`static/`), template (`templates/`), database (`data/`), dan file skema acuan (`shape_col.csv`, `dot_col.csv`) selalu diturunkan dari `config.BASE_DIR` yang stabil.

