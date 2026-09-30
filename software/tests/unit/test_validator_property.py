"""SC-31: property-based validator test against independent geometry.

Hypothesis generates missions around the Milton site. Every mission the
validator accepts is re-checked with separate code (winding-number
point-in-polygon, 0.1 m sampling, direct circle and segment distances):
no accepted route may leave the fence or enter a no-go zone, and every
accepted route keeps at least 2.9 m clear (3 m margin less sampling
tolerance). Derandomised, so the run is repeatable.
"""
import pytest
import math

from hypothesis import HealthCheck, given, settings, strategies as st

import boaty  # noqa: F401
from boaty.mcn.site import Site
from boaty.mcn.validator import validate

from .test_validator import T, mk

SITE = Site.named("milton-country-park")
FENCE = list(SITE.inclusion)
STATS = {"accepted": 0, "rejected": 0, "min_clearance": 1e9}


def winding_inside(p, poly):
    """Winding number (independent of the validator's ray cast)."""
    wn = 0
    x, y = p
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        cross = (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)
        if y1 <= y < y2 and cross > 0:
            wn += 1
        elif y2 <= y < y1 and cross < 0:
            wn -= 1
    return wn != 0


def seg_dist(p, a, b):
    ax, ay, bx, by = *a, *b
    vx, vy = bx - ax, by - ay
    wx, wy = p[0] - ax, p[1] - ay
    c1 = vx * wx + vy * wy
    if c1 <= 0:
        return math.hypot(wx, wy)
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        return math.hypot(p[0] - bx, p[1] - by)
    t = c1 / c2
    return math.hypot(p[0] - (ax + t * vx), p[1] - (ay + t * vy))


def clearance(p):
    """Signed distance to the nearest boundary that matters."""
    d_f = min(seg_dist(p, FENCE[i], FENCE[(i + 1) % len(FENCE)])
              for i in range(len(FENCE)))
    if not winding_inside(p, FENCE):
        return -d_f
    best = d_f
    for z in SITE.zones:
        if z.centre is not None:
            best = min(best, math.hypot(p[0] - z.centre[0],
                                        p[1] - z.centre[1]) - z.radius)
        else:
            poly = list(z.poly)
            d = min(seg_dist(p, poly[i], poly[(i + 1) % len(poly)])
                    for i in range(len(poly)))
            best = min(best, -d if winding_inside(p, poly) else d)
    return best


def route_clearance(points):
    route = [(0.0, 0.0)] + points + [(0.0, 0.0)]
    worst = 1e9
    for a, b in zip(route, route[1:]):
        n = max(1, int(math.dist(a, b) / 0.1))
        for i in range(n + 1):
            p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            worst = min(worst, clearance(p))
    return worst


pts = st.lists(st.tuples(st.floats(-70, 80), st.floats(-20, 90)),
               min_size=1, max_size=6)


@settings(max_examples=400, derandomize=True, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(pts)
@pytest.mark.verifies("VAL-002", "VAL-006")
def test_accepted_missions_never_cross_a_boundary(points):
    m = mk([(x, y) for x, y in points])
    r, vm = validate(m, SITE, now_utc=T)
    geo_rules = {v.rule for v in r.violations} - {"VAL-003"}
    worst = route_clearance([tuple(p) for p in points])
    if vm is not None:
        STATS["accepted"] += 1
        STATS["min_clearance"] = min(STATS["min_clearance"], worst)
        assert worst >= 2.9, (points, worst)
    else:
        STATS["rejected"] += 1
        if "VAL-002" not in geo_rules:
            # Rejected for another reason only: geometry must be fine.
            assert worst >= 2.9, (points, worst, r.violations)
        else:
            # Rejected for geometry: the independent check agrees the
            # route comes within 3 m (1 m sampling tolerance).
            assert worst < 3.0 + 0.05, (points, worst)


def test_property_run_found_both_kinds():
    test_accepted_missions_never_cross_a_boundary()
    assert STATS["accepted"] >= 10 and STATS["rejected"] >= 10, STATS
