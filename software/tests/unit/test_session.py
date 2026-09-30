"""C1 session manager, C7 guard and the adult PIN, against a fake helm.

The same flows run against the real firmware in tests/sitl/
test_mission_control.py; these cover every row of the IF-12 button table
and the rules that are awkward to provoke in SITL.
"""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

import boaty  # noqa: F401
from boaty.helm.api import HelmStatus, MissionItem, SrsMode
from boaty.mcn.helm_guard import GuardedHelm, Refused
from boaty.mcn.log import SessionLog
from boaty.mcn.panel import Button, SimPanel
from boaty.mcn.pin import PinLock
from boaty.mcn.planning import Planning
from boaty.mcn.session import CHECKLIST, Config, Session, State, rail_test_ok
from boaty.mcn.site import Site
from boaty.mcn.voice import PHRASES, RecordingSpeaker, ScriptedListener

SITE = Site.named("milton-country-park")
PIN = "482913"


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class FakeHelm:
    def __init__(self, clock):
        self.clock = clock
        lat, lon = SITE.home_ll()
        self.s = HelmStatus(datetime.now(timezone.utc), True, False,
                            SrsMode.DISARMED, lat, lon, 0.0, 0.0, 95.0, 12.4,
                            0.0, 3, 12, 0.7, True, False, None, None)
        self.fence = None
        self.items = ()
        self.calls = []
        self.params = dict(GuardedHelm(self).baseline) if False else None
        self.foreign = []
        self.corrupt_readback = False
        self.texts = []

    # IF-14 subset
    def status(self):
        return self.s

    def set(self, **kw):
        self.s = replace(self.s, **kw)

    def read_params(self, timeout=20):
        return dict(self._params)

    def foreign_gcs(self, within_s=3.0):
        return list(self.foreign)

    def recent_texts(self, since_s=60):
        return list(self.texts)

    def home(self):
        return SITE.home_ll()

    def upload_fence(self, f):
        self.calls.append("upload_fence")
        self.fence = f

    def upload_mission(self, m):
        self.calls.append("upload_mission")
        self.items = m.items

    def read_back(self):
        items = list(self.items)
        if self.corrupt_readback:
            it = items[1]
            items[1] = MissionItem(it.command, it.lat + 1e-4, it.lon, it.alt,
                                   it.params, it.frame)
        return self.fence, items

    def arm(self):
        self.calls.append("arm")
        self.set(armed=True, mode=SrsMode.HOLD)

    def disarm(self, force=False):
        self.set(armed=False, mode=SrsMode.DISARMED)

    def stop(self):
        self.calls.append(("stop", self.clock()))
        self.set(armed=False, mode=SrsMode.DISARMED)

    def start_mission(self):
        self.calls.append("auto")
        self.set(mode=SrsMode.AUTO)

    def hold(self):
        self.calls.append("loiter")
        self.set(mode=SrsMode.HOLD)

    def halt(self):
        self.calls.append("halt")
        self.set(mode=SrsMode.HOLD)

    def return_home(self):
        self.calls.append("rtl")
        self.set(mode=SrsMode.RTL)

    def manual(self):
        self.calls.append("manual")
        self.set(mode=SrsMode.MANUAL)

    def drive(self, t, s):
        self.calls.append(("drive", t, s))


@pytest.fixture
def env(tmp_path):
    clock = Clock()
    helm = FakeHelm(clock)
    guard = GuardedHelm(helm)
    helm._params = dict(guard.baseline)
    speaker = RecordingSpeaker(clock)
    listener = ScriptedListener()
    log = SessionLog(tmp_path / "session.jsonl")
    lock = PinLock.from_pin(PIN, clock)
    s = Session(SITE, guard, Planning(SITE), speaker, pin=lock, log=log,
                clock=clock, listener=listener,
                cfg=Config(reference=(52.2448, 0.1597)))
    panel = SimPanel(s.button, clock, clock.sleep)
    guard.check_params()
    return s, helm, panel, clock, speaker


def adult(s):
    r = s.unlock(PIN)
    assert r.ok
    return r.token


def ready_to_arm(s, tok):
    for k, _ in CHECKLIST:
        s.sign(tok, k, True, by="Dad")


def armed(env):
    s, helm, panel, clock, _ = env
    s.choose_template("explore", "home bay")
    tok = adult(s)
    assert s.approve(tok) == (True, "approved")
    ready_to_arm(s, tok)
    ok, why = s.arm(tok)
    assert ok, why
    s.tick()
    return tok


def said(speaker):
    return speaker.texts()


# ---------------------------------------------------------------- happy path
@pytest.mark.verifies("MC-010", "SWE-003")
def test_full_flow(env):
    s, helm, panel, clock, sp = env
    assert s.state is State.IDLE
    out = s.choose_template("explore", "home bay")
    assert out.ok and s.state is State.PLAN_READY
    assert said(sp)[-1] == PHRASES["plan_ready"]
    tok = armed(env)
    assert s.state is State.ARMED
    panel.press(Button.GO, hold_s=1.05)
    assert s.state is State.MISSION and helm.s.mode is SrsMode.AUTO
    assert "Off we go!" in said(sp)
    panel.press(Button.COME_HOME)
    assert s.state is State.RETURNING and "Coming home!" in said(sp)
    assert tok


@pytest.mark.verifies("MC-003")
def test_leds_follow_state(env):
    s, *_ = env
    assert s.leds()[Button.TALK] and not s.leds()[Button.GO]
    armed(env)
    lit = s.leds()
    assert lit[Button.GO] and lit[Button.STOP] and not lit[Button.TALK]


# ---------------------------------------------------------------- button table
@pytest.mark.parametrize("state,phrase", [
    ("IDLE", "Not yet!"), ("DEBRIEF", "Not yet!"),
    ("PLAN_READY", "Ask a grown-up to arm."),
    ("APPROVED", "Ask a grown-up to arm.")])
@pytest.mark.verifies("VAL-008", "MC-003")
def test_go_before_armed(env, state, phrase):
    s, helm, panel, _, sp = env
    s.state = State[state]
    panel.press(Button.GO, hold_s=1.05)
    assert said(sp)[-1] == phrase and "auto" not in helm.calls


@pytest.mark.verifies("MC-003")
def test_go_needs_hold(env):
    s, helm, panel, *_ = env
    armed(env)
    panel.press(Button.GO, hold_s=0.5)
    assert s.state is State.ARMED and "auto" not in helm.calls
    panel.press(Button.GO, hold_s=1.0)
    assert s.state is State.MISSION


def test_go_ignored_in_mission(env):
    s, helm, panel, _, sp = env
    armed(env)
    panel.press(Button.GO, hold_s=1.05)
    n = helm.calls.count("auto")
    panel.press(Button.GO, hold_s=1.05)
    assert helm.calls.count("auto") == n and said(sp)[-1] == "Not now."


@pytest.mark.parametrize("state", ["IDLE", "PLAN_READY", "APPROVED",
                                   "DEBRIEF", "RETURNING"])
def test_come_home_ignored(env, state):
    s, helm, panel, _, sp = env
    s.state = State[state]
    panel.press(Button.COME_HOME)
    assert "rtl" not in helm.calls and said(sp)[-1] == "Not now."


@pytest.mark.parametrize("state", ["ARMED", "MISSION", "MANUAL"])
@pytest.mark.verifies("MOD-006", "MC-003")
def test_come_home_works(env, state):
    s, helm, panel, *_ = env
    armed(env)
    s.state = State[state]
    panel.press(Button.COME_HOME)
    assert helm.calls[-1] == "rtl" and s.state is State.RETURNING


@pytest.mark.parametrize("state", ["ARMED", "MISSION", "RETURNING", "MANUAL"])
@pytest.mark.verifies("MOD-006", "FS-009")
def test_stop_from_every_armed_state(env, state):
    s, helm, panel, clock, sp = env
    armed(env)
    s.state = State[state]
    panel.press(Button.STOP)
    stops = [c for c in helm.calls if isinstance(c, tuple) and c[0] == "stop"]
    assert stops and not helm.s.armed
    assert s.state in (State.IDLE, State.DEBRIEF)
    assert s.stop_latency_s[-1] <= 0.05                 # MCN-D10


def test_stop_ignored_when_disarmed(env):
    s, helm, panel, _, sp = env
    panel.press(Button.STOP)
    assert said(sp)[-1] == "Not now."


@pytest.mark.verifies("MC-003")
def test_stop_not_blocked_by_lock(env):
    """STOP must not wait behind a long operation holding the lock."""
    import threading
    s, helm, panel, *_ = env
    armed(env)
    got = threading.Event()
    with s._lock:
        t = threading.Thread(target=lambda: (panel.press(Button.STOP),
                                             got.set()))
        t.start()
        # helm.stop happens while we still hold the lock
        for _ in range(100):
            if any(isinstance(c, tuple) for c in helm.calls):
                break
            threading.Event().wait(0.01)
        assert any(isinstance(c, tuple) and c[0] == "stop"
                   for c in helm.calls)
    t.join(2)


@pytest.mark.verifies("NLI-002")
def test_talk_plans_from_voice(env):
    s, helm, panel, _, sp = env
    s.listener.queue.append("explore the bay")
    called = []
    s.instruct = lambda text, src="text": called.append((text, src))
    panel.press(Button.TALK, hold_s=2)
    for th in s._threads:
        th.join(1)
    assert called == [("explore the bay", "voice")]


def test_talk_ignored_while_armed(env):
    s, helm, panel, _, sp = env
    armed(env)
    panel.press(Button.TALK)
    assert said(sp)[-1] == "Not now." and not s.listener.listening


# ---------------------------------------------------------------- approval
@pytest.mark.verifies("VAL-008", "MC-008")
def test_approval_needs_pin(env):
    s, *_ = env
    s.choose_template("lap", "home bay")
    with pytest.raises(PermissionError):
        s.approve("guess")


@pytest.mark.verifies("PRE-005", "VAL-010")
def test_approval_uploads_and_verifies(env):
    s, helm, *_ = env
    s.choose_template("lap", "home bay")
    ok, _ = s.approve(adult(s))
    assert ok and helm.calls[:2] == ["upload_fence", "upload_mission"]
    assert s.approved_checksum == s.plan.mission.checksum


@pytest.mark.verifies("PRE-005", "VAL-010")
def test_readback_mismatch_blocks_approval(env):
    s, helm, *_ = env
    helm.corrupt_readback = True
    s.choose_template("lap", "home bay")
    ok, why = s.approve(adult(s))
    assert not ok and s.state is State.PLAN_READY and not s.approved_checksum


@pytest.mark.verifies("VAL-009")
def test_new_plan_voids_approval(env):
    s, helm, *_ = env
    s.choose_template("lap", "home bay")
    s.approve(adult(s))
    assert s.state is State.APPROVED
    s.choose_template("explore", "home bay")
    assert s.state is State.PLAN_READY and s.approved_checksum is None
    assert s.guard.state.verified_checksum is None
    assert s.log.of("approval_void")


@pytest.mark.verifies("SAF-004", "VAL-009")
def test_edited_mission_is_revalidated(env):
    s, *_ = env
    s.choose_template("lap", "home bay")
    tok = adult(s)
    s.approve(tok)
    m = s.plan.mission
    items = list(m.items)
    lat, lon = SITE.enu.to_ll(10, 45)                  # into the island
    items[1] = items[1].model_copy(update={"lat": lat, "lon": lon})
    out = s.edit_mission(tok, m.model_copy(update={"items": items}))
    assert not out.ok and s.state is State.IDLE
    assert any(v.rule == "VAL-002" for v in out.result.violations)


@pytest.mark.verifies("PRE-005", "MC-003")
def test_go_refused_if_boat_copy_not_verified(env):
    s, helm, panel, _, sp = env
    armed(env)
    s.guard.invalidate()
    panel.press(Button.GO, hold_s=1.05)
    assert s.state is State.ARMED and "auto" not in helm.calls
    assert any("VAL-010" in a for _, a in s.alerts)


# ---------------------------------------------------------------- arming
@pytest.mark.verifies("MOD-004", "MC-010")
def test_arm_blocked_until_checklist(env):
    s, *_ = env
    s.choose_template("lap", "home bay")
    tok = adult(s)
    s.approve(tok)
    ok, why = s.arm(tok)
    assert not ok and any("checklist" in w for w in why)


@pytest.mark.verifies("MOD-004", "PRE-001")
def test_arm_blocked_by_few_satellites(env):
    s, helm, *_ = env
    s.choose_template("lap", "home bay")
    tok = adult(s)
    s.approve(tok)
    ready_to_arm(s, tok)
    helm.set(sats=6)
    ok, why = s.arm(tok)
    assert not ok and any("satellites" in w for w in why)


@pytest.mark.verifies("MOD-004", "PRE-001")
def test_arm_blocked_by_poor_hdop(env):
    """PRE-001 / MCN-D15: HDOP > 1.5 blocks arming (Rover has no native
    HDOP gate; SDR RID-11)."""
    s, helm, *_ = env
    s.choose_template("lap", "home bay")
    tok = adult(s)
    s.approve(tok)
    ready_to_arm(s, tok)
    helm.set(hdop=1.8)
    ok, why = s.arm(tok)
    assert not ok and any("HDOP" in w for w in why)


@pytest.mark.verifies("MOD-004")
def test_arm_blocked_by_param_mismatch(env):
    """MCN-D45 / SC-24 (unit level)."""
    s, helm, *_ = env
    helm._params["FENCE_RADIUS"] = 300
    s.guard.check_params()
    s.choose_template("lap", "home bay")
    tok = adult(s)
    s.approve(tok)
    ready_to_arm(s, tok)
    ok, why = s.arm(tok)
    assert not ok and any("FENCE_RADIUS" in w for w in why)


def test_arm_blocked_by_wind(env):
    s, *_ = env
    s.choose_template("lap", "home bay")
    tok = adult(s)
    s.approve(tok)
    ready_to_arm(s, tok)
    s.sign(tok, "wind", False)
    ok, why = s.arm(tok)
    assert not ok and any("wind" in w for w in why)
    assert any("jetty" in a or "east beach" in a for _, a in s.alerts)


def test_arm_blocked_by_low_disk(env):
    s, *_ = env
    s.free_mb = lambda: 500
    s.choose_template("lap", "home bay")
    tok = adult(s)
    s.approve(tok)
    ready_to_arm(s, tok)
    ok, why = s.arm(tok)
    assert not ok and any("1 GB" in w for w in why)


def test_rail_test_rule():
    assert rail_test_ok(0.1, 12.3, 12.4)
    assert not rail_test_ok(0.8, 12.3, 12.4)            # key switch fault
    assert not rail_test_ok(0.1, 3.0, 12.4)


# ---------------------------------------------------------------- impostor
def test_impostor_blocks_arming_and_go_but_not_stop(env):
    s, helm, panel, clock, sp = env
    armed(env)
    helm.foreign.append((255, 190))
    s.tick()
    assert PHRASES["impostor"] in said(sp)
    assert any("Another ground station" in a for _, a in s.alerts)
    panel.press(Button.GO, hold_s=1.05)
    assert "auto" not in helm.calls
    with pytest.raises(Refused):
        s.guard.drive(0.5, 0)
    panel.press(Button.STOP)
    assert not helm.s.armed


def test_impostor_clears(env):
    s, helm, panel, *_ = env
    armed(env)
    helm.foreign.append((255, 190))
    s.tick()
    helm.foreign.clear()
    s.tick()
    panel.press(Button.GO, hold_s=1.05)
    assert s.state is State.MISSION


# ---------------------------------------------------------------- monitoring
def go(env):
    s, helm, panel, clock, _ = env
    armed(env)
    panel.press(Button.GO, hold_s=1.05)
    lat, lon = SITE.enu.to_ll(10, 20)                  # out on the water
    helm.set(lat=lat, lon=lon, speed_mps=1.0)
    s.tick()


@pytest.mark.verifies("MC-007")
def test_failsafe_rtl_is_announced(env):
    s, helm, panel, clock, sp = env
    go(env)
    helm.texts = ["Failsafe: GCS"]
    helm.set(mode=SrsMode.RTL, mission_seq=2, mission_total=6)
    s.tick()
    assert s.state is State.RETURNING
    assert said(sp)[-1] == "I need to come home now."
    assert any("GCS" in a for _, a in s.alerts)


def test_mission_end_rtl_is_normal(env):
    s, helm, panel, clock, sp = env
    go(env)
    last = s.plan.mission.items[-1].seq
    helm.set(mode=SrsMode.RTL, mission_seq=last, mission_total=last)
    s.tick()
    assert said(sp)[-1] == "Coming home!"


def test_rtl_item_inside_auto_means_returning(env):
    """ArduPilot runs the final RTL item in AUTO; the session follows the
    item sequence."""
    s, helm, panel, clock, sp = env
    go(env)
    last = s.plan.mission.items[-1].seq
    helm.set(mission_seq=last, mission_total=last)
    s.tick()
    assert s.state is State.RETURNING and said(sp)[-1] == "Coming home!"


@pytest.mark.verifies("MC-007")
def test_photo_point_announced_on_arrival(env):
    s, helm, panel, clock, sp = env
    s.state = State.IDLE
    s.choose_template("duck_watch", "home bay")
    tok = adult(s)
    s.approve(tok)
    ready_to_arm(s, tok)
    s.arm(tok)
    panel.press(Button.GO, hold_s=1.05)
    pp = next(i for i in s.plan.mission.items if i.kind == "photo_point")
    helm.set(mission_seq=pp.seq, lat=pp.lat + 0.0002, lon=pp.lon)
    s.tick()
    assert "Taking pictures!" not in said(sp)
    helm.set(lat=pp.lat, lon=pp.lon)
    s.tick()
    s.tick()
    assert said(sp).count("Taking pictures!") == 1


def test_b7_hold_needs_pin_to_resume(env):
    s, helm, panel, clock, sp = env
    go(env)
    helm.texts = ["BOATY B7 STUCK"]
    helm.set(mode=SrsMode.HOLD)
    s.tick()
    assert s.held_reason and "STUCK" in s.held_reason
    assert said(sp)[-1] == PHRASES["held"]
    with pytest.raises(PermissionError):
        s.command("nope", "resume")
    ok, _ = s.command(adult(s), "resume")
    assert ok and helm.calls[-1] == "auto"


def test_weed_shedding_said_once_then_still_stuck_holds(env):
    s, helm, panel, clock, sp = env
    go(env)
    helm.texts = ["BOATY B5 SHED START"]
    for mode in (SrsMode.HOLD, SrsMode.AUTO, SrsMode.HOLD, SrsMode.AUTO):
        helm.set(mode=mode)                  # GUIDED bursts show as HOLD
        s.tick()
        clock.t += 0.5
    assert said(sp).count(PHRASES["stuck"]) == 1 and s.held_reason is None
    helm.set(mode=SrsMode.HOLD)               # B5 gives up: HOLD first...
    s.tick()
    clock.t += 0.3
    helm.texts = helm.texts + ["BOATY B5 STILL STUCK: HOLD"]   # ...text later
    s.tick()
    assert s.held_reason and "STILL STUCK" in s.held_reason
    assert said(sp)[-1] == PHRASES["held"]


def test_unexplained_hold_declared_after_grace(env):
    s, helm, panel, clock, sp = env
    go(env)
    helm.set(mode=SrsMode.HOLD)
    s.tick()
    clock.t += 0.5
    s.tick()
    assert s.held_reason is None
    clock.t += 0.6
    s.tick()
    assert s.held_reason == "helm HOLD" and said(sp)[-1] == PHRASES["held"]


@pytest.mark.verifies("MOD-008")
def test_arrival_then_auto_disarm_after_60s(env):
    s, helm, panel, clock, sp = env
    go(env)
    panel.press(Button.COME_HOME)
    s.tick()
    lat, lon = SITE.enu.to_ll(2, 2)
    helm.set(lat=lat, lon=lon, speed_mps=0.1)
    s.tick()
    assert "I'm back! Let's look at the pictures." in said(sp)
    clock.t += 59
    s.tick()
    assert helm.s.armed
    clock.t += 1.5
    s.tick()
    assert not helm.s.armed and s.state is State.DEBRIEF


def test_breach_30s_halts(env):
    s, helm, panel, clock, sp = env
    go(env)
    lat, lon = SITE.enu.to_ll(0, -14)                   # 4 m outside
    helm.set(lat=lat, lon=lon, fence_breached=True, mode=SrsMode.RTL)
    s.tick()
    clock.t += 29.5
    s.tick()
    assert "halt" not in helm.calls
    clock.t += 1
    s.tick()
    assert "halt" in helm.calls and s.held_reason == "fence"
    assert said(sp)[-1] == PHRASES["fence"]


def test_breach_10m_halts_at_once(env):
    s, helm, panel, clock, sp = env
    go(env)
    lat, lon = SITE.enu.to_ll(0, -21)                   # 11 m outside
    helm.set(lat=lat, lon=lon, mode=SrsMode.RTL)
    s.tick()
    assert helm.calls.count("halt") == 1
    s.tick()
    assert helm.calls.count("halt") == 1                # once per breach


@pytest.mark.verifies("MC-009")
def test_link_loss_keeps_last_position(env):
    s, helm, panel, clock, sp = env
    go(env)
    lat, lon = SITE.enu.to_ll(10, 20)
    helm.set(lat=lat, lon=lon)
    s.tick()
    helm.set(link_ok=False)
    s.tick()
    assert s.last_known["lat"] == lat
    assert any("Link to the boat lost" in a for _, a in s.alerts)


@pytest.mark.verifies("MOD-006")
def test_adult_manual_and_drive(env):
    s, helm, panel, clock, sp = env
    tok = armed(env)
    ok, _ = s.command(tok, "manual")
    assert ok and s.state is State.MANUAL
    s.drive(tok, 0.3, -0.2)
    assert helm.calls[-1] == ("drive", 0.3, -0.2)


def test_commands_need_armed(env):
    s, *_ = env
    assert s.command(adult(s), "rtl") == (False, "not armed")


# ---------------------------------------------------------------- PIN
def test_pin_lockout_and_expiry():
    c = Clock()
    lock = PinLock.from_pin(PIN, c)
    for i in range(4):
        assert not lock.unlock("000000").ok
    r = lock.unlock("000000")
    assert not r.ok and "locked" in r.message
    assert not lock.unlock(PIN).ok                      # locked out
    c.t += 301
    r = lock.unlock(PIN)
    assert r.ok and lock.valid(r.token)
    c.t += 599
    assert lock.valid(r.token)
    c.t += 2
    assert not lock.valid(r.token)                      # 10 min unlock


def test_pin_format_and_change(tmp_path):
    c = Clock()
    with pytest.raises(ValueError):
        PinLock.from_pin("1234", c)
    lock = PinLock.from_pin(PIN, c)
    tok = lock.unlock(PIN).token
    assert lock.change(tok, PIN, "135790")
    assert not lock.unlock(PIN).ok and lock.unlock("135790").ok
    f = tmp_path / "settings.json"
    lock.save(f)
    assert oct(f.stat().st_mode & 0o777) == "0o600"
    assert PIN not in f.read_text() and "135790" not in f.read_text()
    assert PinLock.load(c, f).unlock("135790").ok


@pytest.mark.verifies("LOG-002", "MC-008")
def test_pin_never_logged(env, tmp_path):
    s, *_ = env
    s.unlock(PIN)
    s.unlock("111111")
    text = (tmp_path / "session.jsonl").read_text()
    assert PIN not in text and "111111" not in text


@pytest.mark.verifies("LOG-002")
def test_session_log_is_json_lines(env, tmp_path):
    import json
    s, *_ = env
    s.choose_template("lap", "home bay")
    rows = [json.loads(x) for x in
            (tmp_path / "session.jsonl").read_text().splitlines()]
    kinds = {r["kind"] for r in rows}
    assert {"session_start", "plan", "validation", "state"} <= kinds
    assert all(r["t_utc"].endswith("+00:00") for r in rows)


@pytest.mark.verifies("MC-005")
def test_snapshot_has_what_the_map_needs(env):
    import json
    s, *_ = env
    s.choose_template("lap", "home bay")
    snap = s.snapshot()
    for k in ("state", "helm", "track", "site", "plan", "leds", "said"):
        assert k in snap
    assert snap["plan"]["preview"]["furthest_m"] > 0
    json.dumps(snap)                                      # serialisable
