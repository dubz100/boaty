"""ArduPilotHelm: the IF-14 Helm API over MAVLink 2 (IF-02) using pymavlink.

Threading: one reader thread owns receiving and keeps the status cache fresh;
one heartbeat thread announces Mission Control (system 255, component 190) at
1 Hz; callers' threads send commands under a send lock and wait on the
reader's inbox. stop() never waits for other calls: it bumps a pre-emption
counter that makes any in-progress wait give up.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable

from pymavlink import mavutil

from .api import (ArrivedHome, Breach, CommandRejected, FailsafeEvent, Fence,
                  HelmError, HelmEvent, HelmStatus, LinkChange, Mission,
                  MissionItem, ModeChanged, NoResponse, NotAllowedWhileArmed,
                  PreArmFailed, RoverMode, SrsMode, Text, TransferFailed,
                  srs_mode)

log = logging.getLogger(__name__)
mav = mavutil.mavlink

# IF-02 telemetry set: message id -> rate in Hz.
STREAMS = {0: 1, 1: 1, 33: 4, 24: 1, 147: 1, 74: 2, 42: 1, 62: 1, 193: 1,
           162: 1, 242: 0.2}

MISSION, FENCE = mav.MAV_MISSION_TYPE_MISSION, mav.MAV_MISSION_TYPE_FENCE
F_INCL, F_EXCL, F_CIRC_EXCL = 5001, 5002, 5004
FORCE_DISARM_MAGIC = 21196
EKF_NEEDED = (mav.EKF_ATTITUDE | mav.EKF_VELOCITY_HORIZ
              | mav.EKF_POS_HORIZ_ABS)


def now() -> datetime:
    return datetime.now(timezone.utc)


def distance_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * \
        math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Preempted(HelmError):
    """A STOP arrived while this call was waiting."""


class ArduPilotHelm:
    def __init__(self, url: str = "udpin:0.0.0.0:14550", sysid: int = 255,
                 compid: int = 190, target_system: int = 1,
                 target_component: int = 1, cmd_timeout: float = 1.5,
                 retries: int = 3, link_timeout: float = 3.0,
                 time_scale: float = 1.0):
        """time_scale: simulator speed-up. Heartbeats are sent time_scale
        times per wall second so the helm still sees 1 Hz in its own time."""
        self.url = url
        self.sysid, self.compid = sysid, compid
        self.ts, self.tc = target_system, target_component
        self.cmd_timeout, self.retries = cmd_timeout, retries
        self.time_scale = max(1.0, time_scale)
        self.link_timeout = link_timeout / self.time_scale
        self.conn = None
        self._send_lock = threading.Lock()
        self._cv = threading.Condition()
        self._inbox: deque = deque(maxlen=2000)       # (seq, msg)
        self._seq = 0
        self._texts: deque = deque(maxlen=200)       # (monotonic, sev, text)
        self._subs: list[Callable[[HelmEvent], None]] = []
        self._stop = threading.Event()
        self._preempt = 0
        self._heartbeat_enabled = True
        self._threads: list[threading.Thread] = []
        self.params: dict[str, float] = {}
        self._param_count = None
        # Status cache.
        self._s = dict(link_t=0.0, armed=False, mode=None, lat=None, lon=None,
                       hdg=None, speed=0.0, batt_pct=0.0, batt_v=0.0,
                       rail_v=0.0, fix=0, sats=0, hdop=99.9, ekf_ok=False,
                       breached=False, breach_count=0, seq=None, total=None,
                       home=None, link_ok=False, arrived=False)

    # ------------------------------------------------------------------
    # Connection

    def connect(self, timeout_s: float = 10) -> None:
        self.conn = mavutil.mavlink_connection(
            self.url, source_system=self.sysid, source_component=self.compid,
            dialect="ardupilotmega", autoreconnect=True)
        self._stop.clear()
        for target, name in ((self._reader, "helm-reader"),
                             (self._heartbeat, "helm-heartbeat"),
                             (self._watchdog, "helm-link")):
            t = threading.Thread(target=target, name=name, daemon=True)
            t.start()
            self._threads.append(t)
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            if self._s["mode"] is not None:
                break
            time.sleep(0.05)
        else:
            raise NoResponse("no heartbeat from the helm")
        self._request_streams()

    def close(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=2)
        self._threads.clear()
        if self.conn:
            self.conn.close()

    def set_heartbeat(self, enabled: bool) -> None:
        """Test hook: stop announcing Mission Control (simulates C7 dying)."""
        self._heartbeat_enabled = enabled

    def _send(self, fn: str, *args) -> None:
        with self._send_lock:
            getattr(self.conn.mav, fn)(*args)

    def _heartbeat(self) -> None:
        while not self._stop.is_set():
            if self._heartbeat_enabled and self.conn:
                try:
                    self._send("heartbeat_send", mav.MAV_TYPE_GCS,
                               mav.MAV_AUTOPILOT_INVALID, 0, 0,
                               mav.MAV_STATE_ACTIVE)
                except OSError:
                    pass
            self._stop.wait(1.0 / self.time_scale)

    def _request_streams(self) -> None:
        for msg_id, hz in STREAMS.items():
            try:
                # Intervals are in the helm's (simulated) time.
                self._command(mav.MAV_CMD_SET_MESSAGE_INTERVAL,
                              [msg_id, 1e6 / hz])
            except HelmError as e:
                log.warning("stream %s: %s", msg_id, e)

    # ------------------------------------------------------------------
    # Receiving

    def _reader(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self.conn.recv_match(blocking=True, timeout=0.2)
            except (OSError, ValueError) as e:
                log.debug("recv: %s", e)
                continue
            if msg is None or msg.get_type() == "BAD_DATA":
                continue
            if msg.get_srcSystem() != self.ts:
                continue
            try:
                self._handle(msg)
            except Exception:  # noqa: BLE001
                log.exception("handling %s", msg.get_type())

    def _handle(self, msg) -> None:
        t, s = msg.get_type(), self._s
        comp = msg.get_srcComponent()
        events: list[HelmEvent] = []
        if t == "HEARTBEAT":
            if comp != self.tc:
                return
            s["link_t"] = time.monotonic()
            armed = bool(msg.base_mode & mav.MAV_MODE_FLAG_SAFETY_ARMED)
            old = srs_mode(s["armed"], s["mode"]) if s["mode"] is not None \
                else None
            changed = (armed, msg.custom_mode) != (s["armed"], s["mode"])
            s["armed"], s["mode"] = armed, msg.custom_mode
            if changed and old is not None:
                events.append(ModeChanged(now(), old, srs_mode(armed,
                                                               msg.custom_mode),
                                          msg.custom_mode))
                if msg.custom_mode == RoverMode.RTL:
                    s["arrived"] = False
            if not s["link_ok"]:
                s["link_ok"] = True
                events.append(LinkChange(now(), True))
        elif t == "GLOBAL_POSITION_INT":
            s["lat"], s["lon"] = msg.lat / 1e7, msg.lon / 1e7
            s["hdg"] = None if msg.hdg == 65535 else msg.hdg / 100
            s["speed"] = math.hypot(msg.vx, msg.vy) / 100
            events += self._check_arrival()
        elif t == "GPS_RAW_INT":
            s["fix"], s["sats"] = msg.fix_type, msg.satellites_visible
            s["hdop"] = msg.eph / 100 if msg.eph != 65535 else 99.9
        elif t == "BATTERY_STATUS":
            v = msg.voltages[0] / 1000 if msg.voltages[0] != 65535 else 0.0
            if msg.id == 0:
                s["batt_v"] = v
                s["batt_pct"] = max(0, msg.battery_remaining)
            elif msg.id == 1:
                s["rail_v"] = v
        elif t == "EKF_STATUS_REPORT":
            s["ekf_ok"] = (msg.flags & EKF_NEEDED) == EKF_NEEDED
        elif t == "FENCE_STATUS":
            s["breached"] = bool(msg.breach_status)
            if msg.breach_count > s["breach_count"]:
                events.append(Breach(now(), msg.breach_count))
            s["breach_count"] = msg.breach_count
        elif t == "MISSION_CURRENT":
            s["seq"] = msg.seq
            s["total"] = getattr(msg, "total", None)
        elif t == "HOME_POSITION":
            s["home"] = (msg.latitude / 1e7, msg.longitude / 1e7)
        elif t == "STATUSTEXT":
            text = msg.text
            self._texts.append((time.monotonic(), msg.severity, text))
            events.append(Text(now(), msg.severity, text))
            if "failsafe" in text.lower() or "crash" in text.lower():
                events.append(FailsafeEvent(now(), text))
        elif t == "PARAM_VALUE":
            self.params[msg.param_id] = msg.param_value
            self._param_count = msg.param_count
        with self._cv:
            self._seq += 1
            self._inbox.append((self._seq, msg))
            self._cv.notify_all()
        for e in events:
            self._emit(e)

    def _check_arrival(self) -> list[HelmEvent]:
        s = self._s
        if s["mode"] != RoverMode.RTL or s["arrived"] or not s["home"] \
                or s["lat"] is None:
            return []
        if distance_m(s["lat"], s["lon"], *s["home"]) < 5 and s["speed"] < 0.3:
            s["arrived"] = True
            return [ArrivedHome(now())]
        return []

    def _watchdog(self) -> None:
        while not self._stop.is_set():
            s = self._s
            ok = time.monotonic() - s["link_t"] < self.link_timeout
            if s["link_ok"] and not ok:
                s["link_ok"] = False
                self._emit(LinkChange(now(), False))
            self._stop.wait(0.25)

    def _emit(self, e: HelmEvent) -> None:
        for cb in list(self._subs):
            try:
                cb(e)
            except Exception:  # noqa: BLE001
                log.exception("subscriber failed on %s", e)

    def _mark(self) -> int:
        """Sequence number of the newest inbox message."""
        with self._cv:
            return self._seq

    def _wait(self, pred: Callable, timeout: float, since: int | None = None):
        r = self._wait_n(pred, timeout, since)
        return r[1] if r else None

    def _wait_n(self, pred: Callable, timeout: float,
                since: int | None = None):
        """Wait for a message newer than `since` (default: now) matching
        pred; return (seq, msg) or None. Raises Preempted if stop() is
        called meanwhile."""
        end = time.monotonic() + timeout
        token = self._preempt
        with self._cv:
            last = self._seq if since is None else since
            while True:
                for n, m in self._inbox:
                    if n > last and pred(m):
                        return n, m
                last = self._seq
                if self._preempt != token:
                    raise Preempted("pre-empted by STOP")
                left = end - time.monotonic()
                if left <= 0:
                    return None
                self._cv.wait(min(left, 0.1))

    # ------------------------------------------------------------------
    # Commands

    def _command(self, cmd: int, params: list[float], timeout: float = None,
                 retries: int = None, preemptible: bool = True):
        timeout = timeout or self.cmd_timeout
        retries = retries or self.retries
        p = (list(params) + [0.0] * 7)[:7]
        for attempt in range(retries):
            mark = self._mark()
            self._send("command_long_send", self.ts, self.tc, cmd, attempt,
                       *p)
            ack = self._wait(lambda m: m.get_type() == "COMMAND_ACK"
                             and m.command == cmd, timeout, since=mark) \
                if preemptible else self._wait_nopreempt(cmd, timeout, mark)
            if ack is None:
                continue
            if ack.result == mav.MAV_RESULT_ACCEPTED:
                return ack
            if ack.result == mav.MAV_RESULT_IN_PROGRESS:
                continue
            raise CommandRejected(ack.result, mav.enums["MAV_RESULT"]
                                  [ack.result].name)
        raise NoResponse(f"no ACK for command {cmd}")

    def _wait_nopreempt(self, cmd, timeout, mark):
        token = self._preempt
        try:
            return self._wait(lambda m: m.get_type() == "COMMAND_ACK"
                              and m.command == cmd, timeout, since=mark)
        except Preempted:
            self._preempt = token
            return None

    def _set_mode(self, mode: RoverMode, preemptible: bool = True) -> None:
        self._command(mav.MAV_CMD_DO_SET_MODE,
                      [mav.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, int(mode)],
                      preemptible=preemptible)
        end = time.monotonic() + 3
        while time.monotonic() < end:
            if self._s["mode"] == mode:
                return
            time.sleep(0.05)
        raise NoResponse(f"helm did not enter {mode.name}")

    def arm(self) -> None:
        if self._s["armed"]:
            return
        t0 = time.monotonic()
        try:
            self._command(mav.MAV_CMD_COMPONENT_ARM_DISARM, [1],
                          timeout=3, retries=1)
        except CommandRejected:
            time.sleep(0.5)
            reasons = [txt for (ts, _, txt) in list(self._texts)
                       if ts >= t0 - 0.2 and ("prearm" in txt.lower()
                                              or "arm" in txt.lower())]
            raise PreArmFailed(reasons)
        self._await(lambda: self._s["armed"], 3, "helm did not arm")

    def disarm(self, force: bool = False) -> None:
        self._command(mav.MAV_CMD_COMPONENT_ARM_DISARM,
                      [0, FORCE_DISARM_MAGIC if force else 0],
                      preemptible=False)
        self._await(lambda: not self._s["armed"], 3, "helm did not disarm")

    def _await(self, cond: Callable[[], bool], timeout: float, err: str):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if cond():
                return
            time.sleep(0.05)
        raise NoResponse(err)

    def start_mission(self) -> None:
        if self._s["seq"] in (None, 0):
            self._command(mav.MAV_CMD_DO_SET_MISSION_CURRENT, [1])
        self._set_mode(RoverMode.AUTO)

    def hold(self) -> None:
        self._set_mode(RoverMode.LOITER)

    def return_home(self) -> None:
        self._set_mode(RoverMode.RTL)

    def manual(self) -> None:
        self._set_mode(RoverMode.STEERING)

    def stop(self) -> None:
        """HOLD (motors off), then disarm. Idempotent; pre-empts other calls.
        """
        self._preempt += 1
        with self._cv:
            self._cv.notify_all()
        if self._s["armed"] and self._s["mode"] != RoverMode.HOLD:
            try:
                self._set_mode(RoverMode.HOLD, preemptible=False)
            except HelmError as e:
                log.warning("stop: HOLD failed: %s", e)
        if self._s["armed"]:
            try:
                self.disarm()
            except HelmError:
                self.disarm(force=True)

    def drive(self, throttle: float, turn: float) -> None:
        """MANUAL_CONTROL. Rover reads z as throttle and y as steering
        (Rover 4.7.1 GCS_MAVLink_Rover.cpp); send at >= 5 Hz."""
        clamp = lambda v: int(max(-1.0, min(1.0, v)) * 1000)  # noqa: E731
        self._send("manual_control_send", self.ts, 0, clamp(turn),
                   clamp(throttle), 0, 0)

    # ------------------------------------------------------------------
    # Status and subscriptions

    def status(self) -> HelmStatus:
        s = self._s
        return HelmStatus(
            t_utc=now(), link_ok=s["link_ok"], armed=s["armed"],
            mode=srs_mode(s["armed"], s["mode"]) if s["mode"] is not None
            else SrsMode.UNKNOWN, lat=s["lat"], lon=s["lon"],
            heading_deg=s["hdg"], speed_mps=s["speed"],
            battery_pct=s["batt_pct"], battery_v=s["batt_v"],
            rail_v=s["rail_v"], gps_fix=s["fix"], sats=s["sats"],
            hdop=s["hdop"], ekf_ok=s["ekf_ok"], fence_breached=s["breached"],
            mission_seq=s["seq"], mission_total=s["total"],
            ardupilot_mode=s["mode"])

    def home(self) -> tuple[float, float] | None:
        return self._s["home"]

    def subscribe(self, cb: Callable[[HelmEvent], None]) -> None:
        self._subs.append(cb)

    def recent_texts(self, since_s: float = 60) -> list[str]:
        t = time.monotonic() - since_s
        return [txt for (ts, _, txt) in list(self._texts) if ts >= t]

    # ------------------------------------------------------------------
    # Parameters (C7 baseline check, SAF-007)

    def read_params(self, timeout: float = 20) -> dict[str, float]:
        self.params.clear()
        self._param_count = None
        self._send("param_request_list_send", self.ts, self.tc)
        end = time.monotonic() + timeout
        last = time.monotonic()
        n = 0
        while time.monotonic() < end:
            time.sleep(0.2)
            if len(self.params) != n:
                n, last = len(self.params), time.monotonic()
            if self._param_count and n >= self._param_count:
                break
            if n and time.monotonic() - last > 2:
                break
        return dict(self.params)

    def set_param(self, name: str, value: float) -> None:
        if self._s["armed"]:
            raise NotAllowedWhileArmed("parameter writes are disarmed only")
        mark = self._mark()
        for _ in range(self.retries):
            self._send("param_set_send", self.ts, self.tc, name.encode(),
                       float(value), mav.MAV_PARAM_TYPE_REAL32)
            m = self._wait(lambda m: m.get_type() == "PARAM_VALUE"
                           and m.param_id == name, self.cmd_timeout,
                           since=mark)
            if m and abs(m.param_value - value) < 1e-4 * max(1, abs(value)):
                return
        raise NoResponse(f"PARAM_SET {name} not confirmed")

    def set_param_sim(self, name: str, value: float) -> None:
        """Simulation only: SIM_* and fault-injection writes are allowed
        while armed (the real helm has no SIM_* parameters)."""
        mark = self._mark()
        self._send("param_set_send", self.ts, self.tc, name.encode(),
                   float(value), mav.MAV_PARAM_TYPE_REAL32)
        self._wait(lambda m: m.get_type() == "PARAM_VALUE"
                   and m.param_id == name, self.cmd_timeout, since=mark)

    # ------------------------------------------------------------------
    # Mission and fence transfer (MAVLink mission protocol)

    def _item_int(self, seq, frame, cmd, p, lat, lon, alt, mtype):
        return (self.ts, self.tc, seq, frame, cmd, 0, 1, p[0], p[1], p[2],
                p[3], int(round(lat * 1e7)), int(round(lon * 1e7)), alt,
                mtype)

    def _upload(self, items: list[tuple], mtype: int) -> None:
        mark = self._mark()
        self._send("mission_count_send", self.ts, self.tc, len(items), mtype)
        sent_any = False
        while True:
            r = self._wait_n(lambda m: m.get_type() in (
                "MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK")
                and getattr(m, "mission_type", 0) == mtype,
                self.cmd_timeout * 2, since=mark)
            m = r[1] if r else None
            if r:
                mark = r[0]
            if m is None:
                if not sent_any:
                    raise TransferFailed("no response to MISSION_COUNT")
                raise TransferFailed("transfer stalled")
            if m.get_type() == "MISSION_ACK":
                if m.type == mav.MAV_MISSION_ACCEPTED:
                    return
                raise TransferFailed(mav.enums["MAV_MISSION_RESULT"]
                                     [m.type].name)
            if m.seq >= len(items):
                raise TransferFailed(f"helm asked for item {m.seq}")
            self._send("mission_item_int_send", *items[m.seq])
            sent_any = True

    def _download(self, mtype: int) -> list:
        mark = self._mark()
        self._send("mission_request_list_send", self.ts, self.tc, mtype)
        c = self._wait(lambda m: m.get_type() == "MISSION_COUNT"
                       and getattr(m, "mission_type", 0) == mtype,
                       self.cmd_timeout * 2, since=mark)
        if c is None:
            raise TransferFailed("no MISSION_COUNT")
        out = []
        for seq in range(c.count):
            for _ in range(self.retries):
                mark = self._mark()
                self._send("mission_request_int_send", self.ts, self.tc, seq,
                           mtype)
                it = self._wait(lambda m: m.get_type() == "MISSION_ITEM_INT"
                                and m.seq == seq
                                and getattr(m, "mission_type", 0) == mtype,
                                self.cmd_timeout, since=mark)
                if it:
                    out.append(it)
                    break
            else:
                raise TransferFailed(f"item {seq} not received")
        self._send("mission_ack_send", self.ts, self.tc,
                   mav.MAV_MISSION_ACCEPTED, mtype)
        return out

    def upload_fence(self, fence: Fence) -> None:
        if self._s["armed"]:
            raise NotAllowedWhileArmed("fence upload is disarmed only")
        items, g = [], mav.MAV_FRAME_GLOBAL
        n = len(fence.inclusion)
        for lat, lon in fence.inclusion:
            items.append((F_INCL, [n, 0, 0, 0], lat, lon))
        for poly in fence.exclusions:
            for lat, lon in poly:
                items.append((F_EXCL, [len(poly), 0, 0, 0], lat, lon))
        for lat, lon, r in fence.exclusion_circles:
            items.append((F_CIRC_EXCL, [r, 0, 0, 0], lat, lon))
        packed = [self._item_int(i, g, c, p, la, lo, 0, FENCE)
                  for i, (c, p, la, lo) in enumerate(items)]
        self._upload(packed, FENCE)
        self._command(mav.MAV_CMD_DO_FENCE_ENABLE, [1])

    def upload_mission(self, m: Mission) -> None:
        if self._s["armed"]:
            raise NotAllowedWhileArmed("mission upload is disarmed only")
        home = self._s["home"] or (0.0, 0.0)
        rows = [self._item_int(0, mav.MAV_FRAME_GLOBAL, 16, [0, 0, 0, 0],
                               home[0], home[1], 0, MISSION)]
        for i, it in enumerate(m.items, 1):
            rows.append(self._item_int(i, it.frame, it.command, it.params,
                                       it.lat, it.lon, it.alt, MISSION))
        self._upload(rows, MISSION)

    def read_back(self) -> tuple[Fence, list[MissionItem]]:
        f_items = self._download(FENCE)
        incl, excl, circ = [], [], []
        i = 0
        while i < len(f_items):
            it = f_items[i]
            if it.command in (F_INCL, F_EXCL):
                n = int(it.param1)
                poly = tuple((x.x / 1e7, x.y / 1e7) for x in f_items[i:i + n])
                (incl if it.command == F_INCL else excl).append(poly)
                i += max(1, n)
            else:
                if it.command == F_CIRC_EXCL:
                    circ.append((it.x / 1e7, it.y / 1e7, it.param1))
                i += 1
        fence = Fence(incl[0] if incl else (), tuple(excl), tuple(circ))
        m_items = self._download(MISSION)[1:]          # drop home slot
        mission = [MissionItem(x.command, x.x / 1e7, x.y / 1e7, x.z,
                               (x.param1, x.param2, x.param3, x.param4),
                               x.frame) for x in m_items]
        return fence, mission

    def verify(self, m: Mission) -> bool:
        """VAL-010: what the helm holds equals what we sent."""
        _, got = self.read_back()
        if len(got) != len(m.items):
            return False
        for a, b in zip(m.items, got):
            if a.command != b.command:
                return False
            if round(a.lat * 1e7) != round(b.lat * 1e7) or \
                    round(a.lon * 1e7) != round(b.lon * 1e7):
                return False
            if any(abs(x - y) > 1e-3 for x, y in zip(a.params, b.params)):
                return False
        return True
