"""
Modul Ekstraksi Titik Gagal / Offside.
Mengekstrak titik offside dari dataset masukan (berdasarkan flag_repair, status,
ataupun evaluasi spasial langsung terhadap batas poligon SLS) dan menyimpannya menjadi failed.geojson.
"""
import os
import json
from collections import defaultdict
from shapely.geometry import shape as shapely_shape, Point
from shapely.ops import unary_union


def _load_polygon_map(poly_path: str) -> dict:
    if not poly_path or not os.path.exists(poly_path):
        return {}
    try:
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

        return poly_map
    except Exception as e:
        print(f"   [Peringatan] Gagal memuat poligon acuan {poly_path}: {e}")
        return {}


def extract_failed_dots(input_file: str, output_file: str, poly_path: str = None):
    print("=" * 60)
    print("  EKSTRAKSI TITIK GAGAL / OFFSIDE")
    print("=" * 60)

    if not os.path.exists(input_file):
        print(f"[ERROR] Berkas input tidak ditemukan: {input_file}")
        return False

    # Auto-resolve poly_path jika tidak disediakan
    if not poly_path or not os.path.exists(poly_path):
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_poly = os.path.abspath(os.path.join(curr_dir, "..", "..", "00-identify dots", "slsmentah fixed-2025sm1.geojson"))
        if os.path.exists(candidate_poly):
            poly_path = candidate_poly

    poly_map = _load_polygon_map(poly_path) if poly_path else {}
    if poly_map:
        print(f"Menggunakan poligon acuan spasial: {os.path.basename(poly_path)} ({len(poly_map):,} batas terindeks)")

    print(f"Membaca titik dari: {os.path.basename(input_file)}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    failed_features = []

    for feat in features:
        props = feat.get("properties") or {}
        flag_repair = str(props.get("flag_repair", "")).strip()
        status = str(props.get("status", "")).strip().upper()

        # IMMUTABLE WHITELIST: Jika flag_repair == 0, titik MUTLAK dilindungi dari pergeseran
        if flag_repair in ("0", "0.0", "False", "false"):
            continue

        is_failed = False

        # 1. Kriteria Berdasarkan Flag Eksplisit
        if flag_repair in ("1", "1.0", "True", "true"):
            is_failed = True
        elif status in ("OFFSIDE", "GAGAL", "FAILED"):
            is_failed = True

        # 2. Kriteria Inkonsistensi ID Overlay (jika atribut tersedia)
        if not is_failed and props.get("idsubsls_261"):
            home_id = str(props.get("level_6_full_code") or props.get("idsubsls_origin") or "").strip()
            overlay_id = str(props.get("idsubsls_261")).strip()
            if home_id and overlay_id and home_id != overlay_id:
                # Periksa apakah home_id memang berbeda secara SLS (14 digit)
                if home_id[:14] != overlay_id[:14]:
                    is_failed = True

        # 3. Kriteria Evaluasi Geometri Spasial Nyata (Ground Truth Mutlak)
        if poly_map:
            home_id = str(props.get("level_6_full_code") or props.get("idsubsls_origin") or props.get("idsubsls") or "").strip()
            geom = feat.get("geometry")
            coords = geom.get("coordinates") if geom else None
            pt = None
            if coords and len(coords) >= 2:
                try:
                    pt = Point(float(coords[0]), float(coords[1]))
                except Exception:
                    pass
            elif props.get("latitude_edited") is not None and props.get("longitude_edited") is not None:
                try:
                    pt = Point(float(props["longitude_edited"]), float(props["latitude_edited"]))
                except Exception:
                    pass

            if pt and home_id:
                poly = poly_map.get(home_id)
                sls_poly = poly_map.get(home_id[:14]) if len(home_id) >= 14 else None
                
                # Ground truth: jika fisik titik di dalam SubSLS atau Home SLS 14-digit, mutlak INSIDE
                if (poly is not None and (poly.contains(pt) or poly.intersects(pt))) or \
                   (sls_poly is not None and (sls_poly.contains(pt) or sls_poly.intersects(pt))):
                    is_failed = False
                elif poly is not None or sls_poly is not None:
                    is_failed = True

        if is_failed:
            failed_features.append(feat)

    print(f"Total fitur diperiksa : {len(features):,}")
    print(f"Titik offside ditemukan : {len(failed_features):,}")

    out_data = {
        "type": "FeatureCollection",
        "name": "failed_dots",
        "crs": data.get("crs"),
        "features": failed_features
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    while True:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)
            break
        except (PermissionError, OSError) as e:
            print("\n" + "=" * 65)
            print("  [PERINGATAN] BERKAS FAILED DOTS SEDANG DIKUNCI APLIKASI LAIN!")
            print(f"  Berkas : {output_file}")
            print("  Aplikasi (seperti QGIS atau editor lain) sedang membuka berkas ini.")
            print("  -> Silakan TUTUP / HAPUS LAYER berkas tersebut di QGIS sekarang!")
            print("=" * 65)
            jawab = input("Tekan [Enter] setelah menutup aplikasi untuk mencoba menyimpan ulang (atau ketik 'batal'): ").strip().lower()
            if jawab in ("batal", "exit", "quit"):
                raise e

    print(f"[SUKSES] Berkas tersimpan ke: {output_file}\n")
    return True


