"""C5 planner: Intent v1 -> Mission v1 (MCN-D34, D35, D37).

The language model only ever names things ("explore the north pond, then
visit the island"); all geometry is made here, from the site file. The
planner aims to produce missions the validator will accept, but it is not
trusted: every mission still goes through validate().

Geometry:
  explore      lawnmower lanes along the area's long axis, spacing
               light 20 m / medium 12 m / thorough 8 m, split around no-go
               zones
  visit        one photo point keep_out_m + 1 m from the landmark, on the
               side the boat approaches from
  photo_stops  n photo points on a ring keep_out_m + 2 m round a landmark,
               or spread across the fence
  lap          the area's outline, pulled 5 m inwards
  return_home  the final RTL (MIS-002)
Legs that would pass a no-go zone are re-routed round it.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from . import geo
from .geo import XY
from .models import Capture, Estimates, Intent, Item, LatLon, Mission
from .site import Named, Site
from .validator import Limits, estimate

LANE_SPACING_M = {"light": 20.0, "medium": 12.0, "thorough": 8.0}
EDGE_INSET_M = 4.0           # lanes stop this far inside the area edge
PLAN_CLEARANCE_M = 1.5       # planner's extra margin over the validator's 3 m
LAP_INSET_M = 5.0
STOP_PHOTOS, STOP_HOLD_S = 3, 10
SPEED = {"slow": 0.6, "normal": 1.0}
INTERVAL_S = {"explore": 10, "lap": 10}


class PlanError(Exception):
    """The intent can't be turned into a safe mission. message is for the
    adult and for the retry prompt; child is spoken."""

    def __init__(self, message: str, child: str = "I can't plan that one. "
                 "Shall we pick an adventure?"):
        super().__init__(message)
        self.message, self.child = message, child


@dataclass
class _Pt:
    xy: XY
    kind: str = "waypoint"
    photos: int | None = None
    hold_s: int | None = None


class Planner:
    def __init__(self, site: Site, limits: Limits = Limits()):
        self.site, self.limits = site, limits
        self.margin = limits.margin_m + PLAN_CLEARANCE_M
        self.incl = list(site.inclusion)

    # ---- public ----------------------------------------------------------
    def from_intent(self, intent: Intent, *, source: str, now_utc: str,
                    battery_pct: float = 100.0,
                    mission_id: str | None = None) -> Mission:
        if intent.declined is not None:
            raise PlanError("the request was declined",
                            intent.declined.reason_for_child)
        pts: list[_Pt] = []
        interval = 0
        here = self.site.home.point
        for step in intent.steps:
            if step.op == "explore":
                new = self._explore(self._area(step.area), step.coverage, here)
                interval = max(interval, INTERVAL_S["explore"])
            elif step.op == "visit":
                new = [self._visit(self._landmark(step.landmark), here,
                                   step.photos, step.hold_s)]
            elif step.op == "photo_stops":
                lm = self._landmark(step.near) if step.near else None
                new = self._photo_stops(step.n, lm, here)
            elif step.op == "lap":
                new = self._lap(self._area(step.area), here)
                interval = max(interval, INTERVAL_S["lap"])
            else:                                     # return_home
                break
            pts += new
            if new:
                here = new[-1].xy
        return self._build(pts, SPEED[intent.speed], interval, source,
                           now_utc, battery_pct, mission_id,
                           intent.summary_for_child)

    def template(self, name: str, area: str | None = None, *,
                 now_utc: str, battery_pct: float = 100.0,
                 mission_id: str | None = None) -> Mission:
        """MIS-005 offline templates, parameterised by a site area."""
        area = area or self.site.areas[0].name
        steps = TEMPLATES[name](area)
        intent = Intent.model_validate({
            "schema": "boaty.intent/1", "speed": "normal", "declined": None,
            "summary_for_child": TEMPLATE_SUMMARY[name].format(area=area),
            "steps": steps + [{"op": "return_home"}]})
        return self.from_intent(intent, source="template", now_utc=now_utc,
                                battery_pct=battery_pct,
                                mission_id=mission_id)

    def time_guide(self) -> dict:
        """Rough minutes for each thing the model can ask for, each as a
        whole trip from home and back (estimates x 1.2, as validated).
        Sent to the model so it can judge 'a short trip' (IF-11); no
        coordinates."""
        def minutes(steps) -> float | str:
            it = Intent.model_validate({
                "schema": "boaty.intent/1", "speed": "normal",
                "declined": None, "summary_for_child": "",
                "steps": steps + [{"op": "return_home"}]})
            try:
                m = self.from_intent(it, source="text", now_utc="")
            except PlanError:
                return "too long"
            return round(m.estimates.duration_s / 30) / 2
        areas = {a.name: {**{f"explore_{c}": minutes(
            [{"op": "explore", "area": a.name, "coverage": c}])
            for c in ("light", "medium", "thorough")},
            "lap": minutes([{"op": "lap", "area": a.name}])}
            for a in self.site.areas}
        marks = {m.name: minutes([{"op": "visit", "landmark": m.name,
                                   "photos": 3, "hold_s": 10}])
                 for m in self.site.landmarks}
        return {"areas": areas, "visit_landmark": marks}

    # ---- lookups ---------------------------------------------------------
    def _area(self, name: str) -> Named:
        a = self.site.find(name, "area")
        if a is None:
            raise PlanError(f"'{name}' is not an area on this site "
                            f"(areas: {[x.name for x in self.site.areas]})")
        return a

    def _landmark(self, name: str) -> Named:
        m = self.site.find(name, "landmark")
        if m is None:
            raise PlanError(f"'{name}' is not a landmark on this site "
                            f"(landmarks: "
                            f"{[x.name for x in self.site.landmarks]})")
        return m

    # ---- clearance -------------------------------------------------------
    def clear(self, p: XY, extra: float = 0.0) -> bool:
        m = self.margin + extra
        if geo.signed_depth(p, self.incl) < m:
            return False
        if geo.dist(p, self.site.home.point) > \
                self.site.max_distance_from_home_m - m:
            return False
        return all(z.depth(p) >= m for z in self.site.zones)

    def leg_clear(self, a: XY, b: XY) -> bool:
        return all(self.clear(p, -PLAN_CLEARANCE_M / 2)
                   for p in geo.sample_leg(a, b, 1.0))

    # ---- step geometry ---------------------------------------------------
    def _explore(self, area: Named, coverage: str, here: XY) -> list[_Pt]:
        spacing = LANE_SPACING_M[coverage]
        poly = list(area.poly)
        ang = geo.long_axis(poly)
        rot = [geo.rotate(p, -ang) for p in poly]
        ys = [p[1] for p in rot]
        y0, y1 = min(ys) + EDGE_INSET_M, max(ys) - EDGE_INSET_M
        if y1 < y0:
            y0 = y1 = (min(ys) + max(ys)) / 2
        n = max(1, int((y1 - y0) // spacing) + 1)
        off = (y1 - y0 - (n - 1) * spacing) / 2
        runs: list[list[XY]] = []
        for i in range(n):
            y = y0 + off + i * spacing
            xs = geo.scanline(rot, y)
            for xa, xb in zip(xs[::2], xs[1::2]):
                xa, xb = xa + EDGE_INSET_M, xb - EDGE_INSET_M
                if xb - xa < 2:
                    continue
                lane = [geo.rotate((x, y), ang) for x in
                        _linspace(xa, xb, max(2, int(xb - xa) + 1))]
                runs += self._clear_runs(lane)
        if not runs:
            raise PlanError(f"no clear water to explore in '{area.name}'")
        # Boustrophedon from the end nearest the boat.
        out: list[_Pt] = []
        pos = here
        for i, r in enumerate(runs):
            if geo.dist(pos, r[-1]) < geo.dist(pos, r[0]):
                r = r[::-1]
            out += [_Pt(r[0]), _Pt(r[-1])]
            pos = r[-1]
        return out

    def _clear_runs(self, lane: list[XY]) -> list[list[XY]]:
        runs, cur = [], []
        for p in lane:
            if self.clear(p):
                cur.append(p)
            else:
                if len(cur) >= 3:
                    runs.append(cur)
                cur = []
        if len(cur) >= 3:
            runs.append(cur)
        return runs

    def _ring(self, lm: Named, radius: float, facing: XY, k: int = 36
              ) -> list[XY]:
        """Candidate points round a landmark, nearest `facing` first."""
        c = lm.centre
        a0 = math.atan2(facing[1] - c[1], facing[0] - c[0])
        cand = []
        for j in range(k):
            a = a0 + (j + 1) // 2 * (2 * math.pi / k) * (-1) ** j
            r = radius
            p = (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
            while lm.distance(p) < radius and r < radius + 60:
                r += 0.5
                p = (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
            cand.append(p)
        return cand

    def _visit(self, lm: Named, here: XY, photos: int, hold_s: int) -> _Pt:
        for p in self._ring(lm, lm.keep_out_m + 1, here):
            if self.clear(p):
                return _Pt(p, "photo_point", photos, hold_s)
        raise PlanError(f"no safe place to stop near {lm.name}")

    def _photo_stops(self, n: int, lm: Named | None, here: XY) -> list[_Pt]:
        if lm is not None:
            cand = [p for p in self._ring(lm, lm.keep_out_m + 2, here, 72)
                    if self.clear(p)]
        else:
            xs = [p[0] for p in self.incl]
            ys = [p[1] for p in self.incl]
            cand = [(x, y) for x in _linspace(min(xs), max(xs), 30)
                    for y in _linspace(min(ys), max(ys), 30)
                    if self.clear((x, y))]
        if len(cand) < n:
            raise PlanError(f"only {len(cand)} safe photo stops available")
        # Farthest-point selection starting nearest the boat: spread out.
        chosen = [min(cand, key=lambda p: geo.dist(p, here))]
        while len(chosen) < n:
            chosen.append(max(cand, key=lambda p: min(geo.dist(p, c)
                                                      for c in chosen)))
        # Visit in nearest-neighbour order.
        out, pos, left = [], here, chosen[:]
        while left:
            p = min(left, key=lambda q: geo.dist(q, pos))
            left.remove(p)
            out.append(_Pt(p, "photo_point", STOP_PHOTOS, STOP_HOLD_S))
            pos = p
        return out

    def _lap(self, area: Named, here: XY) -> list[_Pt]:
        poly = list(area.poly)
        c = geo.centroid(poly)
        ring = []
        for p in poly:
            d = geo.dist(p, c)
            k = max(0.0, (d - LAP_INSET_M * 1.5) / d) if d else 0
            ring.append((c[0] + (p[0] - c[0]) * k, c[1] + (p[1] - c[1]) * k))
        ring = [p for p in ring if self.clear(p)]
        if len(ring) < 3:
            raise PlanError(f"'{area.name}' is too small or too crowded for "
                            "a lap")
        i = min(range(len(ring)), key=lambda j: geo.dist(ring[j], here))
        ring = ring[i:] + ring[:i]
        return [_Pt(p) for p in ring + [ring[0]]]

    # ---- routing ---------------------------------------------------------
    def _route(self, pts: list[_Pt]) -> list[_Pt]:
        """Insert detour waypoints where a leg would pass a no-go zone."""
        home = self.site.home.point
        out: list[_Pt] = []
        prev = home
        for p in pts + [_Pt(home, "home")]:
            if not self.leg_clear(prev, p.xy):
                out += [_Pt(v) for v in self._detour(prev, p.xy)]
            if p.kind != "home":
                out.append(p)
            prev = p.xy
        return out

    def _detour(self, a: XY, b: XY) -> list[XY]:
        vias: list[XY] = []
        for z in self.site.zones:
            c, r = z.bounding_circle()
            R = r + self.margin + 2
            vias += [(c[0] + R * math.cos(t * math.pi / 12),
                      c[1] + R * math.sin(t * math.pi / 12))
                     for t in range(24)]
        vias = [v for v in vias if self.clear(v)]
        # Shortest path over the visibility graph of a, the vias and b
        # (Dijkstra). Large zones, such as a nest stand-off, can need
        # several hops to get round.
        nodes = [a, *vias, b]
        n = len(nodes)
        dist = [math.inf] * n
        prev: list[int | None] = [None] * n
        dist[0] = 0.0
        done = [False] * n
        for _ in range(n):
            u = min((i for i in range(n) if not done[i]),
                    key=lambda i: dist[i], default=None)
            if u is None or dist[u] == math.inf or u == n - 1:
                break
            done[u] = True
            for v in range(1, n):
                if done[v]:
                    continue
                d = dist[u] + geo.dist(nodes[u], nodes[v])
                if d < dist[v] and self.leg_clear(nodes[u], nodes[v]):
                    dist[v], prev[v] = d, u
        if dist[n - 1] < math.inf:
            path, i = [], prev[n - 1]
            while i is not None and i != 0:
                path.append(nodes[i])
                i = prev[i]
            return path[::-1]
        raise PlanError("can't find a safe way round a no-go zone")

    # ---- assembly --------------------------------------------------------
    def _build(self, pts: list[_Pt], speed: float, interval: int,
               source: str, now_utc: str, battery_pct: float,
               mission_id: str | None, summary: str) -> Mission:
        if not pts:
            raise PlanError("the plan has nowhere to go")
        pts = self._route(pts)
        # Drop consecutive duplicates (e.g. a lap that ends where it began
        # right before the next step starts).
        dedup: list[_Pt] = []
        for p in pts:
            if dedup and p.kind == "waypoint" and \
                    geo.dist(dedup[-1].xy, p.xy) < 1.0:
                continue
            dedup.append(p)
        pts = dedup
        ll = self.site.enu.to_ll
        items = [Item(seq=1, kind="speed", speed_mps=speed)]
        for p in pts:
            lat, lon = ll(*p.xy)
            items.append(Item(seq=len(items) + 1, kind=p.kind,
                              lat=round(lat, 7), lon=round(lon, 7),
                              hold_s=p.hold_s, photos=p.photos))
        items.append(Item(seq=len(items) + 1, kind="rtl"))
        home = self.site.home.point
        route = [home] + [p.xy for p in pts] + [home]
        holds = sum(p.hold_s or 0 for p in pts)
        est = estimate(route, holds, speed, self.limits)
        cap = min(self.limits.max_duration_s, self.limits.duration_cap_s)
        if est.duration_s > cap:
            raise PlanError(
                f"that would take about {est.duration_s / 60:.0f} min; the "
                f"limit is {cap / 60:.0f} min. Use lighter coverage, a "
                "smaller area or fewer steps.",
                "That's too far for one trip! Shall we do a shorter one?")
        budget = self.limits.usable_energy_wh * battery_pct / 100 * \
            self.limits.energy_fraction
        if est.energy_wh > budget:
            raise PlanError(f"needs {est.energy_wh:.1f} Wh; only "
                            f"{budget:.1f} Wh may be used",
                            "The battery is too low for that trip.")
        hl = self.site.home_ll()
        m = Mission(id=mission_id or str(uuid.uuid4()), created_utc=now_utc,
                    source=source, site=self.site.name,
                    site_version=self.site.git_version,
                    home=LatLon(lat=round(hl[0], 7), lon=round(hl[1], 7)),
                    cruise_mps=max(0.6, min(1.2, speed)), items=items,
                    estimates=Estimates(distance_m=est.distance_m,
                                        duration_s=est.duration_s,
                                        energy_wh=est.energy_wh),
                    capture=Capture(interval_s=interval), checksum="",
                    summary_for_child=summary)
        return m.with_checksum()


def _linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [(a + b) / 2]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


TEMPLATES = {
    "explore": lambda area: [{"op": "explore", "area": area,
                              "coverage": "medium"}],
    "duck_watch": lambda area: [{"op": "explore", "area": area,
                                  "coverage": "light"},
                                 {"op": "photo_stops", "n": 3, "near": None}],
    "lap": lambda area: [{"op": "lap", "area": area}],
}
TEMPLATE_NAMES = {"explore": "Explore the bay", "duck_watch": "Duck watch",
                  "lap": "Lap of the bay"}
TEMPLATE_SUMMARY = {
    "explore": "Let's explore {area} and take pictures!",
    "duck_watch": "Duck watch! We'll look round {area} and stop for "
                  "photos from a safe distance.",
    "lap": "Let's go all the way round {area}!",
}


@dataclass(frozen=True)
class Preview:
    """MCN-D56: shown prominently before the approve control."""
    duration_s: int
    distance_m: float
    photos: int
    furthest_m: float


def preview(m: Mission, site: Site) -> Preview:
    enu, h = site.enu, site.home.point
    far = max((geo.dist(enu.to_xy(i.lat, i.lon), h) for i in m.items
               if i.lat is not None), default=0.0)
    n = m.photo_count
    if m.capture.interval_s:
        n += m.estimates.duration_s // m.capture.interval_s
    return Preview(m.estimates.duration_s, m.estimates.distance_m, n,
                   round(far, 1))
