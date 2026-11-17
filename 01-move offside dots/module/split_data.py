"""
Modul Pemecah GeoJSON Poligon & Titik per-Desa (10 digit pertama kode wilayah).
Menggunakan pustaka standar json tanpa ketergantungan geopandas/GDAL.
"""
import os
import json
from collections import defaultdict


def split_geojson_per_desa(peta_file: str, titik_file: str, folder_poly: str, folder_geo: str):
    os.makedirs(folder_poly, exist_ok=True)
    os.makedirs(folder_geo, exist_ok=True)

    print("=" * 60)
    print("  MEMECAH DATASET WILAYAH (SPLIT PER-DESA)")
    print("=" * 60)

    # 1. Split Poligon
    print("\n1. Membaca & membagi Poligon SLS per Desa...")
    if os.path.exists(peta_file):
        with open(peta_file, "r", encoding="utf-8") as f:
            peta_data = json.load(f)

        poly_groups = defaultdict(list)
        for feat in peta_data.get("features", []):
            props = feat.get("properties") or {}
            idsub = str(props.get("idsubsls") or props.get("idsls") or "").strip()
            iddesa = idsub[:10]
            if iddesa:
                poly_groups[iddesa].append(feat)

        print(f"   Ditemukan {len(peta_data.get('features', []))} poligon dari {len(poly_groups)} desa.")
        for iddesa, feats in poly_groups.items():
            out_geojson = {
                "type": "FeatureCollection",
                "name": f"final_sls_251_{iddesa}",
                "crs": peta_data.get("crs"),
                "features": feats
            }
            out_path = os.path.join(folder_poly, f"final_sls_251_{iddesa}.geojson")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out_geojson, f)
        print(f"   [SUKSES] Poligon tersimpan ke: {folder_poly}")
    else:
        print(f"   [ERROR] Berkas poligon tidak ditemukan: {peta_file}")

    # 2. Split Titik
    print("\n2. Membaca & membagi Titik Bangunan per Desa...")
    if os.path.exists(titik_file):
        with open(titik_file, "r", encoding="utf-8") as f:
            titik_data = json.load(f)

        point_groups = defaultdict(list)
        for feat in titik_data.get("features", []):
            props = feat.get("properties") or {}
            idsub = str(props.get("level_6_full_code") or props.get("idsubsls_origin") or props.get("idsubsls") or "").strip()
            iddesa = idsub[:10]
            if iddesa:
                coords = feat.get("geometry", {}).get("coordinates", [None, None]) if feat.get("geometry") else [None, None]
                lat = props.get("latitude_origin") if props.get("latitude_origin") is not None else (coords[1] if len(coords) > 1 else 0)
                lon = props.get("longitude_origin") if props.get("longitude_origin") is not None else (coords[0] if len(coords) > 0 else 0)
                try:
                    props["geotag_latitude"] = float(lat)
                except Exception:
                    props["geotag_latitude"] = 0.0
                try:
                    props["geotag_longitude"] = float(lon)
                except Exception:
                    props["geotag_longitude"] = 0.0
                props["idsls"] = idsub[:14]
                props["level_5_full_code"] = idsub[:14]
                props["id_assignment"] = props.get("assignment_id", "")
                point_groups[iddesa].append(feat)

        print(f"   Ditemukan {len(titik_data.get('features', []))} titik dari {len(point_groups)} desa.")
        for iddesa, feats in point_groups.items():
            out_geojson = {
                "type": "FeatureCollection",
                "name": f"{iddesa}_geotagging",
                "crs": titik_data.get("crs"),
                "features": feats
            }
            out_path = os.path.join(folder_geo, f"{iddesa}_geotagging.geojson")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out_geojson, f)
        print(f"   [SUKSES] Titik tersimpan ke: {folder_geo}")
    else:
        print(f"   [ERROR] Berkas titik tidak ditemukan: {titik_file}")

    print("\n[SELESAI] Pemecahan data per-desa selesai.")

