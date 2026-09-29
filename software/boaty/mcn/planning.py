"""C5 planning flow: instruction -> Intent -> Mission -> ValidationResult.

    TALK / typed text -> IntentClient (IF-11) -> Planner -> validate()

A malformed reply, a planner failure or a validator rejection is retried
once, with the problem passed back to the model as data (IF-11 response
table; within MCN-D29's "at most 2"). After that, or on refusal, decline,
HTTP error or no internet, the adult is offered the templates (NLI-004,
MC-011). Templates go through the same validator (VAL-001).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .llm import REFUSED_CHILD, IntentClient
from .models import Mission, ValidationResult
from .planner import TEMPLATE_NAMES, PlanError, Planner, Preview, preview
from .site import Site
from .validator import Limits, ValidatedMission, validate

RETRIES = 1
NO_INTERNET = "No internet: templates only."


@dataclass
class PlanOutcome:
    ok: bool
    child: str                       # spoken / shown to the child
    adult: str = ""                  # shown on the adult's screen
    mission: Mission | None = None
    result: ValidationResult | None = None
    validated: ValidatedMission | None = None
    preview: Preview | None = None
    offer_templates: bool = False
    attempts: list[str] = field(default_factory=list)
    intent: object = None


class Planning:
    def __init__(self, site: Site, llm: IntentClient | None = None,
                 limits: Limits = Limits(), log=None):
        self.site, self.llm, self.limits = site, llm, limits
        self.planner = Planner(site, limits)
        self.log = log or (lambda *a, **k: None)

    def _check(self, m: Mission, now_utc: str, **ctx) -> PlanOutcome:
        res, vm = validate(m, self.site, now_utc=now_utc, limits=self.limits,
                           **ctx)
        self.log("validation", mission_id=m.id, ok=res.ok,
                 violations=[v.model_dump() for v in res.violations])
        if vm is None:
            return PlanOutcome(False, res.violations[0].message_for_child,
                               "; ".join(v.message_for_adult
                                         for v in res.violations),
                               mission=m, result=res)
        return PlanOutcome(True, m.summary_for_child, mission=m, result=res,
                           validated=vm, preview=preview(m, self.site))

    def from_text(self, text: str, *, source: str, now_utc: str,
                  battery_pct: float = 100.0, photo_capacity: int = 1000,
                  boat_home=None) -> PlanOutcome:
        ctx = dict(battery_pct=battery_pct, photo_capacity=photo_capacity,
                   boat_home=boat_home)
        if self.llm is None:
            return PlanOutcome(False, "Let's pick an adventure!", NO_INTERNET,
                               offer_templates=True)
        note, attempts = None, []
        max_min = min(self.limits.max_duration_s,
                      self.limits.duration_cap_s) // 60
        for _ in range(1 + RETRIES):
            r = self.llm.ask(self.site.context_for_llm(), text, battery_pct,
                             max_min, note)
            attempts.append(r.kind)
            if r.kind == "error":
                return PlanOutcome(False, "Let's pick an adventure!",
                                   f"{NO_INTERNET} ({r.detail})",
                                   offer_templates=True, attempts=attempts)
            if r.kind == "refused":
                return PlanOutcome(False, REFUSED_CHILD, "The request was "
                                   "declined by the model.",
                                   offer_templates=True, attempts=attempts)
            if r.kind == "declined":
                return PlanOutcome(False, r.child, "Declined (NLI-006).",
                                   offer_templates=True, attempts=attempts)
            if r.kind == "truncated":
                note = "The reply was cut off. Keep the plan short."
                continue
            if r.kind == "invalid":
                note = f"The reply did not match Intent v1: {r.detail}"
                continue
            try:
                m = self.planner.from_intent(r.intent, source=source,
                                             now_utc=now_utc,
                                             battery_pct=battery_pct)
            except PlanError as e:
                note = f"The planner could not use that plan: {e.message}"
                continue
            out = self._check(m, now_utc, **ctx)
            out.attempts, out.intent = attempts, r.intent
            if out.ok:
                return out
            note = f"The safety check rejected the route: {out.adult}"
        return PlanOutcome(False, "I couldn't make a plan for that. Shall we "
                           "pick an adventure?", f"Gave up after "
                           f"{len(attempts)} attempts: {note}",
                           offer_templates=True, attempts=attempts)

    def from_template(self, name: str, area: str | None = None, *,
                      now_utc: str, battery_pct: float = 100.0,
                      photo_capacity: int = 1000, boat_home=None
                      ) -> PlanOutcome:
        try:
            m = self.planner.template(name, area, now_utc=now_utc,
                                      battery_pct=battery_pct)
        except PlanError as e:
            return PlanOutcome(False, e.child, e.message)
        return self._check(m, now_utc, battery_pct=battery_pct,
                           photo_capacity=photo_capacity, boat_home=boat_home)

    def from_mission(self, m: Mission, *, now_utc: str, **ctx) -> PlanOutcome:
        """Adult map editor (MCN-D20): every edit comes back through here."""
        return self._check(m.with_checksum(), now_utc, **ctx)

    def templates(self) -> list[dict]:
        return [{"id": k, "name": v, "areas": [a.name for a in
                                               self.site.areas]}
                for k, v in TEMPLATE_NAMES.items()]
