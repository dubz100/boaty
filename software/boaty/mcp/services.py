"""Boat services B4-B7 (SSS-MCP, ICD IF-04).

    B4 link watchdog      MCP-D12  RTL after 60 s link loss in AUTO, or 10 s
                                   after a MANUAL link loss (FS-002/003)
    B5 weed-shedding      MCP-D18/34  up to 3 astern bursts after a stuck
                                   event, then resume if moving forward, else
                                   HOLD + alarm; > 3 episodes in 2 min: HOLD
                                   (FS-006)
    B6 health             MCP-D15/26  moisture / box heat -> RTL; position
                                   loss 1 s -> HOLD, 10 s healthy -> RTL
                                   (FS-004); critical battery -> slow RTL
                                   (FS-001)
    B7 navigation monitor MCP-D22..25  first-motion heading check, second
                                   stuck detector, divergence watchdog,
                                   persistent fence breach (FEN-006).
                                   Only ever requests HOLD.

Each service has its own filtered ServiceClient and ticks at 10 Hz on its
clock. Events and alarms are STATUSTEXTs starting "BOATY ", which Mission
Control shows and the other services read (B5 acts on "BOATY B7 STUCK").
"""
from __future__ import annotations

import json
import logging
import math
import threading
from collections import deque
from pathlib import Path

from pymavlink import mavutil

from .client import EVENT_PREFIX, ServiceClient
from .geometry import FenceGeometry
from .policy import AUTO, GUIDED, HOLD, RTL

log = logging.getLogger(__name__)
mav = mavutil.mavlink
STEERING = 3
CONFIG = Path(__file__).resolve().parents[2] / "params" / "boat-services.json"


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(Path(path).read_text())


def angdiff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


class Service:
    name = "B?"
    period = 0.1

    def __init__(self, client: ServiceClient, cfg: dict):
        self.c, self.v, self.cfg = client, client.view, cfg
        self.clock = client.clock
        self.actions: list = []          # (t, text) for tests and logs
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Service":
        self._thread = threading.Thread(target=self._run, name=self.name,
                                        daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick(self.clock.now())
            except Exception:  # noqa: BLE001
                log.exception("%s tick", self.name)
            self.clock.sleep(self.period)

    def tick(self, now: float) -> None:
        raise NotImplementedError

    def act(self, mode: int, text: str,
            severity: int = mav.MAV_SEVERITY_WARNING) -> bool:
        ok = self.c.set_mode(mode)
        self.actions.append((self.clock.now(), text, ok))
        self.c.event(text, severity)
        return ok

    def events_since(self, t: float, key: str) -> list:
        """BOATY events from boat services (component 191) since t."""
        return [(tm, x) for tm, comp, x in self.v.texts
                if tm >= t and comp == 191 and x.startswith(EVENT_PREFIX + key)]

    def shedding(self) -> bool:
        """True while B5 is between SHED START and SHED END."""
        state = False
        for _, comp, x in self.v.texts:
            if comp != 191:
                continue
            if x.startswith(EVENT_PREFIX + "B5 SHED START"):
                state = True
            elif x.startswith(EVENT_PREFIX + "B5 SHED END"):
                state = False
        return state


# ---------------------------------------------------------------------------
class LinkWatchdog(Service):
    """B4 (MCP-D12)."""
    name = "B4"

    def __init__(self, client, cfg):
        super().__init__(client, cfg["b4_link_watchdog"])
        self.acted_for = None             # heartbeat time already acted on

    def tick(self, now: float) -> None:
        v, c = self.v, self.cfg
        hb = v.mc_heartbeat_t
        if hb is None or not v.armed or self.acted_for == hb:
            return
        lost = now - hb
        if v.mode == AUTO and lost >= c["auto_rtl_after_s"]:
            if self.act(RTL, "B4 LINK LOST 60S: RTL"):
                self.acted_for = hb
        elif v.mode == HOLD and lost >= c["manual_rtl_after_s"]:
            at = v.mode_at(hb)
            if at and at[1] == STEERING:
                if self.act(RTL, "B4 LINK LOST IN MANUAL: RTL"):
                    self.acted_for = hb


# ---------------------------------------------------------------------------
class Health(Service):
    """B6 (MCP-D15, MCP-D26; FS-004 HOLD and FS-001 slow RTL added in
    slice 2)."""
    name = "B6"

    def __init__(self, client, cfg, sensors):
        super().__init__(client, cfg["b6_health"])
        self.sensors = sensors
        self.moisture, self.box_temp_c = False, None
        self._reset()

    def _reset(self) -> None:
        self.bad_since = self.good_since = None
        self.pos_hold = False
        self.hazard_acted = False
        self.slowed_for = None

    def tick(self, now: float) -> None:
        v, c = self.v, self.cfg
        self.moisture, self.box_temp_c = self.sensors.read()
        if not v.armed:
            self._reset()
            return
        healthy = v.position_healthy(c["max_hdop"]) and now - v.pos_t < 2.0

        # FS-004: position loss -> HOLD after 3 s; healthy 10 s -> RTL.
        if not healthy:
            self.good_since = None
            self.bad_since = self.bad_since if self.bad_since else now
            if not self.pos_hold and now - self.bad_since >= \
                    c["position_bad_hold_s"]:
                self.pos_hold = True
                if v.mode != HOLD:
                    self.act(HOLD, "B6 POSITION LOST: HOLD")
                else:
                    self.c.event("B6 POSITION LOST")
        else:
            self.bad_since = None
            if self.pos_hold:
                if v.mode != HOLD:
                    self.pos_hold = False       # an adult has taken over
                else:
                    self.good_since = self.good_since or now
                    if now - self.good_since >= c["position_good_rtl_s"]:
                        self.pos_hold = False
                        self.act(RTL, "B6 POSITION OK: RTL")

        # FS-010 / A-11: water or heat in the box -> RTL (HOLD wins if the
        # position is bad: FS-011).
        hot = self.box_temp_c is not None and \
            self.box_temp_c > c["box_temp_rtl_c"]
        wet = self.moisture and c["moisture_rtl"]
        if (wet or hot) and not self.hazard_acted:
            self.hazard_acted = True
            what = "WATER IN BOX" if wet else "BOX HOT"
            if healthy and v.mode not in (RTL,):
                self.act(RTL, f"B6 {what}: RTL", mav.MAV_SEVERITY_CRITICAL)
            else:
                self.c.event(f"B6 {what}", mav.MAV_SEVERITY_CRITICAL)

        # FS-001: at critical battery, continue RTL at reduced speed.
        crit = v.battery_pct <= c["critical_battery_pct"] or \
            v.battery_crit_t is not None
        if crit and v.mode == RTL and self.slowed_for != v.mode_since:
            if self.c.change_speed(c["critical_rtl_speed_mps"]):
                self.slowed_for = v.mode_since
                self.actions.append((now, "slow RTL", True))
                self.c.event("B6 CRITICAL BATTERY: SLOW RTL",
                             mav.MAV_SEVERITY_CRITICAL)

    def snapshot(self) -> dict:
        """Fields of the IF-03 Health object that B6 owns."""
        return {"moisture": bool(self.moisture),
                "box_temp_c": self.box_temp_c}


# ---------------------------------------------------------------------------
class NavMonitor(Service):
    """B7 (MCP-D22..25, FEN-006). Only ever requests HOLD."""
    name = "B7"

    def __init__(self, client, cfg):
        super().__init__(client, cfg["b7_nav_monitor"])
        self.fence: FenceGeometry | None = None
        self._fetching = False
        self._reset()

    def _reset(self) -> None:
        self.fm_bad_since = None
        self.stuck_since = None
        self.samples: deque = deque()
        self.last_outside_m = 0.0

    def _fetch_fence(self) -> None:
        try:
            items = self.c.download(1)
            self.fence = FenceGeometry.from_items(items) if items else None
        finally:
            self._fetching = False

    def hold(self, text: str) -> None:
        if self.v.mode != HOLD:
            self.act(HOLD, text)
        self._reset()

    def tick(self, now: float) -> None:
        v, c = self.v, self.cfg
        if not v.armed:
            self._reset()
            self.fence = None
            return
        if self.fence is None and not self._fetching:
            self._fetching = True
            threading.Thread(target=self._fetch_fence, daemon=True).start()
        m, spd, course, hdg = v.mode, v.groundspeed, v.course, v.heading

        # FEN-006: persistent breach (any powered mode).
        if m not in (HOLD,):
            if v.breached and v.breach_since is not None and \
                    now - v.breach_since >= c["breach_max_s"]:
                self.hold("B7 OUTSIDE FENCE 30S: HOLD")
                return
            if self.fence and v.lat is not None:
                self.last_outside_m = self.fence.outside_by(v.lat, v.lon)
                if self.last_outside_m > c["breach_max_outside_m"]:
                    self.hold("B7 10M OUTSIDE FENCE: HOLD")
                    return

        if self.shedding() or m not in (AUTO, RTL, STEERING):
            self._reset()
            return

        # MCP-D22: first-motion heading check.
        in_window = now - v.mode_since <= c["first_motion_window_s"]
        err = angdiff(course, hdg) if course is not None and hdg is not None \
            else 0.0
        if m == STEERING and err > 135:
            err = 0.0                     # an adult driving astern
        if (in_window or self.fm_bad_since is not None) and \
                spd > c["first_motion_min_speed_mps"] and \
                err > c["first_motion_max_error_deg"]:
            if self.fm_bad_since is None and in_window:
                self.fm_bad_since = now
            if self.fm_bad_since is not None and \
                    now - self.fm_bad_since >= c["first_motion_dwell_s"]:
                self.hold("B7 HEADING CHECK FAILED: HOLD")
                return
        else:
            self.fm_bad_since = None

        if m not in (AUTO, RTL):
            return
        if v.wp_dist < c["near_target_m"]:
            # Arriving or station-keeping: progress along a leg means
            # nothing here (RTL holds position at home for boats).
            self.stuck_since = None
            self.samples.clear()
            return
        tb = v.target_bearing
        # MCP-D23: second stuck detector (progress along the leg).
        prog = spd * math.cos(math.radians(course - tb)) \
            if course is not None and tb is not None else 0.0
        if v.throttle >= c["stuck_min_throttle_pct"] and \
                prog < c["stuck_max_progress_mps"]:
            self.stuck_since = self.stuck_since or now
            if now - self.stuck_since >= c["stuck_dwell_s"]:
                self.hold("B7 STUCK")
                return
        else:
            self.stuck_since = None

        # MCP-D24: divergence watchdog over a sliding window.
        ref = course if course is not None and spd > 0.3 else hdg
        bad_hdg = ref is not None and tb is not None and \
            angdiff(ref, tb) > c["divergence_heading_deg"]
        self.samples.append((now, bad_hdg,
                             abs(v.xtrack) > c["divergence_xtrack_m"]))
        w = c["divergence_window_s"]
        while self.samples and self.samples[0][0] < now - w:
            self.samples.popleft()
        if self.samples and self.samples[0][0] <= now - w + 0.5:
            n = len(self.samples)
            frac = sum(1 for s in self.samples if s[1]) / n
            all_xt = all(s[2] for s in self.samples)
            if frac >= c["divergence_fraction"] or all_xt:
                self.hold("B7 OFF COURSE: HOLD")


# ---------------------------------------------------------------------------
class WeedShedder(Service):
    """B5 (MCP-D18). Acts only on a stuck event: the helm's crash check or
    B7's second stuck detector."""
    name = "B5"

    def __init__(self, client, cfg):
        super().__init__(client, cfg["b5_weed_shedding"])
        self.active = False
        self.seen_until = 0.0
        self.bursts = 0
        self.why = ""
        self.watch_log: list[dict] = []
        self.episodes: list[float] = []

    def _triggers(self, since: float) -> list[float]:
        out = []
        for tm, comp, x in self.v.texts:
            if tm <= since:
                continue
            if (comp == 1 and x.startswith("Crash")) or \
                    (comp == 191 and x.startswith(EVENT_PREFIX + "B7 STUCK")):
                out.append(tm)
        return out

    def tick(self, now: float) -> None:
        if self.active:
            return
        trig = self._triggers(self.seen_until)
        self.seen_until = now
        if trig and self.v.armed:
            win = self.cfg["episode_window_s"]
            self.episodes = [t for t in self.episodes if now - t < win]
            self.episodes.append(now)
            if len(self.episodes) > self.cfg["max_episodes"]:
                # Stuck again and again (e.g. a dead motor that looks like
                # weed): stop, and let B7 / the adult take over.
                self.episodes.clear()
                self.actions.append((now, "repeatedly stuck", True))
                self.c.set_mode(HOLD)
                self.c.event("B5 REPEATEDLY STUCK: HOLD",
                             mav.MAV_SEVERITY_CRITICAL)
                return
            self.active = True
            threading.Thread(target=self._shed, args=(trig[0],),
                             daemon=True).start()

    def _prev_mode(self, t: float) -> int | None:
        prev = None
        for tm, armed, m in self.v.modes:
            if tm > t:
                break
            if armed and m not in (HOLD, GUIDED):
                prev = m
        return prev

    def _await_mode(self, mode: int, timeout: float = 3.0) -> bool:
        """The filter checks commands against the helm's reported mode, so
        wait until the heartbeat shows the mode we asked for."""
        end = self.clock.now() + timeout
        while self.clock.now() < end:
            if self.v.mode == mode:
                return True
            self.clock.sleep(0.05)
        return False

    def _forward_speed(self) -> float:
        """Velocity along the heading (m/s); negative when going astern."""
        v = self.v
        if v.heading is None:
            return 0.0
        h = math.radians(v.heading)
        return v.vn * math.cos(h) + v.ve * math.sin(h)

    def _take_control(self, tries: int = 2) -> bool:
        """Switch to GUIDED and see it in the heartbeat. A refused or
        unconfirmed switch is not a burst: retry once, and if it still
        fails say so, rather than report the weed as 'still stuck'."""
        for i in range(tries):
            ok = self.c.set_mode(GUIDED)
            if ok and self._await_mode(GUIDED):
                return True
            self.why = (f"mode {self.v.mode} after "
                        f"{'ACK' if ok else 'no/refused ACK'}")
            self.clock.sleep(1.0)
        return False

    def _shed(self, t_trigger: float) -> None:
        c, v, clk = self.cfg, self.v, self.clock
        try:
            prev = self._prev_mode(t_trigger)
            if prev not in (AUTO, RTL):
                self.c.event("B5 STUCK: HOLD", mav.MAV_SEVERITY_CRITICAL)
                return
            self.c.event("B5 SHED START")
            for burst in range(1, c["max_bursts"] + 1):
                self.bursts = burst
                self.actions.append((clk.now(), f"burst {burst}", True))
                if not self._take_control():
                    self.actions.append((clk.now(), "no control", False))
                    self.c.event(f"B5 NO CONTROL ({self.why}): HOLD",
                                 mav.MAV_SEVERITY_CRITICAL)
                    self.c.set_mode(HOLD)
                    return
                for _ in range(int(c["burst_s"] * c["target_hz"])):
                    self.c.astern(c["astern_fraction"])
                    clk.sleep(1.0 / c["target_hz"])
                self.c.set_mode(HOLD)
                clk.sleep(1.0)
                self.c.filter.grant_resume(prev)
                ok = self.c.set_mode(prev)
                self.c.filter.grant_resume(None)
                t_res = clk.now()
                end = t_res + c["watch_after_resume_s"]
                free = False
                peak, why = 0.0, "timeout"
                fwd_since = None
                while ok and clk.now() < end:
                    # Forward speed, not ground speed: the burst leaves
                    # the boat drifting astern, and that is not "free".
                    fwd = self._forward_speed()
                    peak = max(peak, fwd)
                    if v.mode == prev and fwd > c["free_speed_mps"]:
                        if fwd_since is None:
                            fwd_since = clk.now()
                        if clk.now() - fwd_since >= c["free_hold_s"]:
                            free, why = True, "moving forward"
                            break
                    else:
                        fwd_since = None
                    if v.mode == HOLD:
                        why = "helm HOLD"
                        break
                    clk.sleep(0.1)
                self.watch_log.append(dict(burst=burst, resume_ack=ok,
                                           mode=v.mode, peak_mps=round(peak, 2),
                                           after_s=round(clk.now() - t_res, 1),
                                           ended=why if ok else "no resume"))
                if free:
                    self.actions.append((clk.now(), "free", True))
                    self.c.event(f"B5 FREE AFTER {burst}: RESUMED")
                    return
                self.c.set_mode(HOLD)
            self.actions.append((clk.now(), "still stuck", True))
            self.c.event("B5 STILL STUCK: HOLD", mav.MAV_SEVERITY_CRITICAL)
        finally:
            self.c.event("B5 SHED END")
            self.seen_until = clk.now() + 1.0
            self.active = False


# ---------------------------------------------------------------------------
class ServiceHost:
    """Runs B4-B7 (each with its own client, as separate systemd units would
    on the Pi Zero)."""

    def __init__(self, clock, url: str = "udpout:127.0.0.1:14560",
                 sensors=None, cfg: dict | None = None,
                 names=("B4", "B5", "B6", "B7")):
        from .sensors import SimSensors
        self.cfg = cfg or load_config()
        self.sensors = sensors or SimSensors()
        mk = {"B4": lambda cl: LinkWatchdog(cl, self.cfg),
              "B5": lambda cl: WeedShedder(cl, self.cfg),
              "B6": lambda cl: Health(cl, self.cfg, self.sensors),
              "B7": lambda cl: NavMonitor(cl, self.cfg)}
        self.services = {n: mk[n](ServiceClient(n, url, clock)) for n in names}

    def start(self) -> "ServiceHost":
        for s in self.services.values():
            s.c.start(request_streams=(s.name == "B6"))
            s.start()
        for s in self.services.values():
            if s.name == "B7":
                s.c.request_home()
        return self

    def stop(self) -> None:
        if getattr(self, "_stopped", False):
            return
        self._stopped = True
        for s in self.services.values():
            s.stop()
            s.c.stop()

    def __getitem__(self, name: str) -> Service:
        return self.services[name]
