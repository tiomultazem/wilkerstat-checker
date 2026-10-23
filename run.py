"""
WilkerStat Checker — Entry point.

Flow:
1. Kill proses lama di port yang sama (via run.bat)
2. Start Flask/Waitress di background thread
3. Jika ENABLE_TRAY=true → jalankan systray (blocking, di main thread)
   - Console auto-hide setelah 3 detik
   - Minimize console → langsung ke tray
   - Keluar lewat menu tray atau Ctrl+C
4. Jika ENABLE_TRAY=false → blocking di server thread saja
"""
import signal
import sys
import os
import threading

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT_DIR, "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import config

# Wajib import dulu agar .env sudah terbaca sebelum apapun
from app import create_app
from waitress import serve


def _run_server():
    """Jalankan Flask + Waitress di thread ini (blocking)."""
    app = create_app()
    print(f"[wilkerstat] Waitress bind {config.HOST}:{config.PORT}")
    serve(app, host=config.HOST, port=config.PORT, threads=4)


if __name__ == "__main__":
    server_thread = threading.Thread(target=_run_server, daemon=True, name="waitress-server")
    server_thread.start()

    if config.ENABLE_TRAY and os.name == "nt":
        from tray import run_tray

        # Ctrl+C di terminal → exit bersih
        def _handle_sigint(sig, frame):
            print("\n[wilkerstat] Ctrl+C — menghentikan server...")
            os._exit(0)

        signal.signal(signal.SIGINT, _handle_sigint)
        signal.signal(signal.SIGTERM, _handle_sigint)

        run_tray(server_thread)
    else:
        print(f"[wilkerstat] Berjalan di http://{config.HOST}:{config.PORT}")
        print("[wilkerstat] Tekan Ctrl+C untuk berhenti.")
        try:
            server_thread.join()
        except KeyboardInterrupt:
            print("[wilkerstat] Dihentikan.")
            sys.exit(0)
