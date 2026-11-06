# Modul 01: Reposisi Titik Offside (Move Offside Dots)

Folder ini berfungsi sebagai mesin penanganan titik bermasalah (*Phase 1*): menarik titik-titik yang terlempar ke luar batas poligon (`OFFSIDE` / `flag_repair = 1`) agar masuk ke dalam interior poligon SLS induknya (`INSIDE`).

---

## 1. Arsitektur: Modern vs Legacy

```
                        titik hasil identifikasi.geojson
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
                ▼ (Modern - Rekomendasi)                      ▼ (Legacy 6-Tahap)
        [bridge_repair.py]                           [run.py / module/]
        - Single-pass STRtree                        - Step 1: split_data
        - Home SLS 14-digit union guard              - Step 2: s02_repair (131 desa)
        - Preservasi 21 kolom Model 2                - Step 3: s03_muatan
        - Waktu proses: ~2 menit                     - Step 4: extract_failed
                │                                    - Step 5: move_failed
                │                                    - Step 6: sync_final
                ▼                                             │
      titik_siap_model2.geojson                               ▼
  (Siap load ke Model 2 QGIS)                    final_landmark_*.geojson
```

---

## 2. Mesin Produksi Utama: `bridge_repair.py`

Skrip tunggal berperforma tinggi yang menggantikan seluruh pipeline 6-tahap usang yang lambat dan rawan bug kaskade.

### Keunggulan Teknis:
1. **STRtree Spatial Indexing**: Memetakan seluruh poligon master kabupaten secara vektor tanpa perlu memecah data per-desa.
2. **Immutability Guard (SLS 14-Digit)**: Mencegah titik yang berada di SubSLS 01 terseret ke SubSLS 02 di utara; selama titik berada di dalam RT yang sama, koordinat fisik dikunci 100%.
3. **Interior Projection Fallback**: Titik yang benar-benar offside ditarik masuk ke poligon target dengan bantalan aman (`buffer(-0.00005)` atau `representative_point`).
4. **Preservasi Skema Model 2**: Menjamin 21 kolom atribut wajib masukan Model 2 QGIS tetap utuh tanpa terpotong.

### Cara Menjalankan:
```cmd
rtk python "01-move offside dots/bridge_repair.py"
```

---

## 3. Pipeline Warisan (Legacy Fallback)

Modul-modul di dalam folder `module/` dipertahankan sebagai referensi audit dan penanganan manual bila diperlukan:

| Berkas | Fungsi Teknis |
| :--- | :--- |
| `run.py` | Runner antarmuka menu interaktif CLI untuk mengeksekusi langkah 1 s.d. 6. |
| `module/split_data.py` | Memecah poligon dan titik kabupaten ke dalam subfolder 131 desa. |
| `module/s02_repair_geotagging.py` | Menjalankan iterasi perbaikan spasial per desa. |
| `module/s03_perhitungan_muatan.py` | Menghitung agregasi muatan bangunan dan mengekspor master Ground Segment. |
| `module/extract_failed.py` | Menyaring titik yang masih offside pasca-reparasi ke `failed.geojson`. |
| `module/move_failed.py` | Memproyeksikan titik gagal ke batas inward poligon. |
| `module/sync_final_landmark.py` | Menimpa koordinat lama dengan koordinat baru pada master landmark. |

Jalankan menu interaktif warisan:
```cmd
rtk python "01-move offside dots/run.py"
```

---

## 4. Atribusi & Kredit

Pipeline perbaikan bertahap (`module/`) serta fondasi logika penanganan pergeseran titik muatan pada modul ini diturunkan dari repositori resmi:
- **Sumber Acuan**: [PMSS-BPS/Pengolahan-Wilkerstat-SE2026](https://github.com/PMSS-BPS/Pengolahan-Wilkerstat-SE2026) (Direktorat Pengembangan Metodologi Sensus dan Survei, Badan Pusat Statistik RI).
- **Modernisasi Arsitektur**: Pipeline warisan tersebut telah dikonsolidasikan dan dioptimasi menjadi mesin tunggal berkinerja tinggi `bridge_repair.py` menggunakan *spatial indexing* STRtree, penjaga batas 14-digit SLS, dan preservasi 21 kolom skema Model 2.
