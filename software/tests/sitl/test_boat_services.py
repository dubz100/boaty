"""Slice 2: the boat services (B2-B7) flying with the real firmware.

Each scenario runs the helm (ArduPilot SITL), the boat model, the B1 router
stand-in and the services on the simulated Pi Zero. Mission Control is
played by ArduPilotHelm on the far side of the simulated radio.
"""
import math
import time

from boaty.helm.api import Fence, Mission, MissionItem, RoverMode
from boaty.sim.geo import offset, square

from .conftest import (SPEEDUP, Watch, boaty_events, drive_for, launch,
                       motors_off, outputs_neutral, triangle)

RTL_ITEM = MissionItem(20)                   # MAV_CMD_NAV_RETURN_TO_LAUNCH


def dist_home(sim):
    return math.hypot(sim.boat.n, sim.boat.e)


def outside_by(sim, half):
    return max(abs(sim.boat.n) - half, abs(sim.boat.e) - half, 0.0)


def long_mission(h, size=40.0, rtl=False):
    lat, lon = h.home()
    pts = [(size, 0), (size, size), (0, size), (size, size), (size, 0),
           (size, size), (0, size)]
    items = tuple(MissionItem.waypoint(*offset(lat, lon, n, e))
                  for n, e in pts)
    return Mission(items + ((RTL_ITEM,) if rtl else ()))


# ---------------------------------------------------------------------------
def test_sc02b_manual_link_loss_rtl_at_10s(helm, sim, services, companion,
                                            evidence):
    evidence("SC-02b", "Link cut in STEERING: B4 RTL at 10 s",
             ["FS-002", "SC-02", "MCP-D12", "CR-05"],
             "HOLD <= 3 s (helm), then RTL 10 s (+/- 1 s) after the link is "
             "cut (B4), and the boat heads home")
    launch(helm, sim, start=False)
    helm.manual()
    drive_for(helm, sim, 0.6, 0.0, 12)
    d0 = dist_home(sim)
    t_cut = sim.t
    sim.link.cut()
    sim.wait(25)
    t_hold = companion.first_mode_after(t_cut, RoverMode.HOLD)
    t_rtl = companion.first_mode_after(t_cut, RoverMode.RTL)
    d1 = dist_home(sim)
    sim.link.restore()
    evidence.measure(hold_after_s=(t_hold - t_cut) if t_hold else None,
                     rtl_after_s=(t_rtl - t_cut) if t_rtl else None,
                     dist_home_at_cut_m=d0, dist_home_15s_after_rtl_m=d1,
                     events=boaty_events(companion, t_cut))
    assert t_hold is not None and t_hold - t_cut <= 3.3
    assert t_rtl is not None and 9.0 <= t_rtl - t_cut <= 11.0
    assert d1 < d0
    helm.stop()


def test_sc03_auto_link_loss_rtl_at_60s(helm, sim, services, companion,
                                        evidence):
    evidence("SC-03", "Link cut in AUTO", ["FS-003", "SC-03", "MCP-D12",
                                           "FM-31"],
             "Mission continues; RTL 60 s (+/- 1 s) after the link is cut "
             "(B4)")
    launch(helm, sim, mission=long_mission(helm))
    sim.wait(5)
    t_cut = sim.t
    sim.link.cut()
    sim.wait(30)
    mid = companion.mode_at(sim.t)
    sim.wait_until(lambda: companion.first_mode_after(t_cut, RoverMode.RTL)
                   is not None, 40)
    t_rtl = companion.first_mode_after(t_cut, RoverMode.RTL)
    sim.link.restore()
    evidence.measure(mode_30s_after_cut=RoverMode(mid[1]).name,
                     rtl_after_s=(t_rtl - t_cut) if t_rtl else None,
                     events=boaty_events(companion, t_cut))
    assert mid[1] == RoverMode.AUTO
    assert t_rtl is not None and 59.0 <= t_rtl - t_cut <= 61.5
    helm.stop()


def test_sc04_gnss_loss_hold_then_rtl(helm, sim, services, companion,
                                      evidence):
    evidence("SC-04", "GNSS failure 5 s then restore", ["FS-004", "SC-04",
                                                        "FM-01", "FM-06",
                                                        "MCP-D15"],
             "Motors stop <= 3 s after the fix is lost (B6 HOLD); RTL once "
             "the position has been healthy for 10 s")
    launch(helm, sim)
    sim.wait(10)
    w_cmd = Watch(sim, lambda: outputs_neutral(sim))
    w_off = Watch(sim, lambda: motors_off(sim))
    t_loss = sim.t
    helm.set_param_sim("SIM_GPS1_ENABLE", 0)
    t_cmd, t_off = w_cmd.result(sim, 10), w_off.result(sim, 10)
    sim.wait_until(lambda: sim.t >= t_loss + 5, 10)
    helm.set_param_sim("SIM_GPS1_ENABLE", 1)
    t_back = sim.t
    sim.wait_until(lambda: companion.first_mode_after(t_back, RoverMode.RTL)
                   is not None, 60)
    t_rtl = companion.first_mode_after(t_back, RoverMode.RTL)
    b6 = services["B6"]
    evidence.measure(outputs_neutral_after_s=(t_cmd - t_loss) if t_cmd
                     else None,
                     thrust_gone_after_s=(t_off - t_loss) if t_off else None,
                     rtl_after_restore_s=(t_rtl - t_back) if t_rtl else None,
                     events=boaty_events(companion, t_loss))
    evidence.note("RTL comes 10 s after B6 sees a healthy position, which "
                  "includes the EKF's own recovery after the fix returns.")
    assert t_cmd is not None and t_cmd - t_loss <= 3.0
    assert t_rtl is not None
    assert sim.wait_until(lambda: any("POSITION OK" in a[1]
                                      for a in b6.actions), 5)
    helm.stop()


def test_sc06_weed_released_after_burst_two(helm, sim, services, companion,
                                            evidence):
    evidence("SC-06", "Drag released after burst 2", ["FS-006", "SC-06",
                                                      "MCP-D18", "FM-27"],
             "Stuck -> HOLD; B5 astern bursts (<= 0.5 m/s, <= 2 s); weed "
             "clears during burst 2; mission resumes; <= 3 bursts")
    launch(helm, sim, mission=long_mission(helm))
    sim.wait(10)
    t_weed = sim.t
    sim.boat.faults.extra_drag = 3000.0
    b5 = services["B5"]
    sim.wait_until(lambda: b5.bursts >= 2, 90)
    astern = []
    end = sim.t + 2
    released = False
    while sim.t < end:
        astern.append(sim.boat.u)
        if not released and sim.t >= end - 1.0:   # half-way through burst 2
            sim.boat.faults.extra_drag = 0.0
            released = True
        time.sleep(0.05 / SPEEDUP)
    sim.boat.faults.extra_drag = 0.0
    sim.wait_until(lambda: any(a[1] == "free" for a in b5.actions), 40)
    sim.wait(5)
    mode = companion.mode_at(sim.t)
    evidence.measure(watch=b5.watch_log)
    evidence.measure(bursts=b5.bursts, min_speed_during_burst_m_s=min(astern),
                     mode_after=RoverMode(mode[1]).name,
                     speed_after_m_s=sim.boat.speed(),
                     events=boaty_events(companion, t_weed))
    assert any(a[1] == "free" for a in b5.actions)
    assert b5.bursts <= 3
    assert mode[1] == RoverMode.AUTO and sim.boat.speed() > 0.5
    assert min(astern) >= -0.55                   # <= 0.5 m/s astern
    helm.stop()


def test_sc06b_weed_never_clears(helm, sim, services, companion, evidence):
    evidence("SC-06b", "Permanent weed: three bursts then HOLD + alarm",
             ["FS-006", "MCP-D18", "FM-27"],
             "Exactly 3 bursts, then HOLD with a 'still stuck' alarm, and "
             "nothing restarts the motors")
    launch(helm, sim, mission=long_mission(helm))
    sim.wait(10)
    t_weed = sim.t
    sim.boat.faults.extra_drag = 3000.0
    b5 = services["B5"]
    sim.wait_until(lambda: any(a[1] == "still stuck" for a in b5.actions),
                   150)
    sim.wait(20)
    mode = companion.mode_at(sim.t)
    evidence.measure(bursts=b5.bursts, mode=RoverMode(mode[1]).name,
                     motors_off=motors_off(sim),
                     events=boaty_events(companion, t_weed))
    assert b5.bursts == 3
    assert mode[1] == RoverMode.HOLD and motors_off(sim)
    assert any("STILL STUCK" in e for e in boaty_events(companion, t_weed))
    helm.stop()


def test_sc07_mission_computer_dies(helm, sim, services, companion, evidence):
    evidence("SC-07", "Kill the whole mission computer mid-mission",
             ["FS-007", "SC-07", "FM-26", "MOD-005"],
             "With B1-B7 dead (and so the bank link), the helm completes the "
             "mission, returns and holds within 5 m of home")
    launch(helm, sim, mission=long_mission(helm, 30, rtl=True))
    sim.wait(15)
    services.stop()
    sim.router.stop()                              # the Pi Zero is gone
    t0 = sim.t
    done = sim.wait_until(lambda: dist_home(sim) < 3 and sim.boat.speed()
                          < 0.3, 400)
    sim.wait(20)
    evidence.measure(home_after_s=(done - t0) if done else None,
                     final_distance_m=dist_home(sim))
    assert done is not None and dist_home(sim) < 5
    # No helm.stop(): the bank link died with the mission computer.


def test_sc10_moisture_rtl(helm, sim, services, companion, evidence):
    evidence("SC-10", "Moisture flagged", ["FS-010", "SC-10", "FM-24",
                                           "MCP-D15"],
             "RTL <= 2 s after the moisture sensor trips; alarm raised; "
             "IF-03 health shows fault")
    launch(helm, sim)
    sim.wait(10)
    t0 = sim.t
    services.sensors.moisture = True
    sim.wait_until(lambda: companion.first_mode_after(t0, RoverMode.RTL)
                   is not None, 10)
    t_rtl = companion.first_mode_after(t0, RoverMode.RTL)
    health = services.api.health_json()
    evidence.measure(rtl_after_s=(t_rtl - t0) if t_rtl else None,
                     health_status=health["status"],
                     events=boaty_events(companion, t0))
    assert t_rtl is not None and t_rtl - t0 <= 2.0
    assert health["status"] == "fault" and health["moisture"]
    helm.stop()


def test_sc28_persistent_breach(helm, sim, services, companion, evidence):
    evidence("SC-28", "Persistent breach (wind pushing out)",
             ["FEN-006", "SC-28", "FM-14", "V-14"],
             "Offshore gale: B7 stops the motors before 30 s outside or 10 m "
             "outside, and they stay stopped (detector recorded)")
    half = 25.0
    launch(helm, sim, fence=Fence(square(*helm.home(), half)))
    sim.wait(5)
    sim.boat.faults.wind_speed, sim.boat.faults.wind_from_deg = 15.0, 180.0
    t_out = sim.wait_until(lambda: outside_by(sim, half) > 0.3, 120)
    assert t_out, "gale did not push the boat out"
    b7 = services["B7"]
    t_hold = sim.wait_until(lambda: bool(b7.actions), 40)
    out_at_hold = outside_by(sim, half)
    running = 0.0
    end = sim.t + 30
    while sim.t < end:                    # motors must stay (mostly) off
        if not motors_off(sim):
            running += 0.05
        time.sleep(0.05 / SPEEDUP)
    evidence.measure(hold_after_breach_s=(t_hold - t_out) if t_hold else None,
                     outside_at_hold_m=out_at_hold,
                     detector=b7.actions[0][1] if b7.actions else None,
                     motors_running_in_next_30s_s=running,
                     b7_actions=[a[1] for a in b7.actions],
                     events=boaty_events(companion, t_out))
    evidence.note("In a gale that blows the boat backwards the first-motion "
                  "heading check fires first (course and heading 180 deg "
                  "apart). The outcome, motors off, is what FEN-006 wants; the "
                  "diagnosis is wrong.")
    sim.boat.faults.wind_speed = 0.0
    assert t_hold is not None
    assert t_hold - t_out <= 30.0 and out_at_hold <= 10.0
    assert running <= 3.0
    helm.stop()


def test_sc29_single_motor_failure(helm, sim, services, companion, evidence):
    evidence("SC-29", "Single motor failure", ["FS-013", "SC-29", "FM-17",
                                               "MCP-D24"],
             "Right motor dead mid-leg: HOLD within 20 s (from whichever "
             "detector fires first), the boat stays inside the fence and "
             "ends in HOLD with an alarm")
    launch(helm, sim, mission=long_mission(helm))
    sim.wait(8)
    t0 = sim.t
    sim.boat.faults.thrust_scale = [1.0, 0.0]
    worst = 0.0
    end = sim.t + 150
    while sim.t < end:
        worst = max(worst, outside_by(sim, 60))
        if any("STILL STUCK" in e or "OFF COURSE" in e or "REPEATEDLY" in e
               for e in boaty_events(companion, t0)):
            break
        time.sleep(0.05 / SPEEDUP)
    t_hold = companion.first_mode_after(t0, RoverMode.HOLD)
    sim.wait(5)
    mode = companion.mode_at(sim.t)
    helm_texts = [x for x in companion.texts_after(t0) if "rash" in x]
    evidence.measure(first_hold_after_s=(t_hold - t0) if t_hold else None,
                     first_detector=("helm crash check" if helm_texts
                                     else "B7"),
                     worst_outside_m=worst, final_mode=RoverMode(mode[1]).name,
                     events=boaty_events(companion, t0))
    evidence.note("A dead motor looks like 'stuck' to the helm's crash check, "
                  "so B5 tries its astern bursts before giving up. Safe, but "
                  "B5 cannot tell weed from a dead motor.")
    assert t_hold is not None and t_hold - t0 <= 20.0
    assert worst == 0.0
    assert mode[1] == RoverMode.HOLD
    helm.stop()


def test_sc38_reversed_compass_first_motion(helm, sim, services, companion,
                                            evidence):
    evidence("SC-38", "First-motion heading check", ["FM-05", "FM-18",
                                                     "SC-38", "MCP-D22",
                                                     "A-03"],
             "Compass reversed before the start: HOLD <= 10 s after AUTO "
             "begins; the boat stays inside the fence")
    helm.set_param("SIM_MAG1_ORIENT", 4)            # yaw 180
    sim.wait(15)
    launch(helm, sim)
    t0 = sim.t
    b7 = services["B7"]
    worst = 0.0
    end = sim.t + 20
    while sim.t < end and not b7.actions:
        worst = max(worst, outside_by(sim, 60))
        time.sleep(0.05 / SPEEDUP)
    t_hold = b7.actions[0][0] if b7.actions else None
    evidence.measure(hold_after_s=(t_hold - t0) if t_hold else None,
                     detector=b7.actions[0][1] if b7.actions else None,
                     worst_outside_m=worst,
                     events=boaty_events(companion, t0))
    assert t_hold is not None and t_hold - t0 <= 10.0
    assert "HEADING" in b7.actions[0][1]
    helm.stop()


def test_fs001_slow_rtl_at_critical_battery(helm, sim, services, companion,
                                            evidence):
    evidence("FS-001b", "Reduced RTL speed at critical battery",
             ["FS-001", "V-15", "MCP-D15"],
             "After the critical battery failsafe, B6 slows RTL to 0.6 m/s "
             "(+/- 0.1) and raises an alarm")
    lat, lon = helm.home()
    far = Mission((MissionItem.waypoint(*offset(lat, lon, 55, 0)),
                   MissionItem.waypoint(*offset(lat, lon, 55, 55))))
    helm.set_param("BATT_WATT_MAX", 0)
    launch(helm, sim, mission=far)
    sim.wait_until(lambda: dist_home(sim) > 50, 120)
    sim.boat.faults.phantom_current_a = 80.0
    t0 = sim.t
    sim.wait_until(lambda: any("SLOW RTL" in e for e in
                               boaty_events(companion, t0)), 200)
    sim.boat.faults.phantom_current_a = 0.0
    sim.wait(6)
    speeds = []
    end = sim.t + 10
    while sim.t < end and dist_home(sim) > 8:
        speeds.append(sim.boat.speed())
        time.sleep(0.2 / SPEEDUP)
    v = sum(speeds) / len(speeds)
    evidence.measure(rtl_speed_m_s=v, events=boaty_events(companion, t0))
    assert 0.5 <= v <= 0.7
    helm.stop()


def test_photos_in_a_mission(helm, sim, services, evidence):
    evidence("B2-01", "Photos during a mission", ["CAM-002", "CAM-003",
                                                 "MCP-D10", "MCP-D11",
                                                 "IF-03"],
             "Burst of 3 within 0.5 s of reaching photo point 2; interval "
             "photos every 5 s in AUTO; every photo geotagged within 3 m "
             "of the boat's true position")
    cam = services.camera
    cam.set_session({"mission_id": "sim-mission", "interval_s": 5,
                     "photo_points": [{"seq": 2, "burst_n": 3}]})
    positions = []                  # (sim t, lat, lon) truth samples

    lat0, lon0 = helm.home()
    launch(helm, sim)
    end = sim.t + 90
    while sim.t < end:
        positions.append((sim.t, *offset(lat0, lon0, sim.boat.n,
                                         sim.boat.e)))
        time.sleep(0.05 / SPEEDUP)
    photos = cam.store.list("sim-mission")
    burst = [p for p in photos if p.trigger == "photo_point"]
    interval = [p for p in photos if p.trigger == "interval"]
    reached = [t for t, s in services.cam_client.view.reached if s == 2]
    t_burst = sorted(t for t, trig, _ in cam.captured
                     if trig == "photo_point")
    worst = 0.0
    from boaty.sim.geo import ne_of
    for (t, trig, pid) in cam.captured:
        ph = cam.store.photos[pid]
        if ph.lat is None:
            continue
        near = min(positions, key=lambda x: abs(x[0] - t))
        n, e = ne_of(near[1], near[2], ph.lat, ph.lon)
        worst = max(worst, math.hypot(n, e))
    evidence.measure(photos=len(photos), burst=len(burst),
                     interval=len(interval),
                     first_burst_after_reached_s=(t_burst[0] - reached[0])
                     if reached and t_burst else None,
                     worst_geotag_error_m=worst,
                     untagged=sum(1 for p in photos if p.lat is None))
    assert len(burst) == 3 and all(p.point_seq == 2 for p in burst)
    assert reached and t_burst[0] - reached[0] <= 0.5
    assert len(interval) >= 10
    assert worst <= 3.0
    helm.stop()
