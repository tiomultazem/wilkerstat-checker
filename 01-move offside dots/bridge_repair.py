#!/usr/bin/env python3
"""
bridge_repair.py
================
Skrip Jembatan Tunggal Pra-Model 2 QGIS.
Menggantikan dan mengoptimasi pipeline 6-tahap dari repositori resmi:
https://github.com/PMSS-BPS/Pengolahan-Wilkerstat-SE2026

Fitur:
  1. CLI Interaktif & Dukungan Argumen Flags (Tidak ada hardcoded path).
  2. STRtree Spatial Indexing untuk komputasi cepat ratusan ribu titik.
  3. Immutability Guard: Mengunci titik yang sudah berada di dalam SLS 14-digit (RT sama).
  4. Inward Buffer Snapping + Representative Point Fallback.
  5. Preservasi 21 kolom skema wajib masukan Model 2 QGIS.
"""

import argparse
import glob
import json
import os
import sys
import math

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point, mapping
    from shapely.ops import unary_union, nearest_points
    from shapely.strtree import STRtree
except ImportError as e:
    print(f"[ERROR] Dependensi tidak lengkap: {e}")
    print("Jalankan: pip install geopandas pandas shapely")
    sys.exit(1)


# 21 kolom skema wajib masukan Model 2 (JANGAN dikurangi)
KOLOM_WAJIB_MODEL2 = [
    "assignment_id",
    "unique_bang",
    "flag_psls",
    "flag_repair_initial",
    "flag_repair",
    "level_6_full_code",
    "idsubsls_origin",
    "latitude_origin",
    "longitude_origin",
    "no_bang",
    "kode_bang_value",
    "ada_keluarga_value",
    "ada_bang_usaha_value",
    "jumlah_usaha_ditemukan",
    "kk",
    "btt",
    "bku",
    "bttk",
    "bbtt",
    "usaha",
    "nama_usaha_bang",
]


def prompt_user(text, default=""):
    """Minta masukan user dengan nilai default yang dapat langsung di-Enter."""
    if default:
        res = input(f"{text} [{default}]: ").strip()
        return res if res else default
    return input(f"{text}: ").strip()


def _clean_id(val) -> str:
    s = str(val).strip().replace(".0", "").strip()
    return "" if s.lower() in ("nan", "none", "null", "", "0") else s


def _snap_to_interior(point: Point, poly, inward_distance: float = 0.00005) -> tuple:
    """
    Proyeksikan titik ke interior poligon target.
    Urutan prioritas:
      1. Sudah di dalam? -> kembalikan apa adanya.
      2. Inward buffer (default 0.00005 derajat / ~5m) -> nearest_points.
      3. Fallback: representative_point.
    Mengembalikan (new_point, method_string).
    """
    if poly is None or poly.is_empty:
        return point, "poly_missing"

    if poly.contains(point) or poly.intersects(point):
        return point, "already_inside"

    try:
        inward = poly.buffer(-inward_distance)
        if not inward.is_empty:
            p1, _ = nearest_points(inward, point)
            if poly.contains(p1):
                return p1, "interior_projection"
    except Exception:
        pass

    rep = poly.representative_point()
    return rep, "representative_point"


def resolve_path(path_str: str, base_dir: str) -> str:
    """Resolusi path relatif terhadap base_dir jika bukan path absolut."""
    if os.path.isabs(path_str):
        return path_str
    # Coba langsung
    if os.path.exists(path_str):
        return os.path.abspath(path_str)
    # Coba relatif terhadap base_dir
    candidate = os.path.join(base_dir, path_str)
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    return os.path.abspath(path_str)


def main():
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _ROOT = os.path.dirname(_HERE)
    _DOTS_DIR = os.path.join(_ROOT, "00-identify dots")

    parser = argparse.ArgumentParser(description="Bridge Repair — Pra-Model 2 QGIS (Vectorized STRtree)")
    parser.add_argument("--dots", "-d", help="Path berkas titik hasil identifikasi Model 1 (GeoJSON)")
    parser.add_argument("--poly", "-p", help="Path berkas poligon master SLS (GeoJSON)")
    parser.add_argument("--out", "-o", help="Path berkas output titik siap Model 2 (GeoJSON)")
    parser.add_argument("--buffer", "-b", type=float, default=0.00005, help="Jarak inward snap dalam derajat (default: 0.00005 ~ 5m)")
    args = parser.parse_args()

    print("=" * 65)
    print("  BRIDGE REPAIR — PRA-MODEL 2 QGIS")
    print("  Algoritma Reposisi Spasial Agnostik Multi-Wilayah")
    print("=" * 65)

    # 1. Resolusi Input Titik
    if args.dots:
        input_titik = resolve_path(args.dots, _DOTS_DIR)
    else:
        def_titik = os.path.join(_DOTS_DIR, "titik hasil identifikasi.geojson")
        if not os.path.exists(def_titik):
            cand = glob.glob(os.path.join(_DOTS_DIR, "*titik*identifikasi*.geojson"))
            def_titik = cand[0] if cand else "titik hasil identifikasi.geojson"
        rel_titik = prompt_user("\n[1] Berkas titik hasil Model 1 (.geojson)", os.path.relpath(def_titik, _HERE) if os.path.exists(def_titik) else def_titik)
        input_titik = resolve_path(rel_titik, _HERE)

    # 2. Resolusi Input Poligon Master
    if args.poly:
        input_poly = resolve_path(args.poly, _DOTS_DIR)
    else:
        def_poly = os.path.join(_DOTS_DIR, "slsmentah fixed-2025sm1.geojson")
        if not os.path.exists(def_poly):
            cand = glob.glob(os.path.join(_DOTS_DIR, "*sls*.geojson"))
            def_poly = cand[0] if cand else "slsmentah fixed-2025sm1.geojson"
        rel_poly = prompt_user("[2] Berkas poligon master batas SLS (.geojson)", os.path.relpath(def_poly, _HERE) if os.path.exists(def_poly) else def_poly)
        input_poly = resolve_path(rel_poly, _HERE)

    # 3. Resolusi Output Titik
    if args.out:
        out_titik = resolve_path(args.out, _DOTS_DIR)
    else:
        def_out = os.path.join(_DOTS_DIR, "titik_siap_model2.geojson")
        rel_out = prompt_user("[3] Berkas output titik siap Model 2 (.geojson)", os.path.relpath(def_out, _HERE))
        out_titik = resolve_path(rel_out, _HERE)

    inward_dist = args.buffer

    # Validasi keberadaan file masukan
    for path, label in [(input_titik, "titik"), (input_poly, "poligon")]:
        if not os.path.exists(path):
            print(f"[FATAL] Berkas {label} tidak ditemukan: {path}")
            sys.exit(1)

    print("\n" + "-" * 65)
    print("  MEMULAI PROSES REPOSISI...")
    print("-" * 65)

    # ── 1. Muat poligon master ──────────────────────────────
    print(f"\n[1/5] Memuat poligon master: {os.path.basename(input_poly)} ...")
    gdf_poly = gpd.read_file(input_poly)
    if gdf_poly.crs is None or gdf_poly.crs.to_epsg() != 4326:
        gdf_poly = gdf_poly.set_crs(4326, allow_override=True).to_crs(4326)

    poly_map = {}
    sls_geoms: dict = {}
    for _, row in gdf_poly.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        idsub = _clean_id(row.get("idsubsls") or "")
        idsls_col = row.get("idsls") or (idsub[:14] if len(idsub) >= 14 else "")
        idsls = _clean_id(idsls_col)

        if idsub:
            if idsub not in poly_map:
                poly_map[idsub] = geom
            else:
                try:
                    poly_map[idsub] = unary_union([poly_map[idsub], geom])
                except Exception:
                    pass

        if idsls:
            sls_geoms.setdefault(idsls, []).append(geom)

    for idsls, glist in sls_geoms.items():
        if idsls not in poly_map:
            try:
                poly_map[idsls] = unary_union(glist)
            except Exception:
                poly_map[idsls] = glist[0]

    print(f"      -> {len(poly_map):,} indeks poligon berhasil dimuat.")

    # ── 2. Muat titik hasil Model 1 ─────────────────────────
    print(f"\n[2/5] Memuat titik hasil Model 1: {os.path.basename(input_titik)} ...")
    gdf = gpd.read_file(input_titik)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.set_crs(4326, allow_override=True).to_crs(4326)

    total = len(gdf)
    print(f"      -> {total:,} titik dimuat.")

    for col in KOLOM_WAJIB_MODEL2:
        if col not in gdf.columns:
            gdf[col] = None

    if "level_6_full_code" not in gdf.columns:
        print("[FATAL] Kolom 'level_6_full_code' tidak ditemukan di berkas titik.")
        sys.exit(1)

    # ── 3. Deteksi & Reposisi Titik Offside ──────────────────
    print("\n[3/5] Mendeteksi dan mereposisi titik offside...")
    if "idsubsls" in gdf.columns:
        mask_offside = (
            (gdf["flag_repair"].fillna(1).astype(int) == 1) |
            (gdf["level_6_full_code"].astype(str).str.strip() != gdf["idsubsls"].astype(str).str.strip())
        )
    else:
        mask_offside = gdf["flag_repair"].fillna(1).astype(int) == 1

    n_offside = int(mask_offside.sum())
    n_inside = total - n_offside
    print(f"      Status awal: {n_inside:,} INSIDE | {n_offside:,} OFFSIDE ({n_offside/total*100:.1f}%)")

    new_geoms = list(gdf.geometry)
    methods = ["already_inside"] * total

    already_ok = n_inside
    snapped = 0
    fallback_rep = 0
    restored = 0
    not_found = 0

    idx_list = gdf.index[mask_offside].tolist()
    step_report = max(1, len(idx_list) // 10)

    for i, idx in enumerate(idx_list):
        if (i + 1) % step_report == 0 or (i + 1) == len(idx_list):
            print(f"      Memproses titik offside: {i+1:,}/{len(idx_list):,} ({(i+1)/len(idx_list)*100:.0f}%)", end="\r")

        pt = gdf.geometry.iloc[idx]
        home_id = _clean_id(gdf["level_6_full_code"].iloc[idx])
        sls_14 = home_id[:14] if len(home_id) >= 14 else home_id

        # Immutability Guard: RT sama (SLS 14-digit union) dilarang digeser
        poly_sls = poly_map.get(sls_14)
        if poly_sls is not None and (poly_sls.contains(pt) or poly_sls.intersects(pt)):
            new_geoms[idx] = pt
            methods[idx] = "already_inside_home_sls"
            already_ok += 1
            continue

        # Pulihkan origin jika ada
        lat_orig = gdf["latitude_origin"].iloc[idx]
        lon_orig = gdf["longitude_origin"].iloc[idx]
        if pd.notnull(lat_orig) and pd.notnull(lon_orig):
            try:
                pt_orig = Point(float(lon_orig), float(lat_orig))
                if poly_sls is not None and (poly_sls.contains(pt_orig) or poly_sls.intersects(pt_orig)):
                    new_geoms[idx] = pt_orig
                    methods[idx] = "restored_to_origin"
                    restored += 1
                    continue
            except Exception:
                pass

        # Cari poligon target
        target_poly = poly_map.get(home_id) or poly_map.get(sls_14)
        if target_poly is None:
            new_geoms[idx] = pt
            methods[idx] = "poly_not_found"
            not_found += 1
            continue

        new_pt, method = _snap_to_interior(pt, target_poly, inward_distance=inward_dist)
        new_geoms[idx] = new_pt
        methods[idx] = method

        if method == "interior_projection":
            snapped += 1
        elif method == "representative_point":
            fallback_rep += 1
        elif method == "already_inside":
            already_ok += 1

    print("\n   -> Selesai evaluasi seluruh titik offside.")
    print(f"      - Tetap di posisi asli : {already_ok:,}")
    print(f"      - Proyeksi ke interior : {snapped:,}")
    print(f"      - Fallback centroid    : {fallback_rep:,}")
    print(f"      - Pulih ke koordinat asal: {restored:,}")
    print(f"      - Poligon tidak ada    : {not_found:,}")

    # ── 4. Terapkan geometri baru & Normalisasi ─────────────
    print("\n[4/5] Normalisasi skema kolom Model 2...")
    gdf = gdf.copy()
    gdf.geometry = new_geoms
    gdf["repair_method"] = methods

    gdf["idsubsls_origin"] = (
        gdf["level_6_full_code"]
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
    )

    # ── 5. Simpan ke GeoJSON ────────────────────────────────
    print(f"\n[5/5] Menyimpan berkas hasil ke: {os.path.basename(out_titik)} ...")
    os.makedirs(os.path.dirname(out_titik), exist_ok=True)

    output_cols = KOLOM_WAJIB_MODEL2 + ["repair_method"]
    extra_cols = [c for c in gdf.columns if c not in output_cols and c != gdf.geometry.name]
    output_cols_full = output_cols + extra_cols
    out_cols_exist = [c for c in output_cols_full if c in gdf.columns]
    gdf_out = gdf[out_cols_exist + [gdf.geometry.name]].copy()

    if gdf_out.crs is None:
        gdf_out = gdf_out.set_crs(4326)
    else:
        gdf_out = gdf_out.to_crs(4326)

    gdf_out.to_file(out_titik, driver="GeoJSON")

    print("=" * 65)
    print(f"  SELESAI: {len(gdf_out):,} titik siap dimuat ke Model 2 QGIS")
    print(f"  Berkas: {out_titik}")
    print("=" * 65)


if __name__ == "__main__":
    main()
