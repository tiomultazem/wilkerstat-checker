# AUDIT & ARSITEKTUR: PELEBURAN POLIGON SLS MENJADI DESA DAN KECAMATAN 2026 SEMESTER 1

- **Lokasi Berkas**: `c:\laragon\www\wilkerstat-checker\audit-trail\audit peleburan sls ke desa dan kecamatan.md`
- **Tanggal Audit**: 2026-11-05
- **Tingkat Keyakinan**: [certain] (Berdasarkan skema referensi GeoJSON BPS `Prod_Desa_202516309.geojson`, `Prod_Kec_202516309.geojson`, dan standar topologi OGC/Wilkerstat)

---

## 1. The Uncomfortable Truth (Fakta Pahit & Koreksi Asumsi)

[certain] i disagree because instruksi *"bila ada multiparts, make it single parts"* melanggar standar integritas data wilayah administrasi BPS.

Wilayah desa dan kecamatan di Indonesia secara geografis sering memiliki pulau terpisah, enklave, atau eksklave sungai. Jika wilayah tersebut dipaksa menjadi *singlepart* (misalnya via `gdf.explode()`), maka satu entitas desa (misal `iddesa = 6309050015`) yang memiliki 2 bagian poligon terpisah akan terpecah menjadi 2 baris fitur yang berbeda. 

- **here's what i'd do instead**:
  1. Jalankan `unary_union` untuk melebur poligon-poligon SLS yang bertetangga menjadi kesatuan geometri kontinu.
  2. Jika hasil leburan memiliki bagian terpisah (disjoint), pertahankan bagian tersebut dalam wadah **`MultiPolygon`** agar tetap 1 baris fitur per 1 kode administrasi (`iddesa` atau `idkec`).
  3. Bungkus semua geometri `Polygon` tunggal menjadi `MultiPolygon` agar skema seragam 100% dengan `Prod_Desa_202516309.geojson` dan `Prod_Kec_202516309.geojson`.
- **the risk in your approach is**:
  Duplikasi kode `iddesa` dan `idkec` (melanggar *primary key unique constraint*), rusaknya relasi tabular di basis data Wilkerstat, serta kegagalan otomatis saat dibaca oleh Model 1 dan Model 2.

---

## 2. Pemetaan Skema Data Masukan & Luaran Baku

### A. Berkas Sumber
- **Jalur**: `00-identify dots/untuk 2026_1.geojson`
- **Level**: SLS / Sub-SLS Kabupaten Tabalong (`6309`)
- **CRS**: `urn:ogc:def:crs:OGC:1.3:CRS84` (WGS84 EPSG:4326)
- **Atribut Kunci**: `kdprov`, `kdkab`, `kdkec`, `kddesa`, `nmprov`, `nmkab`, `nmkec`, `nmdesa`, `periode` ("2026_1").

### B. Target 1: Peta Desa (`Prod_Desa_202616309.geojson`)
Mengikuti spesifikasi persis `Prod_Desa_202516309.geojson`:

| Kolom | Tipe Data | Contoh Nilai | Aturan Penentuan |
| :--- | :--- | :--- | :--- |
| `gid` | integer | `13422` | Nomor urut unik integer (dimulai dari `13422` atau urutan kontinu). |
| `luas` | float | `8.024668460096464` | Luas geodesik dalam satuan km² (proyeksi UTM Zone 50S EPSG:32650 atau WGS84 Geod). |
| `kdkab` | string | `"09"` | Kode kabupaten (2 digit). |
| `kdkec` | string | `"050"` | Kode kecamatan (3 digit). |
| `nmkab` | string | `"TABALONG"` | Nama kabupaten. |
| `nmkec` | string | `"TANTA"` | Nama kecamatan. |
| `iddesa` | string | `"6309050015"` | Kunci gabungan 10 digit: `kdprov + kdkab + kdkec + kddesa`. |
| `kddesa` | string | `"015"` | Kode desa (3 digit). |
| `kdprov` | string | `"63"` | Kode provinsi (2 digit). |
| `nmdesa` | string | `"TANTA"` | Nama desa/kelurahan. |
| `nmprov` | string | `"KALIMANTAN SELATAN"` | Nama provinsi. |
| `rw_dki` | string | `""` | Kosong/string hampa untuk non-DKI. |
| `sumber` | string | `"BPS"` | Nilai tetap `"BPS"`. |
| `periode`| string | `"2026_1"` | Periode pemutakhiran semester aktif. |
| **Geometry** | MultiPolygon | `coordinates: [[[[lon, lat], ...]]]]` | Seluruh poligon desa dibungkus sebagai `MultiPolygon`. |

### C. Target 2: Peta Kecamatan (`Prod_Kec_202616309.geojson`)
Mengikuti spesifikasi persis `Prod_Kec_202516309.geojson`:

| Kolom | Tipe Data | Contoh Nilai | Aturan Penentuan |
| :--- | :--- | :--- | :--- |
| `gid` | integer | `1025` | Nomor urut unik integer (dimulai dari `1025` atau urutan kontinu). |
| `luas` | float | `153.23702218426226`| Luas geodesik dalam satuan km². |
| `idkec` | string | `"6309010"` | Kunci gabungan 7 digit: `kdprov + kdkab + kdkec`. |
| `kdkab` | string | `"09"` | Kode kabupaten (2 digit). |
| `kdkec` | string | `"010"` | Kode kecamatan (3 digit). |
| `nmkab` | string | `"TABALONG"` | Nama kabupaten. |
| `nmkec` | string | `"BANUA LAWAS"` | Nama kecamatan. |
| `kdprov` | string | `"63"` | Kode provinsi (2 digit). |
| `nmprov` | string | `"KALIMANTAN SELATAN"` | Nama provinsi. |
| `sumber` | string | `"BPS"` | Nilai tetap `"BPS"`. |
| `periode`| string | `"2026_1"` | Periode pemutakhiran semester aktif. |
| **Geometry** | MultiPolygon | `coordinates: [[[[lon, lat], ...]]]]` | Seluruh poligon kecamatan dibungkus sebagai `MultiPolygon`. |

---

## 3. Algoritma Peleburan Python (Production-Grade)

Peleburan tidak boleh menggunakan loop manual yang lambat. Standar industri spasial menggunakan `shapely.validation.make_valid`, agregasi spasial `geopandas.GeoDataFrame.dissolve()`, serta penyelarasan proyeksi metrik untuk akurasi luas.

```
                    ┌──────────────────────────────┐
                    │ untuk 2026_1.geojson (SLS)   │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   make_valid(geometry)       │
                    │   buffer(0) sliver cleanup   │
                    └──────────────┬───────────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 │                                   │
                 ▼                                   ▼
    [Groupby Desa: iddesa]              [Groupby Kecamatan: idkec]
    - unary_union(geometries)           - unary_union(geometries)
    - force MultiPolygon                - force MultiPolygon
    - calculate luas km² (EPSG:32650)   - calculate luas km² (EPSG:32650)
    - assign schema Prod_Desa           - assign schema Prod_Kec
                 │                                   │
                 ▼                                   ▼
    Prod_Desa_202616309.geojson         Prod_Kec_202616309.geojson
```

### Langkah 1: Perbaikan Geometri (Make Valid & Sliver Fix)
- [certain] Poligon masukan diperiksa dengan `geom.is_valid`. Jika invalid, gunakan `shapely.validation.make_valid(geom)`.
- Jika `make_valid` menghasilkan `GeometryCollection` (akibat perpotongan garis atau titik artefak), filter hanya elemen bertipe `Polygon` atau `MultiPolygon`.
- Terapkan `geom.buffer(0)` untuk menyatukan batas-batas mikroskopis (sliver lines) yang sering muncul antar batas SLS bertetangga.

### Langkah 2: Agregasi & Peleburan (Dissolve)
1. **Tingkat Desa**:
   - Kolom agregasi: `['kdprov', 'kdkab', 'kdkec', 'kddesa', 'nmprov', 'nmkab', 'nmkec', 'nmdesa']`.
   - Operasi spasial: `shapely.ops.unary_union`.
   - Bentuk kolom `iddesa`: `kdprov.str.cat([kdkab, kdkec, kddesa])`.
   - Bentuk kolom `rw_dki`: `""`.
   - Bentuk kolom `sumber`: `"BPS"`.
   - Bentuk kolom `periode`: `"2026_1"`.
2. **Tingkat Kecamatan**:
   - Kolom agregasi: `['kdprov', 'kdkab', 'kdkec', 'nmprov', 'nmkab', 'nmkec']`.
   - Operasi spasial: `shapely.ops.unary_union`.
   - Bentuk kolom `idkec`: `kdprov.str.cat([kdkab, kdkec])`.
   - Bentuk kolom `sumber`: `"BPS"`.
   - Bentuk kolom `periode`: `"2026_1"`.

### Langkah 3: Penyeragaman MultiPolygon (Bukan Explode Singlepart)
- Setiap geometri bertipe `Polygon` diubah menjadi `MultiPolygon([poly])`.
- Setiap geometri bertipe `MultiPolygon` dipertahankan apa adanya (1 baris mewakili 1 wilayah administrasi utuh).
- Tidak ada operasi `explode()` yang memecah baris data.

### Langkah 4: Perhitungan Luas Baku (`luas`)
- Luas poligon dihitung dengan mereproyeksikan layer ke sistem koordinat planar metrik lokal Tabalong (**UTM Zone 50S / EPSG:32650**):
  $$\text{luas (km}^2\text{)} = \frac{\text{area (m}^2\text{)}}{1.000.000}$$
- Nilai dibulatkan ke format float presisi tinggi sesuai konvensi Wilkerstat BPS.

---

## 4. Rencana Implementasi Skrip Python

Skrip akan disimpan di:
`00-identify dots/dissolve_wilkerstat.py`

### Fitur Skrip:
1. Menangani pembacaan berkas masukan `00-identify dots/untuk 2026_1.geojson`.
2. Menghasilkan:
   - `00-identify dots/Prod_Desa_202616309.geojson`
   - `00-identify dots/Prod_Kec_202616309.geojson`
3. Memvalidasi kompatibilitas kolom 100% terhadap `Prod_Desa_202516309.geojson` dan `Prod_Kec_202516309.geojson`.
4. Menyediakan verifikasi akhir: jumlah desa harus persis 131 desa, dan jumlah kecamatan harus persis 12 kecamatan untuk Kabupaten Tabalong.

---

## 5. Status Prosedural

Sesuai aturan kerja tahap demi tahap:
1. Tahap Audit & Desain: **SELESAI DITULIS**.
2. Tahap Pembuatan Skrip & Eksekusi: **MENUNGGU KONFIRMASI** (dilarang lanjut sebelum ada perintah eksplisit).

