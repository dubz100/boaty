"""What a boat service knows about the helm, built from MAVLink telemetry.

Times are in the service clock (simulated seconds in simulation).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from pymavlink import mavutil

mav = mavutil.mavlink
EKF_NEEDED = (mav.EKF_ATTITUDE | mav.EKF_VELOCITY_HORIZ
              | mav.EKF_POS_HORIZ_ABS)


@dataclass
class HelmView:
    armed: bool = False
    mode: int | None = None
    mode_since: float = 0.0
    modes: list = field(default_factory=list)      # (t, armed, mode)
    lat: float | None = None
    lon: float | None = None
    pos_t: float = -1e9
    heading: float | None = None                   # deg, EKF yaw
    vn: float = 0.0
    ve: float = 0.0
    fix: int = 0
    hdop: float = 99.9
    ekf_ok: bool = False
    throttle: float = 0.0                          # % (VFR_HUD)
    xtrack: float = 0.0                            # m (NAV_CONTROLLER_OUTPUT)
    target_bearing: float | None = None            # deg
    wp_dist: float = 0.0
    mission_seq: int | None = None
    battery_pct: float = 100.0
    battery_crit_t: float | None = None
    breached: bool = False
    breach_since: float | None = None
    home: tuple | None = None                      # (lat, lon)
    mc_heartbeat_t: float | None = None            # system 255
    helm_heartbeat_t: float | None = None
    reached: list = field(default_factory=list)    # (t, seq)
    texts: list = field(default_factory=list)      # (t, comp, text)

    # ------------------------------------------------------------------
    @property
    def groundspeed(self) -> float:
        return math.hypot(self.vn, self.ve)

    @property
    def course(self) -> float | None:
        if self.groundspeed < 0.05:
            return None
        return math.degrees(math.atan2(self.ve, self.vn)) % 360

    def mode_at(self, t: float) -> tuple[bool, int] | None:
        cur = None
        for tm, armed, m in self.modes:
            if tm > t:
                break
            cur = (armed, m)
        return cur

    def mode_before(self, t: float) -> int | None:
        """The armed mode the helm was in just before time t."""
        prev = None
        for tm, armed, m in self.modes:
            if tm >= t:
                break
            prev = m if armed else None
        return prev

    def update(self, msg, now: float) -> None:
        t = msg.get_type()
        src, comp = msg.get_srcSystem(), msg.get_srcComponent()
        if t == "HEARTBEAT":
            if src == 255:
                self.mc_heartbeat_t = now
                return
            if src != 1 or comp != 1:
                return
            self.helm_heartbeat_t = now
            armed = bool(msg.base_mode & mav.MAV_MODE_FLAG_SAFETY_ARMED)
            if (armed, msg.custom_mode) != (self.armed, self.mode):
                self.modes.append((now, armed, msg.custom_mode))
                if msg.custom_mode != self.mode:
                    self.mode_since = now
            self.armed, self.mode = armed, msg.custom_mode
            return
        if src != 1:
            return
        if t == "STATUSTEXT":
            self.texts.append((now, comp, msg.text))
            if comp == 1 and "ritical" in msg.text and "attery" in msg.text:
                self.battery_crit_t = now
            return
        if comp != 1:
            return
        if t == "GLOBAL_POSITION_INT":
            self.lat, self.lon, self.pos_t = msg.lat / 1e7, msg.lon / 1e7, now
            self.heading = None if msg.hdg == 65535 else msg.hdg / 100
            self.vn, self.ve = msg.vx / 100, msg.vy / 100
        elif t == "GPS_RAW_INT":
            self.fix = msg.fix_type
            self.hdop = msg.eph / 100 if msg.eph != 65535 else 99.9
        elif t == "EKF_STATUS_REPORT":
            self.ekf_ok = (msg.flags & EKF_NEEDED) == EKF_NEEDED
        elif t == "VFR_HUD":
            self.throttle = float(msg.throttle)
        elif t == "NAV_CONTROLLER_OUTPUT":
            self.xtrack = msg.xtrack_error
            self.target_bearing = msg.target_bearing % 360
            self.wp_dist = msg.wp_dist
        elif t == "MISSION_CURRENT":
            self.mission_seq = msg.seq
        elif t == "HOME_POSITION":
            self.home = (msg.latitude / 1e7, msg.longitude / 1e7)
        elif t == "MISSION_ITEM_REACHED":
            self.reached.append((now, msg.seq))
        elif t == "BATTERY_STATUS" and msg.id == 0:
            self.battery_pct = max(0, msg.battery_remaining)
        elif t == "FENCE_STATUS":
            b = bool(msg.breach_status)
            if b and not self.breached:
                self.breach_since = now
            if not b:
                self.breach_since = None
            self.breached = b

    def position_healthy(self, max_hdop: float = 2.5) -> bool:
        """FS-004: 3D fix, HDOP within limit and the EKF healthy."""
        return self.fix >= 3 and self.hdop <= max_hdop and self.ekf_ok
