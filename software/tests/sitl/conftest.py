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
from boaty.sim.sitl import (ARDUPILOT_COMMIT, SimConfig, SimulatedBoat,
                            ardupilot_commit, have_sitl)

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
        if hasattr(rep, "wasxfail"):
            rec["outcome"] = "xfail" if rep.skipped else "xpass"
            rec["known_finding"] = rep.wasxfail.replace("reason: ", "")
        if rep.failed or hasattr(rep, "wasxfail"):
            rec["failure"] = str(rep.longrepr.reprcrash.message
                                 if hasattr(rep.longrepr, "reprcrash")
                                 else rep.longrepr)[:600]
    elif rep.failed and rec["outcome"] is None:
        rec["outcome"] = "error"


def pytest_sessionfinish(session, exitstatus):
    if not _records:
        return
    RESULTS.mkdir(exist_ok=True)
    commit = ardupilot_commit()
    out = dict(generated=datetime.now(timezone.utc).isoformat(),
               speedup=SPEEDUP, ardupilot_commit=commit,
               ardupilot_commit_is_baseline=commit == ARDUPILOT_COMMIT,
               records=list(_records.values()))
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


def outputs_neutral(sim) -> bool:
    """Truth: the helm commands both pods to neutral (or disables them)."""
    pwm = sim.bridge.last_pwm
    return not pwm or all(p == 0 or abs(p - 1500) <= 10
                          for p in (pwm[0], pwm[3]))


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


class Watch:
    """Poll a truth predicate in the background and record the first
    simulated time it holds. Use when the call under test blocks (e.g.
    helm.stop() waits for confirmation) but the event happens during it."""

    def __init__(self, sim, pred, poll: float = 0.002):
        import threading
        self.t = None
        self._stop = threading.Event()

        def run():
            while not self._stop.is_set() and self.t is None:
                if pred():
                    self.t = sim.t
                time.sleep(poll)
        self._th = threading.Thread(target=run, daemon=True)
        self._th.start()

    def result(self, sim, timeout_sim: float = 5.0):
        sim.wait_until(lambda: self.t is not None, timeout_sim)
        self._stop.set()
        return self.t


@pytest.fixture
def services(sim, tmp_path):
    """B2-B7 on the simulated Pi Zero, on simulated time."""
    from boaty.mcp.camera import CameraService, PhotoStore, SimCamera
    from boaty.mcp.client import ServiceClient
    from boaty.mcp.clock import SimClock
    from boaty.mcp.photo_api import PhotoApi
    from boaty.mcp.services import ServiceHost

    clock = SimClock(lambda: sim.t, SPEEDUP)
    url = f"udpout:127.0.0.1:{sim.cfg.companion_port}"
    host = ServiceHost(clock, url).start()
    cam_client = ServiceClient("B2", url, clock).start(request_streams=False)
    cam = CameraService(cam_client, PhotoStore(tmp_path / "photos"),
                        SimCamera((648, 486))).start()
    api = PhotoApi(cam, "test-token", health=host["B6"], host="127.0.0.1",
                   port=0).start()
    host.camera, host.api, host.cam_client = cam, api, cam_client
    yield host
    api.stop()
    cam.stop()
    cam_client.stop()
    host.stop()


def boaty_events(companion, since: float = 0.0) -> list[str]:
    return [x for x in companion.texts_after(since) if x.startswith("BOATY")]
