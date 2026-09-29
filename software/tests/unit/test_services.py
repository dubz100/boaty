"""Decision logic of B4, B6 and B7 on a fake clock and a fake helm view.
(B5's burst sequence needs a helm that answers; it is tested in SITL.)"""
import pytest

import boaty  # noqa: F401
from boaty.mcp.policy import AUTO, HOLD, RTL
from boaty.mcp.sensors import SimSensors
from boaty.mcp.services import (Health, LinkWatchdog, NavMonitor,
                                load_config)
from boaty.mcp.view import HelmView

STEERING = 3


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


class FakeClient:
    """Records what a service asks for; the fake helm obeys at once."""

    def __init__(self, clock):
        self.clock, self.view = clock, HelmView()
        self.modes, self.events, self.speeds = [], [], []

    def set_mode(self, m):
        self.modes.append((self.clock.t, m))
        self.set_helm(self.view.armed, m)
        return True

    def change_speed(self, v):
        self.speeds.append(v)
        return True

    def event(self, text, severity=4):
        self.events.append(text)
        self.view.texts.append((self.clock.t, 191, "BOATY " + text))

    def download(self, mtype):
        return []

    def set_helm(self, armed, mode):
        v = self.view
        if (armed, mode) != (v.armed, v.mode):
            v.modes.append((self.clock.t, armed, mode))
            if mode != v.mode:
                v.mode_since = self.clock.t
        v.armed, v.mode = armed, mode


def run(svc, clock, seconds, each=None, dt=0.1):
    end = clock.t + seconds
    while clock.t < end:
        if each:
            each(clock.t)
        svc.tick(clock.t)
        clock.t += dt


@pytest.fixture
def env():
    clock = FakeClock()
    c = FakeClient(clock)
    v = c.view
    v.fix, v.hdop, v.ekf_ok, v.pos_t = 6, 0.8, True, 0.0
    v.lat, v.lon = 52.2448, 0.1597
    return clock, c, v


def keep_fresh(v, clock):
    def f(t):
        v.pos_t = t
    return f


# ---- B4 -----------------------------------------------------------------
def test_b4_rtl_after_60s_in_auto(env):
    clock, c, v = env
    b4 = LinkWatchdog(c, load_config())
    c.set_helm(True, AUTO)
    v.mc_heartbeat_t = 0.0
    run(b4, clock, 59.5)
    assert v.mode == AUTO and not c.modes
    run(b4, clock, 1.0)
    assert v.mode == RTL
    assert 60.0 <= c.modes[-1][0] <= 60.2
    n = len(c.modes)
    run(b4, clock, 30)
    assert len(c.modes) == n                      # acts once per loss


def test_b4_manual_loss_rtl_at_10s(env):
    clock, c, v = env
    b4 = LinkWatchdog(c, load_config())
    c.set_helm(True, STEERING)
    v.mc_heartbeat_t = 0.0
    clock.t = 3.0
    c.set_helm(True, HOLD)                        # ArduPilot GCS failsafe
    run(b4, clock, 6.5)
    assert v.mode == HOLD
    run(b4, clock, 1.0)
    assert v.mode == RTL and 10.0 <= c.modes[-1][0] <= 10.2


def test_b4_ignores_hold_that_was_not_manual(env):
    clock, c, v = env
    b4 = LinkWatchdog(c, load_config())
    c.set_helm(True, HOLD)                        # e.g. a B7 HOLD
    v.mc_heartbeat_t = 0.0
    run(b4, clock, 30)
    assert all(m != RTL for _, m in c.modes)


def test_b4_waits_for_first_heartbeat(env):
    clock, c, v = env
    b4 = LinkWatchdog(c, load_config())
    c.set_helm(True, AUTO)
    run(b4, clock, 120)                           # never saw Mission Control
    assert all(m != RTL for _, m in c.modes)


# ---- B6 -----------------------------------------------------------------
def test_b6_moisture_rtl_within_2s(env):
    clock, c, v = env
    s = SimSensors()
    b6 = Health(c, load_config(), s)
    c.set_helm(True, AUTO)
    run(b6, clock, 5, keep_fresh(v, clock))
    s.moisture = True
    t0 = clock.t
    run(b6, clock, 3, keep_fresh(v, clock))
    rtl = [t for t, m in c.modes if m == RTL]
    assert rtl and rtl[0] - t0 <= 2.0
    assert any("WATER" in e for e in c.events)


def test_b6_box_hot_rtl(env):
    clock, c, v = env
    s = SimSensors(box_temp_c=61.0)
    b6 = Health(c, load_config(), s)
    c.set_helm(True, AUTO)
    run(b6, clock, 1, keep_fresh(v, clock))
    assert v.mode == RTL


def test_b6_position_loss_hold_then_rtl(env):
    clock, c, v = env
    b6 = Health(c, load_config(), SimSensors())
    c.set_helm(True, AUTO)
    run(b6, clock, 2, keep_fresh(v, clock))
    v.fix = 1
    t_loss = clock.t
    run(b6, clock, 4, keep_fresh(v, clock))
    holds = [t for t, m in c.modes if m == HOLD]
    assert holds and 1.0 <= holds[0] - t_loss <= 1.2
    v.fix = 6
    t_ok = clock.t
    run(b6, clock, 11, keep_fresh(v, clock))
    rtl = [t for t, m in c.modes if m == RTL]
    assert rtl and 10.0 <= rtl[0] - t_ok <= 10.2


def test_b6_high_hdop_counts_as_loss(env):
    clock, c, v = env
    b6 = Health(c, load_config(), SimSensors())
    c.set_helm(True, RTL)
    v.hdop = 3.0
    run(b6, clock, 4, keep_fresh(v, clock))
    assert v.mode == HOLD


def test_b6_water_with_bad_position_holds(env):
    """FS-011: when position is bad, HOLD wins over the moisture RTL."""
    clock, c, v = env
    s = SimSensors(moisture=True)
    b6 = Health(c, load_config(), s)
    c.set_helm(True, AUTO)
    v.fix = 0
    run(b6, clock, 5, keep_fresh(v, clock))
    assert all(m != RTL for _, m in c.modes)
    assert v.mode == HOLD


def test_b6_critical_battery_slows_rtl(env):
    clock, c, v = env
    b6 = Health(c, load_config(), SimSensors())
    c.set_helm(True, RTL)
    v.battery_pct = 14
    run(b6, clock, 2, keep_fresh(v, clock))
    assert c.speeds == [0.6]


# ---- B7 -----------------------------------------------------------------
def b7(env):
    clock, c, v = env
    svc = NavMonitor(c, load_config())
    svc._fetching = True                          # no fence download here
    return svc


def test_b7_first_motion_reversed_compass(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, AUTO)
    v.heading, v.vn, v.ve = 180.0, 1.0, 0.0       # course 0, heading 180
    v.target_bearing, v.throttle = 0.0, 60
    run(svc, clock, 3.5)
    assert v.mode == HOLD
    assert 3.0 <= c.modes[-1][0] <= 3.2
    assert any("HEADING" in e for e in c.events)


def test_b7_first_motion_ignores_manual_astern(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, STEERING)
    v.heading, v.vn, v.ve = 0.0, -0.8, 0.0        # reversing
    run(svc, clock, 8)
    assert v.mode == STEERING


def test_b7_heading_check_only_in_first_10s(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, AUTO)
    v.heading, v.vn, v.ve, v.target_bearing = 0.0, 1.0, 0.0, 0.0
    run(svc, clock, 15)
    v.heading = 90.0                              # compass fails later
    run(svc, clock, 5)
    assert v.mode == AUTO


def test_b7_second_stuck_detector(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, AUTO)
    clock.t = 20.0                                # past the first-motion window
    v.heading, v.vn, v.ve, v.target_bearing = 0.0, 0.05, 0.0, 0.0
    v.throttle, v.wp_dist = 100, 25.0
    run(svc, clock, 9.5)
    assert v.mode == AUTO
    run(svc, clock, 1.0)
    assert v.mode == HOLD
    assert "B7 STUCK" in c.events


def test_b7_divergence(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, AUTO)
    clock.t = 20.0
    v.heading, v.vn, v.ve, v.target_bearing = 90.0, 0.0, 1.0, 0.0
    v.throttle, v.wp_dist = 40, 25.0              # moving, wrong way
    run(svc, clock, 19)
    assert v.mode == AUTO
    run(svc, clock, 2)
    assert v.mode == HOLD
    assert any("OFF COURSE" in e for e in c.events)


def test_b7_persistent_breach(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, RTL)
    v.heading, v.vn, v.ve, v.target_bearing = 0.0, 0.5, 0.0, 0.0
    v.breached, v.breach_since = True, clock.t
    run(svc, clock, 29.5)
    assert v.mode == RTL
    run(svc, clock, 1)
    assert v.mode == HOLD


def test_b7_quiet_while_b5_sheds(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, AUTO)
    clock.t = 20.0
    c.event("B5 SHED START")
    v.heading, v.vn, v.ve, v.target_bearing, v.throttle = 0, 0.0, 0, 0, 100
    run(svc, clock, 15)
    assert v.mode == AUTO


def test_b7_quiet_when_station_keeping_at_home(env):
    clock, c, v = env
    svc = b7(env)
    c.set_helm(True, RTL)
    clock.t = 20.0
    v.heading, v.vn, v.ve, v.target_bearing = 0.0, 0.02, 0.0, 180.0
    v.throttle, v.wp_dist = 80, 1.5
    run(svc, clock, 40)
    assert v.mode == RTL
