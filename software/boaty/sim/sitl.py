"""Start and stop a complete simulated boat (ICD IF-21, proposed DD-19).

    physics (JsonBridge, UDP 9002)  <->  ArduPilot SITL (ardurover --model JSON)
    SITL telemetry (serial0)  ->  LinkRelay (IF-01)  ->  Mission Control :14550

The helm runs the same controlled parameter file as the real boat
(params/boaty-mk1.parm) plus params/sitl.parm.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from .boat import Boat, BoatParams
from .bridge import JsonBridge
from .link import LinkRelay

SOFTWARE = Path(__file__).resolve().parents[2]
PARAMS = SOFTWARE / "params"

# Placeholder home on the lake at Milton Country Park until TBD-02 picks the
# launch point. Heading is the direction the boat faces at launch.
MILTON_HOME = (52.24480, 0.15970, 0.0, 0.0)


def find_ardurover() -> Path:
    env = os.environ.get("BOATY_ARDUROVER")
    if env:
        return Path(env)
    home = os.environ.get("ARDUPILOT_HOME", "/home/user/ardupilot-build/"
                          "ardupilot")
    return Path(home) / "build" / "sitl" / "bin" / "ardurover"


def have_sitl() -> bool:
    return find_ardurover().is_file()


@dataclass
class SimConfig:
    home: tuple = MILTON_HOME
    gcs_port: int = 14550
    link_port: int = 14551
    companion_port: int = 14560       # SERIAL1: the mission computer (IF-04)
    json_port: int = 9002
    instance: int = 0
    speedup: int = 1
    param_files: list = field(default_factory=lambda: [
        PARAMS / "boaty-mk1.parm", PARAMS / "sitl.parm"])
    boat_params: BoatParams = field(default_factory=BoatParams)
    soc: float = 1.0
    keep_workdir: bool = False


class SimulatedBoat:
    """Context manager: physics + SITL + link relay."""

    def __init__(self, cfg: SimConfig | None = None):
        self.cfg = cfg or SimConfig()
        self.proc: subprocess.Popen | None = None
        self.workdir: Path | None = None
        self.bridge: JsonBridge | None = None
        self.link: LinkRelay | None = None

    @property
    def boat(self) -> Boat:
        assert self.bridge is not None
        return self.bridge.boat

    def start(self, timeout: float = 60.0) -> "SimulatedBoat":
        c = self.cfg
        exe = find_ardurover()
        if not exe.is_file():
            raise FileNotFoundError(f"ArduPilot SITL not found at {exe}; set "
                                    "ARDUPILOT_HOME or BOATY_ARDUROVER")
        self.workdir = Path(tempfile.mkdtemp(prefix="boaty-sitl-"))
        # Combine the parameter files into one defaults file, in order.
        defaults = self.workdir / "defaults.parm"
        defaults.write_text("\n".join(Path(p).read_text()
                                      for p in c.param_files))
        self.bridge = JsonBridge(Boat(c.boat_params, soc=c.soc,
                                      heading_deg=c.home[3]),
                                 port=c.json_port).start()
        self.link = LinkRelay(boat_port=c.link_port,
                              gcs_addr=("127.0.0.1", c.gcs_port)).start()
        home = ",".join(str(x) for x in c.home)
        cmd = [str(exe), "--model", "JSON:127.0.0.1", "--speedup",
               str(c.speedup), "--home", home, "--defaults", str(defaults),
               "--wipe", "-I", str(c.instance),
               "--serial0", f"udpclient:127.0.0.1:{c.link_port}",
               "--serial1", f"udpclient:127.0.0.1:{c.companion_port}"]
        self.log = open(self.workdir / "sitl.log", "w")
        self.proc = subprocess.Popen(cmd, cwd=self.workdir, stdout=self.log,
                                     stderr=subprocess.STDOUT)
        if not self.bridge.wait_for_sitl(timeout):
            self.stop()
            raise TimeoutError("SITL never sent a physics frame; see "
                               f"{self.workdir / 'sitl.log'}")
        return self

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.link:
            self.link.stop()
        if self.bridge:
            self.bridge.stop()
        if getattr(self, "log", None):
            self.log.close()
        if self.workdir and not self.cfg.keep_workdir:
            shutil.rmtree(self.workdir, ignore_errors=True)

    def sitl_log(self) -> str:
        try:
            return (self.workdir / "sitl.log").read_text()
        except Exception:  # noqa: BLE001
            return ""

    def __enter__(self) -> "SimulatedBoat":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    @property
    def t(self) -> float:
        """Simulated time in seconds (the physics clock)."""
        return self.bridge.boat.t

    def wait(self, sim_seconds: float) -> None:
        end = self.t + sim_seconds
        while self.t < end:
            time.sleep(0.01)
            if self.proc.poll() is not None:
                raise RuntimeError("SITL exited")

    def wait_until(self, cond, sim_seconds: float, poll: float = 0.01):
        """Wait until cond() is true or sim_seconds of simulated time pass.
        Returns the simulated time at which it became true, or None."""
        end = self.t + sim_seconds
        while self.t < end:
            if cond():
                return self.t
            time.sleep(poll)
            if self.proc.poll() is not None:
                raise RuntimeError("SITL exited")
        return self.t if cond() else None
