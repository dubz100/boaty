"""The boat-service event vocabulary (ICD IF-04, SDR RID-05).

Boat services B4-B7 report what they do as MAVLink STATUSTEXTs from
component 191, "BOATY " followed by one of the texts below. Mission Control
(MCN-D60) and B5 read them back, so this module is the single definition:
the services send only these, Mission Control classifies with match(), and
the ICD's IF-04 event table is generated from EVENTS.

Texts may carry {fields}. A STATUSTEXT holds 50 characters, prefix
included; a unit test checks every event fits.

`mc` is how Mission Control treats an event:
    held     the boat has stopped itself: show and speak the reason, and
             resuming needs the adult PIN (MCN-D60)
    shed     B5 weed-shedding started or ended (spoken once per episode)
    alert    show to the adult; no mode change from Mission Control
    info     log only (the helm's own mode change, if any, is announced
             separately)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PREFIX = "BOATY "
MAX_LEN = 50


@dataclass(frozen=True)
class Event:
    text: str           # after the prefix; may contain {fields}
    service: str
    severity: str       # "warning" or "critical"
    action: str         # what the service asks the helm for
    mc: str             # held | shed | alert | info
    meaning: str
    refs: tuple[str, ...]
    example: dict | None = None     # field values for tests and the ICD

    def format(self, **kw) -> str:
        return self.text.format(**kw)

    @property
    def pattern(self) -> re.Pattern:
        parts = re.split(r"\{\w+\}", self.text)
        body = ".+?".join(re.escape(p) for p in parts)
        return re.compile("^" + body + "$")


def _e(name, *a, **kw) -> Event:
    ev = Event(*a, **kw)
    globals()[name] = ev
    return ev


EVENTS: list[Event] = [
    # B4 link watchdog
    _e("B4_LINK_LOST_AUTO", "B4 LINK LOST 60S: RTL", "B4", "warning", "RTL",
       "info", "No Mission Control heartbeat for 60 s in AUTO", ("FS-003",
                                                                  "MCP-D12")),
    _e("B4_LINK_LOST_MANUAL", "B4 LINK LOST IN MANUAL: RTL", "B4",
       "warning", "RTL", "info", "Link lost while an adult was driving; "
       "RTL 10 s after the helm's own HOLD", ("FS-002", "MCP-D12")),
    # B5 weed-shedding
    _e("B5_SHED_START", "B5 SHED START", "B5", "warning", "GUIDED astern "
       "bursts", "shed", "Stuck: starting up to 3 astern bursts",
       ("FS-006", "MCP-D18")),
    _e("B5_SHED_END", "B5 SHED END", "B5", "warning", "none", "shed",
       "The shedding episode is over (either way)", ("FS-006",)),
    _e("B5_FREE", "B5 FREE AFTER {burst}: RESUMED", "B5", "warning",
       "resume AUTO/RTL", "info", "Moving forward again after the burst",
       ("FS-006", "MCP-D34"), {"burst": 2}),
    _e("B5_STILL_STUCK", "B5 STILL STUCK: HOLD", "B5", "critical", "HOLD",
       "held", "Three bursts did not free it", ("FS-006", "MCP-D18")),
    _e("B5_REPEATEDLY_STUCK", "B5 REPEATEDLY STUCK: HOLD", "B5", "critical",
       "HOLD", "held", "More than 3 episodes in 2 min (a dead motor looks "
       "like weed)", ("MCP-D34", "FM-58")),
    _e("B5_NO_CONTROL", "B5 NO CONTROL ({why}): HOLD", "B5", "critical",
       "HOLD", "held", "The GUIDED switch was refused or not confirmed",
       ("MCP-D34",), {"why": "refused"}),
    _e("B5_STUCK_NOT_AUTO", "B5 STUCK: HOLD", "B5", "critical", "HOLD",
       "held", "Stuck outside AUTO/RTL: no bursts, hold", ("FS-005",)),
    # B6 health
    _e("B6_POSITION_LOST", "B6 POSITION LOST: HOLD", "B6", "warning",
       "HOLD", "held", "No fix, HDOP > 2.5 or EKF unhealthy for 1 s",
       ("FS-004", "MCP-D15")),
    _e("B6_POSITION_LOST_HELD", "B6 POSITION LOST", "B6", "warning", "none "
       "(already HOLD)", "alert", "Position lost while already holding",
       ("FS-004",)),
    _e("B6_POSITION_OK", "B6 POSITION OK: RTL", "B6", "warning", "RTL",
       "info", "Position healthy for 10 s after a loss", ("FS-004",)),
    _e("B6_POSITION_JUMP", "B6 POSITION JUMP: HOLD", "B6", "critical",
       "HOLD (latched)", "held", "The position jumped further than the "
       "boat could move", ("MCP-D35", "FM-02", "SC-20")),
    _e("B6_POSITION_JUMP_HELD", "B6 POSITION JUMP", "B6", "critical",
       "none (already HOLD)", "alert", "Position jump while already "
       "holding", ("MCP-D35",)),
    _e("B6_WATER", "B6 WATER IN BOX: RTL", "B6", "critical", "RTL", "info",
       "Moisture sensor tripped", ("FS-010", "MCP-D26")),
    _e("B6_WATER_NO_RTL", "B6 WATER IN BOX", "B6", "critical", "none",
       "alert", "Moisture, but RTL not possible (position bad or already "
       "RTL): FS-011", ("FS-010", "FS-011")),
    _e("B6_BOX_HOT", "B6 BOX HOT: RTL", "B6", "critical", "RTL", "info",
       "Box over 60 °C", ("A-11", "MCP-D26")),
    _e("B6_BOX_HOT_NO_RTL", "B6 BOX HOT", "B6", "critical", "none", "alert",
       "Box hot, but RTL not possible", ("A-11", "FS-011")),
    _e("B6_CRITICAL_BATTERY", "B6 CRITICAL BATTERY: SLOW RTL", "B6",
       "critical", "RTL speed 0.6 m/s", "alert", "Battery at 15% during "
       "RTL", ("FS-001",)),
    # B7 navigation monitor (only ever HOLD)
    _e("B7_OUTSIDE_30S", "B7 OUTSIDE FENCE 30S: HOLD", "B7", "warning",
       "HOLD", "held", "Outside the fence for 30 s", ("FEN-006", "MCP-D30")),
    _e("B7_FAR_OUTSIDE", "B7 FAR OUTSIDE FENCE: HOLD", "B7", "warning",
       "HOLD", "held", "More than 8 m outside the fence", ("FEN-006",
                                                           "MCP-D30")),
    _e("B7_HEADING", "B7 HEADING CHECK FAILED: HOLD", "B7", "warning",
       "HOLD", "held", "First motion: course and heading disagree > 45°",
       ("MCP-D22", "A-03")),
    _e("B7_STUCK", "B7 STUCK", "B7", "warning", "HOLD (B5 then sheds)",
       "held", "Throttle ≥ 50% and no progress for 10 s", ("MCP-D23",
                                                           "A-07")),
    _e("B7_OFF_COURSE", "B7 OFF COURSE: HOLD", "B7", "warning", "HOLD",
       "held", "Cross-track > 10 m or heading error > 60° for 20 s",
       ("MCP-D24", "A-08")),
]


def match(text: str) -> Event | None:
    """The event a STATUSTEXT carries (prefix optional), or None."""
    body = text[len(PREFIX):] if text.startswith(PREFIX) else text
    body = body.strip()
    for ev in EVENTS:
        if ev.pattern.match(body):
            return ev
    return None


def is_event(text: str, ev: Event) -> bool:
    return match(text) is ev
