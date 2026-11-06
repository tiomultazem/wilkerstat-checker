import geopandas as gpd
import pandas as pd
import numpy as np
import os
import glob


# =========================================================
# 1. AUTO READ SPATIAL
# =========================================================

def read_spatial(path):

    path_lower = path.lower()

    if path_lower.endswith(".geojson"):

        return gpd.read_file(path)

    elif path_lower.endswith(".gpkg"):

        return gpd.read_file(path)

    elif path_lower.endswith(".shp"):

        return gpd.read_file(path)

    else:

        raise ValueError(
            f"Format tidak didukung: {path}"
        )


# =========================================================
# 2. AUTO READ CSV
# =========================================================

def read_csv_auto(path):

    return pd.read_csv(
        path,
        sep=None,
        engine="python",
        encoding_errors="ignore",
        on_bad_lines="skip",
        dtype=str
    )


# =========================================================
# 3. CLEAN GEOMETRY
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
# 4. STANDARDIZE COLUMNS
# =========================================================

def standardize_columns(df):

    # ============================================
    # LOWERCASE COLUMNS
    # ============================================

    df.columns = [
        str(c).lower()
        for c in df.columns
    ]

    # ============================================
    # CHARACTER COLUMNS
    # ============================================

    char_cols = [

        "idsubsls",
        "idsubsls_261",
        "idsubsls_origin",

        "kdprov",
        "nmprov",

        "kdkab",
        "nmkab",

        "kdkec",
        "nmkec",

        "kddesa",
        "nmdesa",

        "idsls",
        "nmsls",

        "id_assignment",
        "assignment_id",
        "idsubsls_edited",
        "unique_bang"

    ]

    for col in char_cols:

        if col in df.columns:

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.replace("nan", "", regex=False)
                .str.replace("None", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.strip()
            )

    # ============================================
    # ZERO PADDING
    # ============================================

    if "kdprov" in df.columns:

        df["kdprov"] = (
            df["kdprov"]
            .str.zfill(2)
        )

    if "kdkab" in df.columns:

        df["kdkab"] = (
            df["kdkab"]
            .str.zfill(2)
        )

    if "kdkec" in df.columns:

        df["kdkec"] = (
            df["kdkec"]
            .str.zfill(3)
        )

    if "kddesa" in df.columns:

        df["kddesa"] = (
            df["kddesa"]
            .str.zfill(3)
        )

    # ============================================
    # INTEGER COLUMNS
    # ============================================

    int_cols = [

        "flag_position",
        "flag_repair",
        "flag_repair_sls",
        "no_bang",
        "kode_bang_value",

        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    for col in int_cols:

        if col in df.columns:

            df[col] = (
                pd.to_numeric(
                    df[col],
                    errors="coerce"
                )
                .fillna(0)
                .astype("int64")
            )

    # ============================================
    # FLOAT COLUMNS
    # ============================================

    float_cols = [

        "latitude_origin",
        "longitude_origin",

        "latitude_edited",
        "longitude_edited"

    ]

    for col in float_cols:

        if col in df.columns:

            df[col] = (
                pd.to_numeric(
                    df[col],
                    errors="coerce"
                )
                .astype(float)
            )
    
    return df


# =========================================================
# 5. READ & MERGE GEOTAGGING
# =========================================================

def read_merge_geotagging(
    folder_path,
    idkab
):

    files = glob.glob(
        os.path.join(
            folder_path,
            "*.geojson"
        )
    )

    files = [
        f for f in files
        if (
            "geotagging"
            in
            os.path.basename(f).lower()
        )
        and
        (
            os.path.basename(f).startswith(
                str(idkab)
            )
        )
    ]

    print(f"Total file geotagging: {len(files)}")

    if len(files) == 0:

        raise ValueError(
            f"Tidak ada file geotagging untuk idkab {idkab}"
        )

    gdfs = []

    for path in files:

        try:

            print(
                f"Loading: {os.path.basename(path)}"
            )

            gdf = gpd.read_file(path)

            gdf = clean_geometry_columns(
                gdf
            )

            gdf = standardize_columns(
                gdf
            )

            gdfs.append(gdf)

        except Exception as e:

            print(
                f"ERROR {os.path.basename(path)}: {e}"
            )

    if len(gdfs) == 0:

        raise ValueError(
            "Tidak ada geotagging berhasil dibaca"
        )

    merged = pd.concat(
        gdfs,
        ignore_index=True
    )

    merged = gpd.GeoDataFrame(
        merged,
        geometry="geometry",
        crs="EPSG:4326"
    )

    print(
        f"Total records: {len(merged)}"
    )

    return merged


# =========================================================
# 6. OVERLAY WILKERSTAT
# =========================================================

def overlay_wilkerstat(
    gdf_titik,
    gdf_wilker
):

    print("Overlay wilkerstat ...")

    gdf_wilker = gdf_wilker.to_crs(
        gdf_titik.crs
    )

    gdf_wilker = standardize_columns(
        gdf_wilker
    )

    if "idsubsls" in gdf_wilker.columns:

        gdf_wilker = gdf_wilker.rename(columns={
            "idsubsls": "idsubsls_261"
        })

    cols_wilker = [
        "idsubsls_261",
        "geometry"
    ]

    cols_exist = [
        c for c in cols_wilker
        if c in gdf_wilker.columns
    ]

    joined = gpd.sjoin(
        gdf_titik,
        gdf_wilker[cols_exist],
        how="left",
        predicate="intersects"
    )

    print(
        "NULL IDSUBSLS:",
        joined["idsubsls_261"]
        .isna()
        .sum()
    )

    joined = standardize_columns(
        joined
    )

    return joined


# =========================================================
# 7. SAVE OUTPUT GS
# =========================================================

def save_output_gs(
    gdf,
    output_path
):

    gdf = clean_geometry_columns(
        gdf
    )

    while True:
        try:
            gdf.to_file(
                output_path,
                driver="GeoJSON"
            )
            print(f"Saved GS: {output_path}")
            break
        except (PermissionError, OSError) as e:
            print("\n" + "=" * 65)
            print("  [PERINGATAN] BERKAS SEDANG DIBUKA / DIKUNCI APLIKASI LAIN!")
            print(f"  Berkas : {output_path}")
            print("  Aplikasi (seperti QGIS atau GIS viewer) sedang mengunci berkas ini.")
            print("  -> Silakan TUTUP / HAPUS LAYER berkas tersebut di QGIS sekarang!")
            print("=" * 65)
            jawab = input("Tekan [Enter] setelah menutup aplikasi untuk mencoba menyimpan ulang (atau ketik 'batal'): ").strip().lower()
            if jawab in ("batal", "exit", "quit"):
                raise e


# =========================================================
# 8. AGGREGATE BANGUNAN
# =========================================================

def aggregate_bangunan(df):

    agg = (
        df
        .groupby("unique_bang")
        .agg({

            "idsubsls_261": "first",

            "kk": "sum",
            "btt": "min",
            "bttk": "max",
            "bku": "sum",
            "bbtt_nonusaha": "max",
            "usaha": "sum"

        })
        .reset_index()
    )

    agg = standardize_columns(
        agg
    )

    return agg


# =========================================================
# 9. AGGREGATE SUBSLS
# =========================================================

def aggregate_subsls(df):

    agg = (
        df
        .groupby("idsubsls_261")
        .agg({

            "kk": "sum",
            "btt": "sum",
            "bttk": "sum",
            "bku": "sum",
            "bbtt_nonusaha": "sum",
            "usaha": "sum"

        })
        .reset_index()
    )

    agg = standardize_columns(
        agg
    )

    return agg


# =========================================================
# 10. JOIN MASTER SUBSLS
# =========================================================

def join_master_subsls(
    master_df,
    agg_df
):

    master_df = standardize_columns(
        master_df
    )

    agg_df = standardize_columns(
        agg_df
    )

    print("MASTER IDSUBSLS SAMPLE:")
    print(master_df["idsubsls"].head())

    print("AGG IDSUBSLS SAMPLE:")
    print(agg_df["idsubsls_261"].head())

    print("MATCH COUNT:")

    print(
        agg_df["idsubsls_261"]
        .isin(master_df["idsubsls"])
        .sum()
    )

    master_cols = [

        "idsubsls",
        "kdprov",
        "nmprov",
        "kdkab",
        "nmkab",
        "kdkec",
        "nmkec",
        "kddesa",
        "nmdesa",
        "idsls",
        "nmsls"

    ]

    master_cols = [
        c for c in master_cols
        if c in master_df.columns
    ]

    master_df = master_df[
        master_cols
    ].copy()

    agg_cols = [

        "idsubsls_261",
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    agg_cols = [
        c for c in agg_cols
        if c in agg_df.columns
    ]

    agg_df = agg_df[
        agg_cols
    ].copy()

    result = master_df.merge(
        agg_df,
        left_on="idsubsls",
        right_on="idsubsls_261",
        how="left"
    )

    numeric_cols = [
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"
    ]

    for col in numeric_cols:

        if col in result.columns:

            result[col] = (
                pd.to_numeric(
                    result[col],
                    errors="coerce"
                )
                .fillna(0)
                .astype("int64")
            )

    result = standardize_columns(
        result
    )

    return result


# =========================================================
# 11. REFACTOR MUATAN
# =========================================================

def refactor_muatan(df):

    cols = [

        "idsubsls",
        "kdprov",
        "nmprov",
        "kdkab",
        "nmkab",
        "kdkec",
        "nmkec",
        "kddesa",
        "nmdesa",
        "idsls",
        "nmsls",
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    cols = [
        c for c in cols
        if c in df.columns
    ]

    output = df[cols].copy()

    output = output.rename(columns={
        "idsubsls": "idsubsls_261"
    })

    output = standardize_columns(
        output
    )

    final_cols = [

        "idsubsls_261",
        "kdprov",
        "nmprov",
        "kdkab",
        "nmkab",
        "kdkec",
        "nmkec",
        "kddesa",
        "nmdesa",
        "idsls",
        "nmsls",
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    final_cols = [
        c for c in final_cols
        if c in output.columns
    ]

    output = output[
        final_cols
    ].copy()

    return output


# =========================================================
# 12. SAVE MUATAN
# =========================================================

def save_output_muatan(
    df,
    output_path
):

    while True:
        try:
            df.to_csv(
                output_path,
                index=False
            )
            print(f"Saved Muatan: {output_path}")
            break
        except (PermissionError, OSError) as e:
            print("\n" + "=" * 65)
            print("  [PERINGATAN] BERKAS CSV MUATAN SEDANG DIBUKA / DIKUNCI APLIKASI LAIN!")
            print(f"  Berkas : {output_path}")
            print("  Aplikasi (seperti Excel) sedang membuka dan mengunci berkas ini.")
            print("  -> Silakan TUTUP berkas tersebut di Excel sekarang!")
            print("=" * 65)
            jawab = input("Tekan [Enter] setelah menutup aplikasi untuk mencoba menyimpan ulang (atau ketik 'batal'): ").strip().lower()
            if jawab in ("batal", "exit", "quit"):
                raise e


# =========================================================
# 13. MAIN PROCESS
# =========================================================

def proses_muatan(
    geotagging_folder,
    idkab,
    wilkerstat_261_path,
    msubsls_26_1_path,
    output_path_gs,
    output_path_muatan
):

    print("=" * 60)
    print("READ GEOTAGGING")
    print("=" * 60)

    gdf_titik = read_merge_geotagging(
        geotagging_folder,
        idkab
    )

    print("=" * 60)
    print("READ WILKERSTAT")
    print("=" * 60)

    gdf_wilker = read_spatial(
        wilkerstat_261_path
    )

    print("=" * 60)
    print("OVERLAY")
    print("=" * 60)

    joined = overlay_wilkerstat(
        gdf_titik,
        gdf_wilker
    )

    joined = standardize_columns(
        joined
    )

    print("=" * 60)
    print("PREPARE GS")
    print("=" * 60)

    gs_internal = joined.copy()

    gs_internal["unique_bang"] = (
        gs_internal["level_6_full_code"].astype(str)
        + "#"
        + (
            gs_internal["no_bang"]
            .astype(int)
            .astype(str)
            .str.zfill(4)
        )
    )

    lat_diff = (
        pd.to_numeric(gs_internal["latitude_origin"], errors="coerce").fillna(0)
        - pd.to_numeric(gs_internal["latitude_edited"], errors="coerce").fillna(0)
    ).abs()
    lon_diff = (
        pd.to_numeric(gs_internal["longitude_origin"], errors="coerce").fillna(0)
        - pd.to_numeric(gs_internal["longitude_edited"], errors="coerce").fillna(0)
    ).abs()

    # Titik dianggap bergeser HANYA jika berpindah posisi > 1e-6 derajat (~0.1m)
    moved_mask = (lat_diff > 1e-6) | (lon_diff > 1e-6)
    gs_internal["flag_position"] = np.where(moved_mask, 1, 0)

    # Inisialisasi flag_repair jika belum ada
    if "flag_repair" not in gs_internal.columns:
        gs_internal["flag_repair"] = 0

    if "flag_position" not in gs_internal.columns:
        lat_diff = np.abs(pd.to_numeric(gs_internal.get("latitude_edited", 0), errors="coerce") - pd.to_numeric(gs_internal.get("latitude_origin", 0), errors="coerce"))
        lon_diff = np.abs(pd.to_numeric(gs_internal.get("longitude_edited", 0), errors="coerce") - pd.to_numeric(gs_internal.get("longitude_origin", 0), errors="coerce"))
        gs_internal["flag_position"] = np.where((lat_diff > 1e-7) | (lon_diff > 1e-7), 1, 0)

    # Guard mutlak: titik yang flag_repair == 0 (di dalam SLS) WAJIB flag_position = 0
    inside_mask = pd.to_numeric(gs_internal["flag_repair"], errors="coerce").fillna(0) == 0
    gs_internal.loc[inside_mask, "flag_position"] = 0
    # Pastikan koordinat edited titik inside sama persis dengan origin
    gs_internal.loc[inside_mask, "latitude_edited"] = gs_internal.loc[inside_mask, "latitude_origin"]
    gs_internal.loc[inside_mask, "longitude_edited"] = gs_internal.loc[inside_mask, "longitude_origin"]

    # Pastikan geometri konsisten dengan latitude_edited dan longitude_edited
    edited_mask = gs_internal["flag_position"] == 1
    if edited_mask.any():
        gs_internal.loc[edited_mask, "geometry"] = gpd.points_from_xy(
            gs_internal.loc[edited_mask, "longitude_edited"],
            gs_internal.loc[edited_mask, "latitude_edited"]
        )

    # =========================================================
    # SUSUN OUTPUT FINAL MASTER PERSIS SESUAI SPESIFIKASI dot_col.csv (22 KOLOM + GEOMETRY)
    # =========================================================
    TARGET_COLS = [
        "assignment_id",
        "flag_repair",
        "flag_position",
        "idsubsls_origin",
        "idsubsls_edited",
        "latitude_origin",
        "longitude_origin",
        "latitude_edited",
        "longitude_edited",
        "no_bang",
        "kode_bang_value",
        "kdprov",
        "nmprov",
        "kdkab",
        "nmkab",
        "kdkec",
        "nmkec",
        "kddesa",
        "nmdesa",
        "idsls",
        "nmsls",
        "sls"
    ]

    gs_clean = pd.DataFrame()
    gs_clean["assignment_id"] = gs_internal.get("assignment_id", gs_internal.get("id_assignment", "")).astype(str)
    gs_clean["flag_repair"] = pd.to_numeric(gs_internal.get("flag_repair", 0), errors="coerce").fillna(0).astype(int)
    gs_clean["flag_position"] = pd.to_numeric(gs_internal.get("flag_position", 0), errors="coerce").fillna(0).astype(int)

    # Prioritaskan level_6_full_code (kode SLS rumah asli), fallback ke idsubsls_origin atau idsls jika kosong
    lvl6 = gs_internal.get("level_6_full_code", pd.Series("", index=gs_internal.index)).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    sub_orig = gs_internal.get("idsubsls_origin", pd.Series("", index=gs_internal.index)).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    sls_code = gs_internal.get("idsls", pd.Series("", index=gs_internal.index)).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    invalid_codes = ["", "nan", "None", "0", "00", "null"]

    valid_origin = np.where(~lvl6.isin(invalid_codes), lvl6,
                   np.where(~sub_orig.isin(invalid_codes), sub_orig, sls_code))
    gs_clean["idsubsls_origin"] = valid_origin

    sub_261 = gs_internal.get("idsubsls_261", pd.Series("", index=gs_internal.index)).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    sub_edit = gs_internal.get("idsubsls", pd.Series("", index=gs_internal.index)).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    valid_edited = np.where(~sub_261.isin(invalid_codes), sub_261,
                   np.where(~sub_edit.isin(invalid_codes), sub_edit, valid_origin))
    gs_clean["idsubsls_edited"] = valid_edited

    gs_clean["latitude_origin"] = pd.to_numeric(gs_internal.get("latitude_origin", gs_internal.get("geotag_latitude", 0)), errors="coerce").round(8)
    gs_clean["longitude_origin"] = pd.to_numeric(gs_internal.get("longitude_origin", gs_internal.get("geotag_longitude", 0)), errors="coerce").round(8)
    gs_clean["latitude_edited"] = pd.to_numeric(gs_internal.get("latitude_edited", gs_clean["latitude_origin"]), errors="coerce").round(8)
    gs_clean["longitude_edited"] = pd.to_numeric(gs_internal.get("longitude_edited", gs_clean["longitude_origin"]), errors="coerce").round(8)
    gs_clean["no_bang"] = pd.to_numeric(gs_internal.get("no_bang", 0), errors="coerce").fillna(0).astype(int)
    gs_clean["kode_bang_value"] = pd.to_numeric(gs_internal.get("kode_bang_value", 0), errors="coerce").fillna(0).astype(int)
    gs_clean["kdprov"] = gs_internal.get("kdprov", "").fillna("").astype(str)
    gs_clean["nmprov"] = gs_internal.get("nmprov", "").fillna("").astype(str)
    gs_clean["kdkab"] = gs_internal.get("kdkab", "").fillna("").astype(str)
    gs_clean["nmkab"] = gs_internal.get("nmkab", "").fillna("").astype(str)
    gs_clean["kdkec"] = gs_internal.get("kdkec", "").fillna("").astype(str)
    gs_clean["nmkec"] = gs_internal.get("nmkec", "").fillna("").astype(str)
    gs_clean["kddesa"] = gs_internal.get("kddesa", "").fillna("").astype(str)
    gs_clean["nmdesa"] = gs_internal.get("nmdesa", "").fillna("").astype(str)
    gs_clean["idsls"] = gs_internal.get("idsls", gs_clean["idsubsls_origin"].str[:14]).fillna("").astype(str)
    gs_clean["nmsls"] = gs_internal.get("nmsls", "").fillna("").astype(str)
    gs_clean["sls"] = gs_internal.get("sls", gs_internal.get("level_6_name", gs_clean["nmsls"])).fillna("").astype(str)

    gs_upload = gpd.GeoDataFrame(
        gs_clean[TARGET_COLS],
        geometry=gpd.points_from_xy(gs_clean["longitude_edited"], gs_clean["latitude_edited"]),
        crs="EPSG:4326"
    )

    save_output_gs(
        gs_upload,
        output_path_gs
    )

    print("=" * 60)
    print("AGGREGATE BANGUNAN")
    print("=" * 60)

    bangunan = aggregate_bangunan(
        gs_internal
    )

    print("=" * 60)
    print("AGGREGATE SUBSLS")
    print("=" * 60)

    subsls = aggregate_subsls(
        bangunan
    )

    print("=" * 60)
    print("READ MASTER SUBSLS")
    print("=" * 60)

    if msubsls_26_1_path and os.path.exists(msubsls_26_1_path):
        master_subsls = read_csv_auto(
            msubsls_26_1_path
        )

        print("=" * 60)
        print("JOIN MASTER")
        print("=" * 60)

        muatan = join_master_subsls(
            master_subsls,
            subsls
        )

        print("=" * 60)
        print("REFACTOR MUATAN")
        print("=" * 60)

        muatan = refactor_muatan(
            muatan
        )

        muatan['idsls'] = muatan['idsubsls_261'].str[:14]
        
        save_output_muatan(
            muatan,
            output_path_muatan
        )
    else:
        print(f"Berkas master subsls ({msubsls_26_1_path}) tidak ditemukan. Modul muatan dilewati.")
        muatan = None

    print("=" * 60)
    print("SELESAI")
    print("=" * 60)

    return {
        "gs_upload": gs_upload,
        "muatan": muatan
    }