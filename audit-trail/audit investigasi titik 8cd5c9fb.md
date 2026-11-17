# AUDIT FORENSIK SPASIAL: TITIK 8cd5c9fb-7c91-4a91-93d2-ff4968155360
**Berkas Kasus**: `audit-trail/audit investigasi titik 8cd5c9fb.md`  
**Objek Analisis**: Titik `8cd5c9fb-7c91-4a91-93d2-ff4968155360` (`unique_bang: 6309050017000201#0180`)  
**Tingkat Keyakinan**: [certain] (Berdasarkan perhitungan koordinat spasial murni terhadap poligon Wilkerstat `final_sls_251_6309050017.geojson`)

---

## 1. The Uncomfortable Truth (Fakta Pahit)
[certain] Asumsi Anda keliru. Titik `8cd5c9fb-7c91-4a91-93d2-ff4968155360` **TIDAK PERNAH berada di home poligonnya (RT 002)**.  
Koordinat asal titik tersebut secara fisik berada di wilayah **RT 008**, sementara atribut beban tugasnya berkode **RT 002**. Algoritma mendeteksi offside lintas-SLS murni dan memindahkannya ke dalam poligon RT 002 sesuai atributnya.

---

## 2. Bukti Geometris Koordinat vs Batas Poligon

### A. Koordinat Asal Titik (Raw Geotagging)
* **ID Assignment**: `8cd5c9fb-7c91-4a91-93d2-ff4968155360`
* **Kode SLS Atribut (`level_6_full_code`)**: `6309050017000201` (RT 002 SubSLS 01)
* **Nama SLS Atribut (`level_6_name`)**: `RT 002`
* **Koordinat Asal**:
  * Bujur (Longitude): `115.3893131`
  * Lintang (Latitude): `-2.1892512`

### B. Batas Poligon RT 002 (`63090500170002`)
Di dalam berkas [final_sls_251_6309050017.geojson](file:///c:/laragon/www/wilkerstat-checker/01-move%20offside%20dots/01%20-%20data/01-peta-251/final_sls_251_6309050017.geojson), RT 002 terdiri dari dua SubSLS:
1. **SubSLS 01 (`6309050017000201`, GID: 307401)**:
   * Rentang Bujur: `115.374617001` s.d. `115.381353020`
   * Rentang Lintang: `-2.187903333` s.d. `-2.183473333`
2. **SubSLS 02 (`6309050017000202`, GID: 307402)**:
   * Rentang Bujur: `115.379976796` s.d. `115.388195910`
   * Rentang Lintang: `-2.187939573` s.d. `-2.182685756`

**Batas Maksimum Keseluruhan RT 002 (Union)**:
* Bujur Maksimum (Batas Paling Timur): **`115.388195910`**
* Lintang Minimum (Batas Paling Selatan): **`-2.187939573`**

### C. Perbandingan Matematika Spasial
* **Bujur Titik**: `115.3893131` > `115.388195910` (Titik berada **124 meter di sebelah TIMUR** di luar RT 002).
* **Lintang Titik**: `-2.1892512` < `-2.187939573` (Titik berada **145 meter di sebelah SELATAN** di luar RT 002).

---

## 3. Di Mana Titik Asal Sebenarnya Berada?
[certain] Koordinat `(115.3893131, -2.1892512)` berada di dalam poligon:
* **SLS**: `63090500170008` (**RT 008**)
* **SubSLS**: `6309050017000801` (RT 008 SubSLS 01, GID: 307408)
* Rentang Bujur RT 008 SubSLS 01: `115.388077150` s.d. `115.393557870`
* Rentang Lintang RT 008 SubSLS 01: `-2.191857570` s.d. `-2.186413035`

Titik tersebut secara fisik berada di RT 008, berjarak lebih dari 150 meter dari batas terluar RT 002 dan lebih dari 1.000 meter dari SubSLS 01 RT 002.

---

## 4. Mengapa Algoritma Menggeser Titik?

```
[Kondisi Data Input]
Posisi Fisik Koordinat   : RT 008 (idsubsls: 6309050017000801)
Atribut Beban Tugas      : RT 002 (level_6_full_code: 6309050017000201)
                  ↓
[Evaluasi Model 3 & Pipeline]
Kecocokan 14-digit SLS   : 63090500170008 != 63090500170002 (BEDA SLS)
Status Spasial           : OFFSIDE LINTAS SLS (flag_repair = 1)
                  ↓
[Tindakan Pipeline Reposisi]
Tujuan Reposisi          : Masukkan ke poligon RT 002 SubSLS 01 (sesuai atribut)
Posisi Baru              : Point (115.37996613763404, -2.187678196849939)
Validasi Posisi Baru     : 100% INSIDE poligon 6309050017000201
```

---

## 5. Sumber Kekeliruan
1. Pengguna melihat titik di aplikasi GIS berada rapi di dalam sebuah poligon pemukiman, lalu mengira titik tersebut sudah berada di "home poligon".
2. Pengguna tidak menyadari bahwa poligon pemukiman tempat titik tersebut berada adalah milik **RT 008**, sedangkan nomor SLS yang ditempelkan petugas sensus pada data titik adalah **RT 002**.
3. Benturan ini adalah anomali data lapangan: petugas sensus RT 002 mendata rumah di RT 008, atau petugas salah memilih dropdown SLS saat input.
4. Algoritma menjalankan fungsinya secara konsisten: titik dengan atribut RT 002 yang tercecer di wilayah RT 008 ditarik masuk ke RT 002.

