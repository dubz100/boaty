"""IF-04 event vocabulary (boaty/mcp/events.py; SDR RID-05)."""
import re
from pathlib import Path

import boaty  # noqa: F401
from boaty.mcp import events as E

SRC = Path(E.__file__).parent


def sample(ev):
    return ev.format(**(ev.example or {}))


def test_every_event_fits_a_statustext():
    for ev in E.EVENTS:
        assert len(E.PREFIX + sample(ev)) <= E.MAX_LEN, ev.text


def test_every_event_round_trips_and_is_unambiguous():
    for ev in E.EVENTS:
        hits = [x for x in E.EVENTS if x.pattern.match(sample(ev))]
        assert hits == [ev], (ev.text, [h.text for h in hits])
        assert E.match(E.PREFIX + sample(ev)) is ev


def test_unknown_text_is_not_an_event():
    assert E.match("BOATY B9 SOMETHING NEW") is None


def test_fields_are_known():
    for ev in E.EVENTS:
        assert ev.service in ("B4", "B5", "B6", "B7")
        assert ev.severity in ("warning", "critical")
        assert ev.mc in ("held", "shed", "alert", "info")
        assert ev.text.startswith(ev.service + " ")
        names = set(re.findall(r"\{(\w+)\}", ev.text))
        assert names == set(ev.example or {}), ev.text


def test_services_send_only_vocabulary_events():
    """No event text is written inline in the services: every send goes
    through events.py, so the ICD table and Mission Control can't drift."""
    src = (SRC / "services.py").read_text()
    inline = re.findall(r'"B[4-7] [A-Z][^"]*"', src)
    assert not inline, inline
    assert "self.c.event(" not in src.replace(
        "self.c.event(ev.format(**fields), SEVERITY[ev.severity])", "")


def test_mission_control_classifies_by_vocabulary():
    src = (SRC.parent / "mcn" / "session.py").read_text()
    assert "E.match(" in src
    assert not re.search(r'"(STILL STUCK|NO CONTROL|B5 SHED)', src)
