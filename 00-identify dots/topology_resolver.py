#!/usr/bin/env python3
"""
topology_resolver.py
Merapikan topologi poligon dalam satu GeoJSON tanpa menghapus feature dan
tanpa mengubah atribut:

  1. Resolve overlaps : area overlap diberikan ke SATU feature pemenang.
  2. Fill gaps        : gap (lubang tertutup) dengan luas di bawah batas
                        (default 50 m2) langsung digabung ke feature terbesar
                        yang bersinggungan dengannya.

Butuh: pip install shapely
Output: <nama-file>-resolved.geojson (semua geometri menjadi MultiPolygon)
"""

import json
import math
import os
import sys

try:
    from shapely.geometry import shape, mapping, MultiPolygon
    from shapely.ops import polygonize, unary_union
    from shapely.strtree import STRtree
    from shapely.validation import make_valid
except ImportError:
    print("Library shapely belum terpasang. Jalankan: pip install shapely")
    sys.exit(1)

# Toleransi 0 = sama ketatnya dengan Topology Checker QGIS
TOL_AREA = 0.0
DEFAULT_GAP_M2 = 50.0


# --------------------------------------------------------------------------
# Utilitas geometri
# --------------------------------------------------------------------------
def polys_only(geom):
    """Kembalikan MultiPolygon berisi hanya bagian poligon dari geom, atau None."""
    if geom is None or geom.is_empty:
        return None
    t = geom.geom_type
    if t == "Polygon":
        return MultiPolygon([geom])
    if t == "MultiPolygon":
        return geom
    if t == "GeometryCollection":
        parts = []
        for g in geom.geoms:
            m = polys_only(g)
            if m is not None:
                parts.extend(m.geoms)
        return MultiPolygon(parts) if parts else None
    return None


def dissolve(geom):
    """Gabungkan bagian-bagian dalam satu feature agar tidak overlap satu sama lain."""
    if geom is None:
        return None
    return polys_only(unary_union(list(geom.geoms)))


def count_overlaps(geoms):
    """Hitung pasangan feature yang masih overlap (luas > TOL_AREA)."""
    idx = [i for i, g in enumerate(geoms) if g is not None]
    tree = STRtree([geoms[i] for i in idx])
    pairs = []
    for i in idx:
        for b_pos in tree.query(geoms[i]):
            j = idx[b_pos]
            if j <= i:
                continue
            if geoms[i].intersection(geoms[j]).area > TOL_AREA:
                pairs.append((i, j))
    return pairs


# --------------------------------------------------------------------------
# Luas dalam meter persegi
# --------------------------------------------------------------------------
def is_geographic(geoms):
    """True bila semua koordinat berada dalam rentang derajat (lon/lat)."""
    gs = [g for g in geoms if g is not None]
    if not gs:
        return True
    minx = min(g.bounds[0] for g in gs)
    miny = min(g.bounds[1] for g in gs)
    maxx = max(g.bounds[2] for g in gs)
    maxy = max(g.bounds[3] for g in gs)
    return -180 <= minx and maxx <= 180 and -90 <= miny and maxy <= 90


def meters_per_degree(lat):
    """Panjang 1 derajat lintang dan bujur (meter) pada lintang tertentu (WGS84)."""
    phi = math.radians(lat)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
             + 0.118 * math.cos(5 * phi))
    return m_lat, m_lon


def area_m2(geom, geographic):
    """Luas dalam m2. Untuk derajat dipakai skala lokal di titik pusat geom."""
    if not geographic:
        return geom.area
    c = geom.centroid
    m_lat, m_lon = meters_per_degree(c.y)
    return geom.area * m_lat * m_lon


# --------------------------------------------------------------------------
# Modul 1: resolve overlaps
# --------------------------------------------------------------------------
def resolve_overlaps(orig, idx, rank):
    """
    Node semua garis batas -> pecah jadi face -> beri tiap face ke 1 pemenang.
    Semua face lahir dari jaringan garis yang sama, jadi batasnya identik
    secara koordinat dan tidak ada noise presisi.

    Mengembalikan (final, unowned):
      final   = geometri baru per feature (None bila habis tertutup)
      unowned = face yang tidak dimiliki feature mana pun (kandidat gap)
    """
    lines = unary_union([orig[i].boundary for i in idx])
    faces = list(polygonize(lines))
    print(f"  Jumlah face: {len(faces)}")

    tree = STRtree([orig[i] for i in idx])
    assigned = {i: [] for i in idx}
    unowned = []
    for face in faces:
        pt = face.representative_point()
        owners = [idx[pos] for pos in tree.query(pt, predicate="intersects")]
        if not owners:
            unowned.append(face)
            continue
        assigned[min(owners, key=rank.get)].append(face)

    final = [None] * len(orig)
    for i in idx:
        if assigned[i]:
            final[i] = polys_only(unary_union(assigned[i]))
    return final, unowned


# --------------------------------------------------------------------------
# Modul 2: fill gaps
# --------------------------------------------------------------------------
def fill_gaps(final, unowned, geographic, max_m2):
    """
    Isi gap yang luasnya < max_m2 dengan menggabungkannya ke feature terbesar
    yang bersinggungan (berbagi garis batas, bukan sekadar titik).

    Mengembalikan (final_baru, jumlah_terisi, gap_tersisa)
      gap_tersisa = list (polygon, luas_m2) yang tidak diisi
    """
    if not unowned or max_m2 <= 0:
        merged = polys_only(unary_union(unowned)) if unowned else None
        rest = [(g, area_m2(g, geographic)) for g in merged.geoms] if merged else []
        return final, 0, rest

    # Satukan face kosong yang saling menempel menjadi gap utuh
    merged = polys_only(unary_union(unowned))
    gaps = list(merged.geoms) if merged is not None else []

    idxf = [i for i, g in enumerate(final) if g is not None]
    base = list(final)  # snapshot agar urutan pengisian tidak mempengaruhi hasil
    areas = {i: base[i].area for i in idxf}
    tree = STRtree([base[i] for i in idxf])

    fills = {}
    remaining = []
    for gap in gaps:
        a = area_m2(gap, geographic)
        if a >= max_m2:
            remaining.append((gap, a))
            continue

        gap_boundary = gap.boundary
        touching = []
        for pos in tree.query(gap):
            j = idxf[pos]
            if gap_boundary.intersection(base[j]).length > 0:
                touching.append(j)

        if not touching:  # tidak ada tetangga yang berbagi garis batas
            remaining.append((gap, a))
            continue

        winner = max(touching, key=lambda j: areas[j])
        fills.setdefault(winner, []).append(gap)

    new_final = list(final)
    filled = 0
    for j, gs in fills.items():
        new_final[j] = polys_only(unary_union([base[j]] + gs))
        filled += len(gs)

    return new_final, filled, remaining


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def ask_float(prompt, default):
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        print(f"Input tidak valid, memakai default {default}.")
        return default


def main():
    path = input("Masukkan path file GeoJSON: ").strip().strip('"').strip("'")
    if not os.path.isfile(path):
        print(f"File tidak ditemukan: {path}")
        sys.exit(1)

    print("\nSiapa yang menang di area overlap?")
    print("  1 = feature yang urutannya lebih atas di file (default)")
    print("  2 = feature yang lebih besar")
    print("  3 = feature yang lebih kecil")
    mode = input("Pilih [1/2/3]: ").strip() or "1"

    max_gap = ask_float(
        f"\nIsi gap yang luasnya di bawah berapa m2? "
        f"(default {DEFAULT_GAP_M2:g}, isi 0 untuk melewati): ",
        DEFAULT_GAP_M2,
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    features = data.get("features", [])

    # 1. Baca geometri, perbaiki yang invalid, pastikan hanya poligon
    orig = []
    for feat in features:
        g = shape(feat["geometry"]) if feat.get("geometry") else None
        if g is not None and not g.is_valid:
            g = make_valid(g)
        orig.append(dissolve(polys_only(g)))

    idx = [i for i, g in enumerate(orig) if g is not None]
    geographic = is_geographic(orig)
    print(f"\nCRS terdeteksi: {'derajat (WGS84), luas dihitung ke m2' if geographic else 'proyeksi (satuan meter diasumsikan)'}")

    # 2. Tentukan prioritas (rank kecil = menang)
    if mode == "2":
        order = sorted(idx, key=lambda i: -orig[i].area)
    elif mode == "3":
        order = sorted(idx, key=lambda i: orig[i].area)
    else:
        order = list(idx)
    rank = {i: r for r, i in enumerate(order)}

    # 3. Resolve overlaps
    print("\n[1/2] Resolve overlaps (node + polygonize)...")
    final, unowned = resolve_overlaps(orig, idx, rank)

    # 4. Fill gaps
    print(f"[2/2] Fill gaps < {max_gap:g} m2...")
    final, filled, remaining = fill_gaps(final, unowned, geographic, max_gap)

    # 5. Tulis output
    out_features, vanished = [], []
    for i, feat in enumerate(features):
        if final[i] is None:
            vanished.append(i)
            continue
        new_feat = dict(feat)
        new_feat["geometry"] = mapping(final[i])
        out_features.append(new_feat)

    result = {k: v for k, v in data.items() if k != "features"}
    result["features"] = out_features

    base, ext = os.path.splitext(path)
    out_path = f"{base}-resolved{ext or '.geojson'}"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    # 6. Verifikasi + laporan
    before = len(count_overlaps(orig))
    after = len(count_overlaps(final))

    print("\nSelesai!")
    print(f"  Pasangan overlap sebelum : {before}")
    print(f"  Pasangan overlap sesudah : {after}")
    print(f"  Gap terisi (< {max_gap:g} m2)  : {filled}")
    print(f"  Gap tersisa              : {len(remaining)}")

    if remaining:
        remaining.sort(key=lambda x: -x[1])
        print("  Gap tersisa terbesar (luas m2 @ lon/lat atau x/y):")
        for gap, a in remaining[:10]:
            c = gap.centroid
            print(f"    - {a:,.1f} m2 @ {c.x:.6f}, {c.y:.6f}")
        if len(remaining) > 10:
            print(f"    ... dan {len(remaining) - 10} lainnya")

    if vanished:
        print(f"\n  PERINGATAN: {len(vanished)} feature habis tertutup feature lain "
              f"dan tidak ditulis (index: {vanished})")
        for i in vanished:
            props = features[i].get("properties") or {}
            print(f"    - index {i}: {dict(list(props.items())[:4])}")
    if after:
        print("\n  Masih ada sisa overlap. Kirim hasil cetakan ini ke saya.")
    print(f"\n  Output: {out_path}")


if __name__ == "__main__":
    main()
