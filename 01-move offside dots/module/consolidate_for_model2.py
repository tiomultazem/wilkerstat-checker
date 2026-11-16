"""
Skrip Jembatan Konsolidasi Pra-QGIS Model 2.

Fungsi:
  1. Menggabungkan 131 berkas GeoJSON per desa (03-geotagging-edited/)
     menjadi 1 layer tunggal.
  2. Menambal titik-titik fallback dari moved_failed.geojson berdasarkan
     assignment_id (update geometri + atribut).
  3. KOREKSI MUTLAK: idsubsls_origin = level_6_full_code
  4. Mempertahankan seluruh kolom bawaan Model 1 (tidak ada yang di-drop).
  5. Menyimpan hasilnya ke titik_siap_model2.geojson siap di-load di QGIS.

Cara menjalankan (dari folder 01-move offside dots):
  rtk python module/consolidate_for_model2.py
  rtk python module/consolidate_for_model2.py --geotagging-dir "01 - data/03-geotagging-edited" --moved-failed "moved_failed.geojson" --output "../00-identify dots/titik_siap_model2.geojson"
"""

import argparse
import glob
import json
import os
import sys


# ─────────────────────────────────────────────────────────────────────────────
# Path default (relatif terhadap lokasi skrip ini)
# ─────────────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
_ROOT_DIR = os.path.abspath(os.path.join(_PIPELINE_DIR, ".."))

DEFAULT_GEOTAGGING_DIR = os.path.join(_PIPELINE_DIR, "01 - data", "03-geotagging-edited")
DEFAULT_MOVED_FAILED = os.path.join(_PIPELINE_DIR, "moved_failed.geojson")
DEFAULT_OUTPUT = os.path.join(_ROOT_DIR, "00-identify dots", "titik_siap_model2.geojson")


# ─────────────────────────────────────────────────────────────────────────────
# Fase 1: Muat seluruh berkas desa
# ─────────────────────────────────────────────────────────────────────────────
def load_geotagging_files(geotagging_dir: str) -> dict:
    """
    Memuat seluruh berkas *.geojson dari direktori 03-geotagging-edited.
    Mengembalikan dict: {assignment_id: feature_dict}
    """
    print(f"\n[Fase 1] Memuat berkas desa dari: {geotagging_dir}")
    pattern = os.path.join(geotagging_dir, "*.geojson")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"  [ERROR] Tidak ada berkas GeoJSON di direktori: {geotagging_dir}")
        sys.exit(1)

    print(f"  Ditemukan {len(files)} berkas desa.")

    feature_map = {}   # assignment_id -> feature
    dup_count = 0
    total_loaded = 0

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [Peringatan] Gagal membaca {os.path.basename(fpath)}: {e}")
            continue

        for feat in data.get("features", []):
            props = feat.get("properties") or {}
            aid = str(props.get("assignment_id") or "").strip()
            if not aid:
                continue
            if aid in feature_map:
                dup_count += 1
                # Ambil yang lebih baru / sudah diproses (berdasarkan keberadaan flag_repair=0)
                existing_repair = feature_map[aid].get("properties", {}).get("flag_repair", 1)
                new_repair = props.get("flag_repair", 1)
                if int(new_repair or 1) <= int(existing_repair or 1):
                    feature_map[aid] = feat
            else:
                feature_map[aid] = feat
                total_loaded += 1

    print(f"  Berhasil dimuat  : {total_loaded:,} fitur unik")
    if dup_count:
        print(f"  Duplikat diabaikan: {dup_count:,} (assignment_id sudah ada)")
    return feature_map


# ─────────────────────────────────────────────────────────────────────────────
# Fase 2: Tempel patch dari moved_failed.geojson
# ─────────────────────────────────────────────────────────────────────────────
def apply_moved_failed_patch(feature_map: dict, moved_failed_path: str) -> int:
    """
    Memperbarui geometri + atribut dari moved_failed.geojson untuk setiap
    assignment_id yang ada di feature_map.  Titik baru (tidak ada di map)
    juga ditambahkan.
    """
    if not os.path.exists(moved_failed_path):
        print(f"\n[Fase 2] Berkas moved_failed tidak ditemukan, dilewati: {moved_failed_path}")
        return 0

    print(f"\n[Fase 2] Menerapkan patch dari: {os.path.basename(moved_failed_path)}")

    with open(moved_failed_path, "r", encoding="utf-8") as f:
        mf_data = json.load(f)

    patched = 0
    added = 0
    for feat in mf_data.get("features", []):
        props = feat.get("properties") or {}
        aid = str(props.get("assignment_id") or "").strip()
        if not aid:
            continue

        if aid in feature_map:
            # Update geometri fisik dan atribut kunci reposisi
            feature_map[aid]["geometry"] = feat["geometry"]
            existing_props = feature_map[aid]["properties"]
            # Salin seluruh kunci dari moved_failed ke atribut base, tanpa overwrite
            # kunci yang nilainya kosong
            for k, v in props.items():
                if v is not None and str(v).strip() not in ("", "nan", "None"):
                    existing_props[k] = v
            patched += 1
        else:
            # Titik di moved_failed yang tidak ada di geotagging-edited (edge case)
            feature_map[aid] = feat
            added += 1

    print(f"  Titik diperbarui  : {patched:,}")
    if added:
        print(f"  Titik baru ditambah: {added:,} (tidak ada di 03-geotagging-edited)")
    return patched + added


# ─────────────────────────────────────────────────────────────────────────────
# Fase 3: Koreksi Mutlak idsubsls_origin = level_6_full_code
# ─────────────────────────────────────────────────────────────────────────────
def apply_idsubsls_origin_correction(feature_map: dict) -> int:
    """
    Menimpa idsubsls_origin dengan nilai level_6_full_code untuk setiap fitur.
    Ini adalah koreksi forensik inti yang memutus cacat warisan QGIS Model 1.
    """
    print("\n[Fase 3] Koreksi idsubsls_origin = level_6_full_code ...")

    corrected = 0
    already_correct = 0
    lvl6_missing = 0

    for aid, feat in feature_map.items():
        props = feat.get("properties") or {}
        lvl6 = str(props.get("level_6_full_code") or "").strip()

        if not lvl6 or lvl6 in ("nan", "None", "null"):
            lvl6_missing += 1
            continue

        current_origin = str(props.get("idsubsls_origin") or "").strip()
        if current_origin == lvl6:
            already_correct += 1
        else:
            props["idsubsls_origin"] = lvl6
            corrected += 1

    print(f"  Dikoreksi       : {corrected:,} titik (origin != level_6_full_code)")
    print(f"  Sudah benar     : {already_correct:,} titik")
    if lvl6_missing:
        print(f"  [Peringatan] level_6_full_code kosong: {lvl6_missing:,} titik — idsubsls_origin tidak disentuh")
    return corrected


# ─────────────────────────────────────────────────────────────────────────────
# Fase 4: Validasi Integritas Geometri
# ─────────────────────────────────────────────────────────────────────────────
def validate_geometry_integrity(feature_map: dict) -> int:
    """
    Memastikan setiap fitur memiliki geometri Point EPSG:4326 yang valid.
    Fitur tanpa geometri atau bukan Point dihapus dari map (dikembalikan
    sebagai jumlahnya).
    """
    print("\n[Fase 4] Validasi integritas geometri ...")
    invalid_keys = []
    for aid, feat in feature_map.items():
        geom = feat.get("geometry") or {}
        if geom.get("type") != "Point":
            invalid_keys.append(aid)
            continue
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            invalid_keys.append(aid)

    for k in invalid_keys:
        del feature_map[k]

    if invalid_keys:
        print(f"  [Peringatan] {len(invalid_keys):,} fitur dihapus karena geometri tidak valid (bukan Point).")
    else:
        print(f"  Semua {len(feature_map):,} fitur memiliki geometri Point valid.")
    return len(invalid_keys)


# ─────────────────────────────────────────────────────────────────────────────
# Fase 5: Simpan ke GeoJSON output
# ─────────────────────────────────────────────────────────────────────────────
def save_output(feature_map: dict, output_path: str):
    features = list(feature_map.values())
    fc = {
        "type": "FeatureCollection",
        "name": "titik_siap_model2",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": features
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Cek kunci berkas
    while True:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(fc, f, indent=2, ensure_ascii=False)
            break
        except (PermissionError, OSError) as e:
            print(f"\n  [PERINGATAN] Berkas terkunci: {output_path}")
            print("  Tutup berkas ini di QGIS atau editor lain, lalu tekan Enter.")
            jawab = input("  Tekan [Enter] atau ketik 'batal': ").strip().lower()
            if jawab in ("batal", "exit", "quit"):
                raise e

    print(f"\n  Output disimpan: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Fungsi utama
# ─────────────────────────────────────────────────────────────────────────────
def consolidate(geotagging_dir: str, moved_failed_path: str, output_path: str):
    print("=" * 65)
    print("  KONSOLIDASI PRA-QGIS MODEL 2")
    print("  Jembatan Pipeline Python → QGIS Model 2")
    print("=" * 65)

    # Fase 1: Muat desa
    feature_map = load_geotagging_files(geotagging_dir)

    # Fase 2: Patch moved_failed
    apply_moved_failed_patch(feature_map, moved_failed_path)

    # Fase 3: Koreksi identitas SLS
    apply_idsubsls_origin_correction(feature_map)

    # Fase 4: Validasi geometri
    validate_geometry_integrity(feature_map)

    # Fase 5: Simpan
    print(f"\n[Fase 5] Menyimpan {len(feature_map):,} fitur ...")
    save_output(feature_map, output_path)

    print("\n" + "=" * 65)
    print(f"  SELESAI — Total fitur: {len(feature_map):,}")
    print(f"  Output siap di-load ke QGIS Model 2:")
    print(f"  {output_path}")
    print("=" * 65)
    print("\n  LANGKAH SELANJUTNYA DI QGIS:")
    print("  1. Buka QGIS → Processing Toolbox → Model 2 (02 Pengecekan Titik)")
    print("  2. Input 'Titik Hasil Penggeseran'    = titik_siap_model2.geojson")
    print("  3. Input 'Peta Batas Wilkerstat Lama' = slsmentah fixed-2025sm1.geojson")
    print("  4. Jalankan → ekspor hasil ke GeoJSON / GPKG.\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def _parse_args():
    parser = argparse.ArgumentParser(
        description="Konsolidasi berkas per-desa untuk input QGIS Model 2."
    )
    parser.add_argument(
        "--geotagging-dir", default=DEFAULT_GEOTAGGING_DIR,
        help="Direktori berisi berkas GeoJSON per desa (03-geotagging-edited)."
    )
    parser.add_argument(
        "--moved-failed", default=DEFAULT_MOVED_FAILED,
        help="Path ke moved_failed.geojson (hasil reposisi fallback)."
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT,
        help="Path berkas output titik_siap_model2.geojson."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    consolidate(
        geotagging_dir=args.geotagging_dir,
        moved_failed_path=args.moved_failed,
        output_path=args.output,
    )

