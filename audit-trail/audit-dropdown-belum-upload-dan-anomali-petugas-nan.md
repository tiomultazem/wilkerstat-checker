# AUDIT: Anomali Dropdown Belum Diupload & Petugas "nan"

**Tanggal Audit**: 2026-11-04  
**Auditor**: Antigravity  
**Status**: CONFIRMED — Root cause teridentifikasi 100% dari kode sumber (Frontend & Backend)  
**Confidence**: [certain] — Bukti baris kode konkret di `static/home.js`, `app/app.py`, dan `app/validate_shape.py`

---

## FAKTA PAHIT (Baca Ini Dulu)

1. **"(Belum Diupload)" memang sengaja dimatikan dropdown-nya oleh kode terdahulu.**  
   Developer sebelumnya secara eksplisit menulis pengecualian `!isUnassigned` di frontend untuk membuang panah dropdown, menghapus container dropdown, dan membatalkan click listener. Backend-nya pun sama sekali belum menyediakan endpoint data untuk poligon yang belum diunggah.
2. **Munculnya petugas "nan" BUKAN murni karena kelalaian Anda mengosongkan data.**  
   Meskipun Anda merasa sudah mengisi semua sel, pustaka Pandas secara agresif mengonversi sel kosong, spasi, atau teks seperti `"NA"` menjadi objek `float('nan')`. Lalu backend secara serampangan memanggil `str(row.get('petugas', ''))` yang secara harfiah mengubah objek tersebut menjadi teks string **`"nan"`**, lalu disimpan ke database sebagai nama orang.

---

## BAGIAN 1: Mengapa "(Belum Diupload)" Tidak Berupa Dropdown?

### 1.1. Bukti Forensik Frontend (`static/home.js`)
Di dalam fungsi `renderPolyBars()`:

```javascript
// Baris 104–114: Bar ditandai secara khusus dengan isUnassigned = true
const unassigned = unassigned_shape_count || 0;
if (mode === 'progress' && unassigned > 0) {
    rows.push({
        petugas: '(Belum Diupload)',
        val: unassigned,
        target: realTarget,
        upload: unassigned,
        isUnassigned: true // <--- PENANDA
    });
}

// Baris 157–174: Pengecualian eksplisit untuk mematikan interaktivitas
row.innerHTML = `
    <div class="bar-header">
        <span class="bar-name"><span style="${dotStyle}"></span>${escHtml(petugas)}</span>
        <span class="bar-label">${escHtml(labelText)}${!isUnassigned ? '<span class="bar-toggle-icon">▾</span>' : ''}</span>
    </div>
    <div class="bar-track">
        <div class="bar-fill" style="width:${pctVal}%;background:${barColour}"></div>
    </div>
    ${!isUnassigned ? '<div class="petugas-error-dropdown"></div>' : ''}
`;
if (!isUnassigned) {
    row.addEventListener('click', () => {
        togglePetugasCard(row, petugas, 'shape', mode, isGrey);
    });
}
```

**Temuan Lapangan**:
- Tanda panah `▾` dihilangkan jika `isUnassigned == true`.
- Elemen penampung `<div class="petugas-error-dropdown">` **tidak di-render**.
- Event listener `click` **tidak dipasang**. Klik pengguna diabaikan sepenuhnya.

### 1.2. Ketiadaan Dukungan Backend (`app/app.py`)
Bila pembatasan frontend di atas dibuka begitu saja, sistem akan memanggil:
`/api/petugas/(Belum%20Diupload)/errors?category=shape&mode=progress`

Di backend baris 355–365:
```python
count_q = f"SELECT COUNT(*) as c FROM shape WHERE LOWER(petugas) = LOWER(?){where_extra}"
# Parameter: ['(belum diupload)']
```
Sistem mencari di tabel `shape` (tabel SLS yang SUDAH diupload). Karena "(Belum Diupload)" bukan nama petugas dan tidak ada poligon di tabel `shape` dengan nama itu, query mengembalikan **0 baris**.

### 1.3. Solusi Eksekusi yang Dibutuhkan
1. **Di `app/app.py` (`api_petugas_errors`)**:  
   Tambahkan percabangan khusus jika `petugas.lower() in ('(belum diupload)', 'belum diupload', 'unassigned')`:
   - Query target dari `master_shape m` yang **TIDAK ADA** di `shape s`:
     ```sql
     SELECT m.idsubsls, m.petugas, m.geom_wkb, m.extra
     FROM master_shape m
     WHERE m.idsubsls NOT IN (SELECT idsubsls FROM shape WHERE geom_wkb IS NOT NULL)
     ```
2. **Di `static/home.js`**:  
   Hapus filter `!isUnassigned` pada baris 162, 167, dan 169 sehingga baris `(Belum Diupload)` memiliki panah dropdown, kontainer dropdown, dan listener klik yang memanggil daftar SLS target yang belum disetor.

---

## BAGIAN 2: Mengapa Bisa Muncul Petugas Bernama "nan"?

### 2.1. Mekanisme Type Coercion Pandas Menjadi Teks Harfiah
Di Python/Pandas:
- Saat membaca Excel/CSV/GeoJSON, sel yang kosong, berisi spasi, atau berisi singkatan standar seperti `"NA"`, `"N/A"`, atau `"null"` otomatis diparsing menjadi nilai floating-point khusus: `float('nan')` (`np.nan`).
- Bila objek `float('nan')` dipaksa menjadi string menggunakan `str()`, hasilnya adalah string **`"nan"`** (bukan string kosong `""`).

### 2.2. Bukti Celah Kode di Backend

#### A. Celah di Unggah Poligon (`app/validate_shape.py:416`)
```python
for idx, row in gdf.iterrows():
    idsub = str(row["idsubsls"])
    petugas = str(row.get("petugas", ""))  # <--- CELAH FATAL
```
Jika sel `petugas` kosong atau NaN:
- `row.get("petugas", "")` mengembalikan `np.nan` (karena kolom "petugas" ada di DataFrame).
- `str(np.nan)` menghasilkan teks string `"nan"`.
- Nilai `"nan"` ini disimpan ke kolom `shape.petugas` di SQLite!

#### B. Celah di Unggah Master Poligon (`app/app.py:1214` & `1236`)
```python
# Baris 1211-1214
idsub = str(row["idsubsls"]).strip()
if not idsub or idsub.lower() in ("nan", "none"):
    continue

# Perhatikan: idsubsls dijaga ketat dari 'nan', tetapi petugas TIDAK DIJAGA:
petugas = str(row.get("petugas", "")).strip() if "petugas" in row.index else ""

# Baris 1236:
petugases = set(str(row.get("petugas", "")).strip() for _, row in df.iterrows() if "petugas" in row.index)
for p in petugases:
    if p:
        get_or_assign_colour(conn, "petugas", p)
```
- Variabel `idsubsls` dijaga dengan `if idsub.lower() in ("nan", "none")`, namun `petugas` sama sekali tidak memiliki sanitasi tersebut!
- String `"nan"` lolos, dimasukkan ke tabel `master_shape.petugas`, dan didaftarkan ke `colour_map` sebagai nama petugas resmi.

#### C. Agregasi Statistik yang Buta (`app/validate_shape.py:600`)
```sql
SELECT petugas, COUNT(*) as c FROM shape WHERE petugas IS NOT NULL AND petugas != '' GROUP BY petugas
```
Karena nilai `"nan"` bukan NULL dan bukan string kosong (panjangnya 3 karakter), SQLite mengelompokkannya sebagai petugas bernama **"nan"** dengan beban tugas tertentu.

### 2.3. Mengapa Terjadi Padahal Anda Yakin Sudah Mengisi Kosongan?
1. **Data Tertinggal di Database**: Jika Anda pernah mengunggah master atau shape sebelum perbaikan kosongan dilakukan, data `"nan"` tersebut masih bersarang di tabel SQLite (`master_shape`, `shape`, `petugas_stats`, dan `colour_map`).
2. **Parsing Pandas pada Singkatan "NA"**: Jika ada petugas bernama "N.A." atau sel diisi "NA" (maksudnya: Not Available), Pandas secara baku menganggapnya sebagai missing value dan mengubahnya menjadi `float('nan')` -> lalu diubah backend menjadi `"nan"`.
3. **Leading/Trailing Whitespace**: Sel yang hanya berisi satu karakter spasi (`" "`) sering kali dianggap NaN oleh pembaca format tabular.

---

## BAGIAN 3: Rencana Solusi Bertahap (Blueprint Eksekusi)

### Langkah 1: Tambahkan Handler Backend untuk SLS Belum Diupload
Di [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py) fungsi `api_petugas_errors`:
- Jika `petugas.strip().lower() in ("(belum diupload)", "belum diupload")`:
  Ambil daftar dari `master_shape` yang `idsubsls`-nya belum ada di `shape`.
  Sajikan dengan format JSON yang sama agar peta dan antarmuka dapat melakukan zoom/highlight.

### Langkah 2: Aktifkan Dropdown di Antarmuka
Di [`static/home.js`](file:///c:/laragon/www/wilkerstat-checker/static/home.js):
- Buang pengecualian `!isUnassigned` pada baris pembuatan bar progress, sehingga bar "(Belum Diupload)" dapat diklik dan menampilkan daftar SLS yang belum diselesaikan.

### Langkah 3: Sanitasi Input Nilai Petugas (Anti-"nan")
Di [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py) dan [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py):
- Buat fungsi pembantu `_clean_petugas(val)`:
  ```python
  def clean_petugas(val) -> str:
      if val is None:
          return "(tanpa petugas)"
      if isinstance(val, float) and math.isnan(val):
          return "(tanpa petugas)"
      s = str(val).strip()
      if not s or s.lower() in ("nan", "none", "null", "undefined"):
          return "(tanpa petugas)"
      return s
  ```
- Terapkan saat ingest `shape` maupun `master_shape`.

### Langkah 4: Pembersihan Data Eksisting di SQLite
Jalankan query sanitasi satu kali untuk membersihkan data sampah di database:
```sql
UPDATE shape SET petugas = '(tanpa petugas)' WHERE LOWER(petugas) IN ('nan', 'none', 'null', '');
UPDATE master_shape SET petugas = '(tanpa petugas)' WHERE LOWER(petugas) IN ('nan', 'none', 'null', '');
DELETE FROM petugas_stats WHERE LOWER(petugas) IN ('nan', 'none', 'null');
DELETE FROM colour_map WHERE category_type = 'petugas' AND LOWER(category_value) IN ('nan', 'none', 'null');
```
Lalu panggil `recheck_shape_topology(conn)` untuk menghitung ulang statistik secara bersih.

---

## BAGIAN 4: Anomali Dropdown Bergetar/Joged Saat Kursor Hover

### 4.1. Bukan Bug JavaScript, Melainkan Racun CSS Micro-Interaction
[certain] Investigasi visual dan kode menunjukkan bahwa getaran ("joged-joged") pada dropdown saat kursor berada di atas baris **bukan disebabkan oleh script JS**, melainkan oleh animasi CSS `transform` pada baris [`static/style.css:996`](file:///c:/laragon/www/wilkerstat-checker/static/style.css#L996):

```css
.error-list-item:hover {
    background: #eff6ff;
    border-color: #93c5fd;
    color: var(--primary);
    transform: translateX(2px); /* <-- BIANG KELADI GETAR */
}
```

### 4.2. Mekanisme Siklus Osilasi 60 FPS (Hover Oscillation Loop)
1. **Pergeseran Hit-Test Kursor**:
   Saat kursor menyentuh tepi kiri atau kanan elemen `.error-list-item`, state `:hover` aktif.
2. **Dislokasi Elemen Fisik**:
   Aturan `transform: translateX(2px)` langsung menggeser posisi fisik elemen 2 pixel ke kanan.
3. **Pelepasan Hover (Hover Lost)**:
   Karena elemen bergeser 2px, kursor yang posisinya statis tiba-tiba berada di luar area bounding box elemen. Browser memicu event `mouseleave`.
4. **Elemen Mental Balik (Snap Back)**:
   Saat hover hilang, elemen kembali ke koordinat `translateX(0)`.
5. **Hover Menyala Kembali**:
   Kembalinya elemen ke posisi awal membuat kursor kembali berada di atasnya, memicu `mouseenter`.
6. **Loop Tanpa Henti**:
   Siklus ini berulang dengan frekuensi frame rate monitor (60Hz–144Hz), menciptakan efek visual bergetar hebat ("joged-joged").

### 4.3. Faktor Pemburuk: Scrollbar Layout Thrashing & Latensi Remote
1. **Horizontal Scrollbar Toggle**:
   Wadah `.error-list-scroll` memiliki lebar tetap 100% dengan `overflow-y: auto` tanpa `overflow-x: hidden`. Ketika item tergeser 2px ke kanan, ia meluber (overflow) secara horizontal, memicu browser merender horizontal scrollbar selama 1 frame. Kemunculan scrollbar mengurangi tinggi vertikal kontainer, memicu layout reflow, lalu hilang lagi saat hover lepas.
2. **Bencana di Akses Remote (RDP / AnyDesk / TeamViewer)**:
   Pada koneksi remote dengan delay 500ms–1000ms, kursor pengguna mengalami desinkronisasi terhadap posisi elemen yang sedang berosilasi cepat. Akibatnya, sinyal klik mendarat di celah kosong (gap) antar-baris atau terdaftar di luar elemen target.
3. **Click Event Bubbling Hazard**:
   Ketiadaan `stopPropagation()` pada kontainer `.petugas-error-dropdown` menyebabkan setiap klik yang meleset dari `.error-list-item` (akibat getaran) langsung menembus ke elemen pembungkus `.petugas-bar-row`, yang secara otomatis **menutup seluruh dropdown**.

### 4.4. Solusi Eksekusi Menyeluruh
1. **Hapus `transform: translateX(2px)`** pada `.error-list-item:hover`. Efek hover cukup menggunakan perubahan warna (`background-color`, `border-color`, `color`) tanpa memanipulasi geometri piksel.
2. **Kunci Overflow & Scrollbar Gutter**:
   Tambahkan `overflow-x: hidden;` dan `scrollbar-gutter: stable;` pada `.error-list-scroll` serta `.dd-panel` agar kehadiran scrollbar vertikal tidak menggeser lebar layout.
3. **Batasi CSS Transition**:
   Ubah `transition: all 0.12s ease;` menjadi transisi properti warna eksplisit (`background-color 0.1s ease, border-color 0.1s ease, color 0.1s ease`).
4. **Karantina Event Klik di Dropdown (JavaScript)**:
   Pasang `dropdown.addEventListener('click', (e) => e.stopPropagation())` di [`static/home.js`](file:///c:/laragon/www/wilkerstat-checker/static/home.js) agar klik yang sedikit meleset saat remote tidak menutup dropdown accordion.

---

## BAGIAN 5: Anomali Dropdown Tertutup Otomatis Saat Klik Peta (Auto-Collapse Hazard)

### 5.1. Akar Masalah: Pola "Click-Outside to Dismiss" di Lingkungan GIS
[certain] Dropdown tertutup sendiri saat Anda mengklik peta karena kode di [`static/home.js:512–516`](file:///c:/laragon/www/wilkerstat-checker/static/home.js#L512-L516) memasang event listener global `document.addEventListener('click')`:

```javascript
// Baris 511–516 static/home.js:
// Close on outside click
document.addEventListener('click', e => {
    if (!e.target.closest('.dropdown-check')) {
        document.querySelectorAll('.dropdown-check.open').forEach(d => d.classList.remove('open'));
    }
});
```

Pola ini umum digunakan di web form biasa, namun merupakan **cacat desain (anti-pattern) fatal pada aplikasi GIS interaktif**:
1. Di aplikasi peta, pengguna membuka dropdown (misal: daftar Kecamatan / Desa / SLS) justru untuk membandingkan isinya dengan visual poligon di peta.
2. Ketika pengguna mengklik kanvas peta (`#mainMap`) untuk menggeser (pan), zoom, atau melihat batas wilayah, event klik naik (bubble) ke `document`.
3. Pengecekan `!e.target.closest('.dropdown-check')` bernilai `true` (karena kanvas peta berada di luar dropdown), sehingga seluruh dropdown yang sedang dibuka dipaksa menutup (`classList.remove('open')`).
4. Selain itu, baris 508 memaksa penutupan dropdown lain saat satu dropdown dibuka (`Close all`), menghilangkan kebebasan membuka multi-panel secara berdampingan.

### 5.2. Risiko Tambahan: Polling Latar Belakang (Interval Reset)
Setiap 30 detik (`setInterval(loadStats, 30000)`), fungsi `renderBars()` dieksekusi ulang dan menghapus seluruh elemen DOM container (`container.innerHTML = ''`). Jika pengguna sedang membuka daftar petugas, DOM yang diperbarui me-reset status elemen sehingga dropdown accordion yang sedang dibuka tiba-tiba lenyap/tertutup sendiri tanpa interaksi klik.

### 5.3. Solusi Eksekusi Menyeluruh
1. **Cabut Global Outside-Click Listener**:
   Hapus event listener `document.addEventListener('click')` di [`static/home.js`](file:///c:/laragon/www/wilkerstat-checker/static/home.js).
2. **Jadikan Toggle Mandiri (Independent State)**:
   Ubah `window.toggleDropdown` menjadi murni `el.classList.toggle('open')` tanpa menutup dropdown lain secara otomatis.
3. **Persistensi State Accordion Petugas**:
   Simpan ID/nama petugas yang sedang aktif dibuka ke dalam variabel state (`expandedPetugasSet`), sehingga saat background worker atau refresh 30 detik berjalan, dropdown yang sedang dilihat pengguna tetap terbuka.

---

## BAGIAN 6: Desain Arsitektur Fallback IDSLS & Pelacakan Visual Duplikat IDSUBSLS

### 6.1. Mekanisme Fallback IDSUBSLS -> IDSLS
[certain] Logika deteksi master terhadap hasil unggahan:
1. **Prioritas 1 (Strict Matching)**: Cocokkan `upload.idsubsls == master.idsubsls` (16 digit). Jika cocok, proses selesai.
2. **Prioritas 2 (Fallback Matching)**: Jika `idsubsls` tidak ditemukan di master, ekstrak `idsls` (14 digit, baik dari kolom `idsls` maupun 14 digit pertama `idsubsls`). Cari record master yang memiliki `idsls` yang sama.
3. **Validasi Wajib Kardinalitas (Mencegah Benturan Ambigu 1-ke-Banyak)**:
   - **Kondisi Tunggal (1 Sub-SLS)**: Jika di master hanya ada 1 record untuk `idsls` tersebut (misal SLS murni tanpa pemekaran / `kdsubsls == '00'`), asosiasi fallback dinyatakan **SAH**.
   - **Kondisi Jamak (Pemekaran Sub-SLS)**: Jika di master terdapat 2 atau lebih sub-SLS untuk `idsls` yang sama (misal SLS 0010 memiliki sub 01 dan 02), sistem **DILARANG KERAS** memasangkannya secara sepihak. Sistem wajib menandainya sebagai isu atribut kritis: `ambiguous_idsubsls_fallback` (severity: error).

### 6.2. Duplikat IDSUBSLS sebagai Eror Spasial Penuh (Setara Eror Topologi)
Agar pelacakan duplikat `idsubsls` memiliki kapabilitas yang sama persis dengan eror topologi (overlap, gap, multipart):

#### A. Penyimpanan Geometri pada Tabel `issue`
Saat terdeteksi baris dengan `idsubsls` kembar di [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py):
- Simpan geometri fisik poligon dalam bentuk binary `geom_wkb` ke kolom `issue.geom_wkb`.
- Simpan bounding box (`bbox`), titik pusat (`label_x`, `label_y`), serta identitas petugas benturan ke dalam JSON `issue.detail`.
- Format kueri:
  ```python
  conn.execute("""
      INSERT INTO issue (issue_type, severity, upload_type, target_id, petugas, detail, geom_wkb, upload_id)
      VALUES ('duplicate_idsubsls', 'error', 'shape', ?, ?, ?, ?, ?)
  """, (idsub, petugas, json.dumps(detail, ensure_ascii=False), geom_wkb_bytes, upload_id))
  ```

#### B. Penyediaan Data GeoJSON Terpadu
Di [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py) pada endpoint `/api/issues/geojson`:
- Pastikan filter `type=duplicate_idsubsls` didukung penuh untuk memuntahkan `FeatureCollection` spasial dari seluruh fitur yang terindikasi duplikat.

#### C. Antarmuka dan Zoom to Feature di Peta
Di [`templates/home.html`](file:///c:/laragon/www/wilkerstat-checker/templates/home.html) dan [`static/home.js`](file:///c:/laragon/www/wilkerstat-checker/static/home.js):
1. **Mode Bar Baru**: Tambahkan tombol mode `Duplikat` di samping `Upload`, `Multipart`, `Gap`, dan `Overlap` pada tab Poligon.
2. **Layer Spasial Peta**: Daftarkan layer peta `issues-duplicate_idsubsls-fill` dan `issues-duplicate_idsubsls-outline` dengan pewarnaan kontras (misal: magenta `#c026d3` berkedip).
3. **Interaktivitas Zoom**: Saat baris duplikat diklik di daftar sidebar, fungsi `focusErrorOnMap(item)` mengeksekusi `map.fitBounds(item.bbox)` untuk langsung mengarahkan kamera ke lokasi poligon yang berkonflik, disertai penanda popup detail konflik.

### 6.3. Status Implementasi
[certain] Seluruh implementasi telah selesai dikerjakan:
1. `validate_shape.py`: Integrasi pencatatan `duplicate_idsubsls` ke tabel `issue` menyertakan `geom_wkb` dan kalkulasi statistik petugas.
2. `validate_dot.py`: Validasi spasial titik dan agregasi statistik kini menerapkan fallback `idsls` (14 digit) dengan pengaman kardinalitas tunggal.
3. `app.py`: Kueri agregasi `unassigned_shape_count`, filter `api_petugas_errors`, endpoint GeoJSON master, dan endpoint GeoJSON isu duplikat telah terhubung.
4. `home.html` & `style.css`: Tombol mode `Duplikat`, filter layer peta, dan lencana styling magenta `#c026d3` telah ditambahkan.
5. `home.js`: Penanganan mode `duplicate`, toggle layer peta, dan aksi interaktif klik `focusErrorOnMap` dengan zoom spasial ke bounding box telah aktif.

---

## BAGIAN 7: Analisis Kasus Kosongan di Peta tapi Tidak Terhitung Belum Upload (Kasus SLS 6309020004000100 - Petugas Saskia)

### 7.1. Data Uji
Record yang dikonsultasikan:
- `idsubsls`: `6309020004000100` (16 digit)
- `idsls`: `63090200040001` (14 digit)
- `kdsubsls`: `00`
- `petugas`: `saskia`
- `nmdesa`: `TAMUNTI`
- `nmsls`: `RT 001`
- `wkt_geom`: Poligon fisik valid di Tabalong (Lon ~115.31 s.d. 115.34, Lat ~ -2.31 s.d. -2.32)

### 7.2. Akar Masalah Teknis

Ada 4 penyebab sistemik mengapa poligon tersebut tampak **kosong di peta** namun **tidak dianggap sebagai progres belum upload**:

#### 1. Ingest Master CSV/TSV Mengabaikan Kolom Geometri WKT (`wkt_geom`)
[certain] Pada fungsi `_process_master_shape()` di [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py):
- Ekstraksi geometri ke `master_shape.geom_wkb` **hanya dieksekusi jika berkas master berekstensi `.geojson` atau `.json`**.
- Jika master diunggah dalam format teks tabel (CSV, TSV, atau XLSX) yang memiliki kolom string `wkt_geom`, teks WKT tersebut **tidak diparsing menjadi geometri binary Spasial (`geom_wkb`)**, melainkan dibiarkan `NULL` dan hanya disimpan sebagai teks mati di dalam JSON `extra`.
- Endpoint `/api/master/shapes/geojson` hanya menarik `WHERE geom_wkb IS NOT NULL`. Akibatnya, poligon master tidak pernah dikirimkan ke kanvas peta (`master-shapes-fill`), sehingga wilayah tersebut tampak **bolong/kosong fisik** di layar.

#### 2. Dampak Fallback 14-Digit IDSLS yang Baru Dipasang
[certain] Sesuai logika fallback yang diminta:
Jika master memiliki `idsubsls` 16 digit `6309020004000100` (14 digit awal: `63090200040001`), dan di tabel `shape` (hasil upload petugas mana pun) terdapat poligon yang memiliki `idsls = '63090200040001'` ATAU `SUBSTR(idsubsls, 1, 14) = '63090200040001'`:
- Kueri `unassigned_shape_count` mendeteksi bahwa SLS 14-digit ini **sudah terwakili di tabel upload**.
- Akibatnya, SLS master ini **otomatis dicoret dari daftar `(Belum Diupload)`** karena dianggap sudah selesai diunggah.
- Namun jika poligon upload pasangannya tersebut berada di koordinat yang melenceng atau tidak menutupi bidang yang dimaksud, pengguna melihat bidang fisik di peta tetap kosong, sementara sistem statistik mencatatnya "sudah upload".

#### 3. Poligon Sudah Tersimpan di Tabel `shape`, tapi Tersembunyi oleh Filter Tampilan
[likely] Jika berkas poligon ini sebenarnya sudah berhasil diunggah ke tabel `shape` (sehingga dihitung "sudah upload" dan tidak muncul di "belum upload"):
- Poligon tidak muncul di peta jika pengguna sedang mengaktifkan filter dropdown (Kecamatan, Desa, SLS, atau Petugas) di panel kiri atas yang tidak mencakup `TAMUNTI` atau `saskia`.
- Atau poligon tertimpa / terpotong oleh batas layer lain.

#### 4. Kesalahpahaman UX: Dropdown Petugas vs Dropdown Belum Diupload
[certain] Pada sidebar progres:
- Mengklik baris petugas **Saskia** (`mode: progress`) akan mengeksekusi kueri `SELECT FROM shape WHERE LOWER(petugas) = 'saskia'`. Dropdown ini **hanya menampilkan daftar SLS yang SUDAH diunggah** oleh Saskia.
- Dropdown petugas **tidak pernah menampilkan SLS master yang BELUM diunggah**.
- Seluruh SLS yang belum diunggah dikumpulkan secara terpusat di bar baris paling bawah: **`(Belum Diupload)`**. Jika pengguna mencari tunggakan Saskia di dalam accordion Saskia, item tersebut memang tidak akan ada.






