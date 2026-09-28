"""Fixtures for tests that fly the real ArduPilot firmware on the boat model.

Every test gets a fresh simulator (about 8 s at 5x speed-up) so no state leaks
between scenarios. Each test records evidence (what was measured, against
which criterion) with the `evidence` fixture; the session writes it all to
results/sitl_results.json for tools/sitl_report.py.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from boaty.helm.api import Fence, Mission, MissionItem
from boaty.helm.ardupilot import ArduPilotHelm
from boaty.sim.geo import offset, square
from boaty.sim.sitl import SimConfig, SimulatedBoat, have_sitl

SPEEDUP = int(os.environ.get("BOATY_SIM_SPEEDUP", "5"))
RESULTS = Path(__file__).resolve().parents[2] / "results"
_records: dict[str, dict] = {}

pytestmark = pytest.mark.sitl


def pytest_collection_modifyitems(config, items):
    if have_sitl():
        return
    skip = pytest.mark.skip(reason="ArduPilot SITL not built (set "
                            "ARDUPILOT_HOME or BOATY_ARDUROVER)")
    for item in items:
        if "sitl" in item.keywords:
            item.add_marker(skip)


class Evidence:
    def __init__(self, nodeid: str):
        self.rec = _records.setdefault(nodeid, dict(
            nodeid=nodeid, id=None, title=None, refs=[], criterion=None,
            measured={}, notes=[], outcome=None))

    def __call__(self, id: str, title: str, refs: list[str],
                 criterion: str) -> "Evidence":
        self.rec.update(id=id, title=title, refs=refs, criterion=criterion)
        return self

    def measure(self, **kw) -> None:
        self.rec["measured"].update({k: (round(v, 3) if isinstance(v, float)
                                         else v) for k, v in kw.items()})

    def note(self, text: str) -> None:
        self.rec["notes"].append(text)


@pytest.fixture
def evidence(request):
    return Evidence(request.node.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    rec = _records.get(item.nodeid)
    if rec is None:
        return
    if rep.when == "call":
        rec["outcome"] = rep.outcome
        if rep.failed:
            rec["failure"] = str(rep.longrepr.reprcrash.message
                                 if hasattr(rep.longrepr, "reprcrash")
                                 else rep.longrepr)[:600]
    elif rep.failed and rec["outcome"] is None:
        rec["outcome"] = "error"


def pytest_sessionfinish(session, exitstatus):
    if not _records:
        return
    RESULTS.mkdir(exist_ok=True)
    out = dict(generated=datetime.now(timezone.utc).isoformat(),
               speedup=SPEEDUP, records=list(_records.values()))
    (RESULTS / "sitl_results.json").write_text(json.dumps(out, indent=2))


# ---------------------------------------------------------------------------


@pytest.fixture
def sim():
    s = SimulatedBoat(SimConfig(speedup=SPEEDUP)).start()
    yield s
    s.stop()


@pytest.fixture
def helm(sim):
    h = ArduPilotHelm(time_scale=SPEEDUP)
    h.connect(30)
    ok = sim.wait_until(lambda: h.status().ekf_ok and h.status().gps_fix >= 3
                        and h.home() is not None, 120)
    assert ok is not None, f"helm never became ready: {h.status()}"
    yield h
    h.close()


# Standard geometry: a 120 m square fence centred on home, and a triangle
# mission 30 m out (well inside the fence).
def standard_fence(h, half_m: float = 60.0) -> Fence:
    lat, lon = h.home()
    return Fence(inclusion=square(lat, lon, half_m))


def triangle(h, size_m: float = 30.0) -> Mission:
    lat, lon = h.home()
    pts = [offset(lat, lon, size_m, 0), offset(lat, lon, size_m, size_m),
           offset(lat, lon, 0, size_m)]
    return Mission(tuple(MissionItem.waypoint(a, b) for a, b in pts))


def launch(h, sim, mission: Mission | None = None, fence: Fence | None = None,
           start: bool = True) -> Mission:
    m = mission or triangle(h)
    h.upload_fence(fence or standard_fence(h))
    h.upload_mission(m)
    assert h.verify(m)
    h.arm()
    if start:
        h.start_mission()
    return m


def events_of(h):
    got = []
    h.subscribe(got.append)
    return got


@pytest.fixture
def companion(sim):
    from boaty.sim.companion import CompanionPort
    c = CompanionPort(lambda: sim.t, port=sim.cfg.companion_port,
                      time_scale=SPEEDUP)
    yield c
    c.close()


def motors_off(sim) -> bool:
    """Truth: both pod outputs at neutral (or disabled) and thrust decayed."""
    pwm = sim.bridge.last_pwm
    if not pwm:
        return True
    neutral = all(p == 0 or abs(p - 1500) <= 10 for p in (pwm[0], pwm[3]))
    return neutral and max(abs(t) for t in sim.boat.thrust) < 0.05


def drive_for(h, sim, throttle: float, turn: float, sim_seconds: float,
              hz: float = 10.0) -> None:
    """Send MANUAL_CONTROL at `hz` in simulated time for sim_seconds."""
    end = sim.t + sim_seconds
    period = 1.0 / (hz * SPEEDUP)
    while sim.t < end:
        h.drive(throttle, turn)
        time.sleep(period)
