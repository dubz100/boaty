"""Slice 3: Mission Control (C1-C10) against the real firmware.

Mission Control runs as it would on the Pi 5: session manager, planner,
validator, guarded helm (C7), photo sync, with the boat services B2-B7 on
the simulated Pi Zero. Claude's replies come from a stand-in client (the
live API is exercised by tools/nli_eval.py); everything after the reply is
the real code path.
"""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from boaty.helm.api import MissionItem, RoverMode, SrsMode
from boaty.mcn.helm_guard import GuardedHelm
from boaty.mcn.llm import IntentClient
from boaty.mcn.log import SessionLog
from boaty.mcn.panel import Button, SimPanel
from boaty.mcn.photos import BoatApi
from boaty.mcn.pin import PinLock
from boaty.mcn.planning import Planning
from boaty.mcn.session import CHECKLIST, Config, Session, State
from boaty.mcn.site import SITES, Site
from boaty.mcn.voice import PHRASES, RecordingSpeaker

from .conftest import SPEEDUP, Watch, boaty_events, motors_off, \
    outputs_neutral

PIN = "271828"
T_FMT = "%Y-%m-%dT%H:%M:%SZ"


def intent_reply(steps, summary="Let's go exploring!"):
    body = {"schema": "boaty.intent/1", "summary_for_child": summary,
            "speed": "normal", "steps": steps + [{"op": "return_home"}],
            "declined": None}
    return SimpleNamespace(
        stop_reason="end_turn", id="msg_sim", _request_id="req_sim",
        content=[SimpleNamespace(type="text", text=json.dumps(body))],
        usage=SimpleNamespace(input_tokens=1000, output_tokens=150))


class StandInClaude:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(
            create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        return self.replies.pop(0)


class MC(SimpleNamespace):
    def adult(self):
        r = self.session.unlock(PIN)
        assert r.ok
        return r.token

    def approve_and_arm(self):
        tok = self.adult()
        ok, msg = self.session.approve(tok)
        assert ok, msg
        for k, _ in CHECKLIST:
            self.session.sign(tok, k, True, by="Dad")
        ok, why = self.session.arm(tok)
        assert ok, (why, self.guard.state.param_diff)
        return tok

    def spoken_after(self, t):
        return [(ts, x) for ts, x in self.speaker.said if ts >= t]


def make_mc(sim, helm, tmp_path, services=None, claude=None, site=None,
            helm_proxy=None):
    site = site or Site.named("milton-country-park")
    clock = lambda: sim.t                                   # noqa: E731
    log = SessionLog(tmp_path / "session.jsonl")
    guard = GuardedHelm(helm_proxy or helm, sim.cfg.param_files)
    guard.check_params()
    speaker = RecordingSpeaker(clock)
    planning = Planning(site, IntentClient(claude) if claude else None)
    api = None
    if services is not None:
        api = BoatApi(f"http://127.0.0.1:{services.api.port}", "test-token")
    s = Session(site, guard, planning, speaker, pin=PinLock.from_pin(PIN,
                                                                      clock),
                log=log, clock=clock,
                utc=lambda: time.strftime(T_FMT, time.gmtime()),
                boat_api=api, photo_dir=tmp_path / "photos",
                cfg=Config(reference=(52.2448, 0.1597)))
    s.start(period_s=0.2 / SPEEDUP)
    panel = SimPanel(s.button, clock, lambda x: sim.wait(x))
    return MC(session=s, guard=guard, speaker=speaker, panel=panel, log=log,
              site=site, api=api, claude=claude)


@pytest.fixture
def mc_factory(sim, helm, tmp_path):
    made = []

    def f(**kw):
        m = make_mc(sim, helm, tmp_path, **kw)
        made.append(m)
        return m
    yield f
    for m in made:
        m.session.close()


def site_xy(site, lat, lon):
    return site.enu.to_xy(lat, lon)


# ---------------------------------------------------------------------------
@pytest.mark.verifies("SWE-003", "LOG-002")
def test_e2e_explore_photos_home(sim, helm, services, companion, mc_factory,
                                 evidence):
    evidence("MC-E2E", "Explore the pond, take photos, come home",
             ["NLI-001", "NLI-005", "VAL-001", "VAL-010", "MCN-D12",
              "MCN-D43", "MCN-D47", "MCN-D49", "CAM-007", "IF-03", "IF-13"],
             "Typed instruction to captain's log with no adult touching the "
             "boat: plan validates, read-back checksum matches, the boat "
             "flies it inside the fence, stops at the photo point, comes "
             "home, auto-disarms after 60 s, photos are synced and sha256 "
             "verified before ack")
    claude = StandInClaude(intent_reply([
        {"op": "explore", "area": "home bay", "coverage": "light"},
        {"op": "visit", "landmark": "the island", "photos": 3, "hold_s": 10}],
        "Let's explore the bay and take pictures of the island!"))
    mc = mc_factory(services=services, claude=claude)
    s = mc.session
    out = s.instruct("explore the bay and take photos of the island, then "
                     "come home")
    assert out.ok, out.adult
    assert s.state is State.PLAN_READY
    m = out.mission
    mc.approve_and_arm()
    assert s.state is State.ARMED
    # VAL-010 on the real helm
    _, items = helm.read_back()
    from boaty.mcn.models import helm_view, helm_view_of, view_checksum
    same = view_checksum(helm_view(m.items)) == view_checksum(
        helm_view_of(items))
    t_go = sim.t
    mc.panel.press(Button.GO, hold_s=1.05)
    assert s.state is State.MISSION
    # Fly: record worst clearance from the fence and no-go zones.
    worst_fence, worst_zone = 1e9, 1e9
    incl = list(mc.site.inclusion)
    from boaty.mcn import geo
    t_rtl = t_home = None
    end = sim.t + m.estimates.duration_s + 200
    while sim.t < end:
        st = helm.status()
        if st.lat is not None:
            xy = site_xy(mc.site, st.lat, st.lon)
            worst_fence = min(worst_fence, geo.signed_depth(xy, incl))
            worst_zone = min(worst_zone, min(z.depth(xy)
                                             for z in mc.site.zones))
        if t_rtl is None and s.state is State.RETURNING:
            t_rtl = sim.t
        if s.state is State.DEBRIEF:
            t_home = sim.t
            break
        time.sleep(0.1 / SPEEDUP)
    assert t_home is not None, f"never finished: {s.state} {helm.status()}"
    # Debrief: photo sync runs in the background.
    ok = sim.wait_until(lambda: s.captains_log is not None, 60)
    rep = s.sync_report
    listing = mc.api.photos(m.id)
    pp = [p for p in listing if p["trigger"] == "photo_point"]
    home_said = [ts for ts, x in mc.speaker.said if x == PHRASES["home"]]
    disarm_rows = [r for r in mc.log.rows if r["kind"] == "command"
                   and r.get("cmd") == "auto_disarm"]
    llm_rows = mc.log.of("llm")
    evidence.measure(
        items=len(m.items), planned_s=m.estimates.duration_s,
        flown_s=(t_rtl - t_go) if t_rtl else None,
        total_s=t_home - t_go, readback_checksum_equal=same,
        min_fence_clearance_m=worst_fence, min_zone_clearance_m=worst_zone,
        photos=len(listing), photo_point_photos=len(pp),
        synced=rep.verified if rep else None, acked=rep.acked if rep else None,
        bad_hash=len(rep.bad_hash) if rep else None,
        home_to_disarm_s=(t_home - home_said[0]) if home_said else None,
        captains_log=bool(s.captains_log),
        llm_logged=len(llm_rows), spoken=[x for _, x in mc.speaker.said])
    evidence.note("Clearances are from the helm's reported position; the "
                  "validator's 3 m margin is on the planned route.")
    assert same
    assert worst_fence > 0 and worst_zone > 0
    assert len(pp) >= 3 and rep and rep.verified == len(listing) and \
        rep.acked == len(listing) and not rep.bad_hash
    assert home_said and 59 <= t_home - home_said[0] <= 63
    assert disarm_rows and not helm.status().armed
    assert ok and s.captains_log.exists()
    assert "Off we go!" in [x for _, x in mc.speaker.said]
    assert llm_rows and llm_rows[0]["request_id"] == "req_sim"
    assert mc.api.health()["photos_unsynced"] == 0


def test_sc09_stop_in_every_armed_state(sim, helm, services, mc_factory,
                                        evidence):
    evidence("SC-09", "STOP in every state", ["FS-009", "MCN-D10", "SC-09"],
             "From ARMED, MISSION, RETURNING and MANUAL: helm.stop() called "
             "<= 50 ms after the button edge; motors off <= 1 s")
    mc = mc_factory(services=services)
    s = mc.session
    res = {}
    for state in ("ARMED", "MISSION", "RETURNING", "MANUAL"):
        out = s.choose_template("lap", "home bay")
        assert out.ok, out.adult
        tok = mc.approve_and_arm()
        if state != "ARMED":
            mc.panel.press(Button.GO, hold_s=1.05)
            sim.wait(8)
        if state == "RETURNING":
            mc.panel.press(Button.COME_HOME)
            sim.wait(3)
        if state == "MANUAL":
            assert s.command(tok, "manual")[0]
            for _ in range(20):
                s.drive(tok, 0.6, 0.0)
                sim.wait(0.1)
        assert s.state.value == state, s.state
        t0 = sim.t
        w = Watch(sim, lambda: outputs_neutral(sim))
        mc.panel.press(Button.STOP, hold_s=0.05)
        t_off = w.result(sim, 5)
        res[state] = dict(edge_to_call_ms=round(s.stop_latency_s[-1] * 1000,
                                                1),
                          outputs_neutral_s=(t_off - t0) if t_off else None,
                          disarmed=not helm.status().armed,
                          after=s.state.value)
        sim.wait(3)
        s.state = State.IDLE                     # next round
        s.photos_expected = False
        b = sim.boat                             # carry it back to the jetty
        b.n = b.e = b.u = b.v = b.r = 0.0
        sim.wait(10)
    evidence.measure(**{k: v for k, v in res.items()})
    for state, r in res.items():
        assert r["edge_to_call_ms"] <= 50, (state, r)
        assert r["outputs_neutral_s"] is not None and \
            r["outputs_neutral_s"] <= 1.0, (state, r)
        assert r["disarmed"], (state, r)


def test_sc24_parameter_differs(sim, helm, mc_factory, evidence):
    evidence("SC-24", "Parameter differs from baseline",
             ["FM-09", "MCN-D45", "SAF-007", "SC-24"],
             "Change one failsafe parameter: arming blocked, the difference "
             "shown; put it back and arming works")
    helm.set_param("FS_GCS_TIMEOUT", 10)
    mc = mc_factory()
    s = mc.session
    s.choose_template("lap", "home bay")
    tok = mc.adult()
    assert s.approve(tok)[0]
    for k, _ in CHECKLIST:
        s.sign(tok, k, True)
    ok, why = s.arm(tok)
    diff = mc.guard.state.param_diff
    evidence.measure(arm_ok=ok, reasons=why,
                     difference={k: list(v) for k, v in diff.items()})
    assert not ok and any("FS_GCS_TIMEOUT" in w for w in why)
    assert diff == {"FS_GCS_TIMEOUT": (2.0, 10.0)}
    assert not helm.status().armed
    helm.set_param("FS_GCS_TIMEOUT", 2)
    mc.guard.check_params()
    ok, why = s.arm(tok)
    evidence.measure(arm_ok_after_restore=ok)
    assert ok, why
    helm.stop()


class Tamper:
    """Between C7 and the helm: drop the fence, or alter one item."""

    def __init__(self, helm, drop_fence=False, shift_item=None):
        self._h, self.drop_fence, self.shift_item = helm, drop_fence, \
            shift_item

    def __getattr__(self, k):
        return getattr(self._h, k)

    def upload_fence(self, f):
        if not self.drop_fence:
            self._h.upload_fence(f)

    def upload_mission(self, m):
        if self.shift_item is not None:
            items = list(m.items)
            it = items[self.shift_item]
            items[self.shift_item] = MissionItem(
                it.command, it.lat + 0.00005, it.lon, it.alt, it.params,
                it.frame)                         # ~5.5 m north
            m = type(m)(tuple(items))
        self._h.upload_mission(m)


def test_sc25_fence_missing(sim, helm, mc_factory, evidence):
    evidence("SC-25", "Fence missing or disabled", ["FM-10", "SC-25",
                                                    "PRE-002"],
             "Skip the fence upload: approval (and so arming) refused")
    mc = mc_factory(helm_proxy=Tamper(helm, drop_fence=True))
    s = mc.session
    s.choose_template("lap", "home bay")
    tok = mc.adult()
    ok, msg = s.approve(tok)
    row = mc.log.of("upload")[-1]
    evidence.measure(approved=ok, fence_ok=row["fence_ok"],
                     state=s.state.value)
    assert not ok and not row["fence_ok"] and s.state is State.PLAN_READY
    assert s.arm(tok)[0] is False


def test_sc26_site_file_swapped_or_wrong(sim, helm, mc_factory, tmp_path,
                                         evidence):
    evidence("SC-26", "Site file lat/lon swapped; wrong site",
             ["FM-11", "MCN-D53", "SC-26", "IF-15"],
             "Linter and pre-arm both refuse; the good site's fence "
             "round-trips through IF-02 exactly")
    from boaty.mcn.helm_guard import _same_fence
    from boaty.mcn.site import blocking, lint
    good = json.loads((SITES / "milton-country-park.geojson").read_text())
    # 1. Fence round-trip for the good file (IF-15 verification).
    site = Site.from_geojson(good)
    helm.upload_fence(site.fence())
    fence, _ = helm.read_back()
    rt = _same_fence(fence, site.fence())
    # 2. Swapped coordinates.
    bad = json.loads(json.dumps(good))
    for f in bad["features"]:
        g = f["geometry"]
        if g["type"] == "Point":
            g["coordinates"] = g["coordinates"][::-1]
        else:
            g["coordinates"] = [[p[::-1] for p in r]
                                for r in g["coordinates"]]
    swapped = [str(i) for i in blocking(lint(bad, (52.2448, 0.1597)))]
    # 3. A valid file for a different lake (moved 5 km north).
    other = json.loads(json.dumps(good))
    for f in other["features"]:
        g = f["geometry"]
        rings = [[g["coordinates"]]] if g["type"] == "Point" else \
            g["coordinates"]
        for r in rings:
            for p in r:
                p[1] += 0.045
    wrong = [str(i) for i in blocking(lint(other, (52.2448, 0.1597)))]
    # Pre-arm: a session on the wrong site refuses to arm.
    mc = mc_factory(site=Site.from_geojson(other))
    s = mc.session
    tok = mc.adult()
    out = s.choose_template("lap", "home bay")
    approve = s.approve(tok) if out.ok else (False, out.adult)
    evidence.measure(fence_round_trip=rt, swapped_errors=swapped,
                     wrong_site_errors=wrong, plan_ok=out.ok,
                     approve=list(approve), plan_adult=out.adult)
    assert rt
    assert swapped and "[lat, lon]" in swapped[0]
    assert wrong and "km from its configured reference" in wrong[0]
    assert not approve[0]
    assert s.state is not State.APPROVED


def test_sc32_readback_corruption(sim, helm, mc_factory, evidence):
    evidence("SC-32", "Read-back corruption", ["FM-35", "FM-47", "SC-32",
                                               "VAL-010", "MCN-D43"],
             "One item altered in transfer: checksum differs, not approved, "
             "GO stays disabled")
    mc = mc_factory(helm_proxy=Tamper(helm, shift_item=2))
    s = mc.session
    s.choose_template("lap", "home bay")
    tok = mc.adult()
    ok, msg = s.approve(tok)
    row = mc.log.of("upload")[-1]
    s.state = State.ARMED                         # even if forced...
    mc.panel.press(Button.GO, hold_s=1.05)
    evidence.measure(approved=ok, expected=row["helm_view"],
                     read_back=row["read_back"], auto_after_go=helm.status()
                     .mode is SrsMode.AUTO)
    assert not ok and row["helm_view"] != row["read_back"]
    assert helm.status().mode is not SrsMode.AUTO     # ...GO refused by C7


def test_sc35_home_sanity(sim, helm, mc_factory, evidence):
    evidence("SC-35", "Home sanity", ["FM-46", "SC-35", "VAL-004"],
             "Boat's home 30 m from the site's home: the plan is refused "
             "before approval")
    good = json.loads((SITES / "milton-country-park.geojson").read_text())
    from boaty.mcn.geo import Enu
    e = Enu(52.2448, 0.1597)
    moved = json.loads(json.dumps(good))
    for f in moved["features"]:
        if f["properties"]["role"] == "home":
            lat, lon = e.to_ll(0, 30)
            f["geometry"]["coordinates"] = [lon, lat]
    mc = mc_factory(site=Site.from_geojson(moved))
    out = mc.session.choose_template("lap", "home bay")
    rules = [v.rule for v in out.result.violations] if out.result else []
    evidence.measure(plan_ok=out.ok, rules=rules, adult=out.adult)
    assert not out.ok and "VAL-004" in rules


def test_sc37_foreign_gcs(sim, helm, services, companion, mc_factory,
                          evidence):
    evidence("SC-37", "Foreign GCS heartbeat", ["FM-41", "MCN-D57", "SC-37",
                                                "V-06b"],
             "Second system-255 source: C7 detects it within 3 s, refuses "
             "arming and GO, alarms; STOP still works; clears when it goes")
    mc = mc_factory(services=services)
    s = mc.session
    s.choose_template("lap", "home bay")
    mc.approve_and_arm()
    t0 = sim.t
    companion.heartbeat_as = (255, 190)
    t_det = sim.wait_until(lambda: s._impostor_alerted, 10)
    mc.panel.press(Button.GO, hold_s=1.05)
    go_refused = helm.status().mode is not SrsMode.AUTO
    alarm = any("Another ground station" in a for _, a in s.alerts)
    spoken = PHRASES["impostor"] in [x for _, x in mc.speaker.said]
    companion.heartbeat_as = None
    t_clear0 = sim.t
    t_clear = sim.wait_until(lambda: not mc.guard.impostors(), 10)
    mc.panel.press(Button.GO, hold_s=1.05)
    sim.wait(2)
    go_after = helm.status().mode is SrsMode.AUTO
    mc.panel.press(Button.STOP)
    evidence.measure(detect_s=(t_det - t0) if t_det else None,
                     go_refused=go_refused, alarm=alarm, spoken=spoken,
                     clear_s=(t_clear - t_clear0) if t_clear else None,
                     go_after_clear=go_after)
    assert t_det is not None and t_det - t0 <= 3.5
    assert go_refused and alarm and spoken
    assert go_after
    assert not helm.status().armed


def test_mcn_d59_persistent_breach_without_b7(sim, helm, companion,
                                              mc_factory, evidence):
    evidence("MCN-D59", "C1 stops the motors on a persistent breach",
             ["FEN-006", "MCN-D59", "A-18", "FM-14"],
             "Boat services not running (no B7). Gale pushes the boat out of "
             "the site fence: C1 commands HOLD before 30 s or 10 m outside; "
             "motors stay off")
    mc = mc_factory()
    s = mc.session
    s.choose_template("explore", "home bay")
    mc.approve_and_arm()
    mc.panel.press(Button.GO, hold_s=1.05)
    sim.wait(15)
    from boaty.mcn import geo
    incl = list(mc.site.inclusion)

    def outside():
        st = helm.status()
        if st.lat is None:
            return 0.0
        return -geo.signed_depth(site_xy(mc.site, st.lat, st.lon), incl)
    sim.boat.faults.wind_speed, sim.boat.faults.wind_from_deg = 15.0, 0.0
    t_out = sim.wait_until(lambda: outside() > 0.3, 180)
    assert t_out, "gale did not push the boat out"
    t_halt = sim.wait_until(
        lambda: any(r.get("cmd") == "halt" for r in mc.log.of("command")),
        45)
    out_at = outside()
    running = 0.0
    end = sim.t + 20
    while sim.t < end:
        if not motors_off(sim):
            running += 0.05
        time.sleep(0.05 / SPEEDUP)
    sim.boat.faults.wind_speed = 0.0
    evidence.measure(halt_after_s=(t_halt - t_out) if t_halt else None,
                     outside_at_halt_m=out_at, motors_running_next_20s=running,
                     spoken=PHRASES["fence"] in [x for _, x in
                                                  mc.speaker.said],
                     helm_mode=helm.status().mode.value)
    assert t_halt is not None and t_halt - t_out <= 31
    assert out_at <= 11
    assert running <= 2.0
    helm.stop()


def test_mcn_d60_b7_hold_spoken_and_pin_resume(sim, helm, services,
                                               companion, mc_factory,
                                               evidence):
    evidence("MCN-D60", "B7 hold is shown and spoken; resuming needs the PIN",
             ["MCN-D60", "MCN-D12", "MOD-007", "A-08"],
             "Dead motor mid-mission: the boat stops itself; Mission Control "
             "says why within 2 s of the helm reporting it; resume refused "
             "without the PIN, accepted with it")
    mc = mc_factory(services=services)
    s = mc.session
    s.choose_template("explore", "home bay")
    mc.approve_and_arm()
    mc.panel.press(Button.GO, hold_s=1.05)
    sim.wait(10)
    t0 = sim.t
    sim.boat.faults.thrust_scale = [1.0, 0.0]
    t_held = sim.wait_until(lambda: s.held_reason is not None, 150)
    said = [(ts, x) for ts, x in mc.speaker.said if ts >= t0]
    t_said = next((ts for ts, x in said if x == PHRASES["held"]), None)
    holds = [tm for tm, armed, m in companion.modes
             if m == RoverMode.HOLD and t0 <= tm <= (t_held or sim.t)]
    t_hold = holds[-1] if holds else None          # the final HOLD
    reason = s.held_reason
    sim.boat.faults.thrust_scale = [1.0, 1.0]
    with pytest.raises(PermissionError):
        s.command("not-a-token", "resume")
    ok, msg = s.command(mc.adult(), "resume")
    sim.wait(3)
    mode_after = helm.status().mode
    evidence.measure(held_after_s=(t_held - t0) if t_held else None,
                     final_helm_hold_after_s=(t_hold - t0) if t_hold else None,
                     said_after_final_hold_s=(t_said - t_hold)
                     if t_said and t_hold else None,
                     spoken=[x for _, x in said], reason=reason,
                     alerts=[a for ts, a in s.alerts if ts >= t0],
                     resumed=ok, mode_after_resume=mode_after.value,
                     events=boaty_events(companion, t0))
    assert t_held is not None and t_said is not None and t_hold is not None
    assert t_said - t_hold <= 2.0
    episodes = sum("SHED START" in e for e in boaty_events(companion, t0))
    assert [x for _, x in said].count(PHRASES["stuck"]) == episodes
    assert ok and mode_after in (SrsMode.AUTO, SrsMode.RTL)
    helm.stop()


# ---------------------------------------------------------------------------
# SC-12 (FS-012): every failsafe is logged and announced within 2 s.

def _gnss_off(helm, sim, services):
    helm.set_param_sim("SIM_GPS1_ENABLE", 0)


def _gnss_on(helm, sim, services):
    helm.set_param_sim("SIM_GPS1_ENABLE", 1)


FAILSAFES = {
    "battery": (lambda h, s, sv: setattr(s.boat.faults,
                                         "phantom_current_a", 50.0),
                lambda h, s, sv: setattr(s.boat.faults,
                                         "phantom_current_a", 0.0),
                "FS-001"),
    "gnss": (_gnss_off, _gnss_on, "FS-004"),
    "water": (lambda h, s, sv: setattr(sv.sensors, "moisture", True),
              lambda h, s, sv: setattr(sv.sensors, "moisture", False),
              "FS-010"),
    "weed": (lambda h, s, sv: setattr(s.boat.faults, "extra_drag", 3000.0),
             lambda h, s, sv: setattr(s.boat.faults, "extra_drag", 0.0),
             "FS-005/006"),
}


@pytest.mark.parametrize("kind", list(FAILSAFES))
@pytest.mark.verifies("LOG-002", "MC-007")
def test_sc12_failsafe_logged_and_announced(sim, helm, services, companion,
                                            mc_factory, evidence, kind):
    inject, clear, ref = FAILSAFES[kind]
    evidence("SC-12", f"Failsafe logged and announced ({kind}, {ref})",
             ["FS-012", "SC-12", ref.split("/")[0]],
             "The boat's failsafe action (helm mode change away from AUTO, "
             "or a BOATY event) is in the session log, and Mission Control "
             "speaks or shows it within 2 s")
    mc = mc_factory(services=services)
    s = mc.session
    s.choose_template("explore", "home bay")
    mc.approve_and_arm()
    mc.panel.press(Button.GO, hold_s=1.05)
    sim.wait(10)
    t0 = sim.t
    n_log = len(mc.log.rows)
    inject(helm, sim, services)
    # The boat's own action: first mode change after the fault (helm or
    # boat service), or its first BOATY event text.
    def boat_acted():
        m = [tm for tm, a, mo in companion.modes if tm >= t0 and
             mo != RoverMode.AUTO]
        e = [tm for tm, x in companion.texts if tm >= t0 and
             x.startswith("BOATY")]
        return min(m + e) if m or e else None
    t_act = sim.wait_until(lambda: boat_acted() is not None, 400)
    t_act = boat_acted()
    sim.wait(4)
    clear(helm, sim, services)
    told = sorted([ts for ts, x in mc.speaker.said if ts >= t0] +
                  [ts for ts, x in s.alerts if ts >= t0])
    t_told = next((ts for ts in told if t_act is not None and
                   ts >= t_act - 0.5), None)
    new = mc.log.rows[n_log:]
    kinds = sorted({r["kind"] for r in new if r["kind"] in
                    ("helm_mode", "boat_event", "alert")})
    evidence.measure(boat_acted_after_s=(t_act - t0) if t_act else None,
                     announced_after_action_s=(t_told - t_act)
                     if t_told and t_act else None,
                     spoken=[x for ts, x in mc.speaker.said if ts >= t0][:4],
                     alerts=[a for ts, a in s.alerts if ts >= t0][:3],
                     log_kinds=kinds,
                     events=boaty_events(companion, t0))
    assert t_act is not None, "the boat never acted on the fault"
    assert t_told is not None and t_told - t_act <= 2.0
    assert kinds, "nothing in the session log"
    helm.stop()
