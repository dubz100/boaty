"""The shared MAVLink client every boat service uses (MCP-D19).

Each service owns one client: a UDP connection to B1's local endpoint as
system 1, component 191 (ONBOARD_COMPUTER). Everything it sends goes through
the service's Filter; refused messages are logged and dropped. A rejected
command is retried at most twice (IF-04).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from pymavlink import mavutil

from .clock import Clock, SystemClock
from .policy import ASTERN_MASK, Filter
from .view import HelmView

log = logging.getLogger(__name__)
mav = mavutil.mavlink

# Telemetry services need, in Hz (requested on the helm's companion channel).
STREAMS = {33: 4, 24: 2, 193: 1, 74: 4, 62: 2, 42: 1, 147: 1, 162: 1}
EVENT_PREFIX = "BOATY "


class ServiceClient:
    def __init__(self, service: str, url: str = "udpout:127.0.0.1:14560",
                 clock: Clock | None = None, sysid: int = 1,
                 compid: int = mav.MAV_COMP_ID_ONBOARD_COMPUTER):
        self.service = service
        self.clock = clock or SystemClock()
        self.filter = Filter(service)
        self.view = HelmView()
        self.conn = mavutil.mavlink_connection(
            url, source_system=sysid, source_component=compid,
            dialect="ardupilotmega")
        self._send_lock = threading.Lock()
        self._listeners: list[Callable] = []
        self._acks: list = []
        self._cv = threading.Condition()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self.sent: list = []            # (t, type, detail) of allowed sends

    # ------------------------------------------------------------------
    def start(self, request_streams: bool = True) -> "ServiceClient":
        self._heartbeat()                        # register with the router
        for fn, name in ((self._rx, "rx"), (self._hb_loop, "hb")):
            th = threading.Thread(target=fn, name=f"{self.service}-{name}",
                                  daemon=True)
            th.start()
            self._threads.append(th)
        if request_streams:
            for msg_id, hz in STREAMS.items():
                self.command(mav.MAV_CMD_SET_MESSAGE_INTERVAL,
                             [msg_id, 1e6 / hz], wait=False)
        return self

    def stop(self) -> None:
        self._stop.set()
        for th in self._threads:
            th.join(timeout=1)
        self.conn.close()

    def on_message(self, cb: Callable) -> None:
        self._listeners.append(cb)

    # ------------------------------------------------------------------
    def _heartbeat(self) -> None:
        with self._send_lock:
            self.conn.mav.heartbeat_send(mav.MAV_TYPE_ONBOARD_CONTROLLER,
                                         mav.MAV_AUTOPILOT_INVALID, 0, 0,
                                         mav.MAV_STATE_ACTIVE)

    def _hb_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._heartbeat()
            except OSError:
                pass
            self.clock.sleep(1.0)

    def _rx(self) -> None:
        while not self._stop.is_set():
            try:
                m = self.conn.recv_match(blocking=True, timeout=0.1)
            except (OSError, ValueError):
                continue
            if m is None or m.get_type() == "BAD_DATA":
                continue
            now = self.clock.now()
            self.view.update(m, now)
            if m.get_type() == "COMMAND_ACK":
                with self._cv:
                    self._acks.append(m)
                    self._cv.notify_all()
            for cb in list(self._listeners):
                try:
                    cb(m, now)
                except Exception:  # noqa: BLE001
                    log.exception("%s listener", self.service)

    # ------------------------------------------------------------------
    def send(self, msg) -> bool:
        """Send a MAVLink message if the filter allows it."""
        ok, why = self.filter.check(msg, self.view.mode)
        if not ok:
            self.filter.refused.append((self.clock.now(), msg.get_type(),
                                        why))
            log.warning("%s refused %s: %s", self.service, msg.get_type(),
                        why)
            return False
        with self._send_lock:
            self.conn.mav.send(msg)
        self.sent.append((self.clock.now(), msg.get_type(), why))
        return True

    def command(self, cmd: int, params: list[float], wait: bool = True,
                timeout: float = 1.5) -> bool:
        p = (list(params) + [0.0] * 7)[:7]
        for attempt in range(3):                 # first try + 2 retries
            with self._cv:
                self._acks.clear()
            msg = self.conn.mav.command_long_encode(1, 1, cmd, attempt, *p)
            if not self.send(msg):
                return False
            if not wait:
                return True
            end = self.clock.now() + timeout
            while self.clock.now() < end:
                with self._cv:
                    for a in self._acks:
                        if a.command == cmd and a.target_component in (0, 191):
                            return a.result == mav.MAV_RESULT_ACCEPTED
                self.clock.sleep(0.02)
        log.warning("%s: no ACK for command %s", self.service, cmd)
        return False

    def set_mode(self, mode: int) -> bool:
        return self.command(mav.MAV_CMD_DO_SET_MODE,
                            [mav.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode])

    def change_speed(self, speed: float) -> bool:
        return self.command(mav.MAV_CMD_DO_CHANGE_SPEED, [1, speed, -1])

    def astern(self, speed_fraction: float) -> bool:
        """B5: straight astern at speed_fraction x WP_SPEED (0..0.5)."""
        msg = self.conn.mav.set_attitude_target_encode(
            0, 1, 1, ASTERN_MASK, [1, 0, 0, 0], 0, 0, 0,
            -abs(speed_fraction))
        return self.send(msg)

    def request_home(self) -> bool:
        return self.command(mav.MAV_CMD_REQUEST_MESSAGE,
                            [mav.MAVLINK_MSG_ID_HOME_POSITION], wait=False)

    def download(self, mission_type: int, timeout: float = 2.0) -> list:
        """Read the helm's mission (0) or fence (1). Read-only protocol."""
        got: dict = {}
        count = [None]

        def listen(m, now):
            if getattr(m, "mission_type", 0) != mission_type or \
                    getattr(m, "target_system", 1) != 1 or \
                    getattr(m, "target_component", 191) not in (0, 191):
                return
            if m.get_type() == "MISSION_COUNT":
                count[0] = m.count
            elif m.get_type() == "MISSION_ITEM_INT":
                got[m.seq] = m
        self.on_message(listen)
        try:
            self.send(self.conn.mav.mission_request_list_encode(
                1, 1, mission_type))
            end = self.clock.now() + timeout
            while count[0] is None and self.clock.now() < end:
                self.clock.sleep(0.02)
            if count[0] is None:
                return []
            for seq in range(count[0]):
                for _ in range(3):
                    self.send(self.conn.mav.mission_request_int_encode(
                        1, 1, seq, mission_type))
                    end = self.clock.now() + timeout / 2
                    while seq not in got and self.clock.now() < end:
                        self.clock.sleep(0.02)
                    if seq in got:
                        break
                else:
                    return []
            self.send(self.conn.mav.mission_ack_encode(
                1, 1, mav.MAV_MISSION_ACCEPTED, mission_type))
            return [got[i] for i in range(count[0])]
        finally:
            self._listeners.remove(listen)

    def event(self, text: str, severity: int = mav.MAV_SEVERITY_WARNING):
        """Alarm/event for Mission Control and the other services."""
        body = (EVENT_PREFIX + text)[:50]
        return self.send(self.conn.mav.statustext_encode(severity,
                                                         body.encode()))
