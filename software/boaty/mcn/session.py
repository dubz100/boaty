"""C1 session manager (ICD IF-12 Figure 4 and button table, MCN-D08..15,
D18, D42, D43, D54..60).

    IDLE -talk-> PLANNING -plan ok-> PLAN_READY -adult approves-> APPROVED
    -adult arms-> ARMED -GO-> MISSION -end / COME HOME / failsafe->
    RETURNING -home, disarm-> DEBRIEF
    STOP from any armed state: motors stop, HOLD, disarm -> IDLE or DEBRIEF.
    Any change to an approved plan -> PLAN_READY (VAL-009).
    MANUAL is the adult's joystick state.

The session never talks to the helm directly: everything goes through
GuardedHelm (C7). STOP is handled first and without taking the session
lock, so a slow operation (planning, upload) can never delay it (MCN-D10).
"""
from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field

from ..helm.api import HelmError, PreArmFailed, SrsMode
from . import geo
from .helm_guard import GuardedHelm, Refused
from .log import SessionLog, utc_now
from .panel import Button
from .pin import PinLock
from .planning import PlanOutcome, Planning
from .site import Site, blocking, lint
from .voice import PHRASES


class State(enum.Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    PLAN_READY = "PLAN_READY"
    APPROVED = "APPROVED"
    ARMED = "ARMED"
    MISSION = "MISSION"
    RETURNING = "RETURNING"
    MANUAL = "MANUAL"
    DEBRIEF = "DEBRIEF"


ARMED_STATES = {State.ARMED, State.MISSION, State.RETURNING, State.MANUAL}
TALK_STATES = {State.IDLE, State.DEBRIEF, State.PLAN_READY, State.APPROVED}

CHECKLIST = [
    ("site", "Site file loaded and passes the linter (MCN-D53)"),
    ("fence", "Fence and no-go zones look right on the map"),
    ("battery", "Battery at least 80 % (PRE-003)"),
    ("hull", "Hatch sealed, box dry, props clear of weed"),
    ("rail", "Key switch test: key out, rail < 0.5 V; key in, rail = battery "
             "(MCN-D54)"),
    ("buttons", "Panel test: TALK, GO, COME HOME and STOP each pressed "
                "(MCN-D55)"),
    ("wind", "Is the wind blowing towards us? (MCN-D58)"),
    ("spotter", "A grown-up is on the bank watching the boat"),
]


@dataclass
class Config:
    auto_disarm_home_s: float = 60.0         # MCN-D12
    home_radius_m: float = 5.0
    breach_max_s: float = 30.0               # MCN-D59
    breach_max_outside_m: float = 8.0         # acts by FEN-006's 10 m
    min_sats: int = 8                        # MCN-D15
    max_hdop: float = 1.5                    # PRE-001, MCN-D15: Rover has
                                             # no native HDOP arming gate
    min_free_mb: int = 1024
    min_battery_pct: float = 80.0            # PRE-003
    reference: tuple[float, float] | None = None
    track_step_m: float = 1.0


@dataclass
class Sign:
    ok: bool
    by: str
    t_utc: str
    note: str = ""


@dataclass
class Snapshot:
    state: str
    data: dict = field(default_factory=dict)


def rail_test_ok(key_out_v: float, key_in_v: float, battery_v: float) -> bool:
    """MCN-D54: key out -> motor rail < 0.5 V; key in -> rail ~ battery."""
    return key_out_v < 0.5 and abs(key_in_v - battery_v) <= \
        max(0.5, 0.05 * battery_v)


class Session:
    def __init__(self, site: Site, guard: GuardedHelm, planning: Planning,
                 speaker, *, pin: PinLock, log: SessionLog | None = None,
                 clock=time.monotonic, utc=utc_now, listener=None,
                 boat_api=None, photo_dir=None, cfg: Config = Config(),
                 free_mb=lambda: 10_000, alert=None):
        self.site, self.guard, self.planning = site, guard, planning
        self.speaker, self.listener = speaker, listener
        self.pin, self.log = pin, log or SessionLog()
        self.clock, self.utc = clock, utc
        self.boat_api, self.photo_dir = boat_api, photo_dir
        self.cfg, self.free_mb = cfg, free_mb
        self.alerts: list[tuple[float, str]] = []
        self._alert_cb = alert
        self.state = State.IDLE
        self._lock = threading.RLock()
        self.plan: PlanOutcome | None = None
        self.approved_checksum: str | None = None
        self.checklist: dict[str, Sign] = {}
        self.site_issues = lint(site.doc, cfg.reference)
        self.track: list[tuple[float, float]] = []
        self.last_known: dict | None = None          # MCN-D18
        self.said: list[tuple[float, str]] = []
        self.stop_latency_s: list[float] = []
        self.held_reason: str | None = None
        self.photos_expected = False
        self.mission_started_t: float | None = None
        self.sync_report = None
        self.captains_log = None
        # monitor state
        self._prev_mode: SrsMode | None = None
        self._prev_ap_mode: int | None = None
        self._commanded: set = set()                 # modes we asked for
        self._home_since: float | None = None
        self._arrived_said = False
        self._breach_since: float | None = None
        self._breach_acted = False
        self._link_alerted = False
        self._impostor_alerted = False
        self._text_seen = 0
        self._photo_said: set[int] = set()
        self._text_t = float("-inf")
        self._shedding = False
        self._hold_seen_t: float | None = None
        self._stop_evt = threading.Event()
        self._threads: list[threading.Thread] = []
        guard.alarm = self.alert
        guard.log = self.log                 # MCN-D50: one session log
        planning.log = self.log
        if planning.llm is not None:
            planning.llm.log = self.log
        self.log("session_start", site=site.name, site_version=site.git_version,
                 lint=[str(i) for i in self.site_issues])

    # ------------------------------------------------------------------
    # Output
    def say(self, key_or_text: str) -> None:
        text = PHRASES.get(key_or_text, key_or_text)
        self.said.append((self.clock(), text))
        self.speaker.say(text)
        self.log("say", text=text)

    def alert(self, text: str) -> None:
        """Adult screen (and the log)."""
        self.alerts.append((self.clock(), text))
        self.log("alert", text=text)
        if self._alert_cb:
            self._alert_cb(text)

    def _set(self, s: State, why: str = "") -> None:
        if s != self.state:
            self.log("state", old=self.state.value, new=s.value, why=why)
            self.state = s

    def leds(self) -> dict[Button, bool]:
        s = self.state
        return {Button.GO: s is State.ARMED,
                Button.COME_HOME: s in {State.ARMED, State.MISSION,
                                        State.MANUAL},
                Button.STOP: s in ARMED_STATES,
                Button.TALK: s in TALK_STATES}

    # ------------------------------------------------------------------
    # Panel (C2 events)
    def button(self, b: Button, ev: str) -> None:
        t_edge = self.clock()
        if b is Button.STOP:
            if ev == "press":
                self._stop(t_edge, "STOP button")
            return
        with self._lock:
            s = self.state
            self.log("button", button=b.value, event=ev, state=s.value)
            if b is Button.GO:
                if ev != "held":
                    return
                if s is State.ARMED:
                    self._go()
                elif s in (State.IDLE, State.DEBRIEF):
                    self.say("not_yet")
                elif s in (State.PLAN_READY, State.APPROVED):
                    self.say("ask_arm")
                else:
                    self.say("not_now")
            elif b is Button.COME_HOME:
                if ev != "press":
                    return
                if s in (State.ARMED, State.MISSION, State.MANUAL):
                    self._rtl("COME HOME button")
                else:
                    self.say("not_now")
            elif b is Button.TALK:
                if s not in TALK_STATES:
                    if ev == "press":
                        self.say("not_now")
                    return
                if ev == "press" and self.listener:
                    self.listener.start()
                elif ev == "release" and self.listener:
                    text = self.listener.stop()
                    if text.strip():
                        self._spawn(self.instruct, text, "voice")

    # ------------------------------------------------------------------
    # Motion commands
    def _stop(self, t_edge: float, why: str) -> None:
        """No lock: STOP must never wait behind anything (MCN-D10)."""
        if self.state not in ARMED_STATES and not self.guard.status().armed:
            self.say("not_now")
            return
        self._commanded.add(SrsMode.HOLD)
        t_call = self.clock()
        self.stop_latency_s.append(t_call - t_edge)
        self.log("command", cmd="stop", why=why,
                 edge_to_call_ms=round((t_call - t_edge) * 1000, 1))
        try:
            self.guard.stop()
        except HelmError as e:
            self.alert(f"STOP: helm did not confirm ({e}). Pull the key.")
        self.say("stop")
        with self._lock:
            self.held_reason = None
            self._end_armed("stopped")

    def _go(self) -> None:
        try:
            self.guard.start_mission(self.approved_checksum or "")
        except Refused as e:
            self.alert(f"GO refused: {e}")
            self.say("not_now")
            return
        except HelmError as e:
            self.alert(f"GO failed: {e}")
            self.say("not_now")
            return
        self._commanded.add(SrsMode.AUTO)
        self._photo_said = set()
        self.mission_started_t = self.clock()
        self.photos_expected = True
        self.log("command", cmd="go", checksum=self.approved_checksum)
        self._set(State.MISSION, "GO")
        self.say("start")

    def _rtl(self, why: str) -> None:
        self._commanded.add(SrsMode.RTL)
        try:
            self.guard.return_home()
        except HelmError as e:
            self.alert(f"COME HOME failed: {e}")
            return
        self.log("command", cmd="rtl", why=why)
        self._set(State.RETURNING, why)
        self._arrived_said = False
        self.say("come_home")

    def _end_armed(self, why: str) -> None:
        self.track_end = self.clock()
        if self.photos_expected:
            self._set(State.DEBRIEF, why)
            self._spawn(self._debrief)
        else:
            self._set(State.IDLE, why)
        self.approved_checksum = None
        self.guard.invalidate()

    # ------------------------------------------------------------------
    # Planning
    def instruct(self, text: str, source: str = "text") -> PlanOutcome:
        with self._lock:
            if self.state not in TALK_STATES:
                self.say("not_now")
                return PlanOutcome(False, PHRASES["not_now"])
            self._void_approval("new instruction")
            self._set(State.PLANNING, source)
            st = self.guard.status()
        self.log("instruction", source=source, text=text)
        out = self.planning.from_text(
            text, source=source, now_utc=self.utc(),
            battery_pct=st.battery_pct, photo_capacity=self._photo_capacity(),
            boat_home=self._boat_home())
        return self._planned(out)

    def choose_template(self, name: str, area: str | None = None
                        ) -> PlanOutcome:
        with self._lock:
            if self.state not in TALK_STATES:
                return PlanOutcome(False, PHRASES["not_now"])
            self._void_approval("template chosen")
            st = self.guard.status()
            out = self.planning.from_template(
                name, area, now_utc=self.utc(), battery_pct=st.battery_pct,
                photo_capacity=self._photo_capacity(),
                boat_home=self._boat_home())
            self._set(State.PLANNING, "template")
        return self._planned(out)

    def edit_mission(self, token: str, mission) -> PlanOutcome:
        """Adult map editor (MCN-D20)."""
        self._need_adult(token)
        with self._lock:
            if self.state not in TALK_STATES:
                return PlanOutcome(False, PHRASES["not_now"])
            self._void_approval("mission edited")
            out = self.planning.from_mission(
                mission, now_utc=self.utc(),
                battery_pct=self.guard.status().battery_pct,
                photo_capacity=self._photo_capacity(),
                boat_home=self._boat_home())
            self._set(State.PLANNING, "edit")
        return self._planned(out)

    def _planned(self, out: PlanOutcome) -> PlanOutcome:
        with self._lock:
            self.plan = out
            self.log("plan", ok=out.ok, attempts=out.attempts,
                     mission=out.mission.to_json() if out.mission else None,
                     child=out.child, adult=out.adult)
            if out.ok:
                self._set(State.PLAN_READY, "plan ok")
                self.say(out.child)
                self.say("plan_ready")
            else:
                self._set(State.IDLE, "no plan")
                self.say(out.child)
                if out.adult:
                    self.alert(out.adult)
        return out

    def _void_approval(self, why: str) -> None:
        if self.approved_checksum:
            self.log("approval_void", checksum=self.approved_checksum,
                     why=why)
        self.approved_checksum = None
        self.guard.invalidate()

    def _photo_capacity(self) -> int:
        if self.boat_api is None:
            return 1000
        try:
            h = self.boat_api.health()
            return max(0, int(h.get("storage_free_mb", 0) * 1024 / 2500))
        except Exception:                                  # noqa: BLE001
            return 0

    def _boat_home(self):
        h = getattr(self.guard.helm, "home", None)
        return h() if callable(h) else None

    # ------------------------------------------------------------------
    # Adult actions (PIN)
    def unlock(self, pin: str):
        r = self.pin.unlock(pin)
        self.log("unlock", ok=r.ok, message=r.message)
        return r

    def _need_adult(self, token: str | None) -> None:
        if not self.pin.valid(token):
            raise PermissionError("adult PIN needed")

    def approve(self, token: str) -> tuple[bool, str]:
        self._need_adult(token)
        with self._lock:
            p = self.plan
            if self.state is not State.PLAN_READY or not p or not p.ok:
                return False, "no plan to approve"
            if blocking(self.site_issues):
                return False, "site file has errors"
            vm = p.validated
            try:
                if self.boat_api is not None:
                    self.boat_api.set_session(vm.mission)
                rep = self.guard.upload(vm)
            except (HelmError, OSError) as e:
                self.alert(f"Upload failed: {e}")
                return False, f"upload failed: {e}"
            if not rep.ok:
                self.alert("The boat's copy of the mission does not match. "
                           "Not approved.")
                return False, rep.detail
            self.approved_checksum = vm.checksum
            self.log("approval", mission_id=vm.mission.id,
                     checksum=vm.checksum, read_back=rep.read_back)
            self._set(State.APPROVED, "adult approved")
            return True, "approved"

    def sign(self, token: str, item: str, ok: bool, by: str = "adult",
             note: str = "") -> Sign:
        self._need_adult(token)
        if item not in dict(CHECKLIST):
            raise KeyError(item)
        s = Sign(ok, by, self.utc(), note)
        self.checklist[item] = s
        self.log("checklist", item=item, ok=ok, by=by, note=note)
        if item == "wind" and not ok:
            self.alert("Wind is not blowing towards us: launch from "
                       + self.suggest_launch())
        return s

    def suggest_launch(self, wind_from: str | None = None) -> str:
        """MCN-D58: a launch point whose good wind includes wind_from."""
        for L in self.site.launches:
            if wind_from is None or wind_from in L.wind_from:
                return f"'{L.name}' (good when wind is from " \
                       f"{', '.join(L.wind_from)})"
        return "nowhere suitable today"

    def arm_blockers(self) -> list[str]:
        out = []
        st = self.guard.status()
        if self.state is not State.APPROVED:
            out.append("no approved mission")
        missing = [k for k, _ in CHECKLIST if k not in self.checklist]
        failed = [k for k, s in self.checklist.items() if not s.ok]
        if missing:
            out.append(f"checklist not done: {', '.join(missing)}")
        if failed:
            out.append(f"checklist items failed: {', '.join(failed)}")
        if blocking(self.site_issues):
            out.append("site file has errors")
        if st.sats < self.cfg.min_sats:
            out.append(f"{st.sats} satellites (need {self.cfg.min_sats})")
        if st.hdop > self.cfg.max_hdop:
            out.append(f"GPS HDOP {st.hdop:.1f} (need ≤ {self.cfg.max_hdop})")
        if st.battery_pct < self.cfg.min_battery_pct:
            out.append(f"battery {st.battery_pct:.0f} % (need "
                       f"{self.cfg.min_battery_pct:.0f} %)")
        if self.free_mb() < self.cfg.min_free_mb:
            out.append("less than 1 GB free on Mission Control")
        if self.guard.state.verified_checksum != self.approved_checksum or \
                not self.approved_checksum:
            out.append("mission on the boat not verified (VAL-010)")
        out += self.guard.arm_blockers()
        return out

    def arm(self, token: str) -> tuple[bool, list[str]]:
        self._need_adult(token)
        with self._lock:
            b = self.arm_blockers()
            if b:
                self.log("arm_blocked", reasons=b)
                return False, b
            try:
                self.guard.arm()
            except PreArmFailed as e:
                return False, e.reasons
            except HelmError as e:
                return False, [str(e)]
            self._commanded.add(SrsMode.HOLD)
            self.log("command", cmd="arm")
            self._set(State.ARMED, "adult armed")
            self.photos_expected = False
            self.track = []
            return True, []

    def command(self, token: str, cmd: str) -> tuple[bool, str]:
        """MCN-D11: HOLD, RTL, MANUAL or STOP at any time while armed."""
        self._need_adult(token)
        if cmd == "stop":
            self._stop(self.clock(), "adult")
            return True, "stopped"
        with self._lock:
            if self.state not in ARMED_STATES:
                return False, "not armed"
            try:
                if cmd == "hold":
                    self._commanded.add(SrsMode.HOLD)
                    self.guard.hold()
                    self.held_reason = "adult"
                elif cmd == "rtl":
                    self._rtl("adult")
                elif cmd == "manual":
                    self._commanded.add(SrsMode.MANUAL)
                    self.guard.manual()
                    self._set(State.MANUAL, "adult")
                elif cmd == "resume":
                    # MCN-D60: after a B7/fence/adult hold, only the adult
                    # resumes; back to the mission if it isn't finished.
                    self.held_reason = None
                    self._shedding = False
                    if self.approved_checksum and self.state is \
                            State.MISSION:
                        self._commanded.add(SrsMode.AUTO)
                        self.guard.start_mission(self.approved_checksum)
                    else:
                        self._rtl("adult resume")
                else:
                    return False, f"unknown command {cmd}"
            except HelmError as e:
                return False, str(e)
            self.log("command", cmd=cmd, by="adult")
            return True, cmd

    def drive(self, token: str, throttle: float, turn: float) -> None:
        self._need_adult(token)
        if self.state is State.MANUAL:
            self.guard.drive(throttle, turn)

    # ------------------------------------------------------------------
    # Monitoring
    def start(self, period_s: float = 0.2, sleep=time.sleep) -> "Session":
        def run():
            while not self._stop_evt.is_set():
                try:
                    self.tick()
                except Exception as e:                    # noqa: BLE001
                    self.log("tick_error", error=repr(e))
                sleep(period_s)
        self._spawn(run)
        return self

    def close(self) -> None:
        self._stop_evt.set()
        self.pin.end_session()
        self.log("session_end")

    def _spawn(self, fn, *a) -> threading.Thread:
        t = threading.Thread(target=fn, args=a, daemon=True)
        t.start()
        self._threads.append(t)
        return t

    def tick(self) -> None:
        st = self.guard.status()
        now = self.clock()
        if self.guard.impostors():
            if not self._impostor_alerted:
                self._impostor_alerted = True
                self.say("impostor")
        else:
            self._impostor_alerted = False
        # Link and find-my-boat (MCN-D18).
        if st.link_ok and st.lat is not None:
            self.last_known = dict(lat=st.lat, lon=st.lon, t_utc=self.utc(),
                                   heading=st.heading_deg, mode=st.mode.value)
            self._link_alerted = False
            if st.armed and (not self.track or geo.dist(
                    self.site.enu.to_xy(*self.track[-1]),
                    self.site.enu.to_xy(st.lat, st.lon)) >=
                    self.cfg.track_step_m):
                self.track.append((st.lat, st.lon))
        elif not st.link_ok and not self._link_alerted and \
                self.state in ARMED_STATES:
            self._link_alerted = True
            self.alert("Link to the boat lost. Last position is on the map; "
                       "the boat comes home on its own after 60 s.")
        with self._lock:
            self._watch_mode(st, now)
            self._watch_events(st, now, self._new_texts())
            self._watch_progress(st)
            self._watch_home(st, now)
            self._watch_breach(st, now)

    def _texts(self) -> list[str]:
        f = getattr(self.guard.helm, "recent_texts", None)
        return f(30) if f else []

    def _watch_mode(self, st, now) -> None:
        mode, ap = st.mode, st.ardupilot_mode
        if (mode, ap) == (self._prev_mode, self._prev_ap_mode):
            return
        old = self._prev_mode
        self._prev_mode, self._prev_ap_mode = mode, ap
        self.log("helm_mode", mode=mode.value, ardupilot_mode=ap,
                 commanded=mode in self._commanded)
        ours = mode in self._commanded
        self._commanded.discard(mode)
        if old is None:
            return
        texts = " | ".join(self._texts()[-5:])
        if mode is SrsMode.DISARMED and self.state in ARMED_STATES:
            self._end_armed("helm disarmed")
            return
        if mode is SrsMode.RTL and self.state in (State.MISSION,
                                                  State.ARMED, State.MANUAL):
            items = self._mission_items()
            end = bool(items) and st.mission_seq is not None and \
                st.mission_seq >= items[-1].seq
            self._set(State.RETURNING, "helm RTL")
            self._arrived_said = False
            if end or ours:
                self.say("come_home")
            else:
                self.say("failsafe")
                self.alert(f"Failsafe: the boat is coming home. {texts}")
            return
        if mode is SrsMode.HOLD and self.state in (State.MISSION,
                                                   State.RETURNING) \
                and not ours:
            # Explained by a boat-service event (see _watch_events), or
            # declared after a short grace if nothing explains it.
            self._hold_seen_t = now
            return
        if mode is SrsMode.AUTO and self.state is State.MISSION and \
                self.held_reason is None and not ours:
            self.log("note", text="helm back in AUTO (B5 resumed)")

    def _new_texts(self) -> list[str]:
        f = getattr(self.guard.helm, "text_log", None)
        if f is not None:
            rows = f()
            new = [t for ts, t in rows if ts > self._text_t]
            if rows:
                self._text_t = max(self._text_t, rows[-1][0])
            return new
        texts = self._texts()
        new = texts[self._text_seen:]
        self._text_seen = len(texts)
        return new

    def _watch_events(self, st, now, texts: list[str]) -> None:
        """MCN-D60: boat-service stops are shown and spoken with the
        reason. B5 switches the helm before it sends its event text, so
        the text, not the mode change, carries the reason."""
        active = self.state in (State.MISSION, State.RETURNING)
        for t in texts:
            u = t.upper()
            if not u.startswith("BOATY"):
                continue
            self.log("boat_event", text=t)
            if not active:
                continue
            if "B5 SHED START" in u:
                if not self._shedding:
                    self.say("stuck")
                self._shedding = True
            elif "B5 SHED END" in u:
                self._shedding = False
            if "STILL STUCK" in u or "REPEATEDLY STUCK" in u or \
                    "NO CONTROL" in u or u.startswith("BOATY B7") or \
                    ("BOATY B6" in u and "HOLD" in u):
                self._shedding = False
                self._declare_held(t)
        if st.mode is not SrsMode.HOLD:
            self._hold_seen_t = None
        elif active and self._hold_seen_t is not None and \
                self.held_reason is None and not self._shedding and \
                now - self._hold_seen_t >= self.HOLD_GRACE_S:
            self._declare_held(" | ".join(self._texts()[-3:]) or "helm HOLD")

    HOLD_GRACE_S = 1.0

    def _declare_held(self, reason: str) -> None:
        if self.held_reason is not None:
            return
        self.held_reason = reason
        self.say("held")
        self.alert(f"The boat stopped itself: {reason}. Check it, then "
                   "Resume (PIN) or Come home.")

    def _mission_items(self):
        p = self.plan
        return p.mission.items if p and p.mission else []

    def _watch_progress(self, st) -> None:
        """Mission progress by item: the final RTL item runs inside AUTO
        (ArduPilot does not switch to RTL mode for it), and photo points
        are announced when the boat gets there (IF-12 phrases)."""
        items = self._mission_items()
        if self.state is not State.MISSION or not items or \
                st.mission_seq is None or st.mode is not SrsMode.AUTO:
            return
        seq = st.mission_seq
        if items[-1].kind == "rtl" and seq >= items[-1].seq:
            self._set(State.RETURNING, "last item: return home")
            self._arrived_said = False
            self.say("come_home")
            return
        it = next((i for i in items if i.seq == seq), None)
        if it is not None and it.kind == "photo_point" and \
                seq not in self._photo_said and st.lat is not None:
            d = geo.dist(self.site.enu.to_xy(st.lat, st.lon),
                         self.site.enu.to_xy(it.lat, it.lon))
            if d <= 4.0:
                self._photo_said.add(seq)
                self.say("photo")

    def _watch_home(self, st, now) -> None:
        if self.state is not State.RETURNING or st.lat is None:
            self._home_since = None
            return
        hl = self.site.home_ll()
        d = geo.dist(self.site.enu.to_xy(st.lat, st.lon),
                     self.site.enu.to_xy(*hl))
        if d <= self.cfg.home_radius_m and st.speed_mps < 0.3:
            if self._home_since is None:
                self._home_since = now
                if not self._arrived_said:
                    self._arrived_said = True
                    self.say("home")
            elif now - self._home_since >= self.cfg.auto_disarm_home_s:
                self.log("command", cmd="auto_disarm")
                try:
                    self.guard.stop()
                except HelmError as e:
                    self.alert(f"Auto-disarm failed: {e}")
                    return
                self._end_armed("home")
        elif d > self.cfg.home_radius_m + 3:
            self._home_since = None

    def _watch_breach(self, st, now) -> None:
        """MCN-D59: HOLD if a breach lasts > 30 s or goes > 10 m outside."""
        if not st.armed or st.lat is None:
            self._breach_since, self._breach_acted = None, False
            return
        depth = geo.signed_depth(self.site.enu.to_xy(st.lat, st.lon),
                                 list(self.site.inclusion))
        outside = depth < 0 or st.fence_breached
        if not outside:
            self._breach_since, self._breach_acted = None, False
            return
        if self._breach_since is None:
            self._breach_since = now
            self.log("breach", outside_m=round(-depth, 1))
        if self._breach_acted:
            return
        if now - self._breach_since > self.cfg.breach_max_s or \
                -depth > self.cfg.breach_max_outside_m:
            self._breach_acted = True
            self._commanded.add(SrsMode.HOLD)
            try:
                self.guard.halt()
            except HelmError as e:
                self.alert(f"Fence HOLD failed: {e}. Pull the key.")
            self.held_reason = "fence"
            self.log("command", cmd="halt", why="MCN-D59",
                     outside_m=round(-depth, 1),
                     for_s=round(now - self._breach_since, 1))
            self.say("fence")
            self.alert(f"The boat is {-depth:.0f} m outside the fence and "
                       "its motors are stopped. Paddle out or use MANUAL.")

    # ------------------------------------------------------------------
    # Debrief (C8)
    def _debrief(self) -> None:
        if self.boat_api is None or self.photo_dir is None or not self.plan \
                or not self.plan.mission:
            return
        from .photos import captains_log, sync
        m = self.plan.mission
        dest = self.photo_dir / m.id
        try:
            self.sync_report = sync(self.boat_api, m.id, dest, self.log)
            listing = self.boat_api.photos(m.id)
        except Exception as e:                            # noqa: BLE001
            self.alert(f"Photo sync failed: {e}")
            return
        places = [s.landmark for s in getattr(
            getattr(self.plan, "intent", None), "steps", [])
            if getattr(s, "landmark", None)]
        dur = (getattr(self, "track_end", self.clock()) -
               (self.mission_started_t or self.clock()))
        self.captains_log = captains_log(
            dest, m, listing, self.track, self.site.fence().inclusion,
            dur, places)
        self.log("captains_log", path=str(self.captains_log))

    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        """What the web UI pushes at >= 1 Hz (MCN-D16)."""
        st = self.guard.status()
        p = self.plan
        m = p.mission if p else None
        left = None
        if m and self.mission_started_t is not None and \
                self.state in (State.MISSION, State.RETURNING):
            left = max(0, m.estimates.duration_s -
                       (self.clock() - self.mission_started_t))
        f = self.site.fence()
        return {
            "t_utc": self.utc(),
            "state": self.state.value,
            "helm": {"mode": st.mode.value, "armed": st.armed,
                     "link_ok": st.link_ok, "lat": st.lat, "lon": st.lon,
                     "heading": st.heading_deg, "speed": st.speed_mps,
                     "battery_pct": st.battery_pct, "sats": st.sats,
                     "hdop": st.hdop, "breached": st.fence_breached},
            "time_left_s": left,
            "track": self.track[-300:],
            "last_known": self.last_known,
            "site": {"name": self.site.name, "fence": f.inclusion,
                     "exclusions": f.exclusions,
                     "circles": f.exclusion_circles,
                     "home": self.site.home_ll(),
                     "issues": [str(i) for i in self.site_issues]},
            "plan": None if not p else {
                "ok": p.ok, "child": p.child, "adult": p.adult,
                "offer_templates": p.offer_templates,
                "preview": p.preview.__dict__ if p.preview else None,
                "points": [(i.lat, i.lon, i.kind) for i in m.items
                           if i.lat is not None] if m else [],
                "checksum": m.checksum if m else None,
                "violations": [v.model_dump() for v in p.result.violations]
                if p.result else []},
            "approved": self.approved_checksum,
            "checklist": {k: {"label": lbl, **(self.checklist[k].__dict__
                                               if k in self.checklist
                                               else {})}
                          for k, lbl in CHECKLIST},
            "arm_blockers": self.arm_blockers()
            if self.state is State.APPROVED else [],
            "leds": {b.value: on for b, on in self.leds().items()},
            "said": [t for _, t in self.said[-8:]],
            "alerts": [t for _, t in self.alerts[-8:]],
            "held": self.held_reason,
            "impostor": bool(self.guard.state.impostors),
            "templates": self.planning.templates(),
        }
