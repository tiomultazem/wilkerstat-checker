"""
WilkerStat Checker — Skrip Verifikasi Keselarasan Skema & Sinkronisasi Titik Spasial

Memeriksa integritas kolom, nilai statis, nilai null, serta melakukan sinkronisasi
(replace-in-place) dari moved_failed.geojson ke final_landmark_6309_se_2026.geojson.

Penggunaan:
    rtk python cekselaras.py --check                              (Default: Audit skema & integritas SLS)
    rtk python cekselaras.py --sync                               (Periksa dan sinkronisasi replacement titik)
    rtk python cekselaras.py --compare berkas_a.geojson berkas_b.geojson (Komparasi 2 berkas mandiri)
"""
import argparse
import json
import os
import shutil
import sys
from typing import Dict, List, Set, Any, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATH_RAW = os.path.join(BASE_DIR, "00-identify dots", "titik sebelum identifikasi.geojson")
PATH_FINAL = os.path.join(BASE_DIR, "01-move offside dots", "03 - final", "final_landmark_6309_se_2026.geojson")
PATH_MOVED = os.path.join(BASE_DIR, "01-move offside dots", "moved_failed.geojson")


def _get_aid(props: dict) -> str:
    """Ambil assignment_id atau id_assignment."""
    return str(props.get("assignment_id") or props.get("id_assignment") or "").strip()


def _get_level6_code(props: dict) -> Tuple[str, str]:
    """Mengambil kode 16-digit SLS/SubSLS dengan fallback dan nama kolom sumber."""
    for col in ("level_6_full_code", "idsubsls_origin", "idsubsls_edited", "idsls", "idsubsls"):
        val = props.get(col)
        if val is not None and str(val).strip() and str(val).strip().lower() not in ("none", "null", "nan"):
            return str(val).strip().replace(".0", ""), col
    return "", ""


def _is_null_or_empty(val: Any) -> bool:
    if val is None:
        return True
    s = str(val).strip().lower()
    return s in ("", "none", "nan", "null")


def load_geojson(filepath: str, label: str) -> dict:
    if not os.path.isfile(filepath):
        print(f"[ERROR] Berkas {label} tidak ditemukan: {filepath}")
        sys.exit(1)
    print(f"[INFO] Memuat {label} ({os.path.basename(filepath)})...", end=" ", flush=True)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Selesai ({len(data.get('features', []))} fitur)")
    return data


def check_level6_alignment(path_a: str, path_b: str, label_a: str = "Berkas A", label_b: str = "Berkas B") -> bool:
    """
    Modul mandiri untuk memverifikasi keselarasan assignment_id dan level_6_full_code
    (atau idsubsls_origin) antara dua berkas GeoJSON.
    """
    print("\n" + "=" * 65)
    print("      AUDIT KESELARASAN IDENTITAS SLS / LEVEL 6 FULL CODE")
    print(f"  Berkas A : {os.path.basename(path_a)}")
    print(f"  Berkas B : {os.path.basename(path_b)}")
    print("=" * 65)

    data_a = load_geojson(path_a, label_a)
    data_b = load_geojson(path_b, label_b)

    feats_a = data_a.get("features", [])
    feats_b = data_b.get("features", [])

    map_a: Dict[str, str] = {}
    col_a: Dict[str, str] = {}
    for f in feats_a:
        props = f.get("properties") or {}
        aid = _get_aid(props)
        if aid:
            code, col = _get_level6_code(props)
            map_a[aid] = code
            col_a[aid] = col

    map_b: Dict[str, str] = {}
    col_b: Dict[str, str] = {}
    for f in feats_b:
        props = f.get("properties") or {}
        aid = _get_aid(props)
        if aid:
            code, col = _get_level6_code(props)
            map_b[aid] = code
            col_b[aid] = col

    set_a = set(map_a.keys())
    set_b = set(map_b.keys())
    common = set_a.intersection(set_b)
    only_a = set_a - set_b
    only_b = set_b - set_a

    print(f"\n1. Ringkasan Kunci (assignment_id):")
    print(f"   - Total fitur A            : {len(feats_a):,}")
    print(f"   - Total fitur B            : {len(feats_b):,}")
    print(f"   - Irisan kunci (cocok)     : {len(common):,}")
    if only_a:
        print(f"   - Hanya di A (hilang di B) : {len(only_a):,}")
    if only_b:
        print(f"   - Hanya di B (hilang di A) : {len(only_b):,}")

    mismatches = []
    empty_a = 0
    empty_b = 0

    for aid in common:
        code_a = map_a[aid]
        code_b = map_b[aid]
        if not code_a:
            empty_a += 1
        if not code_b:
            empty_b += 1
        if code_a != code_b:
            mismatches.append((aid, code_a, col_a[aid], code_b, col_b[aid]))

    print(f"\n2. Verifikasi Nilai Kode SubSLS:")
    if empty_a:
        print(f"   ! Peringatan: {empty_a:,} fitur di A memiliki kode SLS kosong/null")
    if empty_b:
        print(f"   ! Peringatan: {empty_b:,} fitur di B memiliki kode SLS kosong/null")

    passed = (len(mismatches) == 0 and len(only_a) == 0 and len(only_b) == 0)

    if not mismatches:
        print(f"   ✓ [LULUS] 100% kode SubSLS ({len(common):,} titik) identik dan selaras.")
    else:
        print(f"   ✗ [GAGAL] Ditemukan {len(mismatches):,} titik dengan kode SubSLS berbeda!")
        print("   Contoh 5 ketidaksesuaian pertama:")
        for aid, ca, ca_col, cb, cb_col in mismatches[:5]:
            print(f"     - ID: {aid}")
            print(f"       A [{ca_col}]: '{ca}'")
            print(f"       B [{cb_col}]: '{cb}'")

    print("\n" + "=" * 65)
    if passed:
        print(">>> STATUS: KEDUA BERKAS 100% SELARAS")
    else:
        print(">>> STATUS: DITEMUKAN ANOMALI / KETIDAKSELARASAN")
    print("=" * 65 + "\n")

    return passed


def run_checks(raw_data: dict, final_data: dict, moved_data: dict) -> bool:
    raw_feats = raw_data.get("features", [])
    final_feats = final_data.get("features", [])
    moved_feats = moved_data.get("features", [])

    all_passed = True
    print("\n" + "=" * 65)
    print("        AUDIT KESELARASAN SKEMA & DATA TITIK SPASIAL")
    print("=" * 65)

    # -------------------------------------------------------------
    # UJI 1: Keselarasan Kolom (Schema Check)
    # -------------------------------------------------------------
    print("\n[UJI 1] Memeriksa Keselarasan Skema Kolom...")
    # 22 kolom baku Wilkerstat SE2026 (dot_col.csv)
    req_final_cols = [
        "assignment_id", "flag_repair", "flag_position", "idsubsls_origin", "idsubsls_edited",
        "latitude_origin", "longitude_origin", "latitude_edited", "longitude_edited",
        "no_bang", "kode_bang_value", "kdprov", "nmprov", "kdkab", "nmkab",
        "kdkec", "nmkec", "kddesa", "nmdesa", "idsls", "nmsls", "sls"
    ]
    req_moved_cols = [
        "assignment_id", "latitude_edited", "longitude_edited",
        "idsubsls_origin", "flag_position", "flag_repair"
    ]

    final_cols = set(final_feats[0]["properties"].keys()) if final_feats else set()
    moved_cols = set(moved_feats[0]["properties"].keys()) if moved_feats else set()

    missing_in_final = [c for c in req_final_cols if c not in final_cols and c != "assignment_id" or (c == "assignment_id" and "assignment_id" not in final_cols and "id_assignment" not in final_cols)]
    missing_in_moved = [c for c in req_moved_cols if c not in moved_cols and c != "assignment_id" or (c == "assignment_id" and "assignment_id" not in moved_cols and "id_assignment" not in moved_cols)]

    if not missing_in_final and not missing_in_moved:
        print("  ✓ [LULUS] Semua kolom baku Wilkerstat SE2026 (dot_col.csv) tersedia.")
    else:
        all_passed = False
        if missing_in_final:
            print(f"  ✗ [GAGAL] Kolom baku hilang di final_landmark: {missing_in_final}")
        if missing_in_moved:
            print(f"  ✗ [GAGAL] Kolom baku hilang di moved_failed: {missing_in_moved}")

    # -------------------------------------------------------------
    # UJI 2: Integritas Nilai Statis (Integrity Check vs Raw)
    # -------------------------------------------------------------
    print("\n[UJI 2] Memeriksa Integritas Nilai Statis Identitas vs Data Mentah...")
    raw_map = {}
    for f in raw_feats:
        props = f.get("properties", {})
        aid = _get_aid(props)
        if aid:
            raw_map[aid] = props

    static_mismatches = 0
    sample_mismatches = []

    for f in moved_feats:
        props = f.get("properties", {})
        aid = _get_aid(props)
        if not aid or aid not in raw_map:
            continue
        r_props = raw_map[aid]

        # Cocokkan level_6_full_code
        if str(props.get("level_6_full_code")) != str(r_props.get("level_6_full_code")):
            static_mismatches += 1
            sample_mismatches.append((aid, "level_6_full_code", props.get("level_6_full_code"), r_props.get("level_6_full_code")))
            continue

        # Cocokkan no_bang (toleransi integer vs string ber-zero padding)
        nb_moved = str(props.get("no_bang") or "").lstrip("0")
        nb_raw = str(r_props.get("no_bang") or "").lstrip("0")
        if nb_moved != nb_raw:
            static_mismatches += 1
            sample_mismatches.append((aid, "no_bang", props.get("no_bang"), r_props.get("no_bang")))

    final_static_mismatches = 0
    sample_final_mismatches = []
    for f in final_feats:
        props = f.get("properties", {})
        aid = _get_aid(props)
        if not aid or aid not in raw_map:
            continue
        r_props = raw_map[aid]

        raw_code = str(r_props.get("level_6_full_code") or r_props.get("idsubsls_origin") or "").strip().replace(".0", "")
        fin_code = str(props.get("idsubsls_origin") or props.get("level_6_full_code") or "").strip().replace(".0", "")

        if raw_code and fin_code and raw_code != fin_code:
            final_static_mismatches += 1
            sample_final_mismatches.append((aid, fin_code, raw_code))

    if static_mismatches == 0 and final_static_mismatches == 0:
        print(f"  ✓ [LULUS] Seluruh nilai SLS & statis di moved_failed dan master final identik dengan data mentah.")
    else:
        all_passed = False
        if static_mismatches > 0:
            print(f"  ✗ [GAGAL] Ditemukan {static_mismatches} ketidaksesuaian nilai statis di moved_failed.")
            for sm in sample_mismatches[:5]:
                print(f"    - ID: {sm[0]}, Kolom: {sm[1]}, Moved: '{sm[2]}' vs Raw: '{sm[3]}'")
        if final_static_mismatches > 0:
            print(f"  ✗ [GAGAL] Ditemukan {final_static_mismatches} ketidaksesuaian kode SLS di final_landmark!")
            for aid, fc, rc in sample_final_mismatches[:5]:
                print(f"    - ID: {aid}, Final: '{fc}' vs Raw: '{rc}'")

    # -------------------------------------------------------------
    # UJI 3: Nilai Kosong pada Kolom Algoritma (Nullity Check)
    # -------------------------------------------------------------
    print("\n[UJI 3] Memeriksa Kolom Algoritma yang Tidak Boleh Null / Kosong...")
    algo_cols = [
        "latitude_edited", "longitude_edited", "geotag_latitude", "geotag_longitude",
        "level_6_full_code", "idsubsls_origin", "flag_position"
    ]

    null_in_final = {c: 0 for c in algo_cols}
    null_in_moved = {c: 0 for c in algo_cols}

    for f in final_feats:
        props = f.get("properties", {})
        for c in algo_cols:
            if _is_null_or_empty(props.get(c)):
                null_in_final[c] += 1

    for f in moved_feats:
        props = f.get("properties", {})
        for c in algo_cols:
            if _is_null_or_empty(props.get(c)):
                null_in_moved[c] += 1

    total_null_final = sum(null_in_final.values())
    total_null_moved = sum(null_in_moved.values())

    if total_null_final == 0 and total_null_moved == 0:
        print("  ✓ [LULUS] Tidak ada nilai NULL pada seluruh kolom algoritma di kedua berkas.")
    else:
        if total_null_final > 0:
            print(f"  ! [PERINGATAN] Nilai kosong di final_landmark: { {k: v for k, v in null_in_final.items() if v > 0} }")
        if total_null_moved > 0:
            all_passed = False
            print(f"  ✗ [GAGAL] Nilai kosong ditemukan di moved_failed: { {k: v for k, v in null_in_moved.items() if v > 0} }")

    # -------------------------------------------------------------
    # UJI 4: Audit Jumlah Baris & Irisan Key (Subset Replacement)
    # -------------------------------------------------------------
    print("\n[UJI 4] Memeriksa Jumlah Baris & Ketercakupan Kunci (Key Coverage)...")
    final_aids = set(_get_aid(f.get("properties", {})) for f in final_feats)
    moved_aids = set(_get_aid(f.get("properties", {})) for f in moved_feats)

    matched_aids = moved_aids.intersection(final_aids)
    unmatched_aids = moved_aids - final_aids

    print(f"  - Total baris Data Mentah     : {len(raw_feats):,}")
    print(f"  - Total baris Final Master    : {len(final_feats):,}")
    print(f"  - Total baris Moved Failed    : {len(moved_feats):,}")
    print(f"  - Titik Moved cocok di Final  : {len(matched_aids):,} (100.0%)" if len(unmatched_aids) == 0 else f"  - Titik Moved cocok di Final: {len(matched_aids):,}")

    if len(unmatched_aids) == 0:
        print("  ✓ [LULUS] 100% subset titik moved_failed terpetakan ke dalam final_landmark.")
    else:
        all_passed = False
        print(f"  ✗ [GAGAL] Terdapat {len(unmatched_aids)} titik moved_failed yang TIDAK ADA di final_landmark.")

    print("\n" + "=" * 65)
    if all_passed:
        print(">>> HASIL KESELURUHAN: VALID & SELARAS 100% (SIAP DISINKRONKAN)")
    else:
        print(">>> HASIL KESELURUHAN: TERDAPAT ANOMALI (PERIKSA RINCIAN DI ATAS)")
    print("=" * 65 + "\n")

    return all_passed


def execute_sync(final_data: dict, moved_data: dict):
    print("[SINKRONISASI] Memulai proses replace-in-place titik moved_failed...")

    # Backup berkas master final terlebih dahulu
    backup_path = PATH_FINAL + ".bak"
    print(f"[INFO] Membuat salinan cadangan: {os.path.basename(backup_path)}...", end=" ", flush=True)
    shutil.copyfile(PATH_FINAL, backup_path)
    print("Selesai.")

    # Petakan moved_failed berdasarkan assignment_id
    moved_map = {}
    for f in moved_data.get("features", []):
        props = f.get("properties", {})
        aid = _get_aid(props)
        if aid:
            moved_map[aid] = f

    updated_count = 0
    final_feats = final_data.get("features", [])

    for f in final_feats:
        props = f.get("properties", {})
        aid = _get_aid(props)
        if aid in moved_map:
            moved_f = moved_map[aid]
            m_props = moved_f.get("properties", {})
            m_geom = moved_f.get("geometry", {})

            # 1. Update geometri spasial (koordinat titik hasil geser)
            f["geometry"] = m_geom

            # 2. Update koordinat atribut
            props["latitude_edited"] = m_props.get("latitude_edited")
            props["longitude_edited"] = m_props.get("longitude_edited")
            props["geotag_latitude"] = m_props.get("geotag_latitude")
            props["geotag_longitude"] = m_props.get("geotag_longitude")

            # 3. Tandai titik tergeser
            props["flag_position"] = 1

            # 4. Pastikan SLS origin & edited terisi
            if m_props.get("level_6_full_code"):
                props["level_6_full_code"] = m_props.get("level_6_full_code")
            if m_props.get("idsubsls_origin"):
                props["idsubsls_origin"] = m_props.get("idsubsls_origin")
            if m_props.get("idsubsls_edited"):
                props["idsubsls_edited"] = m_props.get("idsubsls_edited")

            # 5. Kolom muatan (kk, btt, dll.) tetap dipertahankan dari master final
            updated_count += 1

    print(f"[INFO] Menyimpan {len(final_feats)} fitur ke {os.path.basename(PATH_FINAL)}...", end=" ", flush=True)
    with open(PATH_FINAL, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False)
    print("Selesai.")

    print("\n" + "=" * 65)
    print(f"  SUKSES: {updated_count} titik di final_landmark berhasil digantikan!")
    print(f"  Berkas cadangan tersimpan di: {backup_path}")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Verifikasi Keselarasan & Sinkronisasi Titik Spasial")
    parser.add_argument("--sync", action="store_true", help="Jalankan audit dan eksekusi replace-in-place titik")
    parser.add_argument("--check", action="store_true", help="Hanya jalankan audit keselarasan skema (default)")
    parser.add_argument("--compare", nargs=2, metavar=("FILE_A", "FILE_B"), help="Bandingkan keselarasan assignment_id & level_6_full_code antara dua berkas GeoJSON")
    parser.add_argument("-a", "--file-a", help="Path berkas GeoJSON A")
    parser.add_argument("-b", "--file-b", help="Path berkas GeoJSON B")

    args = parser.parse_args()

    # Evaluasi mode komparasi mandiri dua berkas
    target_a = None
    target_b = None
    if args.compare:
        target_a, target_b = args.compare[0], args.compare[1]
    elif args.file_a and args.file_b:
        target_a, target_b = args.file_a, args.file_b

    if target_a and target_b:
        check_level6_alignment(target_a, target_b)
        return

    raw_data = load_geojson(PATH_RAW, "Data Mentah Awal")
    final_data = load_geojson(PATH_FINAL, "Final Landmark Master")
    moved_data = load_geojson(PATH_MOVED, "Moved Failed Dots")

    valid = run_checks(raw_data, final_data, moved_data)

    if args.sync:
        if not valid:
            print("[PERINGATAN] Audit menemukan anomali. Apakah tetap ingin melanjutkan sinkronisasi? Batalkan jika ragu.")
        execute_sync(final_data, moved_data)
    else:
        print("[PETUNJUK] Untuk mengeksekusi penggabungan / replacement, jalankan:")
        print("  rtk python cekselaras.py --sync")
        print("\nUntuk membandingkan dua berkas GeoJSON secara mandiri:")
        print("  rtk python cekselaras.py --compare berkas_a.geojson berkas_b.geojson")


if __name__ == "__main__":
    main()

