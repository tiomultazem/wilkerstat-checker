# Indeks Rekam Jejak Audit Arsitektur (Architectural Decision Records)

Folder ini berfungsi sebagai repositori dokumen keputusan arsitektur resmi (*Architectural Decision Records / ADR*) proyek WilkerStat Checker SE2026. Seluruh berkas di sini mendokumentasikan akar masalah teknis, standar skema BPS, dan justifikasi perubahan kode.

---

## 1. Indeks Dokumen Audit

| Berkas Audit | Topik & Cakupan Rekayasa |
| :--- | :--- |
| [`audit aturan commit dan gitignore.md`](audit%20aturan%20commit%20dan%20gitignore.md) | Kebijakan version control Git: matriks berkas wajib commit (kode, template, docs) vs berkas dilarang commit (vektor raksasa, database runtime, log). |
| [`audit peleburan sls ke desa dan kecamatan.md`](audit%20peleburan%20sls%20ke%20desa%20dan%20kecamatan.md) | Desain dan spesifikasi teknis peleburan poligon SLS menjadi peta Desa (14 kolom BPS) dan Kecamatan (11 kolom BPS) Tabalong Semester 1 2026. |
| [`audit akar masalah titik terseret utara.md`](audit%20akar%20masalah%20titik%20terseret%20utara.md) | Forensik mendalam kegagalan pipeline reposisi titik: perbaikan bug non-union SubSLS, penghilangan atribut `flag_repair`, dan perancangan `bridge_repair.py`. |
| [`audit-restrukturisasi-folder.md`](audit-restrukturisasi-folder.md) | Rencana dan tahapan migrasi berkas dari penumpukan root ke modul terisolasi: `app/`, `00-identify dots/`, `01-move offside dots/`, dan `scripts/`. |
| [`audit-fitur-baru.md`](audit-fitur-baru.md) | Desain teknis antarmuka peta MapLibre GL: label teks SLS zoom-gated (level 11-16), pencarian containment cepat, dan efek blinking highlight tanpa pinpoint. |
| [`audit perapian repositori dan eliminasi hardcode.md`](audit%20perapian%20repositori%20dan%20eliminasi%20hardcode.md) | Audit perapian residu arsitektur, decluttering, eliminasi kode hardcode se-Indonesia, dan standardisasi repositori siap push. |

---

## 2. Aturan Pengelolaan

1. **Integritas Dokumen**: Dokumen berformat Markdown ini adalah bagian dari dokumentasi teknis kode sumber dan **wajib dilacak oleh Git** (dikeluarkan dari `.gitignore`).
2. **Bahasa & Etika**: Seluruh analisis wajib ditulis dengan standar formal, teknis, objektif, dan bebas dari kata-kata kasar.

