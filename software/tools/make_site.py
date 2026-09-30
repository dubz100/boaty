"""Write sites/milton-country-park.geojson.

The shape is a stand-in drawn in metres around the simulator's home point
(boaty.sim.sitl.MILTON_HOME) so the simulator and the site agree. Redraw it
on the real map in the fence editor before the first lake trial (IF-15
note, OPS-005); the names and roles are what the planner relies on.

    PYTHONPATH=. python tools/make_site.py
"""
import json
from pathlib import Path

from boaty.mcn.geo import Enu
from boaty.sim.sitl import MILTON_HOME

OUT = Path(__file__).resolve().parents[1] / "sites" / "milton-country-park.geojson"
E = Enu(*MILTON_HOME[:2])


def ll(x, y):
    lat, lon = E.to_ll(x, y)
    return [round(lon, 7), round(lat, 7)]


def poly(pts):
    r = [ll(*p) for p in pts]
    return {"type": "Polygon", "coordinates": [r + [r[0]]]}


def point(x, y):
    return {"type": "Point", "coordinates": ll(x, y)}


def feat(geom, **props):
    return {"type": "Feature", "properties": props, "geometry": geom}


features = [
    feat(poly([(-50, -10), (55, -10), (70, 35), (45, 75), (-30, 80),
               (-60, 40)]), role="fence_inclusion"),
    feat(point(10, 45), role="exclusion", radius_m=7, reason="island"),
    feat(poly([(-50, 25), (-40, 25), (-38, 45), (-48, 48)]),
         role="exclusion", reason="reed bed"),
    # Nest structure (CR-07, OPS-005): a 15 m wildlife stand-off.
    feat(point(-15, 62), role="exclusion", radius_m=15, wildlife="nest",
         reason="floating duck house (nest)"),
    feat(point(58, 15), role="exclusion", radius_m=4,
         reason="fishing platform"),
    feat(point(0, 0), role="home", name="jetty"),
    feat(poly([(-35, -4), (45, -4), (50, 22), (-38, 22)]), role="area",
         name="home bay", aliases=["the bay", "bay"]),
    feat(poly([(-25, 58), (40, 55), (42, 70), (-25, 74)]), role="area",
         name="north pond", aliases=["far end", "the top"]),
    feat(poly([(-47, -7), (52, -7), (66, 34), (43, 72), (-29, 77),
               (-56, 40)]), role="area", name="whole pond",
         aliases=["pond", "lake", "everywhere"]),
    feat(point(10, 45), role="landmark", name="the island",
         aliases=["island"], keep_out_m=12),
    feat(poly([(-50, 25), (-40, 25), (-38, 45), (-48, 48)]), role="landmark",
         name="the reeds", aliases=["reeds", "reed bed"], keep_out_m=6),
    feat(point(-15, 62), role="landmark", name="the duck house",
         aliases=["duck house", "ducks house"], keep_out_m=18),
    feat(point(0, -14), role="launch", name="jetty",
         good_wind_from=["N", "NE", "NW"]),
    feat(point(72, -6), role="launch", name="east beach",
         good_wind_from=["W", "SW", "NW"]),
]

doc = {"type": "FeatureCollection",
       "properties": {"site": "milton-country-park", "version": 2,
                      "wifi_channel": 6, "max_distance_from_home_m": 100,
                      "note": "Stand-in shape at the simulator home; redraw "
                              "on the real map before the first lake trial."},
       "features": features}
OUT.write_text(json.dumps(doc, indent=1) + "\n")
print("wrote", OUT)
