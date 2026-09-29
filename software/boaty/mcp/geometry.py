"""Fence geometry for B7 (FEN-006): how far outside the fence is the boat?"""
from __future__ import annotations

import math

R = 6378137.0


def to_ne(lat0: float, lon0: float, lat: float, lon: float):
    n = math.radians(lat - lat0) * R
    e = math.radians(lon - lon0) * R * math.cos(math.radians(lat0))
    return n, e


def inside(poly, p) -> bool:
    """Ray casting; poly and p in local (n, e) metres."""
    x, y = p
    res = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and \
                x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            res = not res
        j = i
    return res


def dist_to_edges(poly, p) -> float:
    best = float("inf")
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx +
                                                   (p[1] - a[1]) * dy) / L2))
        best = min(best, math.hypot(p[0] - (a[0] + t * dx),
                                    p[1] - (a[1] + t * dy)))
    return best


class FenceGeometry:
    """Inclusion polygon (and exclusion polygons) in lat/lon."""

    def __init__(self, inclusion, exclusions=()):
        self.lat0, self.lon0 = inclusion[0]
        self.incl = [to_ne(self.lat0, self.lon0, *v) for v in inclusion]
        self.excl = [[to_ne(self.lat0, self.lon0, *v) for v in poly]
                     for poly in exclusions]

    def outside_by(self, lat: float, lon: float) -> float:
        """0 inside the allowed area, else metres to the nearest boundary."""
        p = to_ne(self.lat0, self.lon0, lat, lon)
        d = 0.0
        if not inside(self.incl, p):
            d = dist_to_edges(self.incl, p)
        for poly in self.excl:
            if inside(poly, p):
                d = max(d, dist_to_edges(poly, p))
        return d

    @classmethod
    def from_items(cls, items) -> "FenceGeometry | None":
        """Build from downloaded fence items (MAV_CMD 5001/5002)."""
        incl, excl, i = [], [], 0
        while i < len(items):
            it = items[i]
            n = max(1, int(it.param1))
            if it.command in (5001, 5002):
                poly = [(x.x / 1e7, x.y / 1e7) for x in items[i:i + n]]
                (incl if it.command == 5001 else excl).append(poly)
                i += n
            else:
                i += 1
        return cls(incl[0], excl) if incl else None
