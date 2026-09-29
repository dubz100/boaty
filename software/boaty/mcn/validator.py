"""C6 mission validator (SRS VAL-001..007, MCN-D38..41).

Pure and deterministic: no I/O, no clock, no randomness (VAL-006). The
caller passes the time stamp and everything the rules need. Geometry is in
local ENU metres, with every leg sampled at <= 1 m (MCN-D39), including the
final straight RTL leg back to home, which the helm flies without looking
at exclusions (NAV-007).

validate() is the only way to make a ValidatedMission, and
GuardedHelm.upload_mission accepts nothing else (VAL-001, MCN-D38).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import geo
from .models import Item, LatLon, Mission, ValidationResult, Violation, \
    checksum, to_helm_items
from .site import Site

VALIDATOR_VERSION = "1.0.0"


@dataclass(frozen=True)
class Limits:
    margin_m: float = 3.0                # VAL-002
    sample_m: float = 1.0                # MCN-D39
    max_duration_s: int = 1200           # MIS-003: 20 min (configurable)
    duration_cap_s: int = 1800           # ... up to 30 min, never more
    usable_energy_wh: float = 25.9       # ADD 7.2: 3S 3.0 Ah, 80 % usable
    energy_fraction: float = 0.5         # MIS-003
    cruise_power_w: float = 11.1         # ADD 7.2 boat load at cruise
    max_speed_mps: float = 1.5           # NAV-003
    min_speed_mps: float = 0.3
    max_hold_s: int = 60                 # VAL-005
    max_items: int = 250                 # helm mission storage (VAL-005)
    start_radius_m: float = 10.0         # VAL-004
    turn_allowance_s: float = 4.0        # per waypoint: slow, turn, settle
    estimate_factor: float = 1.2         # MCN-D35
    rtl_speed_mps: float = 1.0           # WP_SPEED; RTL_SPEED 0 = WP_SPEED


@dataclass(frozen=True)
class Estimate:
    distance_m: float
    duration_s: int
    energy_wh: float


def estimate(points: list[geo.XY], holds_s: float, speed_mps: float,
             limits: Limits = Limits(), n_waypoints: int | None = None
             ) -> Estimate:
    """Conservative (x 1.2) distance, duration and energy for a route that
    starts and ends at points[0] (home). Shared by planner and validator."""
    d = sum(geo.dist(a, b) for a, b in zip(points, points[1:]))
    n = len(points) - 2 if n_waypoints is None else n_waypoints
    t = (d / max(speed_mps, 0.1) + holds_s + max(0, n) *
         limits.turn_allowance_s) * limits.estimate_factor
    return Estimate(round(d, 1), int(math.ceil(t)),
                    round(t * limits.cruise_power_w / 3600, 2))


class ValidatedMission:
    """A mission that has passed validation, with the helm items made from
    it. Only validate() can create one."""
    __slots__ = ("mission", "result", "helm_items", "fence")
    _token = object()

    def __init__(self, token, mission: Mission, result: ValidationResult,
                 fence):
        if token is not ValidatedMission._token:
            raise TypeError("only the validator makes a ValidatedMission")
        object.__setattr__(self, "mission", mission)
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "helm_items", to_helm_items(mission.items))
        object.__setattr__(self, "fence", fence)

    def __setattr__(self, *_):
        raise AttributeError("ValidatedMission is immutable")

    @property
    def checksum(self) -> str:
        return self.mission.checksum


CHILD = {
    "VAL-002": "That trip goes too close to the edge or to something we "
               "must keep away from.",
    "VAL-003": "That trip is too long for one go.",
    "VAL-004": "The boat has to start at home and come back home.",
    "VAL-005": "That trip asks the boat to do something it can't.",
    "VAL-SITE": "That plan was made for a different map.",
    "VAL-SUM": "Something changed in the plan, so let's check it again.",
}


def validate(m: Mission, site: Site, *, now_utc: str,
             limits: Limits = Limits(), battery_pct: float = 100.0,
             photo_capacity: int = 1000,
             boat_home: tuple[float, float] | None = None
             ) -> tuple[ValidationResult, ValidatedMission | None]:
    v: list[Violation] = []
    enu = site.enu
    home_xy = site.home.point
    incl = list(site.inclusion)

    def add(rule: str, adult: str, seq: int | None = None,
            xy: geo.XY | None = None):
        at = None
        if xy is not None:
            lat, lon = enu.to_ll(*xy)
            at = LatLon(lat=round(lat, 7), lon=round(lon, 7))
        v.append(Violation(rule=rule, message_for_adult=adult,
                           message_for_child=CHILD[rule], item_seq=seq,
                           at=at))

    # ---- integrity -----------------------------------------------------
    if m.checksum != checksum(m.items):
        add("VAL-SUM", "the checksum does not match the items (edited after "
            "planning?)")
    if m.site != site.name or m.site_version != site.git_version:
        add("VAL-SITE", f"planned for {m.site}@{m.site_version}, but the "
            f"loaded site is {site.name}@{site.git_version}")

    items = m.items
    if not items:
        add("VAL-004", "the mission has no items; it must end with RTL")
        return _result(m, v, now_utc, site, None)
    if [i.seq for i in items] != list(range(1, len(items) + 1)):
        add("VAL-005", "item numbers must run 1, 2, 3 ... with no gaps")
    if len(items) > limits.max_items:
        add("VAL-005", f"{len(items)} items; the helm holds at most "
            f"{limits.max_items}")

    # ---- VAL-004: start at home, end with RTL --------------------------
    mh = enu.to_xy(m.home.lat, m.home.lon)
    if geo.dist(mh, home_xy) > limits.start_radius_m:
        add("VAL-004", f"mission home is {geo.dist(mh, home_xy):.0f} m from "
            f"the site's home '{site.home.name}' (max "
            f"{limits.start_radius_m:g} m)", xy=mh)
    if boat_home is not None:
        bh = enu.to_xy(*boat_home)
        if geo.dist(bh, home_xy) > limits.start_radius_m:
            add("VAL-004", f"the boat's home is {geo.dist(bh, home_xy):.0f} "
                "m from the site's home: launch from the jetty", xy=bh)
    if items[-1].kind != "rtl":
        add("VAL-004", "the last item must be return home (MIS-002)",
            items[-1].seq)
    for it in items[:-1]:
        if it.kind == "rtl":
            add("VAL-004", "return home may only be the last item", it.seq)

    # ---- VAL-005: per-item limits --------------------------------------
    speeds = [m.cruise_mps]
    photos = 0
    holds = 0.0
    route: list[tuple[geo.XY, int | None]] = [(home_xy, None)]
    for it in items:
        if it.kind in ("waypoint", "photo_point"):
            if it.lat is None or it.lon is None or \
                    not (math.isfinite(it.lat) and math.isfinite(it.lon)):
                add("VAL-005", "a waypoint without a position", it.seq)
                continue
            route.append((enu.to_xy(it.lat, it.lon), it.seq))
        if it.kind == "photo_point":
            h = it.hold_s
            if h is None or not 0 < h <= limits.max_hold_s:
                add("VAL-005", f"hold of {h} s (1 to {limits.max_hold_s} s)",
                    it.seq)
            else:
                holds += h
            if it.photos is None or not 1 <= it.photos <= 10:
                add("VAL-005", f"{it.photos} photos at a photo point (1 to "
                    "10)", it.seq)
            else:
                photos += it.photos
        elif it.kind == "waypoint":
            if it.hold_s or it.photos:
                add("VAL-005", "a plain waypoint cannot hold or take photos",
                    it.seq)
        elif it.kind == "speed":
            s = it.speed_mps
            if s is None or not math.isfinite(s) or \
                    not limits.min_speed_mps <= s <= limits.max_speed_mps:
                add("VAL-005", f"speed {s} m/s (allowed "
                    f"{limits.min_speed_mps:g} to {limits.max_speed_mps:g})",
                    it.seq)
            else:
                speeds.append(s)
    route.append((home_xy, items[-1].seq if items[-1].kind == "rtl"
                  else None))

    # ---- VAL-002: every point and every leg sample ---------------------
    radius = site.max_distance_from_home_m - limits.margin_m
    for (a, _), (b, seq) in zip(route, route[1:]):
        _check_leg(a, b, seq, incl, site, home_xy, radius, limits, add)

    # ---- VAL-003: duration and energy ----------------------------------
    pts = [p for p, _ in route]
    est = estimate(pts, holds, min(speeds), limits)
    dur = max(est.duration_s, m.estimates.duration_s)
    energy = max(est.energy_wh, m.estimates.energy_wh)
    cap = min(limits.max_duration_s, limits.duration_cap_s)
    if dur > cap:
        add("VAL-003", f"estimated {dur / 60:.1f} min (x1.2 included); the "
            f"limit is {cap / 60:.0f} min")
    budget = limits.usable_energy_wh * max(0.0, min(battery_pct, 100)) / 100 \
        * limits.energy_fraction
    if energy > budget:
        add("VAL-003", f"estimated {energy:.1f} Wh; half of what is left in "
            f"the battery is {budget:.1f} Wh")

    # ---- VAL-005: storage ----------------------------------------------
    if m.capture.interval_s:
        photos += int(dur / m.capture.interval_s) + 1
    if photos > photo_capacity:
        add("VAL-005", f"{photos} photos planned; the camera has room for "
            f"{photo_capacity}")

    return _result(m, v, now_utc, site, None)


def _check_leg(a, b, seq, incl, site: Site, home_xy, radius, limits, add):
    """First failing sample on the leg, per rule, so one bad leg gives one
    message rather than hundreds."""
    # Endpoints first. A leg whose far end is outside the fence or the
    # backstop circle is already wrong, and sampling it at 1 m could mean
    # millions of samples (a waypoint at 0 N 0 E is 5,800 km away).
    for p in (b, a):
        d = geo.signed_depth(p, incl)
        far = geo.dist(p, home_xy) > radius
        if d < limits.margin_m or far:
            where = "outside" if d < 0 else f"{d:.1f} m inside"
            add("VAL-002", f"waypoint is {where} the fence (needs "
                f"{limits.margin_m:g} m)" if not far else
                f"waypoint is beyond {radius:.0f} m from home (the helm's "
                "circular backstop fence)", seq, p)
            return
    # Both ends are inside the backstop circle, which is convex, so the
    # whole leg is too. The fence and zones can be concave: sample.
    fence_bad = zone_bad = False
    for p in geo.sample_leg(a, b, limits.sample_m):
        if not fence_bad:
            d = geo.signed_depth(p, incl)
            if d < limits.margin_m:
                fence_bad = True
                where = "outside" if d < 0 else f"{d:.1f} m inside"
                add("VAL-002", f"route goes {where} the fence (needs "
                    f"{limits.margin_m:g} m)", seq, p)
        if not zone_bad:
            for z in site.zones:
                d = z.depth(p)
                if d < limits.margin_m:
                    zone_bad = True
                    add("VAL-002", f"route passes {max(d, 0):.1f} m from the "
                        f"{z.reason or 'no-go zone'} (needs "
                        f"{limits.margin_m:g} m)", seq, p)
                    break
        if fence_bad and zone_bad:
            return


def _result(m, v, now_utc, site, fence):
    res = ValidationResult(mission_id=m.id, ok=not v, violations=v,
                           checked_utc=now_utc,
                           validator_version=VALIDATOR_VERSION)
    if v:
        return res, None
    return res, ValidatedMission(ValidatedMission._token, m, res,
                                 site.fence())
