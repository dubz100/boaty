"""C9 site store and linter (ICD IF-15, MCN-D53).

A site is one GeoJSON FeatureCollection in software/sites/<site>.geojson,
committed to git (FEN-002). Coordinates are [lon, lat] (RFC 7946).

Site loads the file into local metres around the first home and answers the
planner's and validator's questions: where is the fence, which names exist,
how far is it to the island. lint() checks the IF-15 rules plus the
FMEA-driven ones in MCN-D53; any error blocks arming.
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..helm.api import Fence
from . import geo
from .geo import XY, Enu

SITES = Path(__file__).resolve().parents[2] / "sites"
UK_BBOX = dict(lat=(49.8, 60.95), lon=(-8.7, 1.8))
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
MAX_INCLUSION_VERTICES = 70
MAX_EXCLUSIONS = 10
NEST_STANDOFF_M = 15.0     # OPS-005 (CR-07): photograph wildlife from here
WILDLIFE_KINDS = ("nest",)


@dataclass(frozen=True)
class Zone:
    """An exclusion: polygon (poly) or circle (centre + radius)."""
    poly: tuple[XY, ...] = ()
    centre: XY | None = None
    radius: float = 0.0
    reason: str = ""

    def depth(self, p: XY) -> float:
        """Distance outside the zone: positive outside, negative inside."""
        if self.centre is not None:
            return geo.dist(p, self.centre) - self.radius
        return -geo.signed_depth(p, list(self.poly))

    def bounding_circle(self) -> tuple[XY, float]:
        if self.centre is not None:
            return self.centre, self.radius
        c = geo.centroid(list(self.poly))
        return c, max(geo.dist(c, v) for v in self.poly)


@dataclass(frozen=True)
class Named:
    role: str
    name: str
    aliases: tuple[str, ...]
    point: XY | None = None
    poly: tuple[XY, ...] = ()
    keep_out_m: float = 0.0
    wind_from: tuple[str, ...] = ()

    def names(self) -> set[str]:
        return {norm(self.name), *(norm(a) for a in self.aliases)}

    @property
    def centre(self) -> XY:
        return self.point if self.point is not None else \
            geo.centroid(list(self.poly))

    def distance(self, p: XY) -> float:
        """Distance from the landmark itself (0 inside a polygon)."""
        if self.point is not None:
            return geo.dist(p, self.point)
        return max(0.0, -geo.signed_depth(p, list(self.poly)))


def norm(name: str) -> str:
    n = " ".join(name.lower().replace("'", "").split())
    return n[4:] if n.startswith("the ") else n


class SiteError(ValueError):
    pass


@dataclass
class Site:
    name: str
    version: int
    doc: dict
    enu: Enu
    inclusion: tuple[XY, ...]
    zones: tuple[Zone, ...]
    homes: tuple[Named, ...]
    areas: tuple[Named, ...]
    landmarks: tuple[Named, ...]
    launches: tuple[Named, ...]
    props: dict = field(default_factory=dict)
    git_version: str = "uncommitted"

    # ---- loading ------------------------------------------------------
    @classmethod
    def load(cls, path: Path | str) -> "Site":
        path = Path(path)
        s = cls.from_geojson(json.loads(path.read_text()))
        s.git_version = git_commit_of(path)
        return s

    @classmethod
    def named(cls, site: str) -> "Site":
        return cls.load(SITES / f"{site}.geojson")

    @classmethod
    def from_geojson(cls, doc: dict) -> "Site":
        feats = doc.get("features") or []
        homes = [f for f in feats if _role(f) == "home"
                 and _gtype(f) == "Point"]
        if not homes:
            raise SiteError("the site has no home point")
        lon0, lat0 = homes[0]["geometry"]["coordinates"][:2]
        enu = Enu(lat0, lon0)

        def pt(c) -> XY:
            return enu.to_xy(c[1], c[0])

        def ring(g) -> tuple[XY, ...]:
            r = [pt(c) for c in g["coordinates"][0]]
            if len(r) > 1 and r[0] == r[-1]:
                r = r[:-1]
            return tuple(r)

        incl, zones, hs, areas, lms, launches = (), [], [], [], [], []
        for f in feats:
            role, g, p = _role(f), f.get("geometry") or {}, \
                f.get("properties") or {}
            gt = g.get("type")
            name, aliases = p.get("name", ""), tuple(p.get("aliases", []))
            if role == "fence_inclusion" and gt == "Polygon" and not incl:
                incl = ring(g)
            elif role == "exclusion" and gt == "Polygon":
                zones.append(Zone(poly=ring(g), reason=p.get("reason", "")))
            elif role == "exclusion" and gt == "Point":
                zones.append(Zone(centre=pt(g["coordinates"]),
                                  radius=float(p.get("radius_m", 0)),
                                  reason=p.get("reason", "")))
            elif role in ("home", "launch") and gt == "Point":
                n = Named(role, name, aliases, point=pt(g["coordinates"]),
                          wind_from=tuple(p.get("good_wind_from", [])))
                (hs if role == "home" else launches).append(n)
            elif role == "area" and gt == "Polygon":
                areas.append(Named(role, name, aliases, poly=ring(g)))
            elif role == "landmark" and gt in ("Point", "Polygon"):
                kw = dict(point=pt(g["coordinates"])) if gt == "Point" \
                    else dict(poly=ring(g))
                lms.append(Named(role, name, aliases,
                                 keep_out_m=float(p.get("keep_out_m", 0)),
                                 **kw))
        props = doc.get("properties") or {}
        return cls(props.get("site", "unnamed"), int(props.get("version", 0)),
                   doc, enu, incl, tuple(zones), tuple(hs), tuple(areas),
                   tuple(lms), tuple(launches), props)

    # ---- lookups ------------------------------------------------------
    @property
    def home(self) -> Named:
        return self.homes[0]

    def home_ll(self) -> tuple[float, float]:
        return self.enu.to_ll(*self.home.point)

    def find(self, name: str, role: str) -> Named | None:
        pool = {"area": self.areas, "landmark": self.landmarks,
                "home": self.homes}[role]
        k = norm(name)
        return next((n for n in pool if k in n.names()), None)

    @property
    def max_distance_from_home_m(self) -> float:
        return float(self.props.get("max_distance_from_home_m", 100))

    def fence(self) -> Fence:
        """The helm's fence (IF-02 fence items) from the site file."""
        ll = self.enu.to_ll
        polys = tuple(tuple(ll(*v) for v in z.poly) for z in self.zones
                      if z.centre is None)
        circles = tuple((*ll(*z.centre), z.radius) for z in self.zones
                        if z.centre is not None)
        return Fence(tuple(ll(*v) for v in self.inclusion), polys, circles)

    def context_for_llm(self) -> dict:
        """What the Claude API may know about the site (IF-11 data
        minimisation): names, rough sizes and directions from home. No
        coordinates."""
        h = self.home.point

        def where(c: XY) -> dict:
            d = geo.dist(c, h)
            b = math.degrees(math.atan2(c[0] - h[0], c[1] - h[1])) % 360
            return {"distance_from_home_m": round(d / 5) * 5,
                    "direction_from_home": COMPASS[int((b + 22.5) // 45) % 8]}

        def size(poly) -> dict:
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            return {"size_m": [round(max(xs) - min(xs)),
                               round(max(ys) - min(ys))]}

        return {
            "site": self.name,
            "home": self.home.name,
            "areas": [{"name": a.name, "aliases": list(a.aliases),
                       **size(a.poly), **where(a.centre)} for a in self.areas],
            "landmarks": [{"name": m.name, "aliases": list(m.aliases),
                           **where(m.centre)} for m in self.landmarks],
            "no_go_zones": len(self.zones),
            "fence_size_m": size(self.inclusion)["size_m"],
        }


def _role(f) -> str:
    return (f.get("properties") or {}).get("role", "")


def _gtype(f) -> str:
    return (f.get("geometry") or {}).get("type", "")


def git_commit_of(path: Path) -> str:
    """site_version in Mission v1: the last commit that touched the file,
    with '+dirty' if the working copy differs."""
    try:
        c = subprocess.run(["git", "log", "-1", "--format=%h", "--",
                            path.name], cwd=path.parent, capture_output=True,
                           text=True, timeout=5).stdout.strip()
        d = subprocess.run(["git", "status", "--porcelain", "--", path.name],
                           cwd=path.parent, capture_output=True, text=True,
                           timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "uncommitted"
    if not c:
        return "uncommitted"
    return c + ("+dirty" if d else "")


# ---------------------------------------------------------------------------
# Linter


@dataclass(frozen=True)
class Issue:
    severity: str          # "error" blocks arming; "warning" is shown
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity.upper()} {self.rule}: {self.message}"


FENCE_GUIDE_M = 5.0        # FEN-003 guide
REFERENCE_MAX_M = 1000.0   # MCN-D53


def lint(doc: dict, reference: tuple[float, float] | None = None
         ) -> list[Issue]:
    """IF-15 rules plus MCN-D53. reference is the site's configured
    location in Mission Control's settings (not in the file itself), so a
    file drawn in the wrong place is caught."""
    out: list[Issue] = []

    def err(rule, msg):
        out.append(Issue("error", rule, msg))

    def warn(rule, msg):
        out.append(Issue("warning", rule, msg))

    if doc.get("type") != "FeatureCollection":
        err("IF-15", "not a GeoJSON FeatureCollection")
        return out
    props = doc.get("properties") or {}
    if not props.get("site"):
        err("IF-15", "properties.site is missing")
    feats = doc.get("features") or []

    # Coordinate order and UK box, on every coordinate in the file.
    bad = swapped = 0
    for f in feats:
        for lon, lat in _coords(f.get("geometry") or {}):
            if not _in_uk(lat, lon):
                bad += 1
                if _in_uk(lon, lat):
                    swapped += 1
    if swapped:
        err("MCN-D53", f"{swapped} coordinate(s) look like [lat, lon]; "
            "GeoJSON needs [lon, lat]")
        return out
    if bad:
        err("MCN-D53", f"{bad} coordinate(s) are outside the UK")
        return out

    roles = [_role(f) for f in feats]
    known = {"fence_inclusion", "exclusion", "home", "area", "landmark",
             "launch"}
    for r in sorted(set(roles) - known):
        err("IF-15", f"unknown role '{r}'")

    incl = [f for f in feats if _role(f) == "fence_inclusion"]
    if len(incl) != 1:
        err("FEN-001", f"needs exactly one fence_inclusion, found {len(incl)}")
        return out
    if _gtype(incl[0]) != "Polygon":
        err("FEN-001", "fence_inclusion must be a Polygon")
        return out
    try:
        site = Site.from_geojson(doc)
    except SiteError as e:
        err("PRE-002", str(e))
        return out
    except (KeyError, TypeError, ValueError, IndexError) as e:
        err("IF-15", f"malformed feature: {e}")
        return out
    poly = list(site.inclusion)
    if not 3 <= len(poly) <= MAX_INCLUSION_VERTICES:
        err("FEN-001", f"inclusion has {len(poly)} vertices "
            f"(3 to {MAX_INCLUSION_VERTICES})")
        return out
    if geo.self_intersects(poly):
        err("FEN-001", "inclusion polygon crosses itself")
        return out

    def within(p: XY) -> float:
        return geo.signed_depth(p, poly)

    # Exclusions.
    n_excl = sum(1 for r in roles if r == "exclusion")
    if n_excl > MAX_EXCLUSIONS:
        err("FEN-001", f"{n_excl} exclusions (max {MAX_EXCLUSIONS})")
    for f in feats:
        if _role(f) == "exclusion" and _gtype(f) == "Point" and \
                float((f.get("properties") or {}).get("radius_m", 0)) <= 0:
            err("FEN-001", "circular exclusion needs radius_m > 0")
        if _role(f) == "exclusion" and _gtype(f) not in ("Point", "Polygon"):
            err("FEN-001", "exclusion must be a Polygon or a Point")
        # Wildlife stand-off (OPS-005, CR-07). A nest circle carries the
        # stand-off in its radius; a nest polygon is drawn with it included.
        wl = (f.get("properties") or {}).get("wildlife")
        if _role(f) == "exclusion" and wl is not None:
            p = f.get("properties") or {}
            if wl not in WILDLIFE_KINDS:
                err("OPS-005", f"unknown wildlife kind '{wl}'")
            elif _gtype(f) == "Point" and \
                    float(p.get("radius_m", 0)) < NEST_STANDOFF_M:
                err("OPS-005", f"nest exclusion ({p.get('reason', '')}) "
                    f"radius {float(p.get('radius_m', 0)):g} m is under "
                    f"the {NEST_STANDOFF_M:g} m wildlife stand-off")
            elif _gtype(f) == "Polygon":
                warn("OPS-005", f"nest polygon ({p.get('reason', '')}): "
                     f"check it is drawn {NEST_STANDOFF_M:g} m out from "
                     "the nests")
    for i, z in enumerate(site.zones):
        pts = z.poly if z.centre is None else (z.centre,)
        if any(within(p) - (z.radius if z.centre else 0) < 0 for p in pts):
            err("OPS-005", f"exclusion {i + 1} ({z.reason or 'no reason'}) "
                "is not inside the inclusion fence")

    # Homes (PRE-002, MCN-D53), with the helm's circular backstop.
    if not site.homes:
        err("PRE-002", "no home point")
    radius = site.max_distance_from_home_m
    for h in site.homes:
        d = within(h.point)
        if d <= 0:
            err("MCN-D53", f"home '{h.name}' is outside the inclusion fence")
        elif d < FENCE_GUIDE_M:
            warn("FEN-003", f"home '{h.name}' is {d:.1f} m from the fence, "
                 "inside the 5 m guide")
        for z in site.zones:
            if z.depth(h.point) <= 0:
                err("PRE-002", f"home '{h.name}' is inside an exclusion")
        far = geo.furthest(poly, h.point)
        if far > radius - 3:
            err("IF-15", f"the fence reaches {far:.0f} m from home "
                f"'{h.name}'; the helm's circular backstop "
                f"(FENCE_RADIUS {radius:.0f} m, 3 m margin) would cut it")

    # Areas and landmarks.
    seen: dict[str, str] = {}
    for n in (*site.areas, *site.landmarks, *site.homes, *site.launches):
        if not n.name:
            err("IF-15", f"a {n.role} has no name")
        for k in n.names():
            if k in seen and seen[k] != n.name:
                err("IF-15", f"name '{k}' is used by both '{seen[k]}' and "
                    f"'{n.name}'")
            seen[k] = n.name
    for a in site.areas:
        if any(within(p) < 0 for p in a.poly):
            err("IF-15", f"area '{a.name}' is not inside the inclusion")
        if abs(geo.area(list(a.poly))) < 100:
            warn("IF-15", f"area '{a.name}' is under 100 m²")
    for m in site.landmarks:
        if m.keep_out_m <= 0:
            err("IF-15", f"landmark '{m.name}' needs keep_out_m > 0")
        for z in site.zones:
            if z.depth(m.centre) <= 0 and m.point is not None:
                c, r = z.bounding_circle()
                if m.keep_out_m < r - geo.dist(c, m.point) + 3:
                    warn("MCN-D34", f"landmark '{m.name}': keep_out_m "
                         f"{m.keep_out_m:g} m would put photo stops within "
                         "3 m of its exclusion")

    # Launch points (MCN-D58).
    for L in site.launches:
        bad_dirs = [d for d in L.wind_from if d not in COMPASS]
        if bad_dirs:
            err("MCN-D58", f"launch '{L.name}': unknown wind sectors "
                f"{bad_dirs}")
        if not L.wind_from:
            warn("MCN-D58", f"launch '{L.name}' lists no good_wind_from")

    # Reference (MCN-D53).
    if reference is not None:
        hl = site.home_ll()
        d = geo.dist(Enu(*reference).to_xy(*hl), (0.0, 0.0))
        if d > REFERENCE_MAX_M:
            err("MCN-D53", f"site is {d / 1000:.1f} km from its configured "
                "reference (max 1 km)")
    return out


def _coords(g: dict):
    t, c = g.get("type"), g.get("coordinates")
    if t == "Point":
        yield c[0], c[1]
    elif t == "Polygon":
        for r in c:
            for p in r:
                yield p[0], p[1]


def _in_uk(lat: float, lon: float) -> bool:
    return UK_BBOX["lat"][0] <= lat <= UK_BBOX["lat"][1] and \
        UK_BBOX["lon"][0] <= lon <= UK_BBOX["lon"][1]


def blocking(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.severity == "error"]
