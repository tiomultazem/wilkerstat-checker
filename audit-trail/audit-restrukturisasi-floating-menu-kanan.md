# Audit Trail: Penataan Ulang Seluruh Floating Menu ke Sisi Kanan Antarmuka GIS

**Tanggal**: 5 November 2026  
**Permintaan Pengguna**: *"semua floating menu dirapikan ke kanan aja. tulis di audit baru dan langusng eksekusi. now"*  
**Berkas Terkait**:  
- [`templates/home.html`](file:///c:/laragon/www/wilkerstat-checker/templates/home.html)  
- [`static/style.css`](file:///c:/laragon/www/wilkerstat-checker/static/style.css)  
- [`static/home.js`](file:///c:/laragon/www/wilkerstat-checker/static/home.js)  

---

## 1. Analisis Tata Letak Sebelumnya (Tersebar)

Sebelum restrukturisasi, elemen-elemen mengambang (*floating elements*) tersebar di berbagai penjuru kanvas peta:
1. **Sidebar Utama (`.gis-sidebar`)**: Melayang di pojok kiri atas (`top: 14px; left: 14px;`).
2. **Tab Switcher Layer (`#mainTabs`)**: Melayang terpisah di pojok kanan atas (`top: 10px; right: 56px;`).
3. **Kontrol Navigasi MapLibre (Zoom +/- & Kompas)**: Terletak di pojok kanan atas (`top-right`), berisiko tertabrak pill tab.
4. **Tombol Center ke Data (`#btnFitData`)**: Melayang terpencil di pojok kanan bawah (`bottom: 46px; right: 10px;`).

**Kelemahan UX**: Pengguna harus menggerakkan kursor bolak-balik antara pojok kiri (progres & filter) dan pojok kanan (ganti tab poligon/titik & center peta). Kanvas peta juga terpotong di kedua sisi.

---

## 2. Arsitektur Tata Letak Baru (Unifikasi Sisi Kanan)

Seluruh floating menu dipindahkan dan disatukan secara ergonomis di **sisi kanan** layar:

1. **Sidebar GIS Terpadu di Sisi Kanan**:
   - Posisi: `top: 14px; right: 14px; left: auto; width: 330px;`
   - Menyatukan panel monitoring progres, tab switching, aksi peta, dan filter dalam satu panel melayang elegan.
2. **Integrasi Tab Switcher (`#mainTabs`) ke Sidebar**:
   - Tab pill *Poligon | Titik* disematkan langsung di dalam `.sidebar-header` tepat di bawah judul.
   - Tidak ada lagi elemen pill yang melayang terpisah tanpa konteks di atas peta.
3. **Aksi Center ke Data (`#btnFitData`) Terpadu**:
   - Tombol ikon ⌖ (*fit data*) disematkan di baris header sidebar serta disiapkan tombol aksi melayang di sisi kiri sidebar (`right: 354px; top: 14px;`).
4. **Relokasi Kontrol Navigasi MapLibre ke `top-left`**:
   - Kontrol zoom dan kompas MapLibre dipindahkan ke pojok kiri atas (`'top-left'`) agar tidak bertabrakan dengan sidebar kanan dan memberikan ruang visual peta yang luas.

---

## 3. Status Eksekusi

- [x] **Langkah 1**: Dokumentasi audit desain tata letak baru pada berkas ini.
- [x] **Langkah 2**: Modifikasi struktur DOM di [`templates/home.html`](file:///c:/laragon/www/wilkerstat-checker/templates/home.html) (sidebar dipindah ke kanan, pill switcher dan tombol center data disatukan ke header sidebar).
- [x] **Langkah 3**: Modifikasi aturan CSS di [`static/style.css`](file:///c:/laragon/www/wilkerstat-checker/static/style.css) (`.gis-sidebar` di `right: 14px;`, styling header terpadu dan tab pill).
- [x] **Langkah 4**: Sesuaikan posisi `NavigationControl` MapLibre di [`static/home.js`](file:///c:/laragon/www/wilkerstat-checker/static/home.js) ke `top-left`.

---

## 4. Penyediaan Tombol Antarmuka untuk Seluruh Endpoint Pemeliharaan

### 4.1. Masalah Akses Manual
Sebelumnya, endpoint pemeliharaan dan rekalkulasi latar belakang hanya dapat dipicu secara manual via URL browser atau perintah cURL:
- `GET /api/admin/recheck-topology`: Rekalkulasi ulang topologi (overlap & gap) konsisten standar QGIS.
- `POST /api/admin/recheck-dots`: Rekalkulasi ulang status spasial titik (INSIDE / OFFSIDE) terhadap poligon terbaru.

Pola akses manual ini membebani pengguna dan rentan kesalahan input port/URL.

### 4.2. Solusi Tombol Aksi Langsung pada Antarmuka
1. **Penambahan Panel Utilitas pada Sidebar**:
   Pada [`templates/home.html`](file:///c:/laragon/www/wilkerstat-checker/templates/home.html), di bawah bagian filter wilayah, ditambahkan accordion *🛠️ Pemeliharaan & Sinkronisasi*:
   - Tombol **"🔄 Recheck Topologi (QGIS)"** (`#btnRecheckTopology`): Mengeksekusi `/api/admin/recheck-topology`, menampilkan feedback status, dan me-refresh visualisasi serta statistik poligon.
   - Tombol **"📍 Recheck Posisi Titik"** (`#btnRecheckDots`): Mengeksekusi `/api/admin/recheck-dots`, menampilkan feedback status, dan me-refresh titik pada peta.
2. **Fleksibilitas HTTP Method di Backend**:
   Di [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py), kedua endpoint dipastikan mendukung `methods=["GET", "POST"]`.
3. **Penanganan Interaksi & Toast Notifikasi**:
   Di [`static/home.js`](file:///c:/laragon/www/wilkerstat-checker/static/home.js), tombol otomatis terkunci saat kalkulasi berjalan (*loading state*) dan memunculkan toast konfirmasi saat proses selesai.

- [x] **Status Implementasi Tombol**: Accordion pemeliharaan, kedua tombol recheck, endpoint HTTP method, dan listener JS telah selesai diintegrasikan dan aktif.

