"""Helm API (ICD IF-14): the only way Mission Control commands a helm.

Mk1 has one implementation, ArduPilotHelm (pymavlink over IF-02). The contract
test suite in tests/sitl/ is the acceptance test for any helm implementation.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol


class SrsMode(enum.Enum):
    """Modes as the SRS names them (SRS section on modes)."""
    DISARMED = "DISARMED"
    HOLD = "HOLD"
    MANUAL = "MANUAL"
    AUTO = "AUTO"
    RTL = "RTL"
    UNKNOWN = "UNKNOWN"


# ArduPilot Rover custom_mode numbers (IF-02 mode table).
class RoverMode(enum.IntEnum):
    MANUAL = 0
    ACRO = 1
    STEERING = 3
    HOLD = 4
    LOITER = 5
    FOLLOW = 6
    SIMPLE = 7
    DOCK = 8
    CIRCLE = 9
    AUTO = 10
    RTL = 11
    SMART_RTL = 12
    GUIDED = 15
    INITIALISING = 16


def srs_mode(armed: bool, mode: int | None) -> SrsMode:
    """IF-02 mapping. GUIDED only appears during weed-shedding and is shown
    as HOLD; LOITER is HOLD with station-keeping."""
    if not armed:
        return SrsMode.DISARMED
    return {
        RoverMode.STEERING: SrsMode.MANUAL,
        RoverMode.MANUAL: SrsMode.MANUAL,
        RoverMode.HOLD: SrsMode.HOLD,
        RoverMode.LOITER: SrsMode.HOLD,
        RoverMode.GUIDED: SrsMode.HOLD,
        RoverMode.AUTO: SrsMode.AUTO,
        RoverMode.RTL: SrsMode.RTL,
        RoverMode.SMART_RTL: SrsMode.RTL,
    }.get(mode, SrsMode.UNKNOWN)


# ---------------------------------------------------------------------------
# Data


LatLon = tuple[float, float]


@dataclass(frozen=True)
class Fence:
    """One inclusion polygon, exclusion polygons and exclusion circles
    (IF-15 site roles fence_inclusion and exclusion)."""
    inclusion: tuple[LatLon, ...]
    exclusions: tuple[tuple[LatLon, ...], ...] = ()
    exclusion_circles: tuple[tuple[float, float, float], ...] = ()  # lat, lon, r


@dataclass(frozen=True)
class MissionItem:
    command: int                # MAV_CMD
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0
    params: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    frame: int = 3              # MAV_FRAME_GLOBAL_RELATIVE_ALT

    @staticmethod
    def waypoint(lat: float, lon: float, hold_s: float = 0.0) -> "MissionItem":
        return MissionItem(16, lat, lon, 0.0, (hold_s, 0.0, 0.0, 0.0))


@dataclass(frozen=True)
class Mission:
    """Items after the home slot. ArduPilot's item 0 is home and is handled
    by the helm implementation, not by callers."""
    items: tuple[MissionItem, ...]


@dataclass(frozen=True)
class HelmStatus:
    t_utc: datetime
    link_ok: bool
    armed: bool
    mode: SrsMode
    lat: float | None
    lon: float | None
    heading_deg: float | None
    speed_mps: float
    battery_pct: float
    battery_v: float
    rail_v: float
    gps_fix: int
    sats: int
    hdop: float
    ekf_ok: bool
    fence_breached: bool
    mission_seq: int | None
    mission_total: int | None
    ardupilot_mode: int | None = None


# ---------------------------------------------------------------------------
# Events


@dataclass(frozen=True)
class HelmEvent:
    t_utc: datetime


@dataclass(frozen=True)
class ModeChanged(HelmEvent):
    old: SrsMode
    new: SrsMode
    ardupilot_mode: int | None = None


@dataclass(frozen=True)
class FailsafeEvent(HelmEvent):
    text: str


@dataclass(frozen=True)
class ArrivedHome(HelmEvent):
    pass


@dataclass(frozen=True)
class Breach(HelmEvent):
    count: int


@dataclass(frozen=True)
class Text(HelmEvent):
    severity: int
    text: str


@dataclass(frozen=True)
class LinkChange(HelmEvent):
    ok: bool


# ---------------------------------------------------------------------------
# Errors


class HelmError(Exception):
    pass


class NoResponse(HelmError):
    pass


class CommandRejected(HelmError):
    def __init__(self, code: int, text: str = ""):
        super().__init__(f"rejected ({code}) {text}".strip())
        self.code, self.text = code, text


class PreArmFailed(HelmError):
    def __init__(self, reasons: list[str]):
        super().__init__("; ".join(reasons) or "pre-arm checks failed")
        self.reasons = reasons


class NotAllowedWhileArmed(HelmError):
    pass


class TransferFailed(HelmError):
    pass


# ---------------------------------------------------------------------------


class Helm(Protocol):
    def connect(self, timeout_s: float = 10) -> None: ...
    def close(self) -> None: ...
    def status(self) -> HelmStatus: ...
    def subscribe(self, cb: Callable[[HelmEvent], None]) -> None: ...

    def upload_fence(self, fence: Fence) -> None: ...
    def upload_mission(self, m: Mission) -> None: ...
    def read_back(self) -> tuple[Fence, list[MissionItem]]: ...
    def verify(self, m: Mission) -> bool: ...

    def arm(self) -> None: ...
    def disarm(self, force: bool = False) -> None: ...
    def start_mission(self) -> None: ...
    def hold(self) -> None: ...
    def stop(self) -> None: ...
    def return_home(self) -> None: ...
    def manual(self) -> None: ...
    def drive(self, throttle: float, turn: float) -> None: ...
