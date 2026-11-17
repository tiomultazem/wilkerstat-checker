"""
Modul Sinkronisasi Titik dan Penyesuaian Kompatibilitas Model3.
Menimpa titik di final landmark dengan koordinat valid dari moved_failed.geojson.
"""
import os
import json
import shutil
import sqlite3


def sync_final_landmark(moved_file: str, final_file: str, db_path: str = None):
    print("=" * 60)
    print("  SINKRONISASI TITIK & ATRIBUT MODEL3")
    print("=" * 60)

    if not os.path.exists(moved_file):
        print(f"[ERROR] Berkas {moved_file} tidak ditemukan.")
        return False

    if not os.path.exists(final_file):
        print(f"[ERROR] Berkas {final_file} tidak ditemukan.")
        return False

    # 1. Baca moved_failed.geojson
    print(f"1. Membaca {os.path.basename(moved_file)}...")
    with open(moved_file, "r", encoding="utf-8") as f:
        moved_data = json.load(f)

    moved_map = {}
    for feat in moved_data.get("features", []):
        props = feat.get("properties") or {}
        aid = props.get("assignment_id") or props.get("id_assignment")
        coords = feat.get("geometry", {}).get("coordinates")
        lat_ed = props.get("latitude_edited")
        lon_ed = props.get("longitude_edited")
        idsub = props.get("idsubsls_origin") or props.get("level_6_full_code")

        # Pastikan atribut kompatibilitas Model3
        props["level_6_full_code"] = idsub
        props["geotag_latitude"] = lat_ed
        props["geotag_longitude"] = lon_ed
        props["flag_repair"] = 0
        props["status"] = "INSIDE"

        if aid and coords and lat_ed is not None and lon_ed is not None:
            moved_map[aid] = {
                "coords": coords,
                "lat": float(lat_ed),
                "lon": float(lon_ed),
                "idsub": idsub,
                "props": props,
                "geom": feat.get("geometry")
            }

    print(f"   -> Memuat {len(moved_map)} titik valid dari moved_failed.")

    # 2. Backup berkas final landmark
    bak_file = final_file + ".bak"
    print(f"\n2. Membuat salinan cadangan: {os.path.basename(bak_file)}...", end=" ", flush=True)
    shutil.copyfile(final_file, bak_file)
    print("Selesai.")

    # 3. Baca dan perbarui final landmark
    print(f"\n3. Memperbarui {os.path.basename(final_file)}...")
    with open(final_file, "r", encoding="utf-8") as f:
        final_data = json.load(f)

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

    updated_count = 0
    for feat in final_data.get("features", []):
        props = feat.get("properties") or {}
        aid = props.get("assignment_id") or props.get("id_assignment")

        if aid in moved_map:
            m = moved_map[aid]
            # Replace geometry koordinat dengan pembulatan 8 desimal
            lat_f = round(float(m["lat"]), 8)
            lon_f = round(float(m["lon"]), 8)
            feat["geometry"] = {
                "type": "Point",
                "coordinates": [lon_f, lat_f]
            }

            # Update atribut koordinat & flag
            props["latitude_edited"] = lat_f
            props["longitude_edited"] = lon_f
            props["flag_position"] = 1
            props["flag_repair"] = 0
            if not props.get("idsubsls_origin"):
                props["idsubsls_origin"] = str(m["idsub"])
            props["idsubsls_edited"] = str(m["idsub"])
            updated_count += 1
        else:
            if "flag_repair" not in props:
                props["flag_repair"] = 0
            if "flag_position" not in props:
                props["flag_position"] = 0

        # Kunci atribut HANYA 22 kolom baku dot_col.csv tanpa sampah
        clean_props = {}
        for col in TARGET_COLS:
            val = props.get(col, None)
            if col in ("latitude_origin", "longitude_origin", "latitude_edited", "longitude_edited") and val is not None:
                try:
                    val = round(float(val), 8)
                except Exception:
                    pass
            elif col in ("flag_repair", "flag_position", "no_bang", "kode_bang_value") and val is not None:
                try:
                    val = int(val)
                except Exception:
                    val = 0
            clean_props[col] = val
        feat["properties"] = clean_props

        # Pastikan koordinat geometry dibulatkan 8 desimal
        coords = feat.get("geometry", {}).get("coordinates")
        if coords and len(coords) >= 2:
            try:
                feat["geometry"]["coordinates"] = [round(float(coords[0]), 8), round(float(coords[1]), 8)]
            except Exception:
                pass

    while True:
        try:
            with open(final_file, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, separators=(',', ':'))
            break
        except (PermissionError, OSError) as e:
            print("\n" + "=" * 65)
            print("  [PERINGATAN] BERKAS MASTER FINAL LANDMARK SEDANG DIKUNCI APLIKASI LAIN!")
            print(f"  Berkas : {final_file}")
            print("  Aplikasi (seperti QGIS atau editor lain) sedang membuka berkas ini.")
            print("  -> Silakan TUTUP / HAPUS LAYER berkas tersebut di QGIS sekarang!")
            print("=" * 65)
            jawab = input("Tekan [Enter] setelah menutup aplikasi untuk mencoba menyimpan ulang (atau ketik 'batal'): ").strip().lower()
            if jawab in ("batal", "exit", "quit"):
                raise e

    print(f"   -> Berhasil menimpa {updated_count} titik di master final landmark.")

    # 4. Sinkronisasi DB (jika file DB diberikan dan ada)
    if db_path and os.path.exists(db_path):
        print(f"\n4. Sinkronisasi ke basis data SQLite: {os.path.basename(db_path)}...")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            db_updated = 0
            for aid, m in moved_map.items():
                cur.execute("""
                    UPDATE dot
                    SET lat_edited = ?, lon_edited = ?, flag_repair = 0, status = 'INSIDE', flag_position = 1
                    WHERE assignment_id = ?
                """, (m["lat"], m["lon"], aid))
                if cur.rowcount > 0:
                    db_updated += cur.rowcount
            conn.commit()
            conn.close()
            print(f"   -> {db_updated} baris di tabel 'dot' berhasil diperbarui.")
        except Exception as e:
            print(f"   [Peringatan] Gagal sinkronisasi ke DB: {e}")

    print("\n[SELESAI] Sinkronisasi landmark final berhasil.")
    return True

