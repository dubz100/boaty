"""Sanity checks that the boat model behaves at Boaty's scale (KCL section 8)."""
import math

import pytest

from boaty.sim.boat import Boat, BoatParams, ocv_per_cell


def run(boat, left, right, seconds, dt=0.0025):
    for _ in range(int(seconds / dt)):
        boat.step(left, right, dt)


def test_top_speed_is_about_one_and_a_half_metres_per_second():
    b = Boat()
    run(b, 1, 1, 20)
    # 4 N against 1.62 v^2 (+ linear term) -> about 1.5 m/s (NAV-003).
    assert 1.3 < b.speed() < 1.6


def test_cruise_power_matches_power_budget():
    b = Boat()
    # Find the throttle that gives ~1.0 m/s, then check electrical power.
    lo, hi = 0.0, 1.0
    for _ in range(20):
        mid = (lo + hi) / 2
        b.reset()
        run(b, mid, mid, 15)
        lo, hi = (mid, hi) if b.speed() < 1.0 else (lo, mid)
    motor_w = b.voltage * b.current - b.p.hotel_w
    assert motor_w == pytest.approx(8.0 + 0.3 * 1.0, abs=2.5)
    # PRP-D03: 1.0 m/s at no more than 50% throttle... our u|u| law needs ~70%.
    # Recorded, not asserted: it is exactly what the thrust stand will settle.


def test_left_motor_only_turns_clockwise():
    b = Boat()
    run(b, 1, 0, 2)
    assert b.r > 0                      # positive yaw = turning to starboard


def test_full_counter_rotation_creeps_forward():
    """Props give less thrust astern (0.75 N) than ahead (2 N), so 'full
    left ahead, full right astern' also drives the boat forward. That is
    why the parameter file sets MOT_THST_ASYM = 2.67."""
    b = Boat()
    run(b, 1, -1, 3)
    assert b.u > 0.2


def test_balanced_counter_rotation_spins_on_the_spot():
    b = Boat()
    fwd = math.sqrt(b.p.thrust_ast / b.p.thrust_fwd)   # equal thrusts
    run(b, fwd, -1, 3)
    assert abs(b.r) > 0.5
    assert b.speed() < 0.1


def test_dead_motor_gives_half_thrust_and_a_turn():
    b = Boat()
    b.faults.thrust_scale = [1.0, 0.0]
    run(b, 1, 1, 5)
    assert b.thrust[1] == pytest.approx(0.0, abs=1e-6)
    assert b.r > 0


def test_reversed_motor_flips_its_thrust():
    b = Boat()
    b.faults.reverse_motor = [True, False]
    run(b, 0.5, 0.5, 2)
    assert b.thrust[0] < 0 < b.thrust[1]


def test_key_out_means_no_thrust():
    b = Boat()
    b.faults.key_in = False
    run(b, 1, 1, 3)
    assert b.speed() == pytest.approx(0.0, abs=1e-6)
    assert b.rail_voltage() == 0.0


def test_wind_from_north_pushes_south():
    b = Boat()
    b.faults.wind_speed, b.faults.wind_from_deg = 5.4, 0.0
    run(b, 0, 0, 20)
    assert b.n < -0.5 and abs(b.e) < 0.2


def test_head_wind_still_allows_headway():
    """ENV-002: 0.5 m/s into a 5.4 m/s head wind needs about 1.1 N."""
    b = Boat()
    b.faults.wind_speed, b.faults.wind_from_deg = 5.4, 0.0   # boat heads N
    run(b, 1, 1, 20)
    assert b.velocity_ned()[0] > 0.5


def test_weed_drag_slows_the_boat():
    clean, weedy = Boat(), Boat()
    weedy.faults.extra_drag = 10.0
    run(clean, 0.7, 0.7, 15)
    run(weedy, 0.7, 0.7, 15)
    assert weedy.speed() < 0.5 * clean.speed()


def test_battery_sags_under_load_and_drains():
    b = Boat()
    rest = b.voltage
    run(b, 1, 1, 5)
    assert b.voltage < rest
    before = b.soc
    b.faults.battery_drain_a = 30.0
    run(b, 0, 0, 30)
    assert b.soc < before


def test_bms_cuts_off_an_empty_pack():
    b = Boat(soc=0.02)
    b.faults.battery_drain_a = 20.0
    run(b, 1, 1, 30)
    assert b.bms_open and b.rail_voltage() == 0.0


def test_ocv_table_is_monotonic():
    vs = [ocv_per_cell(s / 100) for s in range(101)]
    assert all(b >= a for a, b in zip(vs, vs[1:]))
    assert vs[0] == pytest.approx(3.0) and vs[-1] == pytest.approx(4.18)


def test_accelerometer_reads_gravity_at_rest():
    b = Boat()
    b.step(0, 0, 0.01)
    ax, ay, az = b.accel_body()
    assert az == pytest.approx(-9.80665)
    assert abs(ax) < 1e-9 and abs(ay) < 1e-9


def test_heading_is_kept_in_range():
    b = Boat(heading_deg=350)
    run(b, 1, 0, 3)
    assert 0 <= b.psi < 2 * math.pi


def test_params_are_those_in_the_kcl():
    p = BoatParams()
    assert p.thrust_fwd * 2 == pytest.approx(4.0)      # PRP-D02
    assert p.r_pack == pytest.approx(0.22)             # KCL section 5
    assert p.capacity_ah == pytest.approx(2.5)         # PWR-D20
