"""What boat-side services may send to the helm (ICD IF-04, MCP-D19).

Every MAVLink message a service sends passes through `Filter.check`. The
filter is default-deny: anything not explicitly allowed for that service is
refused, logged and never sent. It is a guard against bugs in our own
services (SAF-003), independent of the service logic it guards.

Always forbidden for every service: arming or disarming, parameter writes,
fence or mission uploads, AUTO / MANUAL / STEERING (except B5 resuming the
exact mode it interrupted), manual control and RC overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pymavlink import mavutil

mav = mavutil.mavlink

HOLD, LOITER, AUTO, RTL, GUIDED = 4, 5, 10, 11, 15

# Commands any service may send.
COMMON_COMMANDS = {mav.MAV_CMD_SET_MESSAGE_INTERVAL,
                   mav.MAV_CMD_REQUEST_MESSAGE}
# Messages any service may send (read-only protocol traffic and events).
COMMON_MESSAGES = {"HEARTBEAT", "STATUSTEXT", "MISSION_REQUEST_LIST",
                   "MISSION_REQUEST_INT", "MISSION_ACK"}

# SET_ATTITUDE_TARGET: ignore roll rate (1), pitch rate (2) and the attitude
# quaternion (128); use thrust and body yaw rate.
ASTERN_MASK = 1 | 2 | 128


@dataclass
class ServicePolicy:
    modes: frozenset = frozenset()        # DO_SET_MODE targets allowed
    velocity: bool = False                # B5 astern bursts
    change_speed: bool = False            # B6 reduced RTL speed
    max_astern: float = 0.5               # m/s (MCP-D18)
    max_speed: float = 1.0                # m/s, never above WP_SPEED


POLICIES = {
    "B2": ServicePolicy(),
    "B3": ServicePolicy(),
    "B4": ServicePolicy(modes=frozenset({RTL})),
    "B5": ServicePolicy(modes=frozenset({GUIDED, HOLD}), velocity=True),
    "B6": ServicePolicy(modes=frozenset({RTL, HOLD}), change_speed=True),
    "B7": ServicePolicy(modes=frozenset({HOLD})),
    "TEST": ServicePolicy(),              # observers in tests: read only
}


@dataclass
class Filter:
    service: str
    policy: ServicePolicy | None = None     # default: POLICIES[service]
    resume_mode: int | None = None        # set by B5 while shedding
    refused: list = field(default_factory=list)

    def __post_init__(self):
        if self.policy is None:
            self.policy = POLICIES[self.service]

    def grant_resume(self, mode: int | None) -> None:
        """B5 may return the helm to the mode it interrupted: AUTO or RTL
        only, and only that one mode."""
        self.resume_mode = mode if mode in (AUTO, RTL) else None

    def check(self, msg, helm_mode: int | None = None) -> tuple[bool, str]:
        t = msg.get_type()
        p = self.policy if self.policy is not None else \
            POLICIES[self.service]
        if t in COMMON_MESSAGES:
            if t in ("MISSION_REQUEST_INT", "MISSION_REQUEST_LIST",
                     "MISSION_ACK"):
                return True, "read-only mission protocol"
            return True, "common"
        if t == "COMMAND_LONG":
            cmd = msg.command
            if cmd in COMMON_COMMANDS:
                return True, "stream request"
            if cmd == mav.MAV_CMD_DO_SET_MODE:
                target = int(msg.param2)
                if int(msg.param1) & mav.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED \
                        == 0:
                    return False, "mode change without custom mode"
                if target in p.modes:
                    return True, f"mode {target} allowed"
                if self.resume_mode is not None and target == self.resume_mode:
                    return True, f"resume to {target}"
                return False, f"mode {target} not allowed for {self.service}"
            if cmd == mav.MAV_CMD_DO_CHANGE_SPEED:
                if p.change_speed and 0 < msg.param2 <= p.max_speed and \
                        helm_mode == RTL:
                    return True, "reduced RTL speed"
                return False, "speed change not allowed"
            return False, f"command {cmd} forbidden"
        if t == "SET_ATTITUDE_TARGET":
            # B5 astern burst. Rover maps thrust to speed (x WP_SPEED) and
            # body_yaw_rate to turn rate, so thrust -0.5 with zero yaw rate
            # is a straight reverse at 0.5 m/s. (A negative body-frame
            # velocity target would make Rover turn round and drive
            # forwards - Rover 4.7.1 GCS_MAVLink_Rover.cpp.)
            if not p.velocity:
                return False, "astern bursts not allowed"
            if helm_mode != GUIDED:
                return False, "astern bursts only in GUIDED"
            if msg.type_mask != ASTERN_MASK:
                return False, "thrust + yaw rate only"
            if not (-p.max_astern <= msg.thrust <= 0.0) or \
                    msg.body_yaw_rate != 0.0:
                return False, "straight astern only, <= 0.5 m/s"
            return True, "astern burst"
        return False, f"{t} forbidden"
