"""
Modul Reposisi Titik Gagal / Offside Masuk ke Dalam Poligon SLS (Interior Projection).
Murni memproses dan menyimpan berkas GeoJSON tanpa menyentuh basis data.
"""
import glob
import json
import os
import sys
from collections import defaultdict
from shapely.geometry import shape as shapely_shape, Point, mapping
from shapely.ops import nearest_points, unary_union


def _index_features_from_geojson(geojson_path: str, poly_map: dict, sls_geoms: dict) -> int:
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"   [Peringatan] Gagal membaca {os.path.basename(geojson_path)}: {e}")
        return 0

    added = 0
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
            added += 1
        if idsls:
            sls_geoms[idsls].append(geom)

    return added


def load_polygons(poly_source: str) -> dict:
    if not os.path.exists(poly_source):
        raise FileNotFoundError(f"Sumber poligon tidak ditemukan: {poly_source}")

    poly_map = {}
    sls_geoms = defaultdict(list)

    if os.path.isdir(poly_source):
        print(f"1. Memuat poligon dari direktori split: {poly_source}...")
        pattern = os.path.join(poly_source, "**", "*.geojson")
        files = glob.glob(pattern, recursive=True)
        if not files:
            pattern = os.path.join(poly_source, "*.geojson")
            files = glob.glob(pattern)

        print(f"   Ditemukan {len(files)} berkas GeoJSON split.")
        for fpath in files:
            _index_features_from_geojson(fpath, poly_map, sls_geoms)
    else:
        print(f"1. Memuat poligon dari berkas tunggal: {os.path.basename(poly_source)}...")
        _index_features_from_geojson(poly_source, poly_map, sls_geoms)

    for idsls, glist in sls_geoms.items():
        if len(glist) == 1:
            poly_map[idsls] = glist[0]
        elif len(glist) > 1:
            try:
                poly_map[idsls] = unary_union(glist)
            except Exception:
                poly_map[idsls] = glist[0]

    print(f"   -> {len(poly_map)} indeks poligon SLS/Sub-SLS siap.")
    return poly_map


def move_failed_points(failed_file: str, poly_source: str, out_file: str):
    print("=" * 60)
    print("  REPOSISI TITIK GAGAL (INTERIOR PROJECTION)")
    print("=" * 60)

    if not os.path.exists(failed_file):
        print(f"[ERROR] Berkas titik gagal tidak ditemukan: {failed_file}")
        return False

    if not os.path.exists(poly_source):
        print(f"[ERROR] Sumber poligon tidak ditemukan: {poly_source}")
        return False

    poly_map = load_polygons(poly_source)
    if not poly_map:
        print("[ERROR] Tidak ada poligon yang berhasil dimuat.")
        return False

    print(f"\n2. Membaca titik gagal dari {os.path.basename(failed_file)}...")
    with open(failed_file, "r", encoding="utf-8") as f:
        failed_data = json.load(f)

    features = failed_data.get("features", [])
    print(f"   -> Memproses {len(features)} titik...")

    moved_count = 0
    restored_count = 0
    not_found_count = 0

    for feat in features:
        props = feat.get("properties") or {}
        # Multi-tier fallback untuk target_id agar tidak pernah kosong
        target_id = ""
        for cand in [props.get("level_6_full_code"), props.get("idsubsls_origin"), props.get("idsubsls_edited"), props.get("idsls"), props.get("idsubsls")]:
            s_cand = str(cand or "").strip().replace(".0", "")
            if s_cand and s_cand not in ("nan", "None", "0", "00", "null"):
                target_id = s_cand
                break

        poly = poly_map.get(target_id)
        if poly is None and len(target_id) >= 14:
            poly = poly_map.get(target_id[:14])
        if poly is None and props.get("idsls"):
            clean_idsls = str(props.get("idsls")).strip().replace(".0", "")
            poly = poly_map.get(clean_idsls)
        if poly is None and props.get("idsubsls_edited"):
            clean_ed = str(props.get("idsubsls_edited")).strip().replace(".0", "")
            poly = poly_map.get(clean_ed) or (poly_map.get(clean_ed[:14]) if len(clean_ed) >= 14 else None)

        if poly is None:
            not_found_count += 1
            props["repair_status"] = "subsls_not_found_in_master"
            continue

        coords = feat.get("geometry", {}).get("coordinates", [0, 0])
        curr_pt = Point(coords[0], coords[1])

        # Cek apakah sudah di dalam poligon target (SubSLS) ATAU home SLS (14-digit)
        sls_poly = poly_map.get(target_id[:14]) if len(target_id) >= 14 else None

        # Prioritaskan cek koordinat origin asli jika tersedia (pulihkan dari pergeseran liar)
        orig_pt = None
        if props.get("latitude_origin") is not None and props.get("longitude_origin") is not None:
            try:
                orig_pt = Point(float(props["longitude_origin"]), float(props["latitude_origin"]))
            except Exception:
                pass

        if orig_pt and ((poly is not None and (poly.contains(orig_pt) or poly.intersects(orig_pt))) or
                        (sls_poly is not None and (sls_poly.contains(orig_pt) or sls_poly.intersects(orig_pt)))):
            new_pt = orig_pt
            method = "already_inside_pristine_origin"
        elif poly.contains(curr_pt) or poly.intersects(curr_pt):
            new_pt = curr_pt
            method = "already_inside"
        elif sls_poly is not None and (sls_poly.contains(curr_pt) or sls_poly.intersects(curr_pt)):
            new_pt = curr_pt
            method = "already_inside_home_sls"
        else:
            candidate = None
            try:
                inward_poly = poly.buffer(-0.00005)
                if not inward_poly.is_empty:
                    p1, _ = nearest_points(inward_poly, curr_pt)
                    if poly.contains(p1):
                        candidate = p1
            except Exception:
                pass

            if candidate is None:
                new_pt = poly.representative_point()
                method = "representative_point"
            else:
                new_pt = candidate
                method = "interior_projection"

        new_lat = round(float(new_pt.y), 8)
        new_lon = round(float(new_pt.x), 8)

        # Update koordinat spasial dan atribut
        props["latitude_edited"] = new_lat
        props["longitude_edited"] = new_lon
        props["geotag_latitude"] = new_lat
        props["geotag_longitude"] = new_lon

        # Jamin kedua kolom identitas SLS terisi (standar QGIS model3 & Wilkerstat)
        props["level_6_full_code"] = target_id
        props["idsubsls_origin"] = target_id
        props["idsubsls_edited"] = target_id

        if method in ("already_inside", "already_inside_home_sls", "already_inside_pristine_origin"):
            props["flag_position"] = 0
            restored_count += 1
        else:
            props["flag_position"] = 1
            moved_count += 1

        props["flag_repair"] = 0
        props["flag_repair_sls"] = 0
        props["status"] = "INSIDE"
        props["jarak_m"] = 0.0
        props["repair_method"] = method

        feat["geometry"] = mapping(new_pt)

    out_data = {
        "type": "FeatureCollection",
        "name": "moved_failed_dots",
        "crs": failed_data.get("crs"),
        "features": features
    }

    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    while True:
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)
            break
        except (PermissionError, OSError) as e:
            print("\n" + "=" * 65)
            print("  [PERINGATAN] BERKAS MOVED_FAILED SEDANG DIKUNCI APLIKASI LAIN!")
            print(f"  Berkas : {out_file}")
            print("  Aplikasi (seperti QGIS atau editor lain) sedang membuka berkas ini.")
            print("  -> Silakan TUTUP / HAPUS LAYER berkas tersebut di QGIS sekarang!")
            print("=" * 65)
            jawab = input("Tekan [Enter] setelah menutup aplikasi untuk mencoba menyimpan ulang (atau ketik 'batal'): ").strip().lower()
            if jawab in ("batal", "exit", "quit"):
                raise e

    print(f"\n3. Hasil Penarikan Titik:")
    print(f"   -> Diproyeksikan ke INSIDE     : {moved_count} titik")
    print(f"   -> Dipulihkan ke posisi asal   : {restored_count} titik")
    print(f"   -> Poligon SubSLS tidak ada    : {not_found_count} titik")
    print(f"   -> Disimpan murni ke GeoJSON   : {out_file}\n")
    return True

