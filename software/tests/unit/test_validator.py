"""C6 validator: adversarial missions (VAL-006, MCN-D40: >= 50 cases).

Each case builds a mission in local metres on the Milton site (or a small
purpose-built site) and checks the validator names the right rule. The
suite is also run under coverage with branch measurement:

    python -m pytest tests/unit/test_validator.py \
        --cov=boaty.mcn.validator --cov-branch   (if pytest-cov is present)
or  python tools/validator_coverage.py
"""
import copy
import inspect
import json
import math

import pytest

import boaty  # noqa: F401
from boaty.mcn import validator as V
from boaty.mcn.models import Capture, Estimates, Item, LatLon, Mission, \
    checksum
from boaty.mcn.site import Site
from boaty.mcn.validator import Limits, ValidatedMission, validate

T = "2026-09-29T10:00:00Z"
SITE = Site.named("milton-country-park")

# Milton geometry (metres from home): island circle r 7 at (10, 45); reeds
# polygon around (-45, 35); duck house (nest) r 15 at (-15, 62); platform r 4 at
# (58, 15). Fence: (-50,-10) (55,-10) (70,35) (45,75) (-30,80) (-60,40).


def mk(points, site=SITE, rtl=True, speed=None, **over):
    """points: list of (x, y) or (x, y, kind, hold, photos)."""
    items = []
    if speed is not None:
        items.append(Item(seq=1, kind="speed", speed_mps=speed))
    for p in points:
        x, y = p[0], p[1]
        kind = p[2] if len(p) > 2 else "waypoint"
        lat, lon = site.enu.to_ll(x, y)
        items.append(Item(seq=len(items) + 1, kind=kind, lat=lat, lon=lon,
                          hold_s=p[3] if len(p) > 3 else None,
                          photos=p[4] if len(p) > 4 else None))
    if rtl:
        items.append(Item(seq=len(items) + 1, kind="rtl"))
    hl = site.home_ll()
    d = dict(id="m-test", created_utc=T, source="text", site=site.name,
             site_version=site.git_version,
             home=LatLon(lat=hl[0], lon=hl[1]), cruise_mps=1.0, items=items,
             estimates=Estimates(distance_m=0, duration_s=0, energy_wh=0),
             capture=Capture(interval_s=0), checksum="")
    d.update(over)
    m = Mission(**d)
    return m.with_checksum() if "checksum" not in over else m


def rules(m, site=SITE, **kw):
    r, vm = validate(m, site, now_utc=T, **kw)
    assert r.ok == (vm is not None) == (not r.violations)
    return [v.rule for v in r.violations]


def small_site(zone=False, **props):
    """A concave L-shaped fence for leg-crossing cases, 40 m reach."""
    from boaty.mcn.geo import Enu
    e = Enu(52.0, 0.0)

    def ll(x, y):
        lat, lon = e.to_ll(x, y)
        return [lon, lat]
    ring = [(-10, -10), (30, -10), (30, 5), (5, 5), (5, 30), (-10, 30)]
    doc = {"type": "FeatureCollection",
           "properties": {"site": "L", "version": 1,
                          "max_distance_from_home_m": 60, **props},
           "features": [
               {"type": "Feature", "properties": {"role": "fence_inclusion"},
                "geometry": {"type": "Polygon",
                             "coordinates": [[ll(*p) for p in ring]]}},
               {"type": "Feature", "properties": {"role": "home",
                                                  "name": "h"},
                "geometry": {"type": "Point", "coordinates": ll(0, 0)}}]}
    if zone:
        doc["features"].append(
            {"type": "Feature", "properties": {"role": "exclusion",
                                               "radius_m": 2, "reason": "buoy"},
             "geometry": {"type": "Point", "coordinates": ll(22, 2)}})
    return Site.from_geojson(doc)


# ---------------------------------------------------------------- valid
def test_valid_simple_out_and_back():
    assert rules(mk([(0, 20), (20, 20)])) == []


def test_valid_only_rtl():
    assert rules(mk([])) == []


def test_valid_leg_between_island_and_reeds():
    assert rules(mk([(-25, 25), (-25, 38)])) == []


def test_valid_photo_point_and_speed():
    assert rules(mk([(0, 25, "photo_point", 20, 5)], speed=0.8)) == []


@pytest.mark.parametrize("name,area", [(t, a) for t in
                                       ("explore", "duck_watch", "lap")
                                       for a in ("home bay", "north pond")
                                       if (t, a) != ("lap", "north pond")])
@pytest.mark.verifies("MIS-005")
def test_templates_validate(name, area):
    from boaty.mcn.planner import Planner
    m = Planner(SITE).template(name, area, now_utc=T)
    assert rules(m) == []


def test_lap_refused_where_nest_standoff_crowds_area():
    # The duck house's 15 m nest stand-off (CR-07) fills most of the north
    # pond: the planner refuses rather than squeezing a lap past it.
    from boaty.mcn.planner import Planner, PlanError
    with pytest.raises(PlanError, match="too small or too crowded"):
        Planner(SITE).template("lap", "north pond", now_utc=T)


# ---------------------------------------------------------------- VAL-002
@pytest.mark.parametrize("pt", [
    (0, -30),            # south of the fence, behind the jetty
    (100, 30),           # far east
    (-58, 40),           # 2 m inside the west vertex
    (0, -8),             # 2 m inside the south edge
    (10, 45),            # centre of the island
    (10, 53.5),          # 1.5 m off the island's edge
    (-45, 35),           # in the reeds
    (-15, 76),           # 14 m from the duck house (nest stand-off)
    (58, 21),            # 2 m from the fishing platform
])
@pytest.mark.verifies("VAL-002")
def test_val002_bad_points(pt):
    assert "VAL-002" in rules(mk([pt]))


@pytest.mark.verifies("VAL-002")
def test_val002_leg_crosses_island():
    # both ends clear, straight line through the island
    assert "VAL-002" in rules(mk([(10, 25), (10, 65)]))


def test_val002_leg_crosses_reeds():
    assert "VAL-002" in rules(mk([(-45, 18), (-45, 55)]))


@pytest.mark.verifies("VAL-002")
def test_val002_rtl_leg_crosses_island():
    m = mk([(35, 45), (10, 65)])           # straight home from (10,65)
    r, _ = validate(m, SITE, now_utc=T)
    bad = [v for v in r.violations if v.rule == "VAL-002"]
    assert bad and bad[0].item_seq == m.items[-1].seq      # names the RTL


@pytest.mark.verifies("VAL-002")
def test_val002_concave_fence_leg_cuts_corner():
    s = small_site()
    assert rules(mk([(0, 25), (25, 0)], site=s), site=s) == ["VAL-002"]


def test_val002_leg_cuts_corner_and_zone():
    s = small_site(zone=True)
    r, _ = validate(mk([(0, 25), (25, 0)], site=s), s, now_utc=T)
    on_leg = [v for v in r.violations if v.item_seq == 2]
    assert [v.rule for v in on_leg] == ["VAL-002", "VAL-002"]
    assert "fence" in on_leg[0].message_for_adult
    assert "buoy" in on_leg[1].message_for_adult


def test_val002_concave_fence_around_corner_ok():
    s = small_site()
    assert rules(mk([(0, 25), (0, 0), (25, 0)], site=s), site=s) == []


@pytest.mark.verifies("VAL-002")
def test_val002_backstop_circle():
    s = small_site(max_distance_from_home_m=20)
    assert "VAL-002" in rules(mk([(0, 22)], site=s), site=s)


def test_val002_other_lake():
    assert "VAL-002" in rules(mk([(9000, 4000)]))


def test_val002_null_island():
    m = mk([(0, 20)])
    items = list(m.items)
    items[0] = items[0].model_copy(update={"lat": 0.0, "lon": 0.0})
    m = m.model_copy(update={"items": items}).with_checksum()
    assert "VAL-002" in rules(m)


@pytest.mark.parametrize("d,ok", [(2.9, False), (3.1, True)])
def test_val002_margin_edge_to_zone(d, ok):
    # platform circle r 4 at (58, 15): stand d m west of its edge
    x = 58 - 4 - d
    assert ("VAL-002" not in rules(mk([(x, 15)]))) == ok


@pytest.mark.verifies("VAL-007")
def test_val002_one_message_per_leg():
    r, _ = validate(mk([(0, -40)]), SITE, now_utc=T)
    assert sum(v.rule == "VAL-002" for v in r.violations) <= 4


@pytest.mark.verifies("VAL-007")
def test_val002_violations_have_location():
    r, _ = validate(mk([(10, 45)]), SITE, now_utc=T)
    for v in r.violations:
        assert v.at is not None and v.message_for_child
        assert abs(v.at.lat - 52.2448) < 0.01


# ---------------------------------------------------------------- VAL-003
@pytest.mark.verifies("VAL-003")
def test_val003_too_long_zigzag():
    zig = [(x, 10 + (i % 2) * 15) for i, x in
           enumerate(range(-30, 40, 2))] * 6
    assert "VAL-003" in rules(mk(zig))


@pytest.mark.verifies("VAL-003")
def test_val003_understated_estimate_is_not_trusted():
    zig = [(x, 10 + (i % 2) * 15) for i, x in
           enumerate(range(-30, 40, 2))] * 6
    m = mk(zig, estimates=Estimates(distance_m=10, duration_s=60,
                                    energy_wh=0.1))
    assert "VAL-003" in rules(m)


def test_val003_overstated_estimate_counts():
    m = mk([(0, 20)], estimates=Estimates(distance_m=40, duration_s=5000,
                                          energy_wh=0.2))
    assert "VAL-003" in rules(m)


@pytest.mark.verifies("VAL-003", "MIS-003")
def test_val003_low_battery_energy():
    m = mk([(-30, 20), (40, 20), (-30, 5), (40, 5)])
    assert rules(m, battery_pct=100) == []
    assert "VAL-003" in rules(m, battery_pct=3)


def test_val003_empty_battery():
    assert "VAL-003" in rules(mk([(0, 20)]), battery_pct=0)


def test_val003_negative_battery_clamped():
    assert "VAL-003" in rules(mk([(0, 20)]), battery_pct=-5)


@pytest.mark.verifies("MIS-003", "VAL-003")
def test_val003_cap_at_30_min_even_if_configured_longer():
    lim = Limits(max_duration_s=3600)
    m = mk([(0, 20)], estimates=Estimates(distance_m=40, duration_s=1900,
                                          energy_wh=0.2))
    assert "VAL-003" in rules(m, limits=lim)


@pytest.mark.verifies("MIS-003", "VAL-003")
def test_val003_configured_25_min_allows_22():
    lim = Limits(max_duration_s=1500)
    m = mk([(0, 20)], estimates=Estimates(distance_m=40, duration_s=1320,
                                          energy_wh=1.0))
    assert rules(m, limits=lim) == []


def test_val003_slow_speed_makes_it_longer():
    pts = [(-30, 20), (40, 20), (-30, 5), (40, 5)] * 3
    assert "VAL-003" not in rules(mk(pts, speed=1.0))
    assert "VAL-003" in rules(mk(pts, speed=0.3))


# ---------------------------------------------------------------- VAL-004
@pytest.mark.verifies("MIS-002")
def test_val004_no_rtl():
    assert "VAL-004" in rules(mk([(0, 20)], rtl=False))


@pytest.mark.verifies("MIS-002")
def test_val004_rtl_in_middle():
    m = mk([(0, 20)])
    items = [Item(seq=1, kind="rtl")] + [i.model_copy(update={"seq": i.seq +
                                                              1})
                                         for i in m.items]
    m = m.model_copy(update={"items": items}).with_checksum()
    assert "VAL-004" in rules(m)


def test_val004_empty():
    assert rules(mk([], rtl=False)) == ["VAL-004"]


def test_val004_mission_home_elsewhere():
    lat, lon = SITE.enu.to_ll(30, 30)
    assert "VAL-004" in rules(mk([(0, 20)], home=LatLon(lat=lat, lon=lon)))


def test_val004_boat_not_at_home():
    assert "VAL-004" in rules(mk([(0, 20)]),
                              boat_home=SITE.enu.to_ll(0, 25))


def test_val004_boat_near_home_ok():
    assert rules(mk([(0, 20)]), boat_home=SITE.enu.to_ll(3, 4)) == []


# ---------------------------------------------------------------- VAL-005
@pytest.mark.parametrize("s", [2.0, 1.51, 0.0, 0.1, -1.0, float("nan"),
                               float("inf"), None])
@pytest.mark.verifies("VAL-005")
def test_val005_bad_speed(s):
    m = mk([(0, 20)])
    # model_construct: what a caller could do by bypassing the schema
    items = [Item.model_construct(seq=1, kind="speed", speed_mps=s,
                                  lat=None, lon=None, hold_s=None,
                                  photos=None)] + \
        [i.model_copy(update={"seq": i.seq + 1}) for i in m.items]
    m = m.model_copy(update={"items": items}).with_checksum()
    assert "VAL-005" in rules(m)


def test_val005_max_speed_ok():
    assert rules(mk([(0, 20)], speed=1.5)) == []


@pytest.mark.parametrize("hold", [61, 0, -5, None, 3600])
@pytest.mark.verifies("VAL-005")
def test_val005_bad_hold(hold):
    assert "VAL-005" in rules(mk([(0, 20, "photo_point", hold, 3)]))


@pytest.mark.parametrize("photos", [11, 0, None, -1])
def test_val005_bad_photo_count(photos):
    assert "VAL-005" in rules(mk([(0, 20, "photo_point", 10, photos)]))


def test_val005_waypoint_cannot_hold():
    assert "VAL-005" in rules(mk([(0, 20, "waypoint", 30, None)]))


def test_val005_waypoint_cannot_take_photos():
    assert "VAL-005" in rules(mk([(0, 20, "waypoint", None, 4)]))


@pytest.mark.parametrize("lat", [None, float("nan"), float("inf")])
def test_val005_waypoint_without_position(lat):
    m = mk([(0, 20)])
    items = list(m.items)
    items[0] = items[0].model_copy(update={"lat": lat})
    m = m.model_copy(update={"items": items}).with_checksum()
    assert "VAL-005" in rules(m)


def test_val005_too_many_items():
    m = mk([(0, 10 + i) for i in range(10)])
    assert "VAL-005" in rules(m, limits=Limits(max_items=5))


def test_val005_seq_gap():
    m = mk([(0, 20)])
    items = [i.model_copy(update={"seq": i.seq * 2}) for i in m.items]
    m = m.model_copy(update={"items": items}).with_checksum()
    assert "VAL-005" in rules(m)


def test_val005_duplicate_seq():
    m = mk([(0, 20), (0, 25)])
    items = [i.model_copy(update={"seq": 1}) for i in m.items]
    m = m.model_copy(update={"items": items}).with_checksum()
    assert "VAL-005" in rules(m)


@pytest.mark.verifies("VAL-005")
def test_val005_photos_exceed_storage():
    m = mk([(0, 20, "photo_point", 10, 10), (10, 20, "photo_point", 10, 10)])
    assert rules(m, photo_capacity=25) == []
    assert "VAL-005" in rules(m, photo_capacity=15)


def test_val005_interval_photos_count_against_storage():
    m = mk([(0, 20), (20, 20)], capture=Capture(interval_s=2))
    assert "VAL-005" in rules(m, photo_capacity=20)


# ---------------------------------------------------------------- integrity
def test_edit_after_planning_breaks_checksum():
    m = mk([(0, 20)])
    items = list(m.items)
    items[0] = items[0].model_copy(update={"lat": items[0].lat + 1e-5})
    m = m.model_copy(update={"items": items})             # not re-summed
    assert "VAL-SUM" in rules(m)


@pytest.mark.verifies("SAF-004")
def test_forged_checksum():
    assert "VAL-SUM" in rules(mk([(0, 20)], checksum="sha256:" + "0" * 64))


def test_other_site():
    m = mk([(0, 20)]).model_copy(update={"site": "another-lake"})
    assert "VAL-SITE" in rules(m)


def test_stale_site_version():
    assert "VAL-SITE" in rules(mk([(0, 20)], site_version="0000000"))


def test_many_rules_at_once():
    m = mk([(10, 45, "photo_point", 90, 3)], rtl=False, speed=3.0)
    got = set(rules(m))
    assert {"VAL-002", "VAL-004", "VAL-005"} <= got


# ---------------------------------------------------------------- schema
@pytest.mark.verifies("MIS-004")
def test_unknown_major_version_rejected():
    d = mk([(0, 20)]).to_json()
    d["schema"] = "boaty.mission/2"
    with pytest.raises(Exception):
        Mission.model_validate(d)


@pytest.mark.verifies("MIS-004")
def test_extra_fields_rejected():
    d = mk([(0, 20)]).to_json()
    d["items"][0]["altitude"] = 50
    with pytest.raises(Exception):
        Mission.model_validate(d)


def test_unknown_item_kind_rejected():
    d = mk([(0, 20)]).to_json()
    d["items"][0]["kind"] = "jump"
    with pytest.raises(Exception):
        Mission.model_validate(d)


def test_nan_rejected_at_parse():
    d = mk([(0, 20)]).to_json()
    d["items"][0]["lat"] = float("nan")
    with pytest.raises(Exception):
        Mission.model_validate(d)


@pytest.mark.verifies("MIS-004")
def test_round_trip_keeps_checksum():
    m = mk([(0, 20, "photo_point", 10, 2)], speed=0.8)
    m2 = Mission.model_validate(json.loads(json.dumps(m.to_json())))
    assert m2 == m and checksum(m2.items) == m.checksum


def test_checksum_ignores_float_noise():
    m = mk([(0, 20)])
    items = list(m.items)
    items[0] = items[0].model_copy(update={"lat": items[0].lat + 1e-9})
    assert checksum(items) == m.checksum


# ---------------------------------------------------------------- VAL-006
@pytest.mark.verifies("VAL-006")
def test_deterministic():
    m = mk([(10, 45), (0, 20, "photo_point", 90, 11)])
    a = validate(m, SITE, now_utc=T)[0].model_dump()
    b = validate(copy.deepcopy(m), SITE, now_utc=T)[0].model_dump()
    assert a == b


@pytest.mark.verifies("VAL-006")
def test_no_io_or_randomness_in_validator():
    src = inspect.getsource(V)
    for bad in ("import random", "import time", "import socket", "open(",
                "datetime.now", "import requests", "urllib", "subprocess"):
        assert bad not in src, bad


@pytest.mark.verifies("SAF-004")
def test_validated_mission_only_from_validator():
    m = mk([(0, 20)])
    r, vm = validate(m, SITE, now_utc=T)
    with pytest.raises(TypeError):
        ValidatedMission(object(), m, r, None)
    with pytest.raises(AttributeError):
        vm.mission = mk([(10, 45)])
    assert vm.checksum == m.checksum
    assert len(vm.helm_items) == len(m.items)


def test_result_schema():
    r, _ = validate(mk([(10, 45)]), SITE, now_utc=T)
    d = r.model_dump(by_alias=True)
    assert d["schema"] == "boaty.validation/1" and d["ok"] is False
    assert d["validator_version"] == V.VALIDATOR_VERSION
    assert all(v["message_for_adult"] and v["message_for_child"]
               for v in d["violations"])


def test_estimate_matches_hand_calc():
    e = V.estimate([(0, 0), (0, 100), (0, 0)], 10, 1.0)
    # (200 m / 1 m/s + 10 s hold + 1 waypoint * 4 s) * 1.2
    assert e.distance_m == 200 and e.duration_s == math.ceil(214 * 1.2)
