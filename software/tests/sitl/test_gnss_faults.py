"""GNSS faults near the fence and combined with other failsafes (SDR WP3).

SC-20  position jump (glitch) near the fence          FM-02
SC-11  GNSS loss during a battery RTL                 FS-011
"""
import math
import time

import pytest

from boaty.helm.api import Fence, Mission, MissionItem, RoverMode
from boaty.sim.geo import ne_of, offset, square

from .conftest import SPEEDUP, boaty_events, launch, motors_off

HALF = 25.0                  # square fence half-width, m
M_PER_DEG = 111_320.0        # SIM_GPS1_GLTCH_X/Y are offsets in degrees


def outside_by(sim, half: float = HALF) -> float:
    """Truth: metres outside the square fence centred on home."""
    return max(abs(sim.boat.n) - half, abs(sim.boat.e) - half, 0.0)


def powered(sim) -> bool:
    return not motors_off(sim)


def along_the_north_fence(h, n: float = 18.0) -> Mission:
    """Back and forth 7 m inside the north fence line."""
    lat, lon = h.home()
    pts = [(n, -15), (n, 15), (n, -15), (n, 15)]
    return Mission(tuple(MissionItem.waypoint(*offset(lat, lon, a, b))
                         for a, b in pts))


@pytest.mark.parametrize("jump_m,dur_s", [(20.0, 2), (50.0, 2), (-20.0, 2),
                                         (-50.0, 2), (-20.0, 10), (-20.0, 30),
                                         (20.0, 30)],
                         ids=["20m-out", "50m-out", "20m-in", "50m-in",
                              "20m-in-10s", "20m-in-30s", "20m-out-30s"])
def test_sc20_gnss_jump_near_fence(helm, sim, services, companion, evidence,
                                   jump_m, dur_s):
    where = "outwards" if jump_m > 0 else "inwards"
    evidence("SC-20", f"GNSS jump of {abs(jump_m):g} m {where} for {dur_s} s, "
             "7 m from the fence", ["FM-02", "FS-013", "SC-20"],
             "No uncommanded exit: the boat is never outside the fence "
             "under power (truth), and afterwards it is in AUTO, RTL or "
             "HOLD and inside the fence")
    launch(helm, sim, mission=along_the_north_fence(helm),
           fence=Fence(square(*helm.home(), HALF)))
    # Wait until the boat is running along the fence, mid-leg.
    assert sim.wait_until(lambda: sim.boat.n > 16 and abs(sim.boat.e) < 5,
                          120), "never reached the fence leg"
    t0 = sim.t
    helm.set_param_sim("SIM_GPS1_GLTCH_X", jump_m / M_PER_DEG)
    home = helm.home()
    glitch_seen, worst_powered, worst, ekf_err = 0.0, 0.0, 0.0, 0.0
    t_clear = sim.t + dur_s
    end = t_clear + 45
    cleared = False
    while sim.t < end:
        if not cleared and sim.t >= t_clear:
            helm.set_param_sim("SIM_GPS1_GLTCH_X", 0.0)
            cleared = True
        raw = helm._s.get("gps_raw")
        if raw and not cleared:
            n, e = ne_of(*home, *raw)
            glitch_seen = max(glitch_seen,
                              math.hypot(n - sim.boat.n, e - sim.boat.e))
        st = helm.status()
        if st.lat is not None:
            n, e = ne_of(*home, st.lat, st.lon)
            ekf_err = max(ekf_err, math.hypot(n - sim.boat.n,
                                              e - sim.boat.e))
        out = outside_by(sim)
        worst = max(worst, out)
        if powered(sim):
            worst_powered = max(worst_powered, out)
        time.sleep(0.02 / SPEEDUP)
    modes = sorted({RoverMode(m).name for t, a, m in companion.modes
                    if t >= t0})
    final = companion.mode_at(sim.t)
    evidence.measure(jump_m=jump_m, raw_gps_jump_seen_m=glitch_seen,
                     ekf_worst_error_m=ekf_err, duration_s=dur_s,
                     worst_outside_powered_m=worst_powered,
                     worst_outside_m=worst, modes_after=modes,
                     mode_at_end=RoverMode(final[1]).name if final else None,
                     texts=[x for x in companion.texts_after(t0)][:6],
                     events=boaty_events(companion, t0),
                     b6_actions=[a[1] for a in services["B6"].actions])
    assert glitch_seen > 0.8 * abs(jump_m), "the glitch was not injected"
    assert worst_powered == 0.0, f"left the fence under power by " \
                                 f"{worst_powered:.1f} m"
    assert outside_by(sim) == 0.0
    helm.stop()


def far_mission(h) -> Mission:
    lat, lon = h.home()
    pts = [(20, 0), (20, 20), (0, 20), (20, 20), (20, 0)] * 3
    return Mission(tuple(MissionItem.waypoint(*offset(lat, lon, a, b))
                         for a, b in pts))


@pytest.mark.parametrize("order", ["rtl-then-gnss", "gnss-then-battery"])
def test_sc11_gnss_loss_during_battery_rtl(helm, sim, services, companion,
                                           evidence, order):
    evidence("SC-11", "GNSS loss and battery failsafe together ("
             + order.replace("-", " ") + ")", ["FS-011", "FS-001",
                                                "FS-004", "SC-11"],
             "Most conservative wins: motors stopped (no thrust) from <= 3 s "
             "after the fix is lost until it is back, whatever the battery "
             "failsafe asks for; afterwards the boat returns home")
    launch(helm, sim, mission=far_mission(helm),
           fence=Fence(square(*helm.home(), 50.0)))
    sim.wait(8)
    t0 = sim.t
    sim.boat.faults.phantom_current_a = 50.0      # fast-forward capacity use
    if order == "rtl-then-gnss":
        assert sim.wait_until(lambda: helm.status().ardupilot_mode
                              == RoverMode.RTL, 400), "no battery RTL"
        sim.boat.faults.phantom_current_a = 0.0
        sim.wait(4)
    else:
        assert sim.wait_until(lambda: helm.status().battery_pct <= 39, 400)
    t_loss = sim.t
    helm.set_param_sim("SIM_GPS1_ENABLE", 0)
    # FS-004: motors off within 3 s of the loss; FS-011: they stay off
    # until the fix is back, whatever the battery failsafe wants.
    powered_during, t_off, last_on = 0.0, None, t_loss
    loss_s = 25.0
    while sim.t < t_loss + loss_s:
        if helm.status().battery_pct <= 30:
            sim.boat.faults.phantom_current_a = 0.0
        if not motors_off(sim):
            last_on = sim.t
            if sim.t > t_loss + 3.0:
                powered_during += 0.02
        time.sleep(0.02 / SPEEDUP)
    t_off = last_on if last_on <= t_loss + 3.0 else None
    sim.boat.faults.phantom_current_a = 0.0
    pct_at_restore = helm.status().battery_pct
    helm.set_param_sim("SIM_GPS1_ENABLE", 1)
    home = sim.wait_until(lambda: math.hypot(sim.boat.n, sim.boat.e) < 4,
                          240)
    modes = [(round(t - t_loss, 1), RoverMode(m).name)
             for t, a, m in companion.modes if t >= t0]
    evidence.measure(motors_off_after_loss_s=(t_off - t_loss) if t_off
                     else None,
                     powered_from_3s_until_fix_back_s=powered_during,
                     battery_pct_at_restore=pct_at_restore,
                     home_after_restore=bool(home), modes=modes[:10],
                     events=boaty_events(companion, t0),
                     texts=[x for x in companion.texts_after(t_loss)
                            if "ailsafe" in x or "attery" in x][:5])
    assert t_off is not None and t_off - t_loss <= 3.0
    assert powered_during <= 0.5, "motors ran while the position was lost"
    assert pct_at_restore < 35, "the battery failsafe was never tested"
    assert home, "did not get home after the fix came back"
    helm.stop()
