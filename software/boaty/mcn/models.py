"""IF-13 software contracts as versioned pydantic models (MCN-D36).

    Intent v1            Claude API -> planner
    Mission v1           planner (or template, or map editor) -> validator
    ValidationResult v1  validator -> UI and log

The pydantic models check *shape* (types, enums, the ICD's ranges on the
fields that are pure schema). Safety limits such as speed, hold time, fence
clearance and duration are the validator's job, so a bad value reaches the
validator and comes back as a named VAL-xxx violation (VAL-007) instead of
an anonymous parse error.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..helm.api import MissionItem

INTENT_SCHEMA = "boaty.intent/1"
MISSION_SCHEMA = "boaty.mission/1"
VALIDATION_SCHEMA = "boaty.validation/1"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


# ---------------------------------------------------------------------------
# Intent v1


class Explore(_Strict):
    op: Literal["explore"]
    area: str
    coverage: Literal["light", "medium", "thorough"]


class Visit(_Strict):
    op: Literal["visit"]
    landmark: str
    photos: int = Field(ge=1, le=10)
    hold_s: int = Field(ge=5, le=60)


class PhotoStops(_Strict):
    op: Literal["photo_stops"]
    n: int = Field(ge=1, le=6)
    near: str | None


class Lap(_Strict):
    op: Literal["lap"]
    area: str


class ReturnHome(_Strict):
    op: Literal["return_home"]


Step = Annotated[Union[Explore, Visit, PhotoStops, Lap, ReturnHome],
                 Field(discriminator="op")]


class Declined(_Strict):
    reason_for_child: str = Field(max_length=200)


class Intent(_Strict):
    schema_: Literal["boaty.intent/1"] = Field(alias="schema")
    summary_for_child: str = Field(max_length=140)
    speed: Literal["slow", "normal"]
    steps: list[Step] = Field(max_length=8)
    declined: Declined | None

    model_config = ConfigDict(extra="forbid", populate_by_name=True,
                              allow_inf_nan=False)

    @model_validator(mode="after")
    def _steps_or_declined(self):
        if self.declined is not None:
            if self.steps:
                raise ValueError("a declined intent has no steps")
            return self
        if not self.steps:
            raise ValueError("an intent needs 1 to 8 steps, or declined")
        if self.steps[-1].op != "return_home":
            raise ValueError("return_home must be the last step")
        if any(s.op == "return_home" for s in self.steps[:-1]):
            raise ValueError("return_home may only be the last step")
        return self


# ---------------------------------------------------------------------------
# Mission v1


class LatLon(_Strict):
    lat: float
    lon: float


Kind = Literal["waypoint", "photo_point", "speed", "rtl"]


class Item(_Strict):
    seq: int = Field(ge=1)
    kind: Kind
    lat: float | None = None
    lon: float | None = None
    hold_s: int | None = None
    photos: int | None = None
    speed_mps: float | None = None


class Estimates(_Strict):
    distance_m: float
    duration_s: int
    energy_wh: float


class Capture(_Strict):
    interval_s: int = 0

    @model_validator(mode="after")
    def _interval(self):
        if self.interval_s != 0 and not 2 <= self.interval_s <= 30:
            raise ValueError("interval_s is 0 or 2..30")
        return self


class Mission(_Strict):
    schema_: Literal["boaty.mission/1"] = Field(alias="schema",
                                                default=MISSION_SCHEMA)
    id: str
    created_utc: str
    source: Literal["voice", "text", "template", "map"]
    site: str
    site_version: str
    home: LatLon
    cruise_mps: float = Field(ge=0.6, le=1.2)
    items: list[Item]
    estimates: Estimates
    capture: Capture = Capture()
    checksum: str
    summary_for_child: str = ""     # carried for the UI; not in the checksum

    model_config = ConfigDict(extra="forbid", populate_by_name=True,
                              allow_inf_nan=False)

    def to_json(self) -> dict:
        return self.model_dump(by_alias=True, mode="json")

    def with_checksum(self) -> "Mission":
        return self.model_copy(update={"checksum": checksum(self.items)})

    @property
    def photo_count(self) -> int:
        return sum(i.photos or 0 for i in self.items
                   if i.kind == "photo_point")


# ---------------------------------------------------------------------------
# ValidationResult v1


class Violation(_Strict):
    rule: str
    message_for_adult: str
    message_for_child: str
    item_seq: int | None = None
    at: LatLon | None = None


class ValidationResult(_Strict):
    schema_: Literal["boaty.validation/1"] = Field(alias="schema",
                                                   default=VALIDATION_SCHEMA)
    mission_id: str
    ok: bool
    violations: list[Violation]
    checked_utc: str
    validator_version: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True,
                              allow_inf_nan=False)


# ---------------------------------------------------------------------------
# Canonical form and checksum (IF-13)


def _canon(v, key: str):
    if v is None:
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return repr(v)            # only reachable by bypassing validation
    if key in ("lat", "lon"):
        return int(round(v * 1e7))
    if isinstance(v, float):
        return round(v, 2)
    return v


def canonical(items: list[Item]) -> str:
    rows = [{k: _canon(v, k) for k, v in it.model_dump().items()}
            for it in items]
    return json.dumps(rows, sort_keys=True, separators=(",", ":"))


def checksum(items: list[Item]) -> str:
    return "sha256:" + hashlib.sha256(canonical(items).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Mission v1 <-> helm items (IF-13 kind table)

ACCEPT_RADIUS_M = 3.0          # NAV-004 default
CMD_WAYPOINT, CMD_LOITER_TIME, CMD_SPEED, CMD_RTL = 16, 19, 178, 20
_KIND_OF = {CMD_WAYPOINT: "waypoint", CMD_LOITER_TIME: "photo_point",
            CMD_SPEED: "speed", CMD_RTL: "rtl"}


def to_helm_items(items: list[Item]) -> tuple[MissionItem, ...]:
    out = []
    for it in items:
        if it.kind == "waypoint":
            out.append(MissionItem(CMD_WAYPOINT, it.lat, it.lon, 0.0,
                                   (0.0, ACCEPT_RADIUS_M, 0.0, 0.0)))
        elif it.kind == "photo_point":
            out.append(MissionItem(CMD_LOITER_TIME, it.lat, it.lon, 0.0,
                                   (float(it.hold_s or 0), 0.0, 0.0, 0.0)))
        elif it.kind == "speed":
            out.append(MissionItem(CMD_SPEED, 0.0, 0.0, 0.0,
                                   (1.0, float(it.speed_mps), -1.0, 0.0)))
        else:
            out.append(MissionItem(CMD_RTL))
    return tuple(out)


def helm_view(items: list[Item]) -> list[dict]:
    """What of each item the helm can hold. Photo counts live on the boat's
    camera service (IF-03 Session), not in the helm, so they are not part
    of the read-back comparison."""
    out = []
    for it in items:
        d = {"kind": it.kind}
        if it.kind in ("waypoint", "photo_point"):
            d["lat"], d["lon"] = _canon(it.lat, "lat"), _canon(it.lon, "lon")
        if it.kind == "photo_point":
            d["hold_s"] = int(it.hold_s or 0)
        if it.kind == "speed":
            d["speed_mps"] = round(float(it.speed_mps), 2)
        out.append(d)
    return out


def helm_view_of(read_back: list[MissionItem]) -> list[dict]:
    out = []
    for m in read_back:
        kind = _KIND_OF.get(m.command, f"cmd{m.command}")
        d = {"kind": kind}
        if kind in ("waypoint", "photo_point"):
            d["lat"], d["lon"] = int(round(m.lat * 1e7)), int(round(m.lon * 1e7))
        if kind == "photo_point":
            d["hold_s"] = int(round(m.params[0]))
        if kind == "speed":
            d["speed_mps"] = round(float(m.params[1]), 2)
        out.append(d)
    return out


def view_checksum(view: list[dict]) -> str:
    s = json.dumps(view, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()
