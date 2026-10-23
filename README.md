# WilkerStat Checker — SE2026

Aplikasi monitoring progres geospasial berbasis Local Area Network (LAN) untuk validasi poligon batas SLS/Sub-SLS dan titik muatan bangunan (*geotagging*) per petugas dalam kegiatan Sensus Ekonomi 2026 (SE2026) BPS.

Aplikasi ini dijalankan secara mandiri pada PC server/koordinator dan dapat diakses secara *real-time* oleh seluruh petugas melalui peramban web (*browser*).

---

## Fitur Utama

- 🗺️ **Validasi Poligon SLS/Sub-SLS (GeoJSON)**:
  - Deteksi geometri multipart (poligon terpecah).
  - Deteksi celah (*gap*) antar batas SLS dengan toleransi lebar dan luas.
  - Deteksi tumpang tindih (*overlap*) antar poligon dengan pembagian atribusi proporsional per petugas.
  - Validasi kelengkapan atribut wajib (*not-null*) dan konsistensi hierarki kode wilayah (`shape_col.csv`).
- 📍 **Validasi Titik Bangunan (GeoJSON & GPKG)**:
  - Uji posisi spasial titik fisik terhadap poligon induk (`INSIDE` vs `OFFSIDE`).
  - Deteksi pergeseran koordinat perbaikan (`flag_position = 1` jika jarak geser ≥ 0.5 meter).
  - Evaluasi otomatis status kelayakan perbaikan titik (`flag_repair`).
  - Validasi kelengkapan atribut muatan (`dot_col.csv`).
- 📊 **Dashboard Progres Petugas**:
  - Pemantauan progres unggah per petugas dengan visualisasi palet warna unik (*golden-angle*).
  - Dropdown kartu petugas kontekstual: menampilkan daftar SLS terunggah atau rincian masalah perbaikan.
  - **Pencarian Cepat (*Containment Search*)**: Cari SLS atau nama desa dengan filter pencarian instan (contoh: `"jaro rt 002"`).
- 🌍 **Peta Interaktif MapLibre GL**:
  - Peta lokal berkecepatan tinggi tanpa beban internet setelah pemasangan awal.
  - **Fokus SLS Berkedip**: Sorotan batas poligon berkedip warna oranye (*amber pulse*) selama 3 detik saat item dipilih dari daftar tanpa pinpoint pengganggu.
  - **Label SLS Otomatis**: Label nama desa dan SLS otomatis tampil pada rentang zoom 11–16 dengan *GPU collision detection*.
- 🛡️ **Proteksi Data Master (`DEV=false`)**:
  - Mencegah penimpaan master wilayah atau reset data yang tidak disengaja oleh petugas saat pengumpulan data lapangan.
- 💾 **Ekspor Rekapitulasi**:
  - Unduh rekapitulasi capaian, daftar masalah spasial, dan titik muatan dalam format XLSX, CSV, GeoJSON, dan GPKG.

---

## Struktur Direktori Repositori

```text
wilkerstat-checker/
│
├── [ENTRY POINT & KONFIGURASI ROOT]
│   ├── run.py                     # Entry point server Waitress & System Tray
│   ├── run.bat                    # Peluncur satu klik server LAN
│   ├── install.bat                # Skrip instalasi otomatis virtualenv & dependensi
│   ├── shape_col.csv              # Spesifikasi kolom acuan poligon BPS
│   ├── dot_col.csv                # Spesifikasi kolom acuan titik muatan BPS
│   ├── requirements.txt           # Daftar pustaka dependensi Python
│   ├── .env.example               # Template variabel konfigurasi lingkungan
│   ├── .gitignore                 # Aturan version control Git produksi
│   ├── README.md                  # Dokumentasi umum proyek
│   ├── static/                    # Aset frontend (CSS, JS, Vendor MapLibre offline)
│   ├── templates/                 # Antarmuka Jinja2 (HTML)
│   ├── data/                      # Basis data SQLite operasional (WAL) & arsip
│   └── assets/                    # Aset gambar & identitas visual (logo.png)
│
├── app/                           # [PAKET BACKEND CORE]
│   ├── README.md                  # Dokumentasi arsitektur modul backend
│   ├── app.py                     # Controller Flask & REST API endpoints
│   ├── config.py                  # Parsing environment & root path resolving
│   ├── database.py                # Isolasi transaksi SQLite & skema tabel
│   ├── worker.py                  # In-memory background task queue
│   ├── spatial.py                 # Algoritma analisis topologi Shapely
│   ├── validate_shape.py          # Mesin validasi & ingest poligon SLS
│   ├── validate_dot.py            # Mesin validasi & ingest titik muatan
│   ├── colours.py                 # Generator palet warna golden-angle
│   ├── col_loader.py              # Parser CSV kolom acuan
│   ├── tray.py                    # Integrasi Windows System Tray (pystray)
│   └── license_manager.py         # Sentinel pengamanan lisensi terikat HWID
│
├── 00-identify dots/              # [MODUL EVALUASI SPASIAL & PELEBURAN]
│   ├── README.md                  # Panduan penggunaan Model 1 & skrip dissolve
│   ├── 01 Identifikasi Titik.model3# Model alur kerja visual QGIS (Model 1)
│   ├── dissolve_wilkerstat.py     # Skrip peleburan SLS ke Desa & Kecamatan 2026
│   └── (data masukan/luaran: .geojson diabaikan oleh Git)
│
├── 01-move offside dots/          # [MODUL REPOSISI TITIK OFFSIDE]
│   ├── README.md                  # Dokumentasi bridge_repair.py & legacy pipeline
│   ├── bridge_repair.py           # Mesin reposisi titik offside STRtree tunggal
│   ├── run.py                     # Runner interaktif pipeline legacy 6-tahap
│   └── module/                    # Submodul legacy fallback
│
├── audit-trail/                   # [REKAM JEJAK ARSITEKTUR / ADR]
│   ├── README.md                  # Indeks dokumen Architectural Decision Records
│   ├── audit aturan commit dan gitignore.md
│   ├── audit peleburan sls ke desa dan kecamatan.md
│   ├── audit akar masalah titik terseret utara.md
│   ├── audit perapian repositori dan eliminasi hardcode.md
│   ├── audit-restrukturisasi-folder.md
│   └── audit-fitur-baru.md
│
└── scripts/                       # [SKRIP PEMELIHARAAN CLI]
    ├── README.md                  # Panduan skrip utilitas mandiri
    ├── clear_dots.py              # Utilitas reset data titik di basis data
    └── split.py                   # Utilitas pemotong GeoJSON per kecamatan
```

---

## Persyaratan Sistem

- **Sistem Operasi**: Windows 10 / 11 / Windows Server (64-bit).
- **Python**: Versi 3.10 hingga 3.12 (Skrip instalasi otomatis memasang **Python 3.12.7 64-bit** jika Python belum tersedia di PC).
- **Jaringan**: Terhubung ke jaringan kabel (LAN) atau Wi-Fi kantor yang sama.
- **Koneksi Internet**: Hanya diperlukan saat instalasi awal dan unduh dependensi.

---

## Panduan Instalasi Cepat

### 1. Jalankan Skrip Instalasi
Buka folder aplikasi, lalu klik dua kali:

```bat
install.bat
```

Skrip ini akan secara otomatis:
1. Mendeteksi Python di sistem (memasang Python 3.12.7 secara otomatis jika belum ada).
2. Menyiapkan ruang kerja *virtual environment* (`venv`).
3. Memasang seluruh pustaka yang dibutuhkan aplikasi via pip (`requirements.txt`).
4. Menyiapkan berkas konfigurasi `.env` dan menyinkronkan aset logo statis.

*(Catatan: Pustaka peta MapLibre GL sudah disertakan secara luring di `static/vendor/` sehingga tidak memerlukan unduhan eksternal).*

### 2. Konfigurasi Lingkungan (`.env`)
Salin atau sesuaikan berkas template konfigurasi (otomatis dibuat oleh `install.bat`):

```bat
copy .env.example .env
```

---

## Menjalankan Aplikasi

Jalankan launcher aplikasi:

```bat
run.bat
```

Saat `run.bat` dijalankan:
1. Server otomatis berjalan di latar belakang pada port `11750`.
2. Halaman aplikasi otomatis terbuka di peramban web default (`http://localhost:11750`).
3. Jendela konsol otomatis terminimalkan ke **System Tray** (ikon bola dunia di samping jam taskbar).
4. Untuk menutup aplikasi, klik kanan pada ikon bola dunia di taskbar tray, lalu pilih **Keluar**.

---

## Aktivasi Penggunaan Pertama Kali

Jika aplikasi menampilkan halaman aktivasi pada pembukaan pertama:
1. Masukkan **Kode Satker** dan **Token Lisensi** yang diperoleh dari koordinator/admin.
2. Klik **Aktivasi Sekarang**.
3. Aplikasi akan langsung aktif dan siap digunakan untuk operasional.

---

## Akses Bersama di Jaringan Kantor (LAN)

Agar komputer petugas lain dapat mengakses server pemantauan:

### 1. Buka Port Firewall (Hanya di PC Server Koordinator)
Buka Command Prompt sebagai **Administrator**, lalu jalankan:

```cmd
netsh advfirewall firewall add rule name="WilkerStat Checker" dir=in action=allow protocol=TCP localport=11750
```

### 2. Cek Alamat IP PC Server
Buka Command Prompt, ketik:
```cmd
ipconfig
```
Catat alamat IPv4 (contoh: `192.168.1.100`).

### 3. Akses dari Perangkat Petugas
Petugas lain di kantor cukup membuka browser dan memasukkan alamat:
```
http://192.168.1.100:11750
```

---

## Prosedur Pengunggahan Data

### Tahap 1: Setup Master Wilayah (Admin / Koordinator)
1. Buka berkas `.env`, ubah `DEV=true`, lalu jalankan ulang `run.bat`.
2. Buka menu **Upload**, pilih **Master Poligon**, lalu masukkan berkas GeoJSON master SLS se-kabupaten.
3. Setelah selesai, kembalikan nilai di `.env` menjadi `DEV=false` dan mulai ulang aplikasi untuk mengunci data acuan.

### Tahap 2: Pengumpulan Data Lapangan (Petugas)
1. Petugas membuka menu **Upload**.
2. Unggah berkas **Shape (GeoJSON)** poligon SLS hasil perbaikan lapangan.
3. Unggah berkas **Titik Bangunan (GeoJSON / GPKG)** hasil geotagging.
4. Sistem otomatis memvalidasi kualitas data secara instan tanpa menduplikasi data yang sudah pernah diunggah.

---

## Pemecahan Masalah (Troubleshooting)

- **Aplikasi Tidak Bisa Dibuka dari Komputer Petugas**:
  Pastikan firewall port `11750` telah diizinkan pada PC server dan kedua komputer terhubung pada Wi-Fi/LAN kantor yang sama.
- **Tampilan Peta Dasar Kosong**:
  Pastikan komputer terhubung ke internet saat pertama kali membuka halaman peta agar ubin OpenStreetMap dapat di-cache secara otomatis oleh peramban. Pustaka MapLibre GL sendiri sudah tersedia secara luring di `static/vendor/`.
- **Menghentikan / Memulai Ulang Aplikasi**:
  Klik kanan ikon bola dunia di pojok kanan bawah taskbar (System Tray) -> pilih **Keluar**, lalu jalankan kembali `run.bat`.

---

## Atribusi & Kredit

Modul pemrosesan spasial pra-analisis pada proyek ini (`00-identify dots/` dan `01-move offside dots/`) mengacu dan dikembangkan dari repositori resmi:
- **[PMSS-BPS/Pengolahan-Wilkerstat-SE2026](https://github.com/PMSS-BPS/Pengolahan-Wilkerstat-SE2026)** — Direktorat Pengembangan Metodologi Sensus dan Survei (PMSS), Badan Pusat Statistik Republik Indonesia.
- WilkerStat Checker SE2026 dibangun dan dioptimasi oleh Gilang Wahyu Prasetyo &copy; BPS Kabupaten Tabalong.
