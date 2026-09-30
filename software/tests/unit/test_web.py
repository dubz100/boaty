"""C3 web UI: API contract, PIN gating and the WebSocket push."""
import base64
import json
import os
import socket
import time
import urllib.error
import urllib.request

import pytest

import boaty  # noqa: F401
from boaty.mcn.web import WebUI, ws_accept, ws_frame

from .test_session import PIN, env  # noqa: F401  (fixture)


@pytest.fixture
def ui(env):  # noqa: F811
    s = env[0]
    w = WebUI(s, host="127.0.0.1", port=0, push_hz=20).start()
    yield w, s
    w.stop()


def call(w, path, body=None, tok=None):
    url = f"http://127.0.0.1:{w.port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data,
                               method="POST" if data is not None else "GET")
    r.add_header("Content-Type", "application/json")
    if tok:
        r.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if resp.headers[
                "Content-Type"].startswith("application/json") else raw)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def test_page_and_state(ui):
    w, s = ui
    code, page = call(w, "/")
    assert code == 200 and b"<title>Boaty Mission Control</title>" in page
    assert b"http://" not in page.replace(b"http://www.w3.org", b"")
    code, st = call(w, "/api/state")
    assert code == 200 and st["state"] == "IDLE"


@pytest.mark.verifies("VAL-008", "MC-008")
def test_adult_actions_need_pin(ui):
    w, s = ui
    call(w, "/api/template", {"id": "lap", "area": "home bay"})
    for path in ("/api/approve", "/api/arm", "/api/command",
                 "/api/checklist", "/api/drive"):
        code, j = call(w, path, {"cmd": "rtl", "item": "wind", "ok": True})
        assert code == 401, path
    code, j = call(w, "/api/unlock", {"pin": "000000"})
    assert code == 403 and not j["ok"]
    code, j = call(w, "/api/unlock", {"pin": PIN})
    assert code == 200 and j["token"]
    code, j = call(w, "/api/approve", {}, j["token"])
    assert code == 200 and j["ok"] and s.state.value == "APPROVED"


def test_panel_buttons_over_http(ui):
    w, s = ui
    code, j = call(w, "/api/button", {"button": "GO", "event": "held"})
    assert code == 200 and s.said[-1][1] == "Not yet!"
    code, j = call(w, "/api/button", {"button": "NOPE"})
    assert code == 400


def test_bad_json(ui):
    w, s = ui
    r = urllib.request.Request(f"http://127.0.0.1:{w.port}/api/template",
                               data=b"{not json", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(r, timeout=5)
    assert e.value.code == 400


@pytest.mark.verifies("MC-005")
def test_websocket_pushes_state(ui):
    w, s = ui
    key = base64.b64encode(os.urandom(16)).decode()
    sock = socket.create_connection(("127.0.0.1", w.port), timeout=5)
    sock.sendall((f"GET /ws HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\n"
                  f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                  f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += sock.recv(4096)
    head, rest = buf.split(b"\r\n\r\n", 1)
    assert b"101" in head.split(b"\r\n")[0]
    assert ws_accept(key).encode() in head
    frames, t0 = [], time.monotonic()
    buf = rest
    while len(frames) < 3 and time.monotonic() - t0 < 5:
        buf += sock.recv(65536)
        while len(buf) >= 4:
            n = buf[1] & 0x7F
            off = 2
            if n == 126:
                n, off = int.from_bytes(buf[2:4], "big"), 4
            elif n == 127:
                n, off = int.from_bytes(buf[2:10], "big"), 10
            if len(buf) < off + n:
                break
            assert buf[0] == 0x81
            frames.append(json.loads(buf[off:off + n]))
            buf = buf[off + n:]
    sock.close()
    assert len(frames) >= 3 and frames[0]["state"] == "IDLE"
    dt = time.monotonic() - t0
    assert len(frames) / dt >= 1.0                      # MCN-D16: >= 1 Hz


def test_ws_frame_lengths():
    for n in (5, 200, 70000):
        f = ws_frame("x" * n)
        assert f[0] == 0x81 and f.endswith(b"x" * n)
