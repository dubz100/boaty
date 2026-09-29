"""Run Mission Control.

    python -m boaty.mcn.app set-pin                 # once per season (MCN-D61)
    python -m boaty.mcn.app --sim                   # whole system in SITL
    python -m boaty.mcn.app --helm udpin:0.0.0.0:14550 \\
        --boat-api http://192.168.50.2:8080         # the real boat

Open http://<this machine>:8000 on a tablet or phone. In --sim mode the
simulator, the boat services and the photo API all run here, and a PIN is
made up for the session and printed once if none is set.
The Claude API is used when a key file exists (see boaty/mcn/llm.py);
otherwise the planner offers templates only.
"""
from __future__ import annotations

import argparse
import getpass
import os
import secrets
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

from .helm_guard import BOAT_BASELINE, GuardedHelm
from .llm import IntentClient, key_file_status
from .log import SessionLog
from .pin import SETTINGS, PinLock, valid_format
from .planning import Planning
from .session import Config, Session
from .site import Site
from .voice import EspeakSpeaker, RecordingSpeaker
from .web import WebUI

LOGS = Path.home() / ".local" / "share" / "boaty"


def set_pin() -> None:
    pin = getpass.getpass("New 6-digit adult PIN: ")
    if not valid_format(pin) or pin != getpass.getpass("Again: "):
        sys.exit("PIN not set: it must be 6 digits, typed the same twice")
    PinLock.from_pin(pin, time.monotonic).save(SETTINGS)
    print(f"PIN saved (hashed) in {SETTINGS}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="boaty-mc")
    ap.add_argument("cmd", nargs="?", choices=["run", "set-pin"],
                    default="run")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--speedup", type=int, default=1)
    ap.add_argument("--helm", default="udpin:0.0.0.0:14550")
    ap.add_argument("--boat-api", default="http://192.168.50.2:8080")
    ap.add_argument("--boat-token", default=os.environ.get("BOATY_TOKEN", ""))
    ap.add_argument("--site", default="milton-country-park")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(
        KeyboardInterrupt()))              # clean shutdown on kill too
    if a.cmd == "set-pin":
        return set_pin()

    from ..helm.ardupilot import ArduPilotHelm
    from .photos import BoatApi

    site = Site.named(a.site)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    log = SessionLog(LOGS / "sessions" / f"{stamp}.jsonl")
    sim = services = None
    baseline = BOAT_BASELINE
    clock = time.monotonic
    if a.sim:
        from ..mcp.camera import CameraService, PhotoStore, SimCamera
        from ..mcp.client import ServiceClient
        from ..mcp.clock import SimClock
        from ..mcp.photo_api import PhotoApi
        from ..mcp.services import ServiceHost
        from ..sim.sitl import SimConfig, SimulatedBoat
        sim = SimulatedBoat(SimConfig(speedup=a.speedup)).start()
        baseline = sim.cfg.param_files
        clock = lambda: sim.t                                # noqa: E731
        sclock = SimClock(lambda: sim.t, a.speedup)
        url = f"udpout:127.0.0.1:{sim.cfg.companion_port}"
        services = ServiceHost(sclock, url).start()
        cam_client = ServiceClient("B2", url, sclock).start(
            request_streams=False)
        tmp = Path(tempfile.mkdtemp(prefix="boaty-photos-"))
        cam = CameraService(cam_client, PhotoStore(tmp), SimCamera()).start()
        a.boat_token = a.boat_token or secrets.token_hex(16)
        api = PhotoApi(cam, a.boat_token, health=services["B6"],
                       host="127.0.0.1", port=0).start()
        a.boat_api = f"http://127.0.0.1:{api.port}"
    helm = ArduPilotHelm(a.helm, time_scale=a.speedup)
    helm.connect(60)
    guard = GuardedHelm(helm, baseline)
    print("Checking helm parameters ...")
    diff = guard.check_params()
    print(f"  {len(diff)} difference(s) from the baseline")
    if Path(SETTINGS).exists():
        pin = PinLock.load(clock, SETTINGS)
    elif a.sim:
        p = f"{secrets.randbelow(10**6):06d}"
        pin = PinLock.from_pin(p, clock)
        print(f"Simulator session PIN (not saved): {p}")
    else:
        sys.exit("No adult PIN set. Run: python -m boaty.mcn.app set-pin")
    ks = key_file_status()
    llm = IntentClient() if ks == "ok" else None
    print("Claude API:", "ready" if llm else f"templates only ({ks})")
    speaker = EspeakSpeaker() if shutil.which("espeak-ng") or \
        shutil.which("espeak") else RecordingSpeaker(clock)
    session = Session(site, guard, Planning(site, llm), speaker, pin=pin,
                      log=log, clock=clock,
                      boat_api=BoatApi(a.boat_api, a.boat_token)
                      if a.boat_token else None,
                      photo_dir=LOGS / "photos",
                      cfg=Config(reference=site.home_ll()))
    session.start(period_s=0.2 / max(1, a.speedup))
    ui = WebUI(session, port=a.port).start()
    print(f"Mission Control on http://0.0.0.0:{ui.port}  (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        ui.stop()
        session.close()
        helm.close()
        if services:
            services.stop()
        if sim:
            sim.stop()


if __name__ == "__main__":
    main()
