"""Local east-north-up geometry for the planner and the validator.

Everything here is pure: no I/O, no randomness (MCN-D40). Positions are
converted to metres east/north of a site reference point using an
equirectangular projection, which is accurate to millimetres over a lake a
few hundred metres across.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

R_EARTH = 6378137.0

XY = tuple[float, float]            # (east_m, north_m)


@dataclass(frozen=True)
class Enu:
    """Projection about a reference point (lat0, lon0)."""
    lat0: float
    lon0: float

    def to_xy(self, lat: float, lon: float) -> XY:
        e = math.radians(lon - self.lon0) * R_EARTH * \
            math.cos(math.radians(self.lat0))
        n = math.radians(lat - self.lat0) * R_EARTH
        return e, n

    def to_ll(self, x: float, y: float) -> tuple[float, float]:
        lat = self.lat0 + math.degrees(y / R_EARTH)
        lon = self.lon0 + math.degrees(
            x / (R_EARTH * math.cos(math.radians(self.lat0))))
        return lat, lon


def dist(a: XY, b: XY) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_seg_dist(p: XY, a: XY, b: XY) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def edges(poly: list[XY]):
    n = len(poly)
    for i in range(n):
        yield poly[i], poly[(i + 1) % n]


def inside(p: XY, poly: list[XY]) -> bool:
    """Even-odd ray cast. Points exactly on an edge may go either way; the
    callers always add a margin, so that never decides anything."""
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in edges(poly):
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                c = not c
    return c


def boundary_dist(p: XY, poly: list[XY]) -> float:
    return min(point_seg_dist(p, a, b) for a, b in edges(poly))


def signed_depth(p: XY, poly: list[XY]) -> float:
    """Distance to the boundary: positive inside, negative outside."""
    d = boundary_dist(p, poly)
    return d if inside(p, poly) else -d


def area(poly: list[XY]) -> float:
    """Signed shoelace area (positive when anticlockwise)."""
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in edges(poly))


def centroid(poly: list[XY]) -> XY:
    a = area(poly)
    if abs(a) < 1e-9:
        n = len(poly)
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    cx = cy = 0.0
    for (x1, y1), (x2, y2) in edges(poly):
        k = x1 * y2 - x2 * y1
        cx += (x1 + x2) * k
        cy += (y1 + y2) * k
    return cx / (6 * a), cy / (6 * a)


def _cross(o: XY, a: XY, b: XY) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def segments_cross(a: XY, b: XY, c: XY, d: XY) -> bool:
    """Proper intersection of segments ab and cd (touching counts)."""
    d1, d2 = _cross(c, d, a), _cross(c, d, b)
    d3, d4 = _cross(a, b, c), _cross(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and \
            d1 * d2 != 0 and d3 * d4 != 0:
        return True
    for p, q, r, v in ((c, d, a, d1), (c, d, b, d2), (a, b, c, d3),
                       (a, b, d, d4)):
        if v == 0 and min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and \
                min(p[1], q[1]) <= r[1] <= max(p[1], q[1]):
            return True
    return False


def self_intersects(poly: list[XY]) -> bool:
    es = list(edges(poly))
    n = len(es)
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue                      # neighbours share a vertex
            if segments_cross(*es[i], *es[j]):
                return True
    return False


def sample_leg(a: XY, b: XY, step: float = 1.0) -> list[XY]:
    """a, b and points between them no more than `step` apart."""
    n = max(1, math.ceil(dist(a, b) / step))
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            for i in range(n + 1)]


def scanline(poly: list[XY], y: float) -> list[float]:
    """Sorted x where the horizontal line at y crosses the polygon."""
    xs = []
    for (x1, y1), (x2, y2) in edges(poly):
        if (y1 > y) != (y2 > y):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    return sorted(xs)


def rotate(p: XY, ang: float) -> XY:
    c, s = math.cos(ang), math.sin(ang)
    return p[0] * c - p[1] * s, p[0] * s + p[1] * c


def long_axis(poly: list[XY]) -> float:
    """Angle (rad) of the polygon's longest edge: lanes run along it."""
    a, b = max(edges(poly), key=lambda e: dist(*e))
    return math.atan2(b[1] - a[1], b[0] - a[0])


def furthest(points: list[XY], origin: XY) -> float:
    return max((dist(p, origin) for p in points), default=0.0)
