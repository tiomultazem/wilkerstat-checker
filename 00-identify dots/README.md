# Modul 00: Identifikasi Titik & Peleburan Wilayah (Identify Dots & Dissolve)

Folder ini berfungsi sebagai gerbang data geospasial mentah (*Phase 0*): validasi posisi awal titik bangunan (*geotagging*), penyiapan data masukan Model QGIS, serta peleburan poligon SLS menjadi peta batas Desa dan Kecamatan acuan semester aktif.

---

## 1. Inventaris Berkas & Peran Teknis

| Berkas | Kategori | Fungsi Teknis |
| :--- | :--- | :--- |
| `01 Identifikasi Titik.model3` | QGIS Model3 | Model spasial QGIS untuk mengevaluasi posisi fisik titik terhadap poligon batas SLS acuan. Menghasilkan atribut `flag_repair = 1` bila titik berada di luar poligon (`OFFSIDE`). |
| `titik sebelum identifikasi.geojson` | Data Input | Titik geotagging mentah hasil survei lapangan se-kabupaten (~104.000 titik). |
| `slsmentah fixed-2025sm1.geojson` | Peta Acuan | Poligon batas SLS acuan BPS Semester 1 2025. |
| `titik hasil identifikasi.geojson` | Data Output | Luaran Model 1 QGIS; memuat status awal titik (`flag_repair = 0` vs `flag_repair = 1`). Menjadi masukan bagi `bridge_repair.py`. |
| `titik_siap_model2.geojson` | Data Intermediat | Luaran `bridge_repair.py` dengan koordinat fisik yang sudah digeser ke interior poligon SLS dan 21 skema kolom wajib Model 2. |
| `untuk 2026_1.geojson` | Data Input | Poligon SLS/Sub-SLS termutakhir Kabupaten Tabalong untuk semester 1 2026 yang telah bebas dari gap, overlap, dan multipart. |
| `dissolve_wilkerstat.py` | Skrip Produksi | Skrip peleburan poligon SLS menjadi batas Desa (14 kolom BPS) dan batas Kecamatan (11 kolom BPS) dengan kalkulasi luas metrik EPSG:32650. |
| `Prod_Desa_202516309.geojson` | Peta Referensi | Referensi skema baku batas Desa Tabalong semester lalu (131 desa). |
| `Prod_Kec_202516309.geojson` | Peta Referensi | Referensi skema baku batas Kecamatan Tabalong semester lalu (12 kecamatan). |
| `Prod_Desa_202616309.geojson` | Produk Baku | Hasil peleburan resmi batas Desa 2026 Semester 1 (131 desa, skema 14 kolom BPS, MultiPolygon 100%). |
| `Prod_Kec_202616309.geojson` | Produk Baku | Hasil peleburan resmi batas Kecamatan 2026 Semester 1 (12 kecamatan, skema 11 kolom BPS, MultiPolygon 100%). |

---

## 2. Alur Operasional

### A. Alur Evaluasi Spasial Titik Bangunan
1. Buka **QGIS** -> Buka `01 Identifikasi Titik.model3`.
2. Masukkan `titik sebelum identifikasi.geojson` dan `slsmentah fixed-2025sm1.geojson`.
3. Jalankan dan ekspor hasilnya ke `titik hasil identifikasi.geojson`.
4. Jalankan skrip jembatan di modul tetangga:
   ```cmd
   rtk python "01-move offside dots/bridge_repair.py"
   ```
5. Hasil pergeseran akan tersimpan di folder ini sebagai `titik_siap_model2.geojson` untuk evaluasi final di Model 2 QGIS.

### B. Alur Peleburan Batas Wilayah 2026 Semester 1
Jalankan skrip peleburan SLS ke Desa dan Kecamatan:
```cmd
rtk python "00-identify dots/dissolve_wilkerstat.py"
```
Skrip otomatis memverifikasi:
- 131 entitas Desa di `Prod_Desa_202616309.geojson`.
- 12 entitas Kecamatan di `Prod_Kec_202616309.geojson`.
- Preservasi MultiPolygon (tanpa explode yang memecah kode wilayah).
- Luas geodesik dalam satuan km² terproyeksi UTM Zone 50S (EPSG:32650).

---

## 3. Atribusi & Kredit

Konsep alur identifikasi spasial titik dan model pemrosesan QGIS pada tahap ini diadaptasi dan dikembangkan dari repositori resmi:
- **Sumber Acuan**: [PMSS-BPS/Pengolahan-Wilkerstat-SE2026](https://github.com/PMSS-BPS/Pengolahan-Wilkerstat-SE2026) (Direktorat Pengembangan Metodologi Sensus dan Survei, Badan Pusat Statistik RI).
