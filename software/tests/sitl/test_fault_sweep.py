"""SC-13: single-fault sweep across mission phases (FS-013, SDR WP3).

FS-013: no single failure shall cause the boat to leave the inclusion fence
under its own power. Each case flies a fresh simulator with the boat
services running, injects one fault in one phase of a mission close to the
fence, and watches the truth for 45 s: the boat must never be outside the
fence while its motors are driving.
"""
import math
import time

import pytest

from boaty.helm.api import Fence, Mission, MissionItem, RoverMode
from boaty.sim.geo import offset, square

from .conftest import SPEEDUP, boaty_events, launch, motors_off

HALF = 25.0
M_PER_DEG = 111_320.0
WATCH_S = 45.0


def outside_by(sim) -> float:
    return max(abs(sim.boat.n) - HALF, abs(sim.boat.e) - HALF, 0.0)


def mission(h, pts) -> Mission:
    lat, lon = h.home()
    return Mission(tuple(MissionItem.waypoint(*offset(lat, lon, n, e))
                         for n, e in pts))


# Phase: (mission points, "boat is in position" predicate, action once there)
PHASES = {
    "along-fence": ([(18, -15), (18, 15), (18, -15), (18, 15)],
                    lambda s: s.boat.n > 16 and abs(s.boat.e) < 5, None),
    "towards-fence": ([(19, 0), (0, -15), (0, 15)],
                      lambda s: s.boat.n > 9 and abs(s.boat.e) < 3, None),
    "rtl-from-corner": ([(18, 18), (18, 18)],
                        lambda s: math.hypot(s.boat.n - 18, s.boat.e - 18)
                        < 4, "rtl"),
}


def _gnss_loss(h, sim, sv):
    h.set_param_sim("SIM_GPS1_ENABLE", 0)
    return lambda: h.set_param_sim("SIM_GPS1_ENABLE", 1), 15.0


def _gnss_offset(h, sim, sv):
    h.set_param_sim("SIM_GPS1_GLTCH_X", -20.0 / M_PER_DEG)
    return lambda: h.set_param_sim("SIM_GPS1_GLTCH_X", 0.0), 30.0


def _compass_flip(h, sim, sv):
    h.set_param_sim("SIM_MAG1_ORIENT", 4)            # yaw 180
    return None, None


def _motor_dead(h, sim, sv):
    sim.boat.faults.thrust_scale = [1.0, 0.0]
    return None, None


def _link_cut(h, sim, sv):
    sim.link.cut()
    return sim.link.restore, 40.0


def _mc_dead(h, sim, sv):
    sv.stop()
    sim.router.stop()
    return None, None


def _weed(h, sim, sv):
    sim.boat.faults.extra_drag = 3000.0
    return None, None


FAULTS = {"gnss-loss": _gnss_loss, "gnss-offset-20m": _gnss_offset,
          "compass-reversed": _compass_flip, "motor-dead": _motor_dead,
          "link-cut": _link_cut, "mission-computer-dead": _mc_dead,
          "weed": _weed}


@pytest.mark.parametrize("phase", list(PHASES))
@pytest.mark.parametrize("fault", list(FAULTS))
def test_sc13_single_fault_sweep(helm, sim, services, companion, evidence,
                                 fault, phase):
    evidence("SC-13", f"Single fault: {fault} while {phase.replace('-', ' ')}",
             ["FS-013", "SC-13", "SAF-007"],
             f"Truth over {WATCH_S:g} s after the fault: never outside the "
             "fence while the motors are driving")
    pts, ready, action = PHASES[phase]
    launch(helm, sim, mission=mission(helm, pts),
           fence=Fence(square(*helm.home(), HALF)))
    assert sim.wait_until(lambda: ready(sim), 120), "never reached the phase"
    if action == "rtl":
        helm.return_home()
        sim.wait(1)
    t0 = sim.t
    link_alive = fault not in ("mission-computer-dead",)
    clear, after = FAULTS[fault](helm, sim, services)
    worst_powered = worst = 0.0
    cleared = clear is None
    while sim.t < t0 + WATCH_S:
        if not cleared and sim.t >= t0 + after:
            clear()
            cleared = True
        out = outside_by(sim)
        worst = max(worst, out)
        if out > 0 and not motors_off(sim):
            worst_powered = max(worst_powered, out)
        time.sleep(0.02 / SPEEDUP)
    modes = [RoverMode(m).name for t, a, m in companion.modes if t >= t0]
    evidence.measure(worst_outside_powered_m=worst_powered,
                     worst_outside_m=worst, modes=modes[:8],
                     events=boaty_events(companion, t0)[:6])
    assert worst_powered == 0.0, \
        f"left the fence under power by {worst_powered:.1f} m"
    if link_alive:
        helm.stop()
