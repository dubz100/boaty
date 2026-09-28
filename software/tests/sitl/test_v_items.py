"""Early verification items (ADD V-list) that need SITL: do ArduPilot's native
behaviours do what the architecture assumed? Each test answers one V-item
against the real Rover 4.7.1 firmware on the Boaty boat model.

V-items phrased as questions ("is there a native mechanism...?") record the
answer as evidence and assert the property our design relies on.
"""
import math
import time

import pytest

from boaty.helm.api import (CommandRejected, Fence, NotAllowedWhileArmed,
                            PreArmFailed, RoverMode, TransferFailed)
from boaty.helm.ardupilot import FENCE, F_INCL
from boaty.sim.geo import offset, square

from .conftest import (SPEEDUP, drive_for, launch, motors_off, standard_fence,
                       triangle)


def outside_by(sim, half_m: float) -> float:
    """Truth: how far the boat is outside a square fence centred on home."""
    return max(abs(sim.boat.n) - half_m, abs(sim.boat.e) - half_m, 0.0)


def dist_home(sim) -> float:
    return math.hypot(sim.boat.n, sim.boat.e)


# ---------------------------------------------------------------------------


def test_v02_fence_enforced_in_manual(helm, sim, companion, evidence):
    evidence("V-02", "Fence is enforced in the mode used for MANUAL",
             ["FEN-004", "V-02"], "Driving at the fence in STEERING triggers "
             "the fence action; the boat ends up no more than 10 m outside")
    half = 25.0
    launch(helm, sim, fence=Fence(square(*helm.home(), half)), start=False)
    helm.manual()
    worst, t0 = 0.0, sim.t
    end = sim.t + 60
    while sim.t < end:
        helm.drive(0.8, 0.0)                    # straight north
        worst = max(worst, outside_by(sim, half))
        time.sleep(0.1 / SPEEDUP)
        if companion.first_mode_after(t0, RoverMode.RTL):
            break
    t_rtl = companion.first_mode_after(t0, RoverMode.RTL)
    sim.wait(20)
    worst = max(worst, outside_by(sim, half))
    evidence.measure(fence_action_mode="RTL" if t_rtl else "none",
                     worst_outside_m=worst,
                     breach_at_north_m=half)
    assert t_rtl is not None, "no fence action in STEERING"
    assert worst <= 10.0
    helm.stop()


def test_v03_gcs_failsafe_continues_auto(helm, sim, companion, evidence):
    evidence("V-03", "GCS failsafe can 'continue in AUTO'",
             ["FS-003", "V-03"], "Link cut in AUTO for 20 s: mode stays AUTO "
             "and the mission keeps progressing")
    launch(helm, sim)
    sim.wait(5)
    t_cut, n0 = sim.t, sim.boat.n
    sim.link.cut()
    sim.wait(20)
    progressed = math.hypot(sim.boat.n - n0, sim.boat.e)
    modes = [m for t, a, m in companion.modes if t >= t_cut]
    sim.link.restore()
    evidence.measure(modes_during_cut=modes or ["AUTO (unchanged)"],
                     progress_m=progressed,
                     failsafe_texts=[x for x in companion.texts_after(t_cut)
                                     if "ailsafe" in x])
    assert all(m == RoverMode.AUTO for m in modes)
    assert companion.mode_at(sim.t)[1] == RoverMode.AUTO
    assert progressed > 10
    helm.stop()


def test_v04_holds_station_at_home_after_rtl(helm, sim, companion, evidence):
    evidence("V-04", "Boat loiters at home at the end of RTL",
             ["MOD-005", "V-04"], "After arriving home in RTL, with a 4 m/s "
             "wind for 60 s, the boat stays within 5 m of home")
    launch(helm, sim)
    sim.wait(20)
    helm.return_home()
    arrived = sim.wait_until(lambda: dist_home(sim) < 3 and sim.boat.speed()
                             < 0.3, 120)
    assert arrived, "never reached home"
    sim.boat.faults.wind_speed, sim.boat.faults.wind_from_deg = 4.0, 225
    worst, end = 0.0, sim.t + 60
    while sim.t < end:
        worst = max(worst, dist_home(sim))
        time.sleep(0.05 / SPEEDUP)
    mode = companion.mode_at(sim.t)
    evidence.measure(max_drift_m=worst, mode_at_end=RoverMode(mode[1]).name)
    evidence.note("ArduPilot stays in RTL and station-keeps for boats; "
                  "Mission Control must show 'arrived' as HOLD (MOD-005).")
    assert worst <= 5.0
    helm.stop()


def test_v05_crash_check_meets_fs005(helm, sim, companion, evidence):
    evidence("V-05", "Crash check can meet FS-005 (stuck detection)",
             ["FS-005", "V-05", "SC-05", "FM-16"], "Heavy weed drag in AUTO: "
             "HOLD within 5 s of the boat being stuck (< 0.1 m/s)")
    launch(helm, sim)
    sim.wait(10)
    t_weed = sim.t
    sim.boat.faults.extra_drag = 3000.0
    t_stuck = sim.wait_until(lambda: sim.boat.speed() < 0.1, 20)
    assert t_stuck, "boat never slowed below 0.1 m/s"
    sim.wait_until(lambda: companion.first_mode_after(t_weed, RoverMode.HOLD)
                   is not None, 20)
    t_hold = companion.first_mode_after(t_weed, RoverMode.HOLD)
    evidence.measure(stuck_after_weed_s=t_stuck - t_weed,
                     hold_after_stuck_s=(t_hold - t_stuck) if t_hold else None,
                     crash_text=[x for x in companion.texts_after(t_weed)
                                 if "rash" in x])
    assert t_hold is not None, "crash check never triggered"
    assert t_hold - t_stuck <= 5.0 + 1.0     # 5 s requirement + 1 Hz heartbeat
    helm.stop()


def test_v06_only_mission_control_counts_as_gcs(helm, sim, companion,
                                                evidence):
    evidence("V-06", "Helm counts only Mission Control heartbeats as GCS",
             ["FS-002", "V-06", "IF-02"], "With Mission Control silent but the "
             "mission computer (1/191) heartbeating, the GCS failsafe still "
             "fires")
    launch(helm, sim, start=False)
    helm.hold()                              # LOITER: GCS failsafe active
    companion.heartbeat_as = (1, 191)
    sim.wait(3)
    t0 = sim.t
    helm.set_heartbeat(False)
    sim.wait_until(lambda: companion.first_mode_after(t0, RoverMode.HOLD)
                   is not None, 15)
    t_hold = companion.first_mode_after(t0, RoverMode.HOLD)
    evidence.measure(failsafe_after_s=(t_hold - t0) if t_hold else None)
    helm.set_heartbeat(True)
    assert t_hold is not None, "companion heartbeats masked the failsafe"
    helm.stop()


def test_v06b_impostor_gcs_masks_failsafe(helm, sim, companion, evidence):
    evidence("V-06b", "A second system-255 heartbeat masks the GCS failsafe",
             ["FM-41", "SC-37"], "Shows why C7 must refuse to operate when a "
             "foreign system-255 source appears")
    launch(helm, sim, start=False)
    helm.hold()
    companion.heartbeat_as = (255, 190)       # impostor on the companion port
    sim.wait(3)
    t0 = sim.t
    helm.set_heartbeat(False)
    sim.wait(10)
    t_hold = companion.first_mode_after(t0, RoverMode.HOLD)
    evidence.measure(failsafe_fired=t_hold is not None)
    evidence.note("Expected: the failsafe does NOT fire, because ArduPilot "
                  "accepts any system-255 heartbeat. Mitigation is FM-41 / "
                  "SC-37 in Mission Control (slice 3).")
    helm.set_heartbeat(True)
    assert t_hold is None
    helm.stop()


def test_v11_guided_stops_without_targets(helm, sim, evidence):
    evidence("V-11", "GUIDED stops within 3 s if velocity targets stop",
             ["FS-006", "V-11"], "After the last velocity target, motors are "
             "off within 3 s")
    launch(helm, sim, start=False)
    helm._set_mode(RoverMode.GUIDED)
    mav = helm.conn.mav
    end = sim.t + 6
    while sim.t < end:                        # 1 m/s north at 10 Hz sim
        with helm._send_lock:
            mav.set_position_target_local_ned_send(
                0, 1, 1, 1, 0b0000110111000111, 0, 0, 0, 1.0, 0, 0, 0, 0, 0,
                0, 0)
        time.sleep(0.1 / SPEEDUP)
    moving = sim.boat.speed()
    t_last = sim.t
    t_off = sim.wait_until(lambda: motors_off(sim), 15)
    evidence.measure(speed_before_m_s=moving,
                     motors_off_after_s=(t_off - t_last) if t_off else None)
    assert moving > 0.3
    assert t_off is not None and t_off - t_last <= 3.0
    helm.stop()


def test_v12_skid_steer_boat_behaves(helm, sim, evidence):
    evidence("V-12", "Skid-steer boat frame behaves plausibly",
             ["SWE-004", "V-12", "NAV-004", "NAV-005"],
             "Flies the 30 m triangle: cross-track RMS <= 3 m, mean speed "
             "within 20% of 1.0 m/s")
    m = launch(helm, sim)
    lat, lon = helm.home()
    from boaty.sim.geo import ne_of
    legs = [(0.0, 0.0)] + [ne_of(lat, lon, it.lat, it.lon) for it in m.items]
    samples, speeds = [], []
    end = sim.t + 150
    while sim.t < end:
        p = (sim.boat.n, sim.boat.e)
        seq = helm.status().mission_seq or 1
        if 1 <= seq <= len(m.items):
            a, b = legs[seq - 1], legs[seq]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            xt = abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / L
            # Ignore the first/last 5 m of each leg (turns).
            along = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L
            if 5 < along < L - 5:
                samples.append(xt)
                speeds.append(sim.boat.speed())
        if seq >= len(m.items) and math.hypot(p[0] - legs[-1][0],
                                              p[1] - legs[-1][1]) < 3:
            break
        time.sleep(0.2 / SPEEDUP)
    rms = math.sqrt(sum(x * x for x in samples) / len(samples))
    mean_v = sum(speeds) / len(speeds)
    evidence.measure(cross_track_rms_m=rms, cross_track_max_m=max(samples),
                     mean_speed_m_s=mean_v, samples=len(samples))
    assert rms <= 3.0
    assert 0.8 <= mean_v <= 1.2
    helm.stop()


def test_v13_rail_voltage_gates_arming(helm, sim, evidence):
    evidence("V-13", "Second voltage input gates arming (key in/out)",
             ["MOD-003", "PRE-007", "V-13"], "Rail reads < 9 V: arming "
             "refused with a battery-2 reason; rail restored: arming works")
    helm.upload_fence(standard_fence(helm))
    helm.upload_mission(triangle(helm))
    helm.set_param("BATT2_VOLT_MULT", 4.0)     # rail reads ~1.2 V: key out
    sim.wait(3)
    rail = helm.status().rail_v
    with pytest.raises(PreArmFailed) as e:
        helm.arm()
    reasons = e.value.reasons
    helm.set_param("BATT2_VOLT_MULT", 40.4)    # key in
    sim.wait(3)
    helm.arm()
    evidence.measure(rail_v_key_out=rail, refusal=reasons[:3],
                     armed_with_key_in=helm.status().armed)
    evidence.note("SITL cannot switch its second analogue input off, so key "
                  "out is emulated by scaling BATT2_VOLT_MULT; the real "
                  "switch is tested on L2 (L2-13).")
    assert rail < 9.0
    assert any("2" in r for r in reasons)
    assert helm.status().armed
    helm.stop()


def test_v14_persistent_breach(helm, sim, companion, evidence):
    evidence("V-14", "Native mechanism to stop motors on persistent breach",
             ["FEN-006", "V-14", "SC-28", "FM-14"],
             "Offshore gale pushes the boat out: does ArduPilot itself stop "
             "the motors by 30 s / 10 m outside? (answer recorded)")
    half = 25.0
    launch(helm, sim, fence=Fence(square(*helm.home(), half)))
    sim.wait(5)
    sim.boat.faults.wind_speed, sim.boat.faults.wind_from_deg = 15.0, 180.0
    t_out = sim.wait_until(lambda: outside_by(sim, half) > 0.5, 120)
    assert t_out, "gale did not push the boat out"
    sim.wait(40)
    out = outside_by(sim, half)
    running = not motors_off(sim)
    mode = companion.mode_at(sim.t)
    evidence.measure(outside_after_40s_m=out, motors_running=running,
                     mode=RoverMode(mode[1]).name if mode else None)
    evidence.note("Answer: " + ("NO native stop - ArduPilot keeps fighting "
                                "in RTL. FEN-006 must be met by B7/B-services "
                                "(slice 2)." if running else
                                "ArduPilot stopped the motors itself."))
    sim.boat.faults.wind_speed = 0
    helm.stop()


def test_v15_rtl_speed_on_low_battery(helm, sim, companion, evidence):
    evidence("V-15", "Reduced speed during RTL on critical battery",
             ["FS-001", "V-15"], "Answer recorded: RTL speed at critical "
             "battery compared with WP_SPEED")
    launch(helm, sim)
    sim.wait(10)
    sim.boat.faults.phantom_current_a = 40.0
    t0 = sim.t
    sim.wait_until(lambda: helm.status().battery_pct <= 12, 400)
    sim.boat.faults.phantom_current_a = 0.0
    sim.wait(5)
    speeds = []
    end = sim.t + 10
    while sim.t < end:
        speeds.append(sim.boat.speed())
        time.sleep(0.2 / SPEEDUP)
    v = sum(speeds) / len(speeds)
    evidence.measure(rtl_speed_at_critical_m_s=v,
                     texts=[x for x in companion.texts_after(t0)
                            if "attery" in x][:4])
    evidence.note("Answer: " + ("no native speed reduction" if v > 0.8 else
                                "speed is reduced"))
    helm.stop()


def test_v16_compass_fault_does_not_leave_fence(helm, sim, companion,
                                                evidence):
    evidence("V-16", "GNSS-velocity yaw fallback when the compass disagrees",
             ["NAV-008", "V-16", "SC-22", "FM-04", "FS-013"],
             "Compass rotated 90 degrees mid-mission: the boat never leaves "
             "the fence (it may HOLD)")
    half = 60.0
    launch(helm, sim)
    sim.wait(8)
    t0 = sim.t
    helm.set_param_sim("SIM_MAG1_ORIENT", 2)          # yaw 90
    worst, end = 0.0, sim.t + 120
    while sim.t < end:
        worst = max(worst, outside_by(sim, half))
        time.sleep(0.1 / SPEEDUP)
    texts = [x for x in companion.texts_after(t0)
             if any(k in x for k in ("yaw", "EKF", "ailsafe", "ompass"))]
    mode = companion.mode_at(sim.t)
    evidence.measure(worst_outside_m=worst, texts=texts[:6],
                     mode_at_end=RoverMode(mode[1]).name if mode else None)
    assert worst == 0.0
    helm.stop()


def test_v17_fence_change_while_armed(helm, sim, evidence):
    evidence("V-17", "Does the helm refuse fence changes while armed?",
             ["FEN-007", "V-17"], "Answer recorded; our helm API refuses "
             "regardless")
    launch(helm, sim, start=False)
    with pytest.raises(NotAllowedWhileArmed):
        helm.upload_fence(standard_fence(helm, 40))
    # Bypass our guard to see what ArduPilot itself does.
    lat, lon = helm.home()
    pts = square(lat, lon, 40)
    items = [helm._item_int(i, 0, F_INCL, [4, 0, 0, 0], a, b, 0, FENCE)
             for i, (a, b) in enumerate(pts)]
    try:
        helm._upload(items, FENCE)
        native = "accepted"
    except TransferFailed as e:
        native = f"refused ({e})"
    evidence.measure(ardupilot_native=native)
    evidence.note("FEN-007 is enforced by C7 (NotAllowedWhileArmed) whatever "
                  "ArduPilot does.")
    helm.stop()
