import geopandas as gpd
import pandas as pd
import numpy as np
import math
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

from shapely.geometry import Point
from shapely.ops import unary_union


# =========================================================
# 1. AUTO READ SPATIAL FILE
# =========================================================

def read_spatial(path,
                 latitude_col="geotag_latitude",
                 longitude_col="geotag_longitude"):

    path_lower = path.lower()

    # ============================================
    # CSV
    # ============================================

    if path_lower.endswith(".csv"):

        df = pd.read_csv(path)

        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(
                df[longitude_col],
                df[latitude_col]
            ),
            crs="EPSG:4326"
        )

        return gdf

    # ============================================
    # GEOJSON
    # ============================================

    elif path_lower.endswith(".geojson"):

        return gpd.read_file(path)

    # ============================================
    # GPKG
    # ============================================

    elif path_lower.endswith(".gpkg"):

        return gpd.read_file(path)

    # ============================================
    # SHP
    # ============================================

    elif path_lower.endswith(".shp"):

        return gpd.read_file(path)

    else:

        raise ValueError(
            f"Format tidak didukung: {path}"
        )


# =========================================================
# 2. SHIFT POINT 5 METER
# =========================================================

def shift_point_5m(base_point,
                   reference_point,
                   polygon,
                   distance=5):

    dx = reference_point.x - base_point.x
    dy = reference_point.y - base_point.y

    length = math.sqrt(dx**2 + dy**2)

    if length == 0:
        dx = 1
        dy = 0
        length = 1

    ux = dx / length
    uy = dy / length

    # ============================================
    # MAJU
    # ============================================

    new_x = reference_point.x + ux * distance
    new_y = reference_point.y + uy * distance

    candidate = Point(new_x, new_y)

    if polygon.contains(candidate):
        return candidate

    # ============================================
    # MUNDUR
    # ============================================

    new_x = reference_point.x - ux * distance
    new_y = reference_point.y - uy * distance

    candidate = Point(new_x, new_y)

    if polygon.contains(candidate):
        return candidate

    return reference_point


# =========================================================
# 3. CLEAN EXTRA GEOMETRY COLUMNS
# =========================================================

def clean_geometry_columns(gdf):

    geometry_cols = []

    active_geometry = gdf.geometry.name

    for col in gdf.columns:

        if col == active_geometry:
            continue

        try:

            if hasattr(gdf[col], "geom_type"):

                geometry_cols.append(col)

        except:
            pass

    if len(geometry_cols) > 0:

        gdf = gdf.drop(
            columns=geometry_cols,
            errors="ignore"
        )

    return gdf


# =========================================================
# 4. FUNGSI REPAIR COORDINAT
# =========================================================

def find_repair_coordinate(row,
                           valid_points,
                           gdf_poly):

    target_subsls = str(row["level_6_full_code"]).strip()
    if target_subsls.endswith(".0"):
        target_subsls = target_subsls[:-2]

    try:
        target_no = int(float(row["no_bang"])) if row["no_bang"] is not None else 0
    except Exception:
        target_no = 0

    # ============================================
    # POLYGON TARGET
    # ============================================

    poly_match = gdf_poly[
        gdf_poly["idsubsls"].astype(str)
        == target_subsls
    ]

    # Fallback ke poligon SLS (14 digit) jika SubSLS poligon tidak ditemukan
    if len(poly_match) == 0 and len(target_subsls) >= 14:
        if "idsls" in gdf_poly.columns:
            poly_match = gdf_poly[
                gdf_poly["idsls"].astype(str) == target_subsls[:14]
            ]
        if len(poly_match) == 0 and "idsubsls" in gdf_poly.columns:
            poly_match = gdf_poly[
                gdf_poly["idsubsls"].astype(str).str[:14] == target_subsls[:14]
            ]

    if len(poly_match) == 0:
        return (
            row["geotag_latitude"],
            row["geotag_longitude"],
            "subsls_not_found"
        )

    # Union seluruh komponen geometri poligon (mendukung multi-part SLS)
    if len(poly_match) == 1:
        poly = poly_match.iloc[0].geometry
        poly_proj = poly_match.iloc[0]["geometry_proj"]
    else:
        try:
            poly = unary_union(poly_match.geometry.values)
        except Exception:
            poly = poly_match.iloc[0].geometry
        try:
            poly_proj = unary_union(poly_match["geometry_proj"].values)
        except Exception:
            poly_proj = poly_match.iloc[0]["geometry_proj"]

    # ============================================
    # IMMUTABLE GUARD: Jika koordinat mentah SUDAH di dalam poligon target
    # ============================================
    try:
        raw_pt = Point(float(row["geotag_longitude"]), float(row["geotag_latitude"]))
        if poly.contains(raw_pt) or poly.intersects(raw_pt):
            return (
                row["geotag_latitude"],
                row["geotag_longitude"],
                "already_inside_home"
            )
    except Exception:
        pass

    # ============================================
    # SUBSET VALID
    # ============================================

    subset = valid_points[
        valid_points["level_6_full_code"]
        .astype(str)
        == target_subsls
    ].copy()

    # Fallback subset ke SLS (14 digit) jika subset SubSLS kosong
    if len(subset) == 0 and len(target_subsls) >= 14:
        subset = valid_points[
            valid_points["level_6_full_code"].astype(str).str[:14]
            == target_subsls[:14]
        ].copy()

    # ============================================
    # TIDAK ADA TITIK VALID -> REPRESENTATIVE POINT
    # ============================================

    if len(subset) == 0:
        rep_pt = poly.representative_point()
        return (
            rep_pt.y,
            rep_pt.x,
            "polygon_representative"
        )

    # ============================================
    # BEFORE AFTER
    # ============================================

    subset["no_bang_int"] = pd.to_numeric(subset["no_bang"], errors="coerce").fillna(0).astype(int)

    before = subset[
        subset["no_bang_int"]
        < target_no
    ].sort_values("no_bang_int", ascending=False)

    after = subset[
        subset["no_bang_int"]
        > target_no
    ].sort_values("no_bang_int", ascending=True)

    before_pt = before.iloc[0] if len(before) > 0 else None
    after_pt = after.iloc[0] if len(after) > 0 else None

    # ============================================
    # INTERPOLASI
    # ============================================

    if before_pt is not None and after_pt is not None:

        lat = (
            before_pt["geotag_latitude"]
            + after_pt["geotag_latitude"]
        ) / 2

        lon = (
            before_pt["geotag_longitude"]
            + after_pt["geotag_longitude"]
        ) / 2

        candidate = Point(lon, lat)

        if poly.contains(candidate) or poly.intersects(candidate):
            return (
                lat,
                lon,
                "interpolated"
            )

        rep_pt = poly.representative_point()
        return (
            rep_pt.y,
            rep_pt.x,
            "fallback_representative"
        )

    # ============================================
    # HANYA BEFORE
    # ============================================

    elif before_pt is not None:

        ref_point = before_pt.geometry_proj

        before_nb = int(float(before_pt["no_bang"])) if before_pt["no_bang"] is not None else 0
        before2 = subset[
            subset["no_bang_int"]
            < before_nb
        ].sort_values("no_bang_int", ascending=False)

        if len(before2) > 0:
            base_point = before2.iloc[0].geometry_proj
        else:
            base_point = poly_proj.representative_point()

        shifted = shift_point_5m(
            base_point,
            ref_point,
            poly_proj,
            distance=5
        )

        shifted_geom = gpd.GeoSeries(
            [shifted],
            crs=3857
        ).to_crs(4326).iloc[0]

        if poly.contains(shifted_geom) or poly.intersects(shifted_geom):
            return (
                shifted_geom.y,
                shifted_geom.x,
                "shift_after_last"
            )

        rep_pt = poly.representative_point()
        return (
            rep_pt.y,
            rep_pt.x,
            "shift_after_representative"
        )

    # ============================================
    # HANYA AFTER
    # ============================================

    elif after_pt is not None:

        ref_point = after_pt.geometry_proj

        after_nb = int(float(after_pt["no_bang"])) if after_pt["no_bang"] is not None else 0
        after2 = subset[
            subset["no_bang_int"]
            > after_nb
        ].sort_values("no_bang_int", ascending=True)

        if len(after2) > 0:
            base_point = after2.iloc[0].geometry_proj
        else:
            base_point = poly_proj.representative_point()

        shifted = shift_point_5m(
            base_point,
            ref_point,
            poly_proj,
            distance=5
        )

        shifted_geom = gpd.GeoSeries(
            [shifted],
            crs=3857
        ).to_crs(4326).iloc[0]

        if poly.contains(shifted_geom) or poly.intersects(shifted_geom):
            return (
                shifted_geom.y,
                shifted_geom.x,
                "shift_before_first"
            )

        rep_pt = poly.representative_point()
        return (
            rep_pt.y,
            rep_pt.x,
            "shift_before_representative"
        )

    # ============================================
    # FINAL FALLBACK -> REPRESENTATIVE POINT
    # ============================================

    rep_pt = poly.representative_point()

    return (
        rep_pt.y,
        rep_pt.x,
        "final_fallback_representative"
    )


# =========================================================
# 5. MAIN FUNCTION
# =========================================================

def repair_geotagging(path_polygon,
                      path_geotagging):

    print("Membaca data ...")

    gdf_poly = read_spatial(path_polygon)
    gdf_point = read_spatial(path_geotagging)

    # Pastikan koordinat geotag tersedia dan bertipe float
    if "geotag_latitude" not in gdf_point.columns:
        if "latitude_origin" in gdf_point.columns:
            gdf_point["geotag_latitude"] = pd.to_numeric(gdf_point["latitude_origin"], errors="coerce")
        else:
            gdf_point["geotag_latitude"] = gdf_point.geometry.y
    else:
        gdf_point["geotag_latitude"] = pd.to_numeric(gdf_point["geotag_latitude"], errors="coerce")

    if "geotag_longitude" not in gdf_point.columns:
        if "longitude_origin" in gdf_point.columns:
            gdf_point["geotag_longitude"] = pd.to_numeric(gdf_point["longitude_origin"], errors="coerce")
        else:
            gdf_point["geotag_longitude"] = gdf_point.geometry.x
    else:
        gdf_point["geotag_longitude"] = pd.to_numeric(gdf_point["geotag_longitude"], errors="coerce")

    # ============================================
    # CRS
    # ============================================

    gdf_poly = gdf_poly.to_crs(gdf_point.crs)

    # ============================================
    # SPATIAL JOIN
    # ============================================

    print("Spatial join ...")

    # Ambil atribut esensial dari gdf_poly agar tidak bentrok nama kolom dengan gdf_point
    poly_cols = ["geometry", "idsubsls"]
    if "idsls" in gdf_poly.columns:
        poly_cols.append("idsls")
    
    gdf_poly_join = gdf_poly[poly_cols].copy()
    rename_map = {"idsubsls": "idsubsls_overlay"}
    if "idsls" in gdf_poly.columns:
        rename_map["idsls"] = "idsls_overlay"
    gdf_poly_join = gdf_poly_join.rename(columns=rename_map)

    # Gunakan intersects agar titik pada garis batas poligon tidak menghasilkan NaN
    joined = gpd.sjoin(
        gdf_point,
        gdf_poly_join,
        how="left",
        predicate="intersects"
    )

    # ============================================
    # EVALUASI HOME POLYGON & DUAL-LEVEL HIERARCHY
    # ============================================

    clean_sub_pt = joined["level_6_full_code"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    clean_sub_ov = joined["idsubsls_overlay"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    if "level_5_full_code" in joined.columns:
        clean_sls_pt = joined["level_5_full_code"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    elif "idsls" in joined.columns:
        clean_sls_pt = joined["idsls"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    else:
        clean_sls_pt = clean_sub_pt.str[:14]

    if "idsls_overlay" in joined.columns:
        clean_sls_ov = joined["idsls_overlay"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    else:
        clean_sls_ov = clean_sub_ov.str[:14]

    # Kecocokan tingkat SubSLS (16-digit) ATAU tingkat SLS (14-digit)
    match_subsls = (clean_sub_ov == clean_sub_pt) & (~clean_sub_ov.isin(["", "nan", "None"]))
    match_sls = (clean_sls_ov == clean_sls_pt) & (~clean_sls_ov.isin(["", "nan", "None"]))
    match_sls_fallback = (clean_sub_ov.str[:14] == clean_sub_pt.str[:14]) & (~clean_sub_ov.isin(["", "nan", "None"]))

    joined["is_inside_home"] = match_subsls | match_sls | match_sls_fallback

    # Deduplikasi untuk titik di garis batas antar poligon:
    # Prioritaskan baris yang cocok dengan home SLS/SubSLS
    if joined.index.duplicated().any():
        joined = joined.reset_index()
        joined = joined.sort_values(by=["index", "is_inside_home"], ascending=[True, False])
        joined = joined.drop_duplicates(subset=["index"], keep="first")
        joined = joined.set_index("index")

    # IMMUTABLE WHITELIST DARI MODEL 3:
    # Jika titik sudah diidentifikasi Model 3 dengan flag_repair == 0:
    # Titik tersebut DIJAMIN 100% berada di home SLS-nya, HARAM DIGESER!
    if "flag_repair" in joined.columns:
        model3_flag = pd.to_numeric(joined["flag_repair"], errors="coerce").fillna(1).astype(int)
        is_model3_inside = (model3_flag == 0)
        joined["is_inside_home"] = np.where(is_model3_inside, True, joined["is_inside_home"])
        joined["flag_repair"] = np.where(is_model3_inside, 0, np.where(joined["is_inside_home"], 0, 1))
    else:
        joined["flag_repair"] = np.where(joined["is_inside_home"], 0, 1)

    # ============================================
    # UNIQUE BANG
    # ============================================

    joined["no_bang_clean"] = pd.to_numeric(
        joined["no_bang"],
        errors="coerce"
    ).fillna(0).astype(int)

    joined["no_bang_str"] = (
        joined["no_bang_clean"]
        .astype(str)
        .str.zfill(4)
    )

    joined["unique_bang"] = (
        joined["level_6_full_code"].astype(str)
        + "#"
        + joined["no_bang_str"]
    )

    # ============================================
    # INISIALISASI KOORDINAT EDITED (IMMUTABLE GUARD)
    # Default nilai edited WAJIB identik 100% dengan koordinat mentah asli!
    # Titik valid (flag_repair == 0) TIDAK BOLEH disentuh atau digeser ke median!
    # ============================================

    joined["latitude_edited"] = joined["geotag_latitude"]
    joined["longitude_edited"] = joined["geotag_longitude"]
    joined["repair_status"] = "original_inside"

    # ============================================
    # PROJECT TO METER
    # ============================================

    gdf_point_proj = joined.to_crs(3857)
    gdf_poly_proj = gdf_poly.to_crs(3857)

    joined["geometry_proj"] = gdf_point_proj.geometry.values
    gdf_poly["geometry_proj"] = gdf_poly_proj.geometry.values

    # ============================================
    # VALID POINTS (TITIK INSIDE SLS)
    # ============================================

    valid_points = joined[
        joined["flag_repair"] == 0
    ].copy()

    # ============================================
    # REPAIR HANYA UNTUK TITIK OFFSIDE (flag_repair == 1)
    # ============================================

    repair_idx = joined["flag_repair"] == 1
    total_offside = repair_idx.sum()

    print(f"Repair titik offside ({total_offside} titik) ...")

    for idx, row in joined[repair_idx].iterrows():

        lat_new, lon_new, status = find_repair_coordinate(
            row,
            valid_points,
            gdf_poly
        )

        joined.at[idx, "latitude_edited"] = lat_new
        joined.at[idx, "longitude_edited"] = lon_new
        joined.at[idx, "repair_status"] = status
        if status == "already_inside_home":
            joined.at[idx, "flag_repair"] = 0

    # ============================================
    # PERBARUI GEOMETRI HANYA UNTUK TITIK REPAIR
    # Titik valid (flag_repair == 0) MEMPERTAHANKAN geometri asli 100%
    # ============================================

    if total_offside > 0:
        repaired_geoms = gpd.points_from_xy(
            joined.loc[repair_idx, "longitude_edited"],
            joined.loc[repair_idx, "latitude_edited"]
        )
        joined.loc[repair_idx, "geometry"] = repaired_geoms

    # ============================================
    # EVALUASI FLAG_POSITION
    # 0 = posisi asli tidak digeser, 1 = posisi diedit/digeser
    # ============================================

    lat_diff = np.abs(pd.to_numeric(joined["latitude_edited"], errors="coerce") - pd.to_numeric(joined["geotag_latitude"], errors="coerce"))
    lon_diff = np.abs(pd.to_numeric(joined["longitude_edited"], errors="coerce") - pd.to_numeric(joined["geotag_longitude"], errors="coerce"))
    joined["flag_position"] = np.where((lat_diff > 1e-7) | (lon_diff > 1e-7), 1, 0)
    joined["flag_position"] = np.where(joined["flag_repair"] == 0, 0, joined["flag_position"])

    gdf_result = gpd.GeoDataFrame(
        joined,
        geometry="geometry",
        crs="EPSG:4326"
    )

    # ============================================
    # CLEAN EXTRA GEOMETRY
    # ============================================

    gdf_result = clean_geometry_columns(
        gdf_result
    )

    # ============================================
    # AUTO SAVE
    # ============================================

    iddesa = os.path.basename(
        path_geotagging
    ).split("_")[0]

    folder_output = "01 - data/03-geotagging-edited"

    os.makedirs(folder_output, exist_ok=True)

    path_output = os.path.join(
        folder_output,
        f"{iddesa}_geotagging_edited.geojson"
    )

    gdf_result.to_file(
        path_output,
        driver="GeoJSON"
    )

    print(f"Output saved: {path_output}")

    print("Selesai")

    return gdf_result


# =========================================================
# 6. REFACTOR FIELDS FUNCTION
# =========================================================

def refactor_fields(joined):

    if "idsls" not in joined.columns:
        if "level_6_full_code" in joined.columns:
            joined["idsls"] = joined["level_6_full_code"].astype(str).str[:14]
        else:
            joined["idsls"] = ""

    if "level_5_full_code" not in joined.columns:
        joined["level_5_full_code"] = joined["idsls"]

    if "id_assignment" not in joined.columns and "assignment_id" in joined.columns:
        joined["id_assignment"] = joined["assignment_id"]

    if "ec_keluarga" not in joined.columns:
        if "ada_keluarga_value" in joined.columns:
            joined["ec_keluarga"] = joined["ada_keluarga_value"].astype(str).isin(["1", "true", "True"])
        elif "kk" in joined.columns:
            joined["ec_keluarga"] = pd.to_numeric(joined["kk"], errors="coerce").fillna(0) > 0
        else:
            joined["ec_keluarga"] = False

    if "jumlah_usaha_ditemukan" not in joined.columns:
        if "usaha" in joined.columns:
            joined["jumlah_usaha_ditemukan"] = joined["usaha"]
        else:
            joined["jumlah_usaha_ditemukan"] = 0

    if "kode_bang_value" not in joined.columns:
        joined["kode_bang_value"] = 0

    # flag_repair_sls dievaluasi berdasarkan kesesuaian overlay SLS vs home SLS
    if "idsls_overlay" in joined.columns:
        ov_sls = joined["idsls_overlay"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    elif "idsubsls_overlay" in joined.columns:
        ov_sls = joined["idsubsls_overlay"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str[:14]
    else:
        ov_sls = ""

    hm_sls = joined["level_5_full_code"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    joined["flag_repair_sls"] = np.where(
        (ov_sls == hm_sls) & (~ov_sls.isin(["", "nan", "None"])),
        0,
        1
    )
    if "flag_repair" in joined.columns:
        joined["flag_repair_sls"] = np.where(joined["flag_repair"] == 0, 0, joined["flag_repair_sls"])
        if "flag_position" in joined.columns:
            joined["flag_position"] = np.where(joined["flag_repair"] == 0, 0, joined["flag_position"])

    joined["latitude_origin"] = joined["geotag_latitude"]
    joined["longitude_origin"] = joined["geotag_longitude"]

    joined["kk"] = np.where(
        joined["ec_keluarga"]
        .astype(str)
        .str.lower() == "true",
        1,
        0
    )

    joined["btt"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        .isin([2, 3]),
        1,
        0
    )

    joined["bttk"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        == 11,
        1,
        0
    )

    joined["bku"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        == 1,
        1,
        0
    )

    joined["bbtt_nonusaha"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        .isin([4, 5, 6]),
        1,
        0
    )

    joined["usaha"] = pd.to_numeric(
        joined["jumlah_usaha_ditemukan"],
        errors="coerce"
    ).fillna(0).astype(int)

    if "idsubsls_overlay" in joined.columns:
        joined = joined.rename(columns={
            "idsubsls_overlay": "idsubsls"
        })

    if "assignment_id" not in joined.columns and "id_assignment" in joined.columns:
        joined["assignment_id"] = joined["id_assignment"]

    if "idsubsls_origin" not in joined.columns and "level_6_full_code" in joined.columns:
        joined["idsubsls_origin"] = joined["level_6_full_code"]

    if "sls" not in joined.columns:
        joined["sls"] = joined.get("level_6_name", joined.get("nmsls", ""))

    # Sinkronisasi koordinat geotag jika digeser
    if "latitude_edited" in joined.columns:
        joined["geotag_latitude"] = joined["latitude_edited"]
    if "longitude_edited" in joined.columns:
        joined["geotag_longitude"] = joined["longitude_edited"]

    # Pertahankan semua kolom mentah asli tanpa pemangkasan whitelist
    drop_temp = [c for c in ["index_right", "geometry_proj"] if c in joined.columns]
    if drop_temp:
        joined = joined.drop(columns=drop_temp)

    joined = clean_geometry_columns(
        joined
    )

    return joined


# =========================================================
# 7. WORKER FUNCTION & BATCH PROCESSING (PARALLEL)
# =========================================================

def _process_single_desa(path_geo, folder_polygon, folder_output):
    filename = os.path.basename(path_geo)
    iddesa = filename.split("_")[0]
    path_polygon = os.path.join(
        folder_polygon,
        f"final_sls_251_{iddesa}.geojson"
    )

    if not os.path.exists(path_polygon):
        print(f"[{iddesa}] Polygon tidak ditemukan: {path_polygon}")
        return {
            "iddesa": iddesa,
            "status": "polygon_not_found"
        }

    try:
        print(f"[{iddesa}] Memulai proses repair...")
        result = repair_geotagging(
            path_polygon=path_polygon,
            path_geotagging=path_geo
        )

        result = refactor_fields(result)
        result = clean_geometry_columns(result)

        path_output = os.path.join(
            folder_output,
            f"{iddesa}_geotagging_edited.geojson"
        )

        result.to_file(
            path_output,
            driver="GeoJSON"
        )
        print(f"[{iddesa}] SELESAI -> {path_output}")
        return {
            "iddesa": iddesa,
            "status": "success"
        }
    except Exception as e:
        print(f"[{iddesa}] ERROR: {e}")
        return {
            "iddesa": iddesa,
            "status": str(e)
        }


def batch_repair_geotagging(
    folder_polygon="01 - data/01-peta-251",
    folder_geotagging="01 - data/02-geotagging",
    max_workers=5
):

    list_geotagging = glob.glob(
        os.path.join(
            folder_geotagging,
            "*_geotagging.geojson"
        )
    )

    print("=" * 60)
    print(f"TOTAL DESA    : {len(list_geotagging)}")
    print(f"PARALLEL POOL : {max_workers} WORKERS")
    print("=" * 60)

    folder_output = "01 - data/03-geotagging-edited"
    os.makedirs(folder_output, exist_ok=True)

    success = []
    failed = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_single_desa, path_geo, folder_polygon, folder_output): path_geo
            for path_geo in list_geotagging
        }
        for future in as_completed(futures):
            res = future.result()
            if res.get("status") == "success":
                success.append(res)
            else:
                failed.append(res)

    print("\n" + "=" * 60)
    print("SELESAI BATCH REPAIR")
    print("=" * 60)
    print(f"SUCCESS : {len(success)}")
    print(f"FAILED  : {len(failed)}")

    return {
        "success": pd.DataFrame(success),
        "failed": pd.DataFrame(failed)
    }