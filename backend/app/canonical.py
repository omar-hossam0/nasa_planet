"""Request normalization, geometry validation and canonical hashing.

The browser never builds cache keys. Two requests that mean the same area must
hash identically, so ring order, ring orientation, duplicate vertices and
coordinate precision are normalized once here.
"""
from __future__ import annotations

import hashlib
import json
import math

from . import config

ERROR = {
    "INVALID_GEOMETRY": "geometry must be a closed WGS84 lon/lat polygon",
    "SELF_INTERSECTING": "polygon ring intersects itself",
    "OUT_OF_BOUNDS": "requested area lies outside the supported study window",
    "AREA_TOO_SMALL": "requested area is too small for the native grid",
    "AREA_TOO_LARGE": "requested area exceeds the supported maximum",
    "EXCESSIVE_COMPUTE": "requested area covers too many cells",
}


def _round(v: float) -> float:
    return round(float(v), 6)


def _segments_intersect(p1, p2, p3, p4) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def on_seg(a, b, c):
        return (min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and
                min(a[1], b[1]) <= c[1] <= max(a[1], b[1]))

    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    if (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0):
        return True
    if o1 == 0 and on_seg(p1, p2, p3):
        return True
    if o2 == 0 and on_seg(p1, p2, p4):
        return True
    if o3 == 0 and on_seg(p3, p4, p1):
        return True
    if o4 == 0 and on_seg(p3, p4, p2):
        return True
    return False


def polygon_area_deg2(ring: list[list[float]]) -> float:
    a = 0.0
    for i in range(len(ring) - 1):
        a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(a) / 2.0


def normalize_aoi(geometry: dict) -> list[list[float]]:
    """Validate and normalize a GeoJSON Polygon; returns one CCW ring."""
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        raise ValueError("INVALID_GEOMETRY")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or not coords:
        raise ValueError("INVALID_GEOMETRY")
    ring = coords[0]
    if not isinstance(ring, list) or len(ring) < 4:
        raise ValueError("INVALID_GEOMETRY")
    pts: list[list[float]] = []
    for p in ring:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            raise ValueError("INVALID_GEOMETRY")
        lon, lat = _round(p[0]), _round(p[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("INVALID_GEOMETRY")
        if not pts or pts[-1] != [lon, lat]:
            pts.append([lon, lat])
    if pts[0] != pts[-1]:
        pts.append(list(pts[0]))
    if len(pts) < 4:
        raise ValueError("INVALID_GEOMETRY")
    # self-intersection check on the open ring
    open_ring = pts[:-1]
    n = len(open_ring)
    for i in range(n):
        a1, a2 = open_ring[i], open_ring[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or j == (i + 1) % n:
                continue
            b1, b2 = open_ring[j], open_ring[(j + 1) % n]
            if _segments_intersect(a1, a2, b1, b2):
                raise ValueError("SELF_INTERSECTING")
    # normalize orientation to counter-clockwise (positive shoelace)
    signed = 0.0
    for i in range(len(pts) - 1):
        signed += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    if signed < 0:
        pts = list(reversed(pts))
    # rotate the ring so it starts at its lexicographically smallest vertex,
    # so two identical polygons that start at different vertices hash the same
    open_ring = pts[:-1]
    k = min(range(len(open_ring)),
            key=lambda i: (open_ring[i][0], open_ring[i][1]))
    rotated = open_ring[k:] + open_ring[:k]
    pts = [list(p) for p in rotated] + [list(rotated[0])]
    return pts


def point_in_polygon(lon, lat, ring) -> "list[bool] | bool":
    """Ray casting; accepts scalars or numpy arrays."""
    try:
        import numpy as np
        x = np.asarray(lon, dtype="f8")
        y = np.asarray(lat, dtype="f8")
        x, y = np.broadcast_arrays(x, y)
        inside = np.zeros(x.shape, dtype=bool)
        for i in range(len(ring) - 1):
            x1, y1 = ring[i]
            x2, y2 = ring[i + 1]
            cond = ((y1 > y) != (y2 > y))
            with np.errstate(divide="ignore", invalid="ignore"):
                xint = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            inside ^= cond & (x < xint)
        return inside if x.shape else bool(inside)
    except ImportError:  # pragma: no cover
        inside = False
        for i in range(len(ring) - 1):
            x1, y1 = ring[i]
            x2, y2 = ring[i + 1]
            if ((y1 > lat) != (y2 > lat)) and \
                    (lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1):
                inside = not inside
        return inside


def check_area(ring, bbox, cell_deg: float) -> dict:
    """Validate area limits, window containment and compute budget."""
    w, s, e, n = bbox
    tol = 1e-6
    for lon, lat in ring:
        if not (w - tol <= lon <= e + tol and s - tol <= lat <= n + tol):
            raise ValueError("OUT_OF_BOUNDS")
    area = polygon_area_deg2(ring)
    if area < config.MIN_AOI_AREA_DEG2:
        raise ValueError("AREA_TOO_SMALL")
    if area > config.MAX_AOI_AREA_DEG2:
        raise ValueError("AREA_TOO_LARGE")
    est_cells = int(area / (cell_deg ** 2)) + 1
    if est_cells > config.MAX_CELLS_PER_VARIABLE:
        raise ValueError("EXCESSIVE_COMPUTE")
    return {"area_deg2": round(area, 6), "estimated_cells": est_cells}


def canonical_request(payload: dict, defaults: dict) -> dict:
    """Build the canonical request dict used for hashing and the receipt."""
    canonical = {
        "region_id": payload["region_id"],
        "variable_ids": sorted(set(payload["variable_ids"])),
        "start_month": payload["start_month"],
        "end_month": payload["end_month"],
        "aggregation_policy_id": payload.get(
            "aggregation_policy_id") or defaults["aggregation_policy_id"],
        "method_revision": payload.get("method_revision") or
        defaults["method_revision"],
        "data_revision": payload.get("data_revision") or
        defaults["data_revision"],
    }
    if payload.get("aoi"):
        canonical["aoi"] = {"type": "Polygon",
                            "coordinates": [normalize_aoi(payload["aoi"])]}
    else:
        canonical["aoi"] = None
    return canonical


def request_hash(canonical: dict) -> str:
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def month_range(start: str, end: str) -> list[str]:
    y1, m1 = int(start[:4]), int(start[5:7])
    y2, m2 = int(end[:4]), int(end[5:7])
    if (y2, m2) < (y1, m1):
        raise ValueError("INVALID_PERIOD")
    out = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    if not (2001 <= y1 <= 2024 and 2001 <= y2 <= 2024):
        raise ValueError("INVALID_PERIOD")
    return out


def is_month(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 7 or s[4] != "-":
        return False
    try:
        m = int(s[5:7])
        int(s[:4])
    except ValueError:
        return False
    return 1 <= m <= 12
