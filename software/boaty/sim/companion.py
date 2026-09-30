"""A listener on the helm's companion port (IF-04), where the mission computer
sits. Tests use it to timestamp the helm's mode changes in simulated time,
including while the bank link (IF-01) is cut, and to send heartbeats as the
mission computer (system 1, component 191) or as an impostor.
"""
from __future__ import annotations

import threading

from pymavlink import mavutil

mav = mavutil.mavlink


class CompanionPort:
    def __init__(self, clock, port: int = 14560, sysid: int = 1,
                 compid: int = mav.MAV_COMP_ID_ONBOARD_COMPUTER,
                 time_scale: float = 1.0):
        self.clock = clock                      # callable -> sim seconds
        # A client of the B1 router's local endpoint, like any service.
        self.conn = mavutil.mavlink_connection(
            f"udpout:127.0.0.1:{port}", source_system=sysid,
            source_component=compid, dialect="ardupilotmega")
        self.conn.mav.heartbeat_send(mav.MAV_TYPE_ONBOARD_CONTROLLER,
                                     mav.MAV_AUTOPILOT_INVALID, 0, 0,
                                     mav.MAV_STATE_ACTIVE)   # register
        self.time_scale = time_scale
        self.modes: list[tuple[float, bool, int]] = []   # (t, armed, mode)
        self.texts: list[tuple[float, str]] = []
        self.heartbeat_as: tuple[int, int] | None = None
        self._stop = threading.Event()
        self._threads = [threading.Thread(target=self._rx, daemon=True),
                         threading.Thread(target=self._tx, daemon=True)]
        for t in self._threads:
            t.start()

    def close(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=1)
        self.conn.close()

    def _rx(self) -> None:
        while not self._stop.is_set():
            m = self.conn.recv_match(blocking=True, timeout=0.1)
            if m is None or m.get_srcSystem() != 1:
                continue
            t = m.get_type()
            if t == "STATUSTEXT":             # helm (1) and services (191)
                self.texts.append((self.clock(), m.text))
                continue
            if m.get_srcComponent() != 1:
                continue
            if t == "HEARTBEAT":
                armed = bool(m.base_mode & mav.MAV_MODE_FLAG_SAFETY_ARMED)
                cur = (armed, m.custom_mode)
                if not self.modes or self.modes[-1][1:] != cur:
                    self.modes.append((self.clock(), *cur))

    def _tx(self) -> None:
        while not self._stop.is_set():
            if self.heartbeat_as is not None or not self.modes:
                sysid, compid = self.heartbeat_as or (1, 191)
                self.conn.mav.srcSystem, self.conn.mav.srcComponent = \
                    sysid, compid
                kind = mav.MAV_TYPE_GCS if sysid == 255 else \
                    mav.MAV_TYPE_ONBOARD_CONTROLLER
                try:
                    self.conn.mav.heartbeat_send(kind, mav.MAV_AUTOPILOT_INVALID,
                                                 0, 0, mav.MAV_STATE_ACTIVE)
                except OSError:
                    pass
            self._stop.wait(1.0 / self.time_scale)

    # ------------------------------------------------------------------
    def mode_at(self, t: float) -> tuple[bool, int] | None:
        cur = None
        for tm, armed, mode in self.modes:
            if tm <= t:
                cur = (armed, mode)
        return cur

    def first_mode_after(self, t: float, mode: int) -> float | None:
        for tm, _, m in self.modes:
            if tm >= t and m == mode:
                return tm
        return None

    def texts_after(self, t: float) -> list[str]:
        return [x for tm, x in self.texts if tm >= t]
