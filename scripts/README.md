# Modul Skrip Utilitas & Pemeliharaan: `scripts/`

Direktori ini memuat skrip-skrip utilitas CLI (*Command Line Interface*) untuk pemeliharaan data dan operasi ad-hoc di luar aplikasi web utama.

---

## 1. Daftar Skrip & Penggunaan

| Skrip | Fungsi Teknis | Cara Menjalankan |
| :--- | :--- | :--- |
| `clear_dots.py` | Mengosongkan seluruh data tabel titik (`dot`), statistik geotagging petugas, dan master titik di basis data SQLite tanpa menghapus struktur tabel atau data poligon SLS. Digunakan saat reset data titik sebelum reload survei baru. | `rtk python scripts/clear_dots.py` |
| `split.py` | Memecah berkas GeoJSON poligon besar menjadi berkas-berkas terpisah berdasarkan atribut nama kecamatan (`nmkec`). Luaran disimpan di folder `split/`. | `rtk python scripts/split.py <jalur_file.geojson>` |

---

## 2. Catatan Penggunaan

Seluruh skrip di folder ini secara dinamis mengenali struktur root proyek dan modul `app/` melalui injeksi `sys.path`. Skrip dapat dieksekusi dari direktori root proyek.

