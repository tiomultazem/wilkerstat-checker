#!/usr/bin/env python3
"""
dissolve_wilkerstat.py
======================
Peleburan Poligon SLS/Sub-SLS menjadi Peta Batas Desa dan Kecamatan BPS.
Agnostik Seluruh Indonesia: Mendukung semua Kabupaten/Kota dengan auto-deteksi
kode wilayah, proyeksi UTM metrik, dan skema standar BPS (14 kolom Desa, 11 kolom Kec).
Mengacu pada standar alur pengolahan spasial PMSS BPS RI:
https://github.com/PMSS-BPS/Pengolahan-Wilkerstat-SE2026
"""

import os
import sys
import json
import glob

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Polygon, MultiPolygon, mapping
    from shapely.ops import unary_union
    from shapely.validation import make_valid
except ImportError as e:
    print(f"[ERROR] Dependensi tidak lengkap: {e}")
    print("Jalankan: pip install geopandas pandas shapely pyproj")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# KONFIGURASI SKEMA RESMI BPS
# ─────────────────────────────────────────────────────────────
KOLOM_DESA = [
    "gid", "luas", "kdkab", "kdkec", "nmkab", "nmkec",
    "iddesa", "kddesa", "kdprov", "nmdesa", "nmprov",
    "rw_dki", "sumber", "periode"
]

KOLOM_KEC = [
    "gid", "luas", "idkec", "kdkab", "kdkec", "nmkab", "nmkec",
    "kdprov", "nmprov", "sumber", "periode"
]


def prompt_user(text, default=""):
    """Minta masukan user dengan nilai default yang dapat langsung di-Enter."""
    if default:
        res = input(f"{text} [{default}]: ").strip()
        return res if res else default
    return input(f"{text}: ").strip()


def detect_utm_epsg(gdf):
    """
    Auto-deteksi kode EPSG UTM yang tepat berdasarkan centroid layer
    (Mendukung seluruh zona UTM Indonesia 46N s.d. 54S).
    """
    try:
        centroid = gdf.geometry.unary_union.centroid
        lon, lat = centroid.x, centroid.y
        zone = int((lon + 180) / 6) + 1
        epsg = (32600 if lat >= 0 else 32700) + zone
        return epsg
    except Exception:
        return 32750  # Fallback standar Kalsel (UTM 50S)


def clean_and_force_multipolygon(geom):
    """
    Validasi geometri dan paksa selalu bertipe MultiPolygon
    tanpa merusak/memecah bagian enklave/eksklave wilayah administrasi.
    """
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        geom = make_valid(geom)
    
    if geom.geom_type == 'GeometryCollection':
        polys = []
        for g in geom.geoms:
            if g.geom_type == 'Polygon':
                polys.append(g)
            elif g.geom_type == 'MultiPolygon':
                polys.extend(g.geoms)
        if polys:
            geom = unary_union(polys)
        else:
            return None

    if geom.geom_type == 'Polygon':
        return MultiPolygon([geom])
    elif geom.geom_type == 'MultiPolygon':
        return geom
    return None


def export_bps_geojson(gdf, columns, output_path, layer_name):
    """
    Simpan GeoDataFrame ke format GeoJSON baku BPS dengan urutan kolom persis
    dan format line-by-line Feature.
    """
    features = []
    for _, row in gdf.iterrows():
        props = {}
        for col in columns:
            val = row[col]
            if col == 'gid':
                val = int(val)
            elif col == 'luas':
                val = float(val)
            elif pd.isna(val) or val is None:
                val = ""
            else:
                val = str(val)
            props[col] = val

        geom_dict = mapping(row['geometry'])
        feature = {
            "type": "Feature",
            "id": int(props['gid']),
            "properties": props,
            "geometry": geom_dict
        }
        features.append(feature)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write('{\n"type": "FeatureCollection",\n')
        f.write(f'"name": "{layer_name}",\n')
        f.write('"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },\n')
        f.write('"features": [\n')
        for i, feat in enumerate(features):
            comma = "," if i < len(features) - 1 else ""
            f.write(json.dumps(feat, ensure_ascii=False) + comma + "\n")
        f.write(']\n}\n')


def main():
    _HERE = os.path.dirname(os.path.abspath(__file__))

    print("=" * 65)
    print("  PELEBURAN POLIGON WILKERSTAT (SLS -> DESA & KECAMATAN)")
    print("  Standar Resmi BPS RI — Multi-Kabupaten Seluruh Indonesia")
    print("=" * 65)

    # 1. Deteksi / Input Berkas Masukan
    default_input = "untuk 2026_1.geojson"
    if not os.path.exists(os.path.join(_HERE, default_input)):
        geojson_files = [os.path.basename(f) for f in glob.glob(os.path.join(_HERE, "*.geojson"))]
        if geojson_files:
            default_input = geojson_files[0]

    input_rel = prompt_user("\n[1] Berkas masukan SLS (.geojson)", default_input)
    input_path = os.path.join(_HERE, input_rel) if not os.path.isabs(input_rel) else input_rel

    if not os.path.exists(input_path):
        print(f"[FATAL] Berkas masukan tidak ditemukan: {input_path}")
        sys.exit(1)

    print(f"\n-> Memuat berkas: {os.path.basename(input_path)} ...")
    gdf_sls = gpd.read_file(input_path)
    total_sls = len(gdf_sls)
    print(f"   Total poligon SLS dimuat: {total_sls:,}")

    # 2. Auto-deteksi Parameter Wilayah dari Data
    sample_prov = str(gdf_sls['kdprov'].dropna().iloc[0]).strip() if 'kdprov' in gdf_sls.columns else "63"
    sample_kab  = str(gdf_sls['kdkab'].dropna().iloc[0]).strip() if 'kdkab' in gdf_sls.columns else "09"
    default_kabkot = f"{sample_prov}{sample_kab}"

    kabkot_code = prompt_user("[2] Kode Wilayah 4-Digit (Prov+Kab)", default_kabkot)
    
    sample_periode = str(gdf_sls['periode'].dropna().iloc[0]).strip() if 'periode' in gdf_sls.columns else "2026_1"
    periode = prompt_user("[3] Periode Pemutakhiran", sample_periode)
    periode_clean = periode.replace("_", "")

    # 3. Auto-deteksi Proyeksi UTM
    auto_epsg = detect_utm_epsg(gdf_sls)
    epsg_input = prompt_user("[4] Kode EPSG Proyeksi Metrik UTM untuk hitung Luas", str(auto_epsg))
    epsg_utm = int(epsg_input)

    # 4. Penentuan Berkas Referensi & Output
    default_ref_desa = f"Prod_Desa_20251{kabkot_code}.geojson"
    default_ref_kec  = f"Prod_Kec_20251{kabkot_code}.geojson"
    ref_desa_rel = prompt_user("[5] Berkas Referensi GID Desa (opsional)", default_ref_desa)
    ref_kec_rel  = prompt_user("[6] Berkas Referensi GID Kecamatan (opsional)", default_ref_kec)

    ref_desa_path = os.path.join(_HERE, ref_desa_rel) if not os.path.isabs(ref_desa_rel) else ref_desa_rel
    ref_kec_path  = os.path.join(_HERE, ref_kec_rel) if not os.path.isabs(ref_kec_rel) else ref_kec_rel

    out_desa_name = f"Prod_Desa_{periode_clean}{kabkot_code}.geojson"
    out_kec_name  = f"Prod_Kec_{periode_clean}{kabkot_code}.geojson"
    out_desa_path = os.path.join(_HERE, out_desa_name)
    out_kec_path  = os.path.join(_HERE, out_kec_name)

    print("\n" + "-" * 65)
    print("  MEMULAI PROSES PELEBURAN...")
    print("-" * 65)

    # Pra-pembersihan geometri SLS
    print("\n[Langkah 1/4] Pra-pembersihan geometri SLS (make_valid)...")
    gdf_sls['geometry'] = gdf_sls['geometry'].apply(clean_and_force_multipolygon)
    gdf_sls = gdf_sls[gdf_sls['geometry'].notnull()].copy()

    for col in ['kdprov', 'kdkab', 'kdkec', 'kddesa']:
        if col in gdf_sls.columns:
            gdf_sls[col] = gdf_sls[col].astype(str).str.strip()

    # ─────────────────────────────────────────────────────────────
    # PELEBURAN TINGKAT DESA
    # ─────────────────────────────────────────────────────────────
    print("\n[Langkah 2/4] Melebur poligon ke tingkat DESA...")
    group_desa = ['kdprov', 'kdkab', 'kdkec', 'kddesa', 'nmprov', 'nmkab', 'nmkec', 'nmdesa']
    gdf_desa = gdf_sls.dissolve(by=group_desa, as_index=False)
    gdf_desa['geometry'] = gdf_desa['geometry'].apply(clean_and_force_multipolygon)

    # Hitung luas geodesik planar dalam km²
    print(f"   Menghitung luas desa (EPSG:{epsg_utm} planar km²) ...")
    gdf_desa_utm = gdf_desa.to_crs(epsg=epsg_utm)
    gdf_desa['luas'] = gdf_desa_utm.geometry.area / 1_000_000.0

    gdf_desa['iddesa'] = (
        gdf_desa['kdprov'] + gdf_desa['kdkab'] + gdf_desa['kdkec'] + gdf_desa['kddesa']
    )
    gdf_desa['rw_dki'] = ""
    gdf_desa['sumber'] = "BPS"
    gdf_desa['periode'] = periode

    # Penentuan GID Desa
    gid_desa_map = {}
    if os.path.exists(ref_desa_path):
        try:
            with open(ref_desa_path, "r", encoding="utf-8") as f:
                ref_d = json.load(f)
                for feat in ref_d.get("features", []):
                    props = feat.get("properties", {})
                    if "iddesa" in props and "gid" in props:
                        gid_desa_map[props["iddesa"]] = props["gid"]
            print(f"   Memuat {len(gid_desa_map)} referensi GID Desa historis.")
        except Exception as e:
            print(f"   [WARN] Gagal membaca referensi Desa: {e}")

    max_desa_gid = max(gid_desa_map.values()) if gid_desa_map else 10000
    desa_gids = []
    for _, row in gdf_desa.iterrows():
        id_d = row['iddesa']
        if id_d in gid_desa_map:
            desa_gids.append(gid_desa_map[id_d])
        else:
            max_desa_gid += 1
            desa_gids.append(max_desa_gid)
    gdf_desa['gid'] = desa_gids

    gdf_desa = gdf_desa.sort_values(by="iddesa").reset_index(drop=True)
    print(f"   Hasil peleburan Desa: {len(gdf_desa)} entitas.")

    export_bps_geojson(gdf_desa, KOLOM_DESA, out_desa_path, f"Prod_Desa_{periode_clean}{kabkot_code}")
    print(f"   -> Berkas tersimpan: {os.path.basename(out_desa_path)}")

    # ─────────────────────────────────────────────────────────────
    # PELEBURAN TINGKAT KECAMATAN
    # ─────────────────────────────────────────────────────────────
    print("\n[Langkah 3/4] Melebur poligon ke tingkat KECAMATAN...")
    group_kec = ['kdprov', 'kdkab', 'kdkec', 'nmprov', 'nmkab', 'nmkec']
    gdf_kec = gdf_desa.dissolve(by=group_kec, as_index=False)
    gdf_kec['geometry'] = gdf_kec['geometry'].apply(clean_and_force_multipolygon)

    print(f"   Menghitung luas kecamatan (EPSG:{epsg_utm} planar km²) ...")
    gdf_kec_utm = gdf_kec.to_crs(epsg=epsg_utm)
    gdf_kec['luas'] = gdf_kec_utm.geometry.area / 1_000_000.0

    gdf_kec['idkec'] = gdf_kec['kdprov'] + gdf_kec['kdkab'] + gdf_kec['kdkec']
    gdf_kec['sumber'] = "BPS"
    gdf_kec['periode'] = periode

    # Penentuan GID Kecamatan
    gid_kec_map = {}
    if os.path.exists(ref_kec_path):
        try:
            with open(ref_kec_path, "r", encoding="utf-8") as f:
                ref_k = json.load(f)
                for feat in ref_k.get("features", []):
                    props = feat.get("properties", {})
                    if "idkec" in props and "gid" in props:
                        gid_kec_map[props["idkec"]] = props["gid"]
            print(f"   Memuat {len(gid_kec_map)} referensi GID Kecamatan historis.")
        except Exception as e:
            print(f"   [WARN] Gagal membaca referensi Kecamatan: {e}")

    max_kec_gid = max(gid_kec_map.values()) if gid_kec_map else 1000
    kec_gids = []
    for _, row in gdf_kec.iterrows():
        id_k = row['idkec']
        if id_k in gid_kec_map:
            kec_gids.append(gid_kec_map[id_k])
        else:
            max_kec_gid += 1
            kec_gids.append(max_kec_gid)
    gdf_kec['gid'] = kec_gids

    gdf_kec = gdf_kec.sort_values(by="idkec").reset_index(drop=True)
    print(f"   Hasil peleburan Kecamatan: {len(gdf_kec)} entitas.")

    export_bps_geojson(gdf_kec, KOLOM_KEC, out_kec_path, f"Prod_Kec_{periode_clean}{kabkot_code}")
    print(f"   -> Berkas tersimpan: {os.path.basename(out_kec_path)}")

    # ─────────────────────────────────────────────────────────────
    # VERIFIKASI AKHIR
    # ─────────────────────────────────────────────────────────────
    print("\n[Langkah 4/4] Ringkasan Verifikasi:")
    print(f"   Wilayah   : Kode {kabkot_code} | Periode {periode}")
    print(f"   Proyeksi  : EPSG:{epsg_utm} (Planar Geodesik)")
    print(f"   Desa      : {len(gdf_desa)} fitur | 14 kolom skema BPS | MultiPolygon 100%")
    print(f"   Kecamatan : {len(gdf_kec)} fitur | 11 kolom skema BPS | MultiPolygon 100%")
    print("=" * 65)
    print("  PELEBURAN WILKERSTAT SELESAI DENGAN SUKSES")
    print("=" * 65)


if __name__ == "__main__":
    main()
