"""IF-14 contract suite: the acceptance test for any helm implementation
(ICD IF-14 verification), run here against ArduPilotHelm on SITL."""
import pytest

from boaty.helm.api import (Fence, Mission, MissionItem, NotAllowedWhileArmed,
                            RoverMode, SrsMode)
from boaty.helm.params import differences, read_many
from boaty.sim.geo import offset

from .conftest import (SPEEDUP, Watch, drive_for, launch, motors_off,
                       outputs_neutral, standard_fence, triangle)


def test_status_after_connect(helm, evidence):
    evidence("IF-14-01", "Status snapshot after connect", ["IF-14", "IF-02"],
             "Link up, disarmed, 3D fix, EKF healthy, home set")
    s = helm.status()
    evidence.measure(mode=s.mode.value, fix=s.gps_fix, sats=s.sats,
                     battery_v=s.battery_v, rail_v=s.rail_v)
    assert s.link_ok and not s.armed and s.mode is SrsMode.DISARMED
    assert s.gps_fix >= 3 and s.ekf_ok
    assert 12.0 < s.battery_v < 12.7
    assert s.rail_v == pytest.approx(s.battery_v, abs=0.2)


def test_parameter_baseline_is_loaded(helm, sim, evidence):
    evidence("IF-14-02", "Parameter baseline matches the controlled file",
             ["SAF-007", "SC-24"], "Every parameter in boaty-mk1.parm and "
             "sitl.parm exists on Rover 4.7.1 with the file's value")
    base = read_many(sim.cfg.param_files)
    live = helm.read_params()
    diff = differences(base, live)
    evidence.measure(parameters_in_baseline=len(base), live_parameters=len(live),
                     differences=len(diff))
    assert not diff, diff


def test_fence_and_mission_round_trip(helm, evidence):
    evidence("IF-14-03", "Fence and mission upload, read-back and verify",
             ["IF-14", "VAL-010", "SC-32"], "Read-back equals what was sent; "
             "verify() rejects a different mission")
    f, m = standard_fence(helm), triangle(helm)
    helm.upload_fence(f)
    helm.upload_mission(m)
    fb, mb = helm.read_back()
    assert len(fb.inclusion) == len(f.inclusion)
    for a, b in zip(fb.inclusion, f.inclusion):
        assert a == pytest.approx(b, abs=1e-7)
    assert helm.verify(m)
    lat, lon = helm.home()
    other = Mission(m.items[:-1] + (MissionItem.waypoint(
        *offset(lat, lon, 5, 5)),))
    assert not helm.verify(other)
    evidence.measure(fence_vertices=len(fb.inclusion), mission_items=len(mb))


def test_uploads_refused_while_armed(helm, sim, evidence):
    evidence("IF-14-04", "Uploads refused while armed", ["IF-14", "FEN-007",
                                                         "SAF-003"],
             "upload_fence/upload_mission/set_param raise NotAllowedWhileArmed")
    launch(helm, sim, start=False)
    with pytest.raises(NotAllowedWhileArmed):
        helm.upload_fence(standard_fence(helm, 40))
    with pytest.raises(NotAllowedWhileArmed):
        helm.upload_mission(triangle(helm, 10))
    with pytest.raises(NotAllowedWhileArmed):
        helm.set_param("WP_SPEED", 2.0)
    helm.stop()


def test_arms_into_hold(helm, sim, evidence):
    evidence("IF-14-05", "Arming lands in HOLD, never MANUAL",
             ["MOD-003", "INITIAL_MODE"], "After arm(): armed, SRS mode HOLD, "
             "motors off")
    launch(helm, sim, start=False)
    sim.wait(2)
    s = helm.status()
    evidence.measure(mode=s.mode.value, ardupilot_mode=s.ardupilot_mode)
    assert s.armed and s.mode is SrsMode.HOLD
    assert s.ardupilot_mode == RoverMode.HOLD
    assert motors_off(sim)
    helm.stop()


def test_mode_commands_map_to_srs_modes(helm, sim, evidence):
    evidence("IF-14-06", "hold/return_home/manual/start_mission map to the "
             "IF-02 mode table", ["IF-02", "IF-14"], "Each call reaches the "
             "right ArduPilot and SRS mode")
    launch(helm, sim, start=False)
    seen = {}
    for call, ap, srs in ((helm.start_mission, RoverMode.AUTO, SrsMode.AUTO),
                          (helm.hold, RoverMode.LOITER, SrsMode.HOLD),
                          (helm.return_home, RoverMode.RTL, SrsMode.RTL),
                          (helm.manual, RoverMode.STEERING, SrsMode.MANUAL)):
        call()
        sim.wait(1)
        s = helm.status()
        seen[call.__name__] = (s.ardupilot_mode, s.mode.value)
        assert s.ardupilot_mode == ap and s.mode is srs
    evidence.measure(**{k: f"{v[0]}/{v[1]}" for k, v in seen.items()})
    helm.stop()


def test_manual_drive_moves_the_boat(helm, sim, evidence):
    evidence("IF-14-07", "drive() moves the boat in MANUAL", ["IF-02",
                                                             "MC-008"],
             "Throttle 0.6 for 5 s moves the boat > 2 m forward")
    launch(helm, sim, start=False)
    helm.manual()
    n0 = sim.boat.n
    drive_for(helm, sim, 0.6, 0.0, 5)
    moved = sim.boat.n - n0
    evidence.measure(moved_m=moved)
    assert moved > 2.0
    helm.stop()


def test_stop_stops_motors_within_one_second(helm, sim, evidence):
    evidence("SC-09a", "STOP from AUTO: motors off and disarmed",
             ["FS-009", "IF-14"], "Helm commands the motors to neutral <= 1 s "
             "after stop(); helm disarmed; stop() is idempotent")
    launch(helm, sim)
    sim.wait(10)
    assert not motors_off(sim)
    w_cmd = Watch(sim, lambda: outputs_neutral(sim))
    w_off = Watch(sim, lambda: motors_off(sim))
    t0 = sim.t
    helm.stop()
    t_cmd, t_off = w_cmd.result(sim), w_off.result(sim)
    evidence.measure(outputs_neutral_s=(t_cmd - t0) if t_cmd else None,
                     thrust_below_0_05N_s=(t_off - t0) if t_off else None)
    evidence.note(f"Measured at {SPEEDUP}x speed-up, so wall-clock latency in "
                  f"the test harness counts {SPEEDUP} times over; spin-down "
                  "is the model's 0.1 s motor time constant.")
    assert t_cmd is not None and t_cmd - t0 <= 1.0
    assert not helm.status().armed
    helm.stop()                       # idempotent: no error when disarmed
