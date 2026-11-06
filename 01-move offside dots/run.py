"""
=============================================================================
WilkerStat Checker — Pipeline Terpadu Pengolahan & Reposisi Titik Spasial SE2026
=============================================================================
Menyatukan seluruh modul (split, repair, muatan, extract, reposisi, sinkronisasi)
dalam antarmuka menu CLI interaktif dan mencatat seluruh output ke terminal & log.txt.
Diadaptasi dari repositori: https://github.com/PMSS-BPS/Pengolahan-Wilkerstat-SE2026
"""
import datetime
import os
import re
import sys
import time

# Pastikan working directory terkunci ke folder 01-move offside dots
MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(MODULE_ROOT)

# Tambahkan module/ ke sys.path
MODULE_DIR = os.path.join(MODULE_ROOT, "module")
if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)

# Auto-bersihkan residu berkas py lama di root 01 jika sudah ada di module/
for _legacy in ["split_data.py", "move-failed.py", "sync_final_landmark.py", "extract_failed.py"]:
    _p = os.path.join(MODULE_ROOT, _legacy)
    if os.path.isfile(_p):
        try:
            os.remove(_p)
        except Exception:
            pass

# Import seluruh modul dari module/
from module.split_data import split_geojson_per_desa
from module.move_failed import move_failed_points
from module.sync_final_landmark import sync_final_landmark
from module.extract_failed import extract_failed_dots
from module.s02_repair_geotagging import batch_repair_geotagging
from module.s03_perhitungan_muatan import proses_muatan


# ---------------------------------------------------------------------------
# DUAL LOGGER: Tulis serentak ke Terminal dan log.txt
# ---------------------------------------------------------------------------
class DualLogger:
    def __init__(self, log_path: str):
        self.terminal = sys.stdout
        self.log_file = open(log_path, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        try:
            self.log_file.write(message)
            self.log_file.flush()
        except Exception:
            pass

    def flush(self):
        self.terminal.flush()
        try:
            self.log_file.flush()
        except Exception:
            pass


LOG_PATH = os.path.join(MODULE_ROOT, "log.txt")
_logger = DualLogger(LOG_PATH)
sys.stdout = _logger
sys.stderr = _logger


def ask_input(prompt: str, default: str = "") -> str:
    """Meminta input pengguna di terminal dengan nilai default."""
    if default:
        rel = os.path.relpath(default, MODULE_ROOT) if (os.path.isabs(default) and os.path.exists(default)) else default
        display = f"{prompt} [default: {rel}]: "
    else:
        display = f"{prompt}: "

    val = input(display).strip().strip('"\'')
    result = val if val else default
    print(f"   -> Nilai: {result}")
    return result


def banner():
    print("\n" + "=" * 70)
    print("      WILKERSTAT CHECKER — PENGOLAHAN & REPOSISI TITIK SPASIAL")
    print(f"      Waktu Sesi: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"      Log Berkas: {LOG_PATH}")
    print("=" * 70)
    print("  [1] Split Data Poligon & Titik per-Desa")
    print("  [2] Batch Repair Geotagging (Tarik ke Batas SubSLS/SLS)")
    print("  [3] Hitung Muatan & Ekspor Final Landmark Master")
    print("  [4] Ekstrak Titik Gagal / Offside (flag_repair = 1)")
    print("  [5] Reposisi Titik Gagal / Interior Projection (move_failed)")
    print("  [6] Sinkronisasi Replacement Landmark Final (moved_failed -> final)")
    print("  [7] Jalankan Pipeline Penuh (Langkah 1 s.d. 6 End-to-End)")
    print("  [0] Keluar")
    print("=" * 70)


# ---------------------------------------------------------------------------
# FUNGSI MENU
# ---------------------------------------------------------------------------
def menu_split_data():
    def_peta = os.path.abspath(os.path.join(MODULE_ROOT, "..", "00-identify dots", "slsmentah fixed-2025sm1.geojson"))
    def_titik = os.path.abspath(os.path.join(MODULE_ROOT, "..", "00-identify dots", "titik hasil identifikasi.geojson"))
    def_poly_dir = os.path.join(MODULE_ROOT, "01 - data", "01-peta-251")
    def_geo_dir = os.path.join(MODULE_ROOT, "01 - data", "02-geotagging")

    peta_file = ask_input("Masukkan path berkas Poligon SLS", def_peta)
    titik_file = ask_input("Masukkan path berkas Titik Geotagging", def_titik)
    folder_poly = ask_input("Masukkan folder target Poligon per-Desa", def_poly_dir)
    folder_geo = ask_input("Masukkan folder target Titik per-Desa", def_geo_dir)

    split_geojson_per_desa(peta_file, titik_file, folder_poly, folder_geo)


def menu_batch_repair():
    def_poly = os.path.join(MODULE_ROOT, "01 - data", "01-peta-251")
    def_geo = os.path.join(MODULE_ROOT, "01 - data", "02-geotagging")

    folder_poly = ask_input("Masukkan folder Poligon split per-Desa", def_poly)
    folder_geo = ask_input("Masukkan folder Titik geotagging split", def_geo)
    workers_str = ask_input("Masukkan jumlah worker paralel", "5")
    try:
        workers = int(workers_str)
    except Exception:
        workers = 5

    batch_repair_geotagging(folder_polygon=folder_poly, folder_geotagging=folder_geo, max_workers=workers)


def menu_hitung_muatan(idkab: str = None):
    if not idkab:
        idkab = ask_input("Masukkan Kode Kabupaten (4 digit)", "6309")

    def_geo_edited = os.path.join(MODULE_ROOT, "01 - data", "03-geotagging-edited")
    def_wilkerstat = os.path.abspath(os.path.join(MODULE_ROOT, "..", "00-identify dots", "slsmentah fixed-2025sm1.geojson"))
    def_master_sub = os.path.join(MODULE_ROOT, "01 - data", "05-master-261", "msubsls_26_1.csv")
    def_out_gs = os.path.join(MODULE_ROOT, "03 - final", f"final_landmark_{idkab}_se_2026.geojson")
    def_out_muatan = os.path.join(MODULE_ROOT, "03 - final", f"{idkab}_muatan.csv")

    geo_folder = ask_input("Masukkan folder geotagging edited", def_geo_edited)
    wilkerstat_path = ask_input("Masukkan path peta Wilkerstat acuan", def_wilkerstat)
    master_sub_path = ask_input("Masukkan path master SubSLS CSV", def_master_sub)
    out_gs = ask_input("Masukkan target simpan Final Landmark GS", def_out_gs)
    out_muatan = ask_input("Masukkan target simpan data Muatan CSV", def_out_muatan)

    os.makedirs(os.path.dirname(os.path.abspath(out_gs)), exist_ok=True)

    proses_muatan(
        geotagging_folder=geo_folder,
        idkab=idkab,
        wilkerstat_261_path=wilkerstat_path,
        msubsls_26_1_path=master_sub_path,
        output_path_gs=out_gs,
        output_path_muatan=out_muatan
    )


def menu_ekstrak_gagal(idkab: str = "6309"):
    def_input = os.path.join(MODULE_ROOT, "03 - final", f"final_landmark_{idkab}_se_2026.geojson")
    if not os.path.exists(def_input):
        def_input = os.path.abspath(os.path.join(MODULE_ROOT, "..", "00-identify dots", "titik hasil identifikasi.geojson"))
    def_output = os.path.join(MODULE_ROOT, "failed.geojson")

    input_file = ask_input("Masukkan path berkas titik yang akan diekstrak", def_input)
    output_file = ask_input("Masukkan target simpan failed.geojson", def_output)

    extract_failed_dots(input_file, output_file)


def menu_reposisi_gagal():
    def_failed = os.path.join(MODULE_ROOT, "failed.geojson")
    def_poly = os.path.abspath(os.path.join(MODULE_ROOT, "..", "00-identify dots", "slsmentah fixed-2025sm1.geojson"))
    if not os.path.exists(def_poly):
        def_poly = os.path.join(MODULE_ROOT, "01 - data", "01-peta-251")
    def_out = os.path.join(MODULE_ROOT, "moved_failed.geojson")

    failed_file = ask_input("Masukkan path berkas titik gagal (failed.geojson)", def_failed)
    poly_source = ask_input("Masukkan sumber Poligon SLS (berkas GeoJSON atau folder split)", def_poly)
    out_file = ask_input("Masukkan target simpan moved_failed.geojson", def_out)

    move_failed_points(failed_file, poly_source, out_file)


def menu_sinkronisasi_final(idkab: str = "6309"):
    def_moved = os.path.join(MODULE_ROOT, "moved_failed.geojson")
    def_final = os.path.join(MODULE_ROOT, "03 - final", f"final_landmark_{idkab}_se_2026.geojson")
    def_db = os.path.abspath(os.path.join(MODULE_ROOT, "..", "data", "wilkerstat.db"))

    moved_file = ask_input("Masukkan path moved_failed.geojson", def_moved)
    final_file = ask_input("Masukkan path master Final Landmark target", def_final)
    db_file = ask_input("Masukkan path database wilkerstat.db (opsional)", def_db if os.path.exists(def_db) else "")

    sync_final_landmark(moved_file, final_file, db_file if db_file else None)


def menu_pipeline_penuh():
    print("\n" + "=" * 70)
    print(">>> MEMULAI PIPELINE PENUH (LANGKAH 1 s.d. 6 BERURUTAN)")
    print("=" * 70)

    idkab = ask_input("Masukkan Kode Kabupaten", "6309")
    start_total = time.time()

    print("\n--- [LANGKAH 1/6] SPLIT DATASET PER-DESA ---")
    menu_split_data()

    print("\n--- [LANGKAH 2/6] BATCH REPAIR GEOTAGGING ---")
    menu_batch_repair()

    print("\n--- [LANGKAH 3/6] PERHITUNGAN MUATAN & MASTER GS ---")
    menu_hitung_muatan(idkab)

    print("\n--- [LANGKAH 4/6] EKSTRAKSI TITIK OFFSIDE / GAGAL ---")
    menu_ekstrak_gagal(idkab)

    print("\n--- [LANGKAH 5/6] REPOSISI TITIK GAGAL (INTERIOR PROJECTION) ---")
    menu_reposisi_gagal()

    print("\n--- [LANGKAH 6/6] SINKRONISASI REPLACEMENT MASTER FINAL ---")
    menu_sinkronisasi_final(idkab)

    elapsed = round(time.time() - start_total, 2)
    print("\n" + "=" * 70)
    print(f">>> SELURUH PIPELINE PENUH SELESAI DALAM {elapsed} DETIK.")
    print(f">>> Berkas Master Final Landmark : 03 - final/final_landmark_{idkab}_se_2026.geojson")
    print(f">>> Log Eksekusi Tersimpan di   : {LOG_PATH}")
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# MAIN LOOP & INPUT PARSER
# ---------------------------------------------------------------------------
MENU_MAP = {
    "1": ("Split Data Poligon & Titik per-Desa", menu_split_data),
    "2": ("Batch Repair Geotagging (Tarik ke Batas SubSLS/SLS)", menu_batch_repair),
    "3": ("Hitung Muatan & Ekspor Final Landmark Master", menu_hitung_muatan),
    "4": ("Ekstrak Titik Gagal / Offside (flag_repair = 1)", menu_ekstrak_gagal),
    "5": ("Reposisi Titik Gagal / Interior Projection (move_failed)", menu_reposisi_gagal),
    "6": ("Sinkronisasi Replacement Landmark Final (moved_failed -> final)", menu_sinkronisasi_final),
    "7": ("Jalankan Pipeline Penuh (Langkah 1 s.d. 6 End-to-End)", menu_pipeline_penuh),
}


def parse_menu_input(raw: str) -> list[str]:
    """
    Memparse masukan menu pengguna.
    Mendukung:
      - Digit tunggal : "2", "4"
      - Digit gabungan: "23456" -> ['2', '3', '4', '5', '6']
      - Pemisah kustom: "2,3,4,5,6" atau "2 3 4 5 6"
      - Format rentang: "2-6" -> ['2', '3', '4', '5', '6']
      - Keluar        : "0", "exit", "quit", "q"
    """
    raw = raw.strip()
    if not raw:
        return []
    if raw.lower() in ("0", "exit", "quit", "q"):
        return ["0"]

    tokens = [t for t in re.split(r"[,;\s]+", raw) if t]
    steps = []

    for token in tokens:
        range_match = re.match(r"^([1-7])-([1-7])$", token)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            step_range = range(start, end + 1) if start <= end else range(start, end - 1, -1)
            steps.extend([str(i) for i in step_range])
        elif token.isdigit():
            for ch in token:
                if ch in "1234567":
                    steps.append(ch)
                else:
                    return []
        else:
            return []

    return steps


def main():
    while True:
        try:
            banner()
            pilihan = input("Pilih menu [0-7]: ").strip()
            print(f"Pilihan Anda: {pilihan}\n")

            steps = parse_menu_input(pilihan)

            if not steps:
                print("[PERINGATAN] Pilihan tidak valid. Silakan pilih angka 0 sampai 7 (contoh: 2, 23456, atau 2-6).")
            elif steps == ["0"]:
                print("Keluar dari program. Log tersimpan di log.txt.")
                break
            elif len(steps) == 1:
                step = steps[0]
                label, func = MENU_MAP[step]
                func()
            else:
                print("=" * 70)
                print(f">>> MENJALANKAN {len(steps)} TAHAPAN BERURUTAN: {' -> '.join(f'[{s}]' for s in steps)}")
                print("=" * 70)
                start_batch = time.time()
                for idx, s in enumerate(steps, 1):
                    label, func = MENU_MAP[s]
                    print("\n" + "=" * 70)
                    print(f">>> [EKSEKUSI {idx}/{len(steps)}] LANGKAH [{s}]: {label.upper()}")
                    print("=" * 70)
                    func()
                elapsed_batch = round(time.time() - start_batch, 2)
                print("\n" + "=" * 70)
                print(f">>> SELURUH {len(steps)} TAHAPAN BERHASIL DISELESAIKAN DALAM {elapsed_batch} DETIK.")
                print("=" * 70)

            input("\nTekan [Enter] untuk kembali ke menu utama...")
        except KeyboardInterrupt:
            print("\n\n[DIBATALKAN] Interupsi keyboard (Ctrl+C) diterima. Kembali ke menu utama...")
            time.sleep(0.5)


if __name__ == "__main__":
    main()
