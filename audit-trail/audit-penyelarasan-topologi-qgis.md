# Audit Trail: Penyelarasan Algoritma Overlap & Gap Detection dengan Standar QGIS Topology Checker

**Tanggal**: 4 November 2026  
**Referensi Standar**: [`00-identify dots/topology_resolver.py`](file:///c:/laragon/www/wilkerstat-checker/00-identify%20dots/topology_resolver.py) & QGIS Topology Checker Engine (GEOS)  
**Target Modul**: [`app/spatial.py`](file:///c:/laragon/www/wilkerstat-checker/app/spatial.py), [`app/config.py`](file:///c:/laragon/www/wilkerstat-checker/app/config.py), [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py)

---

## 1. Latar Belakang Masalah

Pengguna melaporkan anomali ketidaksinkronan hasil validasi topologi:
- Pada **QGIS Topology Checker** (menggunakan aturan *Must Not Overlap* dan *Must Not Have Gaps*), berkas poligon bersih dengan jumlah eror **0**.
- Pada **WilkerStat Checker (Web)**, berkas yang sama memunculkan banyak sekali eror **Overlap** dan **Gap** yang sangat sensitif.

---

## 2. Investigasi & Akar Masalah

Berdasarkan komparasi antara [`app/spatial.py`](file:///c:/laragon/www/wilkerstat-checker/app/spatial.py) dengan algoritma referensi di [`00-identify dots/topology_resolver.py`](file:///c:/laragon/www/wilkerstat-checker/00-identify%20dots/topology_resolver.py):

### 2.1. Cacat Deteksi Gap: Metode 2 (Morphological Buffer Closing)
- Di [`app/spatial.py`](file:///c:/laragon/www/wilkerstat-checker/app/spatial.py) baris 381–423, diterapkan dua metode deteksi gap:
  - **Metode 1**: Deteksi lubang interior (`interiors` dari `unary_union`). Ini adalah metode resmi dan satu-satunya yang dipakai QGIS Topology Checker untuk aturan *Must Not Have Gaps*.
  - **Metode 2**: Penutupan celah dengan ekspansi dan erosi buffer (`closed = U.buffer(w/2).buffer(-w/2).difference(U)`).
- **Akar Cacat**: Metode 2 bukanlah algoritma topologi valid. Pada setiap batas luar wilayah yang berlekuk (misalnya lekukan sungai, tikungan jalan, atau batas batas pantai/alam), pelebaran buffer $5\text{ m}$ dan penyusutan kembali menciptakan poligon-poligon selisih tiruan (*false positive gaps*). Setiap pertemuan sudut dua poligon di batas luar langsung dituduh sebagai "gap", padahal di dunia nyata dan di QGIS itu hanyalah batas luar teritori.

### 2.2. Cacat Deteksi Overlap: Sensitivitas Ekstrem Nilai Default ($0.0001\text{ m}^2$)
- Di [`app/config.py`](file:///c:/laragon/www/wilkerstat-checker/app/config.py):
  ```python
  OVERLAP_MIN_AREA_M2 = _env_float("OVERLAP_MIN_AREA_M2", 0.0001)
  GAP_MIN_AREA_M2     = _env_float("GAP_MIN_AREA_M2", 0.0001)
  ```
- Nilai $0.0001\text{ m}^2$ setara dengan $1\text{ cm}^2$ (luas perangko).
- Pada sistem koordinat geografis WGS84 (EPSG:4326), selisih pembulatan desimal ke-10 ($10^{-10}$ derajat) menghasilkan irisan mikro seluas $10^{-6}$ derajat persegi.
- Karena batas ambang disetel $0.0001\text{ m}^2$, noise presisi floating-point yang tidak kasat mata langsung dilaporkan sebagai eror overlap fatal.
- Selain itu, blok penanganan eksepsi pada perhitungan luas proyeksi memiliki cacat:
  ```python
  except Exception:
      area = 0.01
  ```
  Jika terjadi kegagalan reproyeksi pada geometri irisan yang degenerasi, sistem memaksa nilai luas menjadi $0.01\text{ m}^2$. Karena $0.01 > 0.0001$, irisan degenerasi tersebut dipaksa masuk sebagai kasus overlap.

---

## 3. Desain Solusi Sesuai Standar QGIS

1. **Eliminasi Metode 2 pada Gap Detection**:
   Hapus seluruh kode penutupan buffer morfologi di [`app/spatial.py`](file:///c:/laragon/www/wilkerstat-checker/app/spatial.py). Deteksi gap murni mengadopsi standar QGIS: lubang tertutup (interior ring) di dalam hasil `unary_union`.

2. **Isolasi Irisan 2D Poligon (`polys_only`)**:
   Gunakan fungsi filter geometri poligon murni dari `topology_resolver.py`. Irisan berupa titik, garis, atau kumpulan geometri non-poligon diabaikan.

3. **Perhitungan Luas Geodesik Cepat & Presisi**:
   Gunakan rumus konversi derajat-ke-meter lokal WGS84 dari `topology_resolver.py`:
   $$\Delta m_{\text{lat}} = 111132.92 - 559.82 \cos(2\phi) + 1.175 \cos(4\phi)$$
   $$\Delta m_{\text{lon}} = 111412.84 \cos(\phi) - 93.5 \cos(3\phi) + 0.118 \cos(5\phi)$$
   Formula ini menghilangkan overhead reproyeksi UTM per-fitur dan menghindari kegagalan reproyeksi.

4. **Koreksi Ambang Batas Default ke Skala Realistis ($1.0\text{ m}^2$)**:
   Ubah default `OVERLAP_MIN_AREA_M2` dan `GAP_MIN_AREA_M2` menjadi $1.0\text{ m}^2$ di [`app/config.py`](file:///c:/laragon/www/wilkerstat-checker/app/config.py) untuk menyaring noise batas floating-point.

---

## 4. Status Eksekusi

- [x] **Langkah 1**: Dokumentasi audit komprehensif akar masalah dan arsitektur perbaikan.
- [x] **Langkah 2**: Perbarui nilai default ambang batas toleransi topologi di [`app/config.py`](file:///c:/laragon/www/wilkerstat-checker/app/config.py) (`OVERLAP_MIN_AREA_M2 = 1.0`, `GAP_MIN_AREA_M2 = 1.0`).
- [x] **Langkah 3**: Refaktor [`app/spatial.py`](file:///c:/laragon/www/wilkerstat-checker/app/spatial.py):
  - Mengadopsi `meters_per_degree()` dan `area_m2()` WGS84 lokal dari `topology_resolver.py`.
  - Mengimplementasikan `polys_only()` untuk mengeliminasi irisan titik/garis/koleksi non-poligon.
  - Merefaktor `detect_overlaps()` murni pada poligon irisan 2D $\ge 1.0\text{ m}^2$.
  - Merefaktor `detect_gaps()`: menghapus tuntas Metode 2 (buffer closing), hanya mendeteksi interior rings (lubang tertutup) $\ge 1.0\text{ m}^2$ setara aturan QGIS *Must Not Have Gaps*.
- [x] **Langkah 4**: Sinkronisasi selesai. Backend siap di-reload.

