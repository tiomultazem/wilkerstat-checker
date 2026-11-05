#!/usr/bin/env python3
"""
convert.py
Mengonversi GeoJSON FeatureCollection yang berisi MultiPolygon dan
GeometryCollection menjadi FeatureCollection yang seluruh geometrinya
adalah MultiPolygon.

Output disimpan di folder yang sama dengan nama file yang sama
ditambah suffix "-fixed". Contoh: data.geojson -> data-fixed.geojson
"""

import json
import os
import sys


def extract_polygons(geom, skipped):
    """Ambil semua polygon (list ring) dari geometri apa pun secara rekursif."""
    if not geom:
        return []

    gtype = geom.get("type")

    if gtype == "Polygon":
        return [geom["coordinates"]]

    if gtype == "MultiPolygon":
        return list(geom["coordinates"])

    if gtype == "GeometryCollection":
        polygons = []
        for sub in geom.get("geometries", []):
            polygons.extend(extract_polygons(sub, skipped))
        return polygons

    # Point, LineString, dll. tidak bisa menjadi polygon
    skipped.append(gtype)
    return []


def convert(data):
    """Kembalikan (FeatureCollection baru, statistik)."""
    # Normalisasi input: bisa FeatureCollection, Feature, atau geometri langsung
    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
    elif data.get("type") == "Feature":
        features = [data]
    else:
        features = [{"type": "Feature", "properties": {}, "geometry": data}]

    new_features = []
    skipped_types = []
    dropped = 0
    converted_from = {}

    for feat in features:
        geom = feat.get("geometry")
        original_type = geom.get("type") if geom else None
        converted_from[original_type] = converted_from.get(original_type, 0) + 1

        polygons = extract_polygons(geom, skipped_types)
        if not polygons:
            dropped += 1
            continue

        new_feat = dict(feat)
        new_feat["geometry"] = {"type": "MultiPolygon", "coordinates": polygons}
        new_features.append(new_feat)

    result = {"type": "FeatureCollection"}
    # Pertahankan properti tingkat atas lain (misal crs, name) bila ada
    if data.get("type") == "FeatureCollection":
        for key, value in data.items():
            if key not in ("type", "features"):
                result[key] = value
    result["features"] = new_features

    stats = {
        "total": len(features),
        "ok": len(new_features),
        "dropped": dropped,
        "by_type": converted_from,
        "skipped_types": skipped_types,
    }
    return result, stats


def main():
    path = input("Masukkan path file GeoJSON: ").strip().strip('"').strip("'")

    if not path:
        print("Path tidak boleh kosong.")
        sys.exit(1)
    if not os.path.isfile(path):
        print(f"File tidak ditemukan: {path}")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"File bukan JSON yang valid: {e}")
        sys.exit(1)

    result, stats = convert(data)

    base, ext = os.path.splitext(path)
    out_path = f"{base}-fixed{ext or '.geojson'}"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    print("\nSelesai!")
    print(f"  Total fitur input : {stats['total']}")
    for t, n in stats["by_type"].items():
        print(f"    - {t}: {n}")
    print(f"  Fitur MultiPolygon: {stats['ok']}")
    if stats["dropped"]:
        print(f"  Fitur dibuang     : {stats['dropped']} (tidak mengandung polygon)")
    if stats["skipped_types"]:
        print(f"  Geometri non-polygon yang diabaikan: {len(stats['skipped_types'])}")
    print(f"  Output            : {out_path}")


if __name__ == "__main__":
    main()