import sys
sys.path.insert(0, r'd:\www\wilkerstat-checker')

import config
print("PORT:", config.PORT)
print("HOST:", config.HOST)
print("MOVED_THRESHOLD_M:", config.MOVED_THRESHOLD_M)
print("OVERLAP_MIN_AREA_M2:", config.OVERLAP_MIN_AREA_M2)
print("GAP_MAX_WIDTH_M:", config.GAP_MAX_WIDTH_M)
print("ENABLE_TRAY:", config.ENABLE_TRAY)
print("AUTO_HIDE_CONSOLE:", config.AUTO_HIDE_CONSOLE)
print("config OK")

import database as db
conn = db.get_connection(r'd:\www\wilkerstat-checker\data\test_smoke.db')
db.init_db(conn)
conn.close()
import os; os.unlink(r'd:\www\wilkerstat-checker\data\test_smoke.db')
print("database OK")

from col_loader import load_shape_columns, load_dot_columns
sc = load_shape_columns(config.SHAPE_COL_CSV)
dc = load_dot_columns(config.DOT_COL_CSV)
print(f"shape cols: {len(sc)}, dot cols: {len(dc)}")
print("col_loader OK")

from colours import generate_colours, unique_check
assert unique_check(500), "500 warna tidak unik!"
print("colours OK (500 warna unik)")

print("\n=== ALL SMOKE TESTS PASSED ===")

