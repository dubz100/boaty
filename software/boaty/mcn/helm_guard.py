"""C7 helm interface guard (MCN-D38, D43, D44, D45, D57).

Wraps the IF-14 helm with Mission Control's own rules:

- upload() takes only a ValidatedMission (VAL-001). It uploads the site
  fence and the mission, reads both back, and compares the helm's view of
  the mission by checksum (VAL-010). GO needs that comparison to pass.
- On connect, the helm's parameters are compared with the committed
  baseline. Any difference blocks arming and is shown (MCN-D45, SC-24).
- Any other system-255 heartbeat on the link means another ground station
  is talking to the boat, which would also mask the GCS failsafe (V-06b).
  While one is heard, commands that start or continue motion are refused
  and an alarm is raised (MCN-D57, SC-37). Commands that stop the boat or
  bring it home stay available: refusing STOP would be less safe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..helm.api import Fence, HelmError, Mission
from ..helm.params import differences, read_many
from .models import helm_view, helm_view_of, view_checksum
from .validator import ValidatedMission

PARAMS = Path(__file__).resolve().parents[2] / "params"
BOAT_BASELINE = [PARAMS / "boaty-mk1.parm", PARAMS / "boaty-mk1-speedybee.parm"]
IMPOSTOR_WINDOW_S = 3.0


class Refused(HelmError):
    """C7 will not send this command now; reasons are for the adult."""

    def __init__(self, reasons: list[str]):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass
class UploadReport:
    ok: bool
    expected: str
    read_back: str
    fence_ok: bool
    detail: str = ""


@dataclass
class GuardState:
    param_diff: dict = field(default_factory=dict)
    params_checked: bool = False
    impostors: list = field(default_factory=list)
    verified_checksum: str | None = None


class GuardedHelm:
    def __init__(self, helm, baseline_files=BOAT_BASELINE, log=None,
                 alarm=None):
        self.helm = helm
        self.baseline = read_many(baseline_files)
        self.log = log or (lambda *a, **k: None)
        self.alarm = alarm or (lambda text: None)
        self.state = GuardState()
        self._alarmed = False

    # ---- checks ------------------------------------------------------
    def check_params(self, timeout: float = 20) -> dict:
        live = self.helm.read_params(timeout)
        diff = differences(self.baseline, live)
        self.state.param_diff = diff
        self.state.params_checked = True
        self.log("params", checked=len(self.baseline), differences={
            k: list(v) for k, v in diff.items()})
        return diff

    def impostors(self) -> list:
        found = self.helm.foreign_gcs(IMPOSTOR_WINDOW_S)
        if found and not self._alarmed:
            self._alarmed = True
            self.log("impostor", sources=found)
            self.alarm("Another ground station is talking to the boat. "
                       "Close QGroundControl or any other app, then try again.")
        elif not found and self._alarmed:
            self._alarmed = False
            self.log("impostor_cleared")
        self.state.impostors = found
        return found

    def arm_blockers(self) -> list[str]:
        out = []
        if not self.state.params_checked:
            out.append("helm parameters not checked yet")
        elif self.state.param_diff:
            names = ", ".join(sorted(self.state.param_diff)[:5])
            out.append(f"helm parameters differ from the baseline: {names}")
        if self.impostors():
            out.append("another ground station is on the link")
        return out

    def _motion_ok(self) -> None:
        if self.impostors():
            raise Refused(["another ground station is on the link (MCN-D57)"])

    # ---- mission transfer -------------------------------------------
    def upload(self, vm: ValidatedMission) -> UploadReport:
        if not isinstance(vm, ValidatedMission):
            raise TypeError("upload() takes a ValidatedMission only "
                            "(VAL-001)")
        self._motion_ok()
        self.state.verified_checksum = None
        self.helm.upload_fence(vm.fence)
        self.helm.upload_mission(Mission(vm.helm_items))
        fence, items = self.helm.read_back()
        want = view_checksum(helm_view(vm.mission.items))
        got = view_checksum(helm_view_of(items))
        fence_ok = _same_fence(fence, vm.fence)
        ok = want == got and fence_ok
        if ok:
            self.state.verified_checksum = vm.checksum
        rep = UploadReport(ok, want, got, fence_ok,
                           "" if ok else "read-back differs from the "
                           "approved mission")
        self.log("upload", mission_id=vm.mission.id, checksum=vm.checksum,
                 helm_view=want, read_back=got, fence_ok=fence_ok, ok=ok)
        return rep

    def invalidate(self) -> None:
        self.state.verified_checksum = None

    # ---- commands ----------------------------------------------------
    def arm(self) -> None:
        b = self.arm_blockers()
        if b:
            raise Refused(b)
        self.helm.arm()

    def start_mission(self, approved_checksum: str) -> None:
        self._motion_ok()
        if self.state.verified_checksum != approved_checksum:
            raise Refused(["the mission on the boat has not been read back "
                           "and matched to the approved one (VAL-010)"])
        self.helm.start_mission()

    def manual(self) -> None:
        self._motion_ok()
        self.helm.manual()

    def drive(self, throttle: float, turn: float) -> None:
        self._motion_ok()
        self.helm.drive(throttle, turn)

    # Always allowed: they stop the boat or bring it home.
    def stop(self) -> None:
        self.helm.stop()

    def hold(self) -> None:
        self.helm.hold()

    def halt(self) -> None:
        self.helm.halt()

    def return_home(self) -> None:
        self.helm.return_home()

    def disarm(self, force: bool = False) -> None:
        self.helm.disarm(force)

    def status(self):
        return self.helm.status()


def _same_fence(a: Fence, b: Fence, tol: float = 2e-7) -> bool:
    def close(p, q):
        return all(abs(x - y) <= tol for x, y in zip(p, q))

    if len(a.inclusion) != len(b.inclusion) or \
            len(a.exclusions) != len(b.exclusions) or \
            len(a.exclusion_circles) != len(b.exclusion_circles):
        return False
    if not all(close(p, q) for p, q in zip(a.inclusion, b.inclusion)):
        return False
    for pa, pb in zip(a.exclusions, b.exclusions):
        if len(pa) != len(pb) or not all(close(p, q) for p, q in zip(pa, pb)):
            return False
    return all(close(ca[:2], cb[:2]) and abs(ca[2] - cb[2]) < 0.01
               for ca, cb in zip(a.exclusion_circles, b.exclusion_circles))
