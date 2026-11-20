# Audit Penyesuaian UI Halaman Aktivasi Lisensi
**Dibuat:** 2026-10-30

---

## 1. Latar Belakang & Masalah
Pada halaman aktivasi lisensi (`templates/license_locked.html`), sebelumnya terdapat tampilan Hardware ID (`hwid-box`) untuk mode dev jika satker bernilai `6309`. Tampilan ini tidak relevan dan membingungkan bagi pengguna akhir/satker. Selain itu, footer halaman masih menggunakan teks default yang kaku (*Sistem Lisensi Terpusat Badan Pusat Statistik © 2026*).

---

## 2. Solusi Perubahan
1. **Penghapusan Tampilan Hardware ID**:
   - Menghapus blok kondisional dev `hwid-box` yang menampilkan string panjang Hardware ID.
   - Menggantinya dengan kartu panduan prosedur berstruktur rapi (`license-info-card`):
     - Judul: *Butuh Token Lisensi?*
     - Keterangan: *Token lisensi disediakan gratis untuk Satker BPS melalui prosedur berikut:*
     - Langkah 1: *Kirimkan surat permohonan resmi atas nama Satker via email dinas.*
     - Langkah 2: *Konfirmasikan melalui chat agar segera diverifikasi dan diterbitkan.*
2. **Pembaruan Hak Cipta & Atribusi Footer**:
   - Mengubah teks hak cipta pada `.license-footer` menjadi:
     > *"2026 made with ❤️, Gilang Wahyu Prasetyo © BPS Kabupaten Tabalong."*

---

## 3. Berkas yang Diubah
- `templates/license_locked.html`

