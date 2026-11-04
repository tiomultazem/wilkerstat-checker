"""
=============================================================================
WilkerStat Checker — Dry Run Audit Penghitungan Titik Offside (Read-Only)
=============================================================================
Memeriksa status spasial titik bangunan terhadap poligon home SLS aslinya
tanpa melakukan modifikasi berkas apa pun (100% murni pengujian/penghitungan).

Penggunaan:
    rtk python dry_run.py
    rtk python dry_run.py --points "00-identify dots/titik sebelum identifikasi.geojson"
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from shapely.geometry import shape as shapely_shape, Point
from shapely.ops import unary_union

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_POINTS = os.path.join(BASE_DIR, "00-identify dots", "titik hasil identifikasi.geojson")
if not os.path.exists(DEFAULT_POINTS):
    DEFAULT_POINTS = os.path.join(BASE_DIR, "00-identify dots", "titik sebelum identifikasi.geojson")

DEFAULT_POLY = os.path.join(BASE_DIR, "00-identify dots", "slsmentah fixed-2025sm1.geojson")


def load_polygons(poly_path: str) -> dict:
    print(f"[1/3] Membaca poligon batas SLS dari: {os.path.basename(poly_path)}...", end=" ", flush=True)
    t0 = time.time()
    with open(poly_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    poly_map = {}
    sls_geoms = defaultdict(list)
    for feat in data.get("features", []):
        props = feat.get("properties") or {}
        geom_json = feat.get("geometry")
        if not geom_json:
            continue
        try:
            geom = shapely_shape(geom_json)
            if not geom.is_valid:
                geom = geom.buffer(0)
        except Exception:
            continue

        idsub = str(props.get("idsubsls") or "").strip()
        idsls = str(props.get("idsls") or (idsub[:14] if len(idsub) >= 14 else "")).strip()

        if idsub:
            poly_map[idsub] = geom
        if idsls:
            sls_geoms[idsls].append(geom)

    for idsls, glist in sls_geoms.items():
        if len(glist) == 1:
            poly_map[idsls] = glist[0]
        elif len(glist) > 1:
            try:
                poly_map[idsls] = unary_union(glist)
            except Exception:
                poly_map[idsls] = glist[0]

    print(f"Selesai dalam {round(time.time() - t0, 2)}s ({len(poly_map):,} poligon terindeks).")
    return poly_map


def run_dry_run(points_path: str, poly_path: str):
    print("=" * 70)
    print("        DRY RUN AUDIT PENGHITUNGAN TITIK OFFSIDE (READ-ONLY)")
    print("=" * 70)
    print(f"  Berkas Titik   : {points_path}")
    print(f"  Berkas Poligon : {poly_path}")
    print("=" * 70)

    if not os.path.exists(points_path):
        print(f"[ERROR] Berkas titik tidak ditemukan: {points_path}")
        sys.exit(1)

    if not os.path.exists(poly_path):
        print(f"[ERROR] Berkas poligon tidak ditemukan: {poly_path}")
        sys.exit(1)

    poly_map = load_polygons(poly_path)

    print(f"[2/3] Membaca dan menganalisis titik dari: {os.path.basename(points_path)}...", end=" ", flush=True)
    t0 = time.time()
    with open(points_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Selesai ({len(data.get('features', [])):,} titik dimuat).")

    print("[3/3] Mengevaluasi posisi spasial setiap titik terhadap poligon asalnya...\n")

    total_points = 0
    count_inside = 0
    count_offside = 0
    count_unmapped_sls = 0
    count_invalid_geom = 0

    has_model3_flag = False
    model3_mismatch = 0

    offside_by_subdistrict = defaultdict(int)
    offside_by_sls = defaultdict(int)

    for feat in data.get("features", []):
        total_points += 1
        props = feat.get("properties") or {}
        geom = feat.get("geometry")

        home_id = str(props.get("level_6_full_code") or props.get("idsubsls_origin") or props.get("idsubsls") or "").strip()

        # Ambil koordinat
        coords = geom.get("coordinates") if geom else None
        if not coords or len(coords) < 2:
            lat = props.get("geotag_latitude") or props.get("latitude_origin")
            lon = props.get("geotag_longitude") or props.get("longitude_origin")
            if lat is not None and lon is not None:
                try:
                    pt = Point(float(lon), float(lat))
                except Exception:
                    count_invalid_geom += 1
                    continue
            else:
                count_invalid_geom += 1
                continue
        else:
            try:
                pt = Point(float(coords[0]), float(coords[1]))
            except Exception:
                count_invalid_geom += 1
                continue

        # Evaluasi terhadap poligon SLS asal (SubSLS 16-digit maupun home SLS 14-digit)
        poly = poly_map.get(home_id)
        sls_poly = poly_map.get(home_id[:14]) if len(home_id) >= 14 else None

        if poly is None and sls_poly is None:
            count_unmapped_sls += 1
            is_inside = False
        else:
            is_inside = (poly is not None and (poly.contains(pt) or poly.intersects(pt))) or \
                        (sls_poly is not None and (sls_poly.contains(pt) or sls_poly.intersects(pt)))

        # Cek apakah ada flag_repair bawaan (dari Model3)
        if "flag_repair" in props:
            has_model3_flag = True
            m3_flag = str(props.get("flag_repair")).strip()
            # Model3: 0 = inside, 1 = offside
            expected_flag = "0" if is_inside else "1"
            if m3_flag != expected_flag:
                model3_mismatch += 1

        if is_inside:
            count_inside += 1
        else:
            count_offside += 1
            kec_code = home_id[:7] if len(home_id) >= 7 else "LAINNYA"
            offside_by_subdistrict[kec_code] += 1
            offside_by_sls[home_id] += 1

    pct_inside = (count_inside / total_points * 100) if total_points else 0
    pct_offside = (count_offside / total_points * 100) if total_points else 0

    print("=" * 70)
    print("                     HASIL DRY RUN EVALUASI SPASIAL")
    print("=" * 70)
    print(f"  Total Titik Dievaluasi      : {total_points:>8,}")
    print(f"  ✓ Sesuai Home SLS (INSIDE)  : {count_inside:>8,}  ({pct_inside:.2f}%)  -> HARAM DIGESER")
    print(f"  ✗ Di Luar Home SLS (OFFSIDE): {count_offside:>8,}  ({pct_offside:.2f}%)  -> TARGET REPOSISI")
    if count_unmapped_sls > 0:
        print(f"    - Dari offside, SLS hilang: {count_unmapped_sls:>8,}")
    if count_invalid_geom > 0:
        print(f"    - Geometri rusak / null   : {count_invalid_geom:>8,}")

    if has_model3_flag:
        print("-" * 70)
        if model3_mismatch == 0:
            print("  ✓ [KONSISTENSI] Perhitungan Python 100% IDENTIK dengan flag Model3 QGIS!")
        else:
            print(f"  ! [PERBEDAAN] Ditemukan {model3_mismatch:,} titik berbeda toleransi batas vs Model3.")

    print("\n" + "-" * 70)
    print("  RINGKASAN TITIK OFFSIDE PER-KECAMATAN:")
    print("-" * 70)
    for kec, count in sorted(offside_by_subdistrict.items(), key=lambda x: x[1], reverse=True):
        print(f"    Kecamatan [{kec}] : {count:>6,} titik offside")

    print("\n" + "-" * 70)
    print("  TOP 5 SLS DENGAN TITIK OFFSIDE TERBANYAK:")
    print("-" * 70)
    top_sls = sorted(offside_by_sls.items(), key=lambda x: x[1], reverse=True)[:5]
    for sls_id, count in top_sls:
        print(f"    SLS [{sls_id}] : {count:>5,} titik offside")

    print("=" * 70)
    print("  STATUS: 100% READ-ONLY (TIDAK ADA BERKAS YANG DIUBAH)")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Dry Run Penghitungan Titik Offside")
    parser.add_argument("--points", default=DEFAULT_POINTS, help=f"Path berkas titik GeoJSON [default: {DEFAULT_POINTS}]")
    parser.add_argument("--poly", default=DEFAULT_POLY, help=f"Path berkas poligon SLS GeoJSON [default: {DEFAULT_POLY}]")

    args = parser.parse_args()
    run_dry_run(args.points, args.poly)


if __name__ == "__main__":
    main()

