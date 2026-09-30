"""C9 site store and linter (IF-15, MCN-D53, SC-26)."""
import copy
import json

import pytest

import boaty  # noqa: F401
from boaty.mcn.site import SITES, Site, blocking, lint

REF = (52.2448, 0.1597)
DOC = json.loads((SITES / "milton-country-park.geojson").read_text())


def doc():
    return copy.deepcopy(DOC)


def feature(d, role, name=None):
    return next(f for f in d["features"] if f["properties"]["role"] == role
                and (name is None or f["properties"].get("name") == name))


def errors(d, ref=REF):
    return [i for i in blocking(lint(d, ref))]


@pytest.mark.verifies("FEN-002")
def test_milton_is_clean():
    assert lint(DOC, REF) == []


def test_load_by_name_and_lookup():
    s = Site.named("milton-country-park")
    assert s.find("The Island", "landmark").name == "the island"
    assert s.find("reed bed", "landmark").name == "the reeds"
    assert s.find("far end", "area").name == "north pond"
    assert s.find("the moon", "area") is None
    assert s.home.name == "jetty"


def test_fence_for_helm():
    f = Site.named("milton-country-park").fence()
    assert len(f.inclusion) == 6
    assert len(f.exclusions) == 1 and len(f.exclusion_circles) == 3
    lat, lon = f.inclusion[0]
    assert 52.2 < lat < 52.3 and 0.1 < lon < 0.2


def test_llm_context_has_no_coordinates():
    """IF-11 data minimisation: names, sizes, directions only."""
    ctx = Site.named("milton-country-park").context_for_llm()
    text = json.dumps(ctx)
    assert "52.2" not in text and "0.15" not in text and "0.16" not in text
    assert "coordinates" not in text
    assert {a["name"] for a in ctx["areas"]} == {"home bay", "north pond",
                                                 "whole pond"}


def test_swapped_coordinates():
    d = doc()
    for f in d["features"]:
        g = f["geometry"]
        if g["type"] == "Point":
            g["coordinates"] = g["coordinates"][::-1]
        else:
            g["coordinates"] = [[p[::-1] for p in r] for r in g["coordinates"]]
    e = errors(d)
    assert e and "[lat, lon]" in e[0].message


def test_outside_uk():
    d = doc()
    for f in d["features"]:
        g = f["geometry"]
        if g["type"] == "Point":
            g["coordinates"][0] += 10
    assert any("outside the UK" in i.message for i in errors(d))


def test_far_from_reference():
    assert any(i.rule == "MCN-D53" for i in errors(DOC, (52.3, 0.2)))


def test_home_outside_inclusion():
    d = doc()
    feature(d, "home")["geometry"]["coordinates"][1] -= 0.0002   # ~22 m S
    assert any("outside the inclusion" in i.message for i in errors(d))


@pytest.mark.verifies("FEN-003")
def test_home_in_guide_is_warning():
    d = doc()
    feature(d, "home")["geometry"]["coordinates"][1] -= 0.00006  # ~7 m S
    out = lint(d, REF)
    assert any(i.rule == "FEN-003" and i.severity == "warning" for i in out)


def test_home_in_exclusion():
    d = doc()
    home = feature(d, "home")
    isl = next(f for f in d["features"]
               if f["properties"].get("reason") == "island")
    home["geometry"]["coordinates"] = list(isl["geometry"]["coordinates"])
    assert any(i.rule == "PRE-002" for i in errors(d))


def test_two_inclusions():
    d = doc()
    d["features"].append(copy.deepcopy(feature(d, "fence_inclusion")))
    assert any(i.rule == "FEN-001" for i in errors(d))


def test_no_inclusion():
    d = doc()
    d["features"] = [f for f in d["features"]
                     if f["properties"]["role"] != "fence_inclusion"]
    assert any(i.rule == "FEN-001" for i in errors(d))


def test_inclusion_as_point():
    d = doc()
    feature(d, "fence_inclusion")["geometry"] = {
        "type": "Point", "coordinates": [0.1597, 52.2448]}
    assert any(i.rule == "FEN-001" for i in errors(d))


def test_bow_tie_inclusion():
    d = doc()
    ring = feature(d, "fence_inclusion")["geometry"]["coordinates"][0]
    ring[1], ring[2] = ring[2], ring[1]
    assert any("crosses itself" in i.message for i in errors(d))


@pytest.mark.verifies("FEN-001")
def test_too_many_vertices():
    d = doc()
    ring = feature(d, "fence_inclusion")["geometry"]["coordinates"][0]
    a, b = ring[0], ring[1]
    extra = [[a[0] + (b[0] - a[0]) * k / 80, a[1] + (b[1] - a[1]) * k / 80]
             for k in range(1, 80)]
    ring[1:1] = extra
    assert any("vertices" in i.message for i in errors(d))


@pytest.mark.verifies("FEN-001")
def test_exclusion_outside_inclusion():
    d = doc()
    d["features"].append({"type": "Feature", "properties": {
        "role": "exclusion", "radius_m": 3, "reason": "car park"},
        "geometry": {"type": "Point", "coordinates": [0.1597, 52.2430]}})
    assert any(i.rule == "OPS-005" for i in errors(d))


@pytest.mark.verifies("FEN-001")
def test_eleven_exclusions():
    d = doc()
    for k in range(7):
        d["features"].append({"type": "Feature", "properties": {
            "role": "exclusion", "radius_m": 1, "reason": f"buoy {k}"},
            "geometry": {"type": "Point",
                         "coordinates": [0.1595 + k * 0.00005, 52.2450]}})
    assert any("exclusions (max 10)" in i.message for i in errors(d))


@pytest.mark.verifies("FEN-001")
def test_circle_without_radius():
    d = doc()
    d["features"].append({"type": "Feature", "properties": {
        "role": "exclusion", "reason": "buoy"},
        "geometry": {"type": "Point", "coordinates": [0.1597, 52.2450]}})
    assert any("radius_m" in i.message for i in errors(d))


def nest(d):
    return next(f for f in d["features"]
                if f["properties"].get("wildlife") == "nest")


@pytest.mark.verifies("OPS-005")
def test_nest_under_standoff_blocks():
    # OPS-005 (CR-07): nests are photographed from 15 m, never closer.
    d = doc()
    nest(d)["properties"]["radius_m"] = 6
    assert any(i.rule == "OPS-005" and "stand-off" in i.message
               for i in errors(d))


def test_unknown_wildlife_kind_blocks():
    d = doc()
    nest(d)["properties"]["wildlife"] = "swan"
    assert any("unknown wildlife" in i.message for i in errors(d))


def test_nest_polygon_warns_to_check_standoff():
    d = doc()
    reeds = next(f for f in d["features"]
                 if f["properties"].get("reason") == "reed bed")
    reeds["properties"]["wildlife"] = "nest"
    out = lint(d, REF)
    assert any(i.rule == "OPS-005" for i in out) and not blocking(out)


def test_fence_beyond_backstop_circle():
    d = doc()
    d["properties"]["max_distance_from_home_m"] = 60
    assert any("backstop" in i.message for i in errors(d))


def test_duplicate_names():
    d = doc()
    feature(d, "area", "north pond")["properties"]["aliases"].append("island")
    assert any("used by both" in i.message for i in errors(d))


def test_landmark_without_keep_out():
    d = doc()
    feature(d, "landmark", "the island")["properties"]["keep_out_m"] = 0
    assert any("keep_out_m" in i.message for i in errors(d))


def test_keep_out_smaller_than_exclusion_warns():
    d = doc()
    feature(d, "landmark", "the island")["properties"]["keep_out_m"] = 8
    out = lint(d, REF)
    assert any(i.rule == "MCN-D34" for i in out) and not blocking(out)


def test_area_outside_fence():
    d = doc()
    ring = feature(d, "area", "home bay")["geometry"]["coordinates"][0]
    ring[0][1] -= 0.0003
    ring[-1][1] -= 0.0003
    assert any("area 'home bay'" in i.message for i in errors(d))


def test_bad_wind_sector():
    d = doc()
    feature(d, "launch", "jetty")["properties"]["good_wind_from"] = ["NNE"]
    assert any(i.rule == "MCN-D58" for i in errors(d))


def test_launch_without_wind_warns():
    d = doc()
    feature(d, "launch", "jetty")["properties"]["good_wind_from"] = []
    assert any(i.rule == "MCN-D58" and i.severity == "warning"
               for i in lint(d, REF))


def test_unknown_role():
    d = doc()
    d["features"][0]["properties"]["role"] = "fence"
    assert any("unknown role" in i.message for i in errors(d))


def test_not_a_feature_collection():
    assert errors({"type": "Feature"})


def test_missing_site_name():
    d = doc()
    del d["properties"]["site"]
    assert any("properties.site" in i.message for i in errors(d))


def test_no_home():
    d = doc()
    d["features"] = [f for f in d["features"]
                     if f["properties"]["role"] != "home"]
    assert any(i.rule == "PRE-002" for i in errors(d))


@pytest.mark.parametrize("sev", ["error", "warning"])
def test_issue_str(sev):
    from boaty.mcn.site import Issue
    assert str(Issue(sev, "X", "m")).startswith(sev.upper())
