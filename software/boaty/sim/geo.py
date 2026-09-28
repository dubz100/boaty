"""Small local-tangent-plane helpers for building test geometry."""
from __future__ import annotations

import math

R_EARTH = 6378137.0


def offset(lat: float, lon: float, north_m: float, east_m: float):
    dlat = north_m / R_EARTH
    dlon = east_m / (R_EARTH * math.cos(math.radians(lat)))
    return lat + math.degrees(dlat), lon + math.degrees(dlon)


def ne_of(lat0: float, lon0: float, lat: float, lon: float):
    """North/east metres of (lat, lon) from (lat0, lon0)."""
    n = math.radians(lat - lat0) * R_EARTH
    e = math.radians(lon - lon0) * R_EARTH * math.cos(math.radians(lat0))
    return n, e


def square(lat: float, lon: float, half_m: float):
    """Four corners of a square centred on (lat, lon), clockwise from NW."""
    return tuple(offset(lat, lon, n, e) for n, e in
                 ((half_m, -half_m), (half_m, half_m), (-half_m, half_m),
                  (-half_m, -half_m)))


def box(lat: float, lon: float, n0: float, n1: float, e0: float, e1: float):
    return tuple(offset(lat, lon, n, e) for n, e in
                 ((n1, e0), (n1, e1), (n0, e1), (n0, e0)))
