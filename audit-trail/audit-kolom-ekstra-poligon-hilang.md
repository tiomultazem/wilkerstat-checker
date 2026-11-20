# AUDIT: Atribut Ekstra Poligon Hilang Setelah Upload-Download

**Tanggal Audit**: 2026-11-04  
**Auditor**: Antigravity  
**Status**: CONFIRMED — Root cause teridentifikasi 100% dari kode sumber  
**Confidence**: [certain] — bukti dari 3 file kode berbeda, bukan asumsi

---

## FAKTA PAHIT (Baca Ini Dulu)

> Atribut ekstra yang kamu upload **BUKAN hilang karena kesalahan sebelum upload**.  
> Sistem **sengaja membuangnya** — by design — sejak detik pertama file masuk.  
> Tidak ada bug. Ini perilaku yang dikodekan secara eksplisit.

---

## 1. Skema Pembuangan: 3 Lapis Berurutan

Sistem membuang atribut ekstra melalui **tiga lapisan berurutan** yang tidak ada satupun yang bisa dilewati tanpa modifikasi kode:

```
FILE UPLOAD (GeoJSON/SHP)
        │
        ▼
[ LAPIS 1 ] validate_shape.py:127–129
  Deteksi kolom ekstra → dicatat sebagai "note" → TIDAK diteruskan
        │
        ▼
[ LAPIS 2 ] validate_shape.py:432–441 _upsert_records()
  Hanya kolom dari shape_col.csv yang dimasukkan ke attrs JSON
        │
        ▼
[ DATABASE ] tabel `shape`, kolom `attrs` (JSON)
  Kolom ekstra TIDAK PERNAH tersimpan di sini
        │
        ▼
[ LAPIS 3 ] app.py:644–654
  Export membaca attrs JSON → hanya mengembalikan apa yang ada di DB
        │
        ▼
FILE DOWNLOAD (GeoJSON)
  Kolom ekstra = raib selamanya
```

---

## 2. Bukti Kode Per Lapis

### LAPIS 1 — Deteksi & Pembungkaman
**File**: [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py#L127-L129)

```python
# Baris 127–129
extra_cols = file_cols - spec_col_set
if extra_cols:
    result.note(f"Kolom ekstra diabaikan: {', '.join(sorted(extra_cols))}")
```

**Analisis**:
- `spec_col_set` = himpunan kolom dari `shape_col.csv`
- `file_cols - spec_col_set` = kolom di file yang **TIDAK ADA** di spec
- Sistem hanya mencatat ini sebagai `note` (bukan `warn`, bukan `reject`)
- `extra_cols` **tidak diteruskan ke mana pun** — variabel ini mati di sini
- `gdf` (GeoDataFrame) tetap mengandung kolom ekstra di memori, **tapi tidak digunakan**

### LAPIS 2 — Penyimpanan Selektif
**File**: [`app/validate_shape.py`](file:///c:/laragon\www\wilkerstat-checker\app\validate_shape.py#L432-L441)

```python
# Baris 432–441
attrs = {}
for col in spec_names:          # ← spec_names = HANYA kolom dari shape_col.csv
    if col in row.index:
        val = row[col]
        if isinstance(val, float) and math.isnan(val):
            val = None
        attrs[col] = val

attrs_json = json.dumps(attrs, ensure_ascii=False, default=str)
```

**Analisis**:
- Loop iterasi `spec_names` — bukan `row.index` (semua kolom di row)
- Kolom ekstra ada di `row.index` tapi **tidak pernah dicek** karena loop-nya bukan di sana
- `attrs_json` yang masuk ke DB = **hanya 34 kolom dari shape_col.csv**

### LAPIS 3 — Export Buta
**File**: [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py#L635-L654)

```python
# Baris 635–654
rows = conn.execute("""
    SELECT idsubsls, petugas, geom_wkb, attrs, label_x, label_y
    FROM shape WHERE geom_wkb IS NOT NULL
""").fetchall()

for r in rows:
    attrs = json.loads(r["attrs"]) if r["attrs"] else {}
    feat = {
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": {
            "idsubsls": r["idsubsls"],
            "petugas": r["petugas"],
            **{k: attrs.get(k, "") for k in ["nmkec","nmdesa","nmsls","kdsubsls","kdkec","kddesa","kdsls"]},
        }
    }
```

**Analisis**:
- Export bahkan lebih ketat dari DB — hanya mengambil **7 kolom hardcoded**: `nmkec`, `nmdesa`, `nmsls`, `kdsubsls`, `kdkec`, `kddesa`, `kdsls`
- Ini lebih kecil dari 34 kolom spec
- Kolom ekstra tidak mungkin muncul di sini karena bahkan tidak ada di `attrs` DB

---

## 3. Kolom yang Diakui Sistem (shape_col.csv)

Total **34 kolom** yang sah:

| # | Kolom | Tipe | Wajib? |
|---|-------|------|--------|
| 1 | `kk` | string | opsional |
| 2 | `gid` | integer | **wajib** |
| 3 | `ikn` | integer | opsional |
| 4 | `bstt` | string | opsional |
| 5 | `luas` | float | opsional |
| 6 | `bsbtt` | string | opsional |
| 7 | `idsls` | string | opsional |
| 8 | `kdprov` | string | **wajib** |
| 9 | `kdkab` | string | **wajib** |
| 10 | `kdkec` | string | **wajib** |
| 11 | `kddesa` | string | **wajib** |
| 12 | `kdsls` | string | **wajib** |
| 13 | `nmprov` | string | **wajib** |
| 14 | `nmkab` | string | **wajib** |
| 15 | `nmkec` | string | **wajib** |
| 16 | `nmdesa` | string | **wajib** |
| 17 | `nmsls` | string | **wajib** |
| 18 | `bstt_k` | string | opsional |
| 19 | `khusus` | string | opsional |
| 20 | `muatan` | string | opsional |
| 21 | `posisi` | string | opsional |
| 22 | `rw_dki` | string | opsional |
| 23 | `segmen` | string | opsional |
| 24 | `sumber` | string | opsional |
| 25 | `dom_sls` | string | opsional |
| 26 | `periode` | string | opsional |
| 27 | `tingkat` | string | opsional |
| 28 | `idsubsls` | string | **wajib** (kunci upsert) |
| 29 | `kdsubsls` | string | opsional |
| 30 | `nm_gedung` | string | opsional |
| 31 | `wil_campur` | string | opsional |
| 32 | `SSN26` | integer | opsional |
| 33 | `inset` | string | opsional |
| 34 | `petugas` | string | **wajib** |

**Kolom apapun di luar 34 ini = DIBUANG tanpa peringatan keras.**

---

## 4. Menjawab Pertanyaan Asli

> *"bila ada baris atribut baru yang tidak ada samsek di master, apakah dia akan terhapus?"*

**Jawaban**: **YA, pasti terhapus.** Bukan "baris" tapi "kolom" — dan sistem membuangnya di **Lapis 1** sebelum bahkan sampai ke database.

> *"atau karna kesalahan sebelum upload saja?"*

**Jawaban**: **BUKAN kesalahan sebelum upload.** File GeoJSON kamu kemungkinan sudah benar dan berisi kolom ekstra. Sistem yang menolak menyimpannya.

---

## 5. Solusi Eksekutabel

### Opsi A — Daftarkan kolom baru ke `shape_col.csv` (REKOMENDASI jika kolom permanen)

Tambahkan baris ke [`shape_col.csv`](file:///c:/laragon/www/wilkerstat-checker/shape_col.csv):
```
nama_kolom_baru,string,
```

Kemudian pastikan kode di `validate_shape.py` membaca ulang spec (sudah otomatis karena dibaca saat runtime).

**Efek**: Kolom tersebut akan:
1. Lolos Lapis 1 (tidak dianggap ekstra)
2. Tersimpan di `attrs` JSON (Lapis 2)
3. **Perlu modifikasi `app.py:653`** untuk ikut ter-export — karena export hardcoded hanya 7 kolom

### Opsi B — Export langsung dari GeoJSON asli (jika kolom ekstra hanya untuk keperluan luar)

Jangan andalkan sistem download app ini. Ekspor langsung dari file sumber sebelum upload, karena sistem ini **bukan archiver** — dia hanya menyimpan kolom yang dia kenal.

### Opsi C — Modifikasi `app.py` agar export semua kolom dari `attrs`

Ganti baris 653 di [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py#L653):
```python
# SEBELUM (hardcoded 7 kolom):
**{k: attrs.get(k, "") for k in ["nmkec","nmdesa","nmsls","kdsubsls","kdkec","kddesa","kdsls"]},

# SESUDAH (semua kolom di attrs):
**attrs,
```

Ini akan mengekspos semua kolom yang **sudah masuk ke attrs** — tapi tidak membantu untuk kolom yang belum terdaftar di `shape_col.csv`.

---

## 6. Urutan Prioritas Perbaikan

Jika kolom ekstra yang kamu upload memang perlu survive:

1. **Identifikasi** nama persis kolom ekstra yang kamu tambahkan
2. **Tambahkan** ke `shape_col.csv` (Opsi A)
3. **Modifikasi** `app.py:653` agar export ikut memasukkan kolom tersebut (Opsi C)
4. **Upload ulang** file GeoJSON — data lama yang sudah masuk DB tidak otomatis ter-update untuk kolom baru
5. **Download** dan verifikasi

Langkah 4 wajib karena DB sudah menyimpan `attrs` tanpa kolom ekstra — perlu upsert ulang setelah spec diperbarui.

---

## 7. Kesimpulan

| Pertanyaan | Jawaban |
|---|---|
| Apakah kolom ekstra terhapus? | **YA, 100%** |
| Kapan terhapus? | Saat upload, Lapis 1, sebelum masuk DB |
| Bug atau by design? | **By design** — kode eksplisit |
| Kesalahan sebelum upload? | **BUKAN** |
| Bisa diperbaiki? | **YA** — via shape_col.csv + modifikasi app.py |
| Data lama di DB bisa diselamatkan? | **TIDAK** — harus upload ulang setelah perbaikan |

---

## 8. Analisis Kritis: Key IDSUBSLS, Fallback GID, & Renumbering Otomatis

### 8.1. Mengapa Renumbering GID Menjadi Bencana Data
[certain] Auto-renumbering `gid` adalah **mutasi data destruktif**.
- `gid` merupakan foreign key implisit bawaan shapefile/geodatabase sumber.
- Jika `gid` diubah sepihak dari 1 hingga n:
  1. Relasi foreign key ke titik landmark/muatan di lapangan akan putus total.
  2. Jejak audit (audit trail) dan sinkronisasi kembali ke Wilkerstat Web/Mobile BPS menjadi mismatch permanen.
  3. Petugas tidak akan bisa melacak poligon mana yang bermasalah di file aslinya karena nomor baris/identitasnya sudah berubah.

### 8.2. Mengapa Fallback GID Membentur Skema Database Saat Ini
[certain] Pada tabel `shape` di [`app/database.py`](file:///c:/laragon/www/wilkerstat-checker/app/database.py#L108), terdapat constraint fisik:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_shape_idsubsls ON shape(idsubsls);
```
Sistem saat ini di [`app/validate_shape.py:444`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py#L444) mengecek:
```python
existing = conn.execute("SELECT geom_hash, attrs FROM shape WHERE idsubsls=?", (idsub,)).fetchone()
```
- Jika ada 2 poligon dengan `idsubsls` sama, poligon kedua akan **menimpa (overwrite)** poligon pertama melalui perintah `UPDATE`.
- Menerima duplikat `idsubsls` tanpa menimpanya secara langsung akan memicu pelanggaran `UNIQUE constraint failed: shape.idsubsls`.
- Oleh karena itu, skema database harus diperbarui terlebih dahulu jika ingin menampung poligon ber-`idsubsls` ganda.

### 8.3. Penanganan Baris Baru (Non-Master)
[certain] Kode validasi di `validate_shape.py` **TIDAK PERNAH** menghapus baris fitur hanya karena kodenya tidak terdaftar di `master_shape`.
- Semua baris yang memiliki geometri valid dan `idsubsls` terisi pasti dieksekusi `INSERT` ke tabel `shape` (baris 474).
- Baris baru non-master tampak "menghilang" saat didownload murni karena:
  1. **Tertimpa duplikasi**: Poligon baru memiliki `idsubsls` yang sama dengan poligon lain, sehingga tertimpa saat proses upsert.
  2. **Geometri kosong**: Geometri bernilai `NULL` / kosong sehingga tersaring oleh `WHERE geom_wkb IS NOT NULL` saat export di `app.py:637`.
  3. **Bukan barisnya yang hilang, melainkan atributnya**: Fiturnya ada di peta, tetapi kolom kustomnya kosong melompong karena dibuang oleh pembatasan 7 kolom export.

---

## 9. Rekomendasi Solusi Berkelanjutan (Best Practice)

1. **Gunakan Surrogate Key Internal**: Jadikan `id` autoincrement SQLite sebagai primary key mutlak untuk setiap entitas poligon.
2. **Lepas Constraint UNIQUE Fisik**: Ubah indeks `idx_shape_idsubsls` menjadi indeks biasa (non-unique) agar poligon dengan `idsubsls` ganda tetap bisa masuk berdampingan.
3. **Catat Error Atribut Tanpa Mengubah Data**: Bila `idsubsls` duplikat ditemukan, masukkan ke tabel `issue` (kategori: error atribut) dan pertahankan nilai `gid` asli apa adanya tanpa renumbering.
4. **Retensi Penuh Baris Non-Master**: Biarkan baris baru non-master tersimpan secara permanen di database dan ikut diekspor apa adanya.

---

## 10. Blueprint Teknis Eksekusi: Solusi Permanen Anti-Hilang (Baris & Kolom)

Berikut langkah operasional teknis presisi agar tidak ada lagi baris maupun atribut poligon yang hilang saat proses upload dan download.

### Langkah 1: Bebaskan Penyimpanan Kolom Ekstra di Ingestion
**Berkas**: [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py)  
**Tujuan**: Menjamin atribut di luar `shape_col.csv` tidak dibuang, melainkan disimpan utuh ke dalam JSON `attrs`.

Modifikasi fungsi `_upsert_records()` (sekitar baris 432–441):
```python
# SEBELUM:
attrs = {}
for col in spec_names:
    if col in row.index:
        val = row[col]
        if isinstance(val, float) and math.isnan(val):
            val = None
        attrs[col] = val

# SESUDAH (Menyerap seluruh kolom atribut yang ada di file sumber):
attrs = {}
for col in row.index:
    if col == "geometry":
        continue
    val = row[col]
    if isinstance(val, float) and math.isnan(val):
        val = None
    attrs[col] = val
```

### Langkah 2: Lepas Constraint UNIQUE Database agar Duplikat Tidak Menimpa Baris
**Berkas**: [`app/database.py`](file:///c:/laragon/www/wilkerstat-checker/app/database.py)  
**Tujuan**: Menghindari saling timpa (overwrite) atau crash saat ada baris ber-`idsubsls` ganda.

Modifikasi baris 108:
```sql
-- SEBELUM:
CREATE UNIQUE INDEX IF NOT EXISTS idx_shape_idsubsls ON shape(idsubsls);

-- SESUDAH:
CREATE INDEX IF NOT EXISTS idx_shape_idsubsls ON shape(idsubsls);
```

### Langkah 3: Modifikasi Logika Upsert untuk Mencegah Penghapusan / Penimpaan Baris
**Berkas**: [`app/validate_shape.py`](file:///c:/laragon/www/wilkerstat-checker/app/validate_shape.py)  
**Tujuan**: Jika ada `idsubsls` kembar dalam satu pengunggahan atau database, simpan keduanya sebagai baris terpisah dan tandai duplikasi sebagai issue atribut.

Modifikasi alur cek `existing` (sekitar baris 444–475):
- Jangan lakukan `UPDATE` yang menghapus data lama jika terdeteksi duplikasi tidak identik.
- Lakukan `INSERT` baris baru dengan mencatat issue ke tabel `issue` (`issue_type='duplicate_idsubsls'`).

### Langkah 4: Buka Kunci Ekspor Penuh di Endpoint Download
**Berkas**: [`app/app.py`](file:///c:/laragon/www/wilkerstat-checker/app/app.py)  
**Tujuan**: Mengeluarkan seluruh atribut yang tersimpan di `attrs` saat diekspor ke GeoJSON/SHP, bukan hanya 7 kolom hardcoded.

Modifikasi fungsi download poligon (baris 644–655):
```python
# SEBELUM:
attrs = json.loads(r["attrs"]) if r["attrs"] else {}
feat = {
    "type": "Feature",
    "geometry": mapping(geom),
    "properties": {
        "idsubsls": r["idsubsls"],
        "petugas": r["petugas"],
        "label_x": r["label_x"],
        "label_y": r["label_y"],
        **{k: attrs.get(k, "") for k in ["nmkec", "nmdesa", "nmsls", "kdsubsls", "kdkec", "kddesa", "kdsls"]},
    }
}

# SESUDAH:
attrs = json.loads(r["attrs"]) if r["attrs"] else {}
feat = {
    "type": "Feature",
    "geometry": mapping(geom),
    "properties": {
        **attrs,
        "idsubsls": r["idsubsls"],
        "petugas": r["petugas"],
        "label_x": r["label_x"],
        "label_y": r["label_y"],
    }
}
```

---

## 11. Matrix Status Solusi

| Masalah | Kondisi Saat Ini | Solusi Pasca Perbaikan |
|---|---|---|
| Kolom di luar `shape_col.csv` | Dibuang di Lapis 1 & 2 | Disimpan 100% ke `attrs` JSON |
| Kolom saat di-download | Dibatasi hardcoded 7 kolom | Seluruh kolom di `attrs` diekspor penuh |
| Poligon ber-`idsubsls` sama | Menimpa poligon pertama (UPDATE) | Keduanya tetap tersimpan (INSERT terpisah) + dicatat di issue |
| Baris non-master | Sudah tersimpan sejak awal | Tetap dipertahankan 100% |



