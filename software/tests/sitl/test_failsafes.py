"""Failsafe scenarios (SSS-SIM catalogue) whose helm part runs natively in
ArduPilot. The mission-computer parts (B4 link watchdog RTL, B6 RTL after
healthy position) come in slice 2 and are noted in the evidence.

SC-03 and SC-05 are covered by test_v_items (V-03 and V-05).
"""
import math
import time

from boaty.helm.api import Mission, MissionItem, RoverMode
from boaty.sim.geo import box, offset

from .conftest import SPEEDUP, drive_for, launch, motors_off


def test_sc01_battery_drain(helm, sim, companion, evidence):
    evidence("SC-01", "Battery drain to 35% then 15%", ["FS-001", "SC-01"],
             "RTL at 35% (+/- 2%); critical alarm at 15%; reaches home "
             "within 5 m")
    lat, lon = helm.home()
    pts = [offset(lat, lon, n, e) for n, e in
           ((40, 0), (40, 40), (0, 40), (40, 40), (40, 0))]
    launch(helm, sim, mission=Mission(tuple(MissionItem.waypoint(a, b)
                                            for a, b in pts)))
    sim.wait(5)
    t0 = sim.t
    sim.boat.faults.phantom_current_a = 50.0      # fast-forward capacity use
    pct_at_rtl = None
    end = sim.t + 400
    while sim.t < end:
        s = helm.status()
        if pct_at_rtl is None and s.ardupilot_mode == RoverMode.RTL:
            pct_at_rtl = s.battery_pct
        if s.battery_pct <= 12:
            sim.boat.faults.phantom_current_a = 0.0
        if pct_at_rtl is not None and math.hypot(sim.boat.n, sim.boat.e) < 3 \
                and s.battery_pct <= 14:
            break
        time.sleep(0.1 / SPEEDUP)
    sim.boat.faults.phantom_current_a = 0.0
    home_d = math.hypot(sim.boat.n, sim.boat.e)
    texts = [x for x in companion.texts_after(t0) if "attery" in x
             or "ailsafe" in x]
    evidence.measure(battery_pct_at_rtl=pct_at_rtl, distance_home_m=home_d,
                     texts=texts[:6])
    evidence.note("Reduced speed at 15% is not native (see V-15); it "
                  "belongs to the mission computer in slice 2.")
    assert pct_at_rtl is not None and 33 <= pct_at_rtl <= 37
    assert any("ritical" in x for x in texts)
    assert home_d < 5.0
    helm.stop()


def test_sc02_link_cut_in_manual(helm, sim, companion, evidence):
    evidence("SC-02", "Link cut in STEERING", ["FS-002", "SC-02"],
             "HOLD <= 2 s after the link is cut (the RTL at 10 s is B4, "
             "slice 2)")
    launch(helm, sim, start=False)
    helm.manual()
    drive_for(helm, sim, 0.5, 0.0, 5)
    t_cut = sim.t
    sim.link.cut()
    sim.wait_until(lambda: companion.first_mode_after(t_cut, RoverMode.HOLD)
                   is not None, 15)
    t_hold = companion.first_mode_after(t_cut, RoverMode.HOLD)
    t_off = sim.wait_until(lambda: motors_off(sim), 1)
    sim.link.restore()
    evidence.measure(hold_after_cut_s=(t_hold - t_cut) if t_hold else None,
                     native_minimum_s="FS_GCS_TIMEOUT 2 + FS_TIMEOUT 1")
    assert t_hold is not None
    assert t_hold - t_cut <= 2.0, (
        f"HOLD after {t_hold - t_cut:.1f} s: Rover's GCS failsafe cannot be "
        "faster than FS_GCS_TIMEOUT (min 2 s) + FS_TIMEOUT (min 1 s)")
    helm.stop()


def test_sc04_gnss_failure(helm, sim, companion, evidence):
    evidence("SC-04", "GNSS failure 5 s then restore", ["FS-004", "SC-04",
                                                        "FM-01", "FM-06"],
             "Motors stop <= 3 s after the fix is lost (the RTL after 10 s "
             "healthy is B6, slice 2)")
    launch(helm, sim)
    sim.wait(10)
    t_loss = sim.t
    helm.set_param_sim("SIM_GPS1_ENABLE", 0)
    t_off = sim.wait_until(lambda: motors_off(sim), 10)
    sim.wait_until(lambda: sim.t >= t_loss + 5, 10)
    helm.set_param_sim("SIM_GPS1_ENABLE", 1)
    sim.wait(20)
    modes = [(round(t - t_loss, 1), RoverMode(m).name)
             for t, a, m in companion.modes if t >= t_loss]
    texts = [x for x in companion.texts_after(t_loss)][:8]
    evidence.measure(motors_off_after_s=(t_off - t_loss) if t_off else None,
                     modes=modes, texts=texts)
    assert t_off is not None and t_off - t_loss <= 3.0, (
        "motors still running 3 s after GNSS loss")
    helm.stop()
