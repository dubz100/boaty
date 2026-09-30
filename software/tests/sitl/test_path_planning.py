"""RTL round exclusion zones (NAV-007, HLM-D19, SDR RID-01).

The boat flies the real Milton site fence (island, reeds, nest, platform).
From beyond the island the straight line home crosses it; with ArduPilot's
Dijkstra path planner (OA_TYPE 2) RTL must go round instead.
"""
import math
import time

import pytest

from boaty.helm.api import Mission, MissionItem, RoverMode
from boaty.mcn.site import Site

from .conftest import SPEEDUP


@pytest.mark.parametrize("wind", [0.0, 3.0], ids=["calm", "wind-3ms-east"])
def test_sc27_rtl_goes_round_the_island(helm, sim, companion, evidence, wind):
    evidence("SC-27", "RTL from the far side of the island avoids it"
             + (f" ({wind:g} m/s wind from the east, pushing towards it)"
                if wind else ""),
             ["NAV-007", "HLM-D19", "FM-13", "FM-44"],
             "RTL commanded where the straight line home crosses the island: "
             "the boat never enters any exclusion zone, stays inside the "
             "inclusion fence, and reaches home (≤ 3 m) within 180 s")
    site = Site.named("milton-country-park")
    hx, hy = site.enu.to_xy(*helm.home())
    assert math.hypot(hx, hy) < 5, "simulator home is not the site home"

    # Out round the east side of the island to a point north of it, on a
    # route the validator would accept.
    out = [(35, 40), (15, 68)]
    far = out[-1]
    isl = next(z for z in site.zones if z.reason == "island")
    (cx, cy), r = isl.bounding_circle()
    # The straight line home from `far` passes through the island.
    t = ((cx - far[0]) * -far[0] + (cy - far[1]) * -far[1]) / \
        (far[0] ** 2 + far[1] ** 2)
    px, py = far[0] - t * far[0], far[1] - t * far[1]
    assert math.hypot(cx - px, cy - py) < r, "scenario geometry is wrong"

    helm.upload_fence(site.fence())
    m = Mission(tuple(MissionItem.waypoint(*site.enu.to_ll(x, y))
                      for x, y in out))
    helm.upload_mission(m)
    assert helm.verify(m)
    helm.arm()
    helm.start_mission()

    def xy():
        return sim.boat.e, sim.boat.n

    got_there = sim.wait_until(
        lambda: math.hypot(xy()[0] - far[0], xy()[1] - far[1]) < 4, 240)
    assert got_there, f"never reached the far point: {xy()}"
    sim.wait(3)
    # Wind from the east pushes the boat onto the island on the east side.
    sim.boat.faults.wind_speed, sim.boat.faults.wind_from_deg = wind, 90

    t0 = sim.t
    helm.return_home()
    min_depth, worst_zone, min_incl = math.inf, "", math.inf
    min_island = math.inf
    arrived = None
    trace: list = []
    end = sim.t + 180
    while sim.t < end:
        p = xy()
        for z in site.zones:
            d = z.depth(p)
            if d < min_depth:
                min_depth, worst_zone = d, z.reason
        min_island = min(min_island, isl.depth(p))
        min_incl = min(min_incl, -site_outside(site, p))
        if int(sim.t - t0) % 5 == 0 and (not trace or trace[-1][0] !=
                                         int(sim.t - t0)):
            trace.append((int(sim.t - t0), round(p[0], 1), round(p[1], 1),
                          round(sim.boat.speed(), 2)))
        if math.hypot(*p) < 3 and sim.boat.speed() < 0.3:
            arrived = sim.t - t0
            break
        time.sleep(0.05 / SPEEDUP)

    texts = companion.texts_after(t0)[:6]
    modes = sorted({RoverMode(mo).name for tm, a, mo in companion.modes
                    if tm >= t0})
    evidence.measure(rtl_to_home_s=arrived, closest_to_any_zone_m=min_depth,
                     closest_zone=worst_zone,
                     closest_to_island_edge_m=min_island,
                     closest_to_inclusion_edge_m=min_incl,
                     wind_mps=wind, modes=modes, texts=texts, track=trace)
    evidence.note("Needs OA_TYPE 2 (Dijkstra) and AVOID_BEHAVE 0 (slide): "
                  "with Rover's default 'stop' behaviour the planner's legs, "
                  "which may pass close to a zone, stalled the boat.")
    evidence.note("Every RTL trigger (COME HOME, fence breach, battery, "
                  "link loss) uses the same RTL mode, so this path planning "
                  "applies to all of them.")
    assert min_depth > 0, f"entered the {worst_zone} exclusion"
    assert min_incl > 0, "left the inclusion fence"
    assert arrived is not None, f"did not get home: {xy()}"
    helm.stop()


def site_outside(site, p) -> float:
    """Metres outside the inclusion fence (negative when inside)."""
    from boaty.mcn import geo
    return -geo.signed_depth(p, list(site.inclusion))
