"""IF-03 contract tests for B2/B3 (camera + photo server)."""
import hashlib
import io
import json
import time
import urllib.error
import urllib.request

import pytest
from PIL import Image

import boaty  # noqa: F401
from boaty.mcp.camera import FULL, CameraService, PhotoStore, SimCamera
from boaty.mcp.clock import SystemClock
from boaty.mcp.photo_api import PhotoApi
from boaty.mcp.sensors import SimSensors
from boaty.mcp.view import HelmView

TOKEN = "t" * 43


class StubClient:
    def __init__(self):
        self.view, self.clock, self.listeners = HelmView(), SystemClock(), []

    def on_message(self, cb):
        self.listeners.append(cb)


class StubHealth:
    def __init__(self):
        self.s = SimSensors()

    def snapshot(self):
        return {"moisture": self.s.moisture, "box_temp_c": self.s.box_temp_c}


@pytest.fixture
def api(tmp_path):
    client = StubClient()
    v = client.view
    v.lat, v.lon, v.heading, v.pos_t = 52.2448, 0.1597, 90.0, time.monotonic()
    v.helm_heartbeat_t = time.monotonic()
    cam = CameraService(client, PhotoStore(tmp_path),
                        SimCamera((640, 480))).start()
    health = StubHealth()
    a = PhotoApi(cam, TOKEN, health=health, host="127.0.0.1", port=0).start()
    a.client, a.health_stub = client, health
    yield a
    a.stop()
    cam.stop()


def call(api, method, path, body=None, token=TOKEN):
    req = urllib.request.Request(f"http://127.0.0.1:{api.port}{path}",
                                 method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data, timeout=5) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "")
            return r.status, (json.loads(raw) if "json" in ctype else raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


def wait_photos(api, n, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if len(api.store.photos) >= n:
            return
        time.sleep(0.02)
    raise AssertionError(f"expected {n} photos, have {len(api.store.photos)}")


def test_auth_required(api):
    assert call(api, "GET", "/v1/health", token=None)[0] == 401
    assert call(api, "GET", "/v1/health", token="wrong")[0] == 401


def test_health_has_every_field(api):
    code, h = call(api, "GET", "/v1/health")
    assert code == 200
    assert set(h) == {"status", "uptime_s", "cpu_temp_c", "throttled",
                      "storage_free_mb", "photos_unsynced", "moisture",
                      "camera_ok", "mavlink_ok", "rssi_dbm", "box_temp_c",
                      "sw_version"}
    assert h["status"] == "ok" and h["mavlink_ok"]


def test_health_fault_on_moisture(api):
    api.health_stub.s.moisture = True
    assert call(api, "GET", "/v1/health")[1]["status"] == "fault"


def test_session_validation(api):
    code, s = call(api, "PUT", "/v1/session",
                   {"mission_id": "m1", "interval_s": 5,
                    "photo_points": [{"seq": 2, "burst_n": 3}]})
    assert code == 200 and s["mission_id"] == "m1"
    assert call(api, "PUT", "/v1/session", {"interval_s": 1})[0] == 400
    assert call(api, "PUT", "/v1/session",
                {"photo_points": [{"seq": 1, "burst_n": 11}]})[0] == 400


def test_capture_list_fetch_ack(api):
    call(api, "PUT", "/v1/session", {"mission_id": "m1", "interval_s": 0})
    code, _ = call(api, "POST", "/v1/capture", {"count": 2,
                                                "interval_s": 0.5})
    assert code == 202
    wait_photos(api, 2)
    code, photos = call(api, "GET", "/v1/photos?mission=m1")
    assert code == 200 and len(photos) == 2
    p = photos[0]
    assert p["trigger"] == "command" and p["mission_id"] == "m1"
    assert p["lat"] == pytest.approx(52.2448) and p["heading_deg"] == 90.0
    code, jpg = call(api, "GET", f"/v1/photos/{p['id']}")
    assert code == 200 and hashlib.sha256(jpg).hexdigest() == p["sha256"]
    code, thumb = call(api, "GET", f"/v1/photos/{p['id']}/thumb")
    assert code == 200 and max(Image.open(io.BytesIO(thumb)).size) == 320
    assert call(api, "GET", "/v1/health")[1]["photos_unsynced"] == 2
    assert call(api, "POST", "/v1/photos/ack", {"ids": [p["id"]]})[0] == 204
    assert call(api, "GET", "/v1/health")[1]["photos_unsynced"] == 1


def test_exif_geotag(api):
    call(api, "POST", "/v1/capture", {"count": 1})
    wait_photos(api, 1)
    pid = next(iter(api.store.photos))
    img = Image.open(api.store.path(pid))
    gps = img.getexif().get_ifd(0x8825)
    lat = sum(float(x) / 60 ** i for i, x in enumerate(gps[2]))
    assert gps[1] == "N" and lat == pytest.approx(52.2448, abs=1e-5)
    assert gps[3] == "E"


def test_stale_position_gives_null_geotag(api):
    api.client.view.pos_t = time.monotonic() - 2.0      # > 0.5 s old
    call(api, "POST", "/v1/capture", {"count": 1})
    wait_photos(api, 1)
    p = next(iter(api.store.photos.values()))
    assert p.lat is None and p.lon is None and p.heading_deg is None
    assert 0x8825 not in Image.open(api.store.path(p.id)).getexif()


def test_errors(api):
    assert call(api, "GET", "/v1/photos/nope")[0] == 404
    assert call(api, "GET", "/v1/nothing")[0] == 404
    assert call(api, "POST", "/v1/capture", {"count": 11})[0] == 400
    assert call(api, "POST", "/v1/photos/ack", {"ids": "x"})[0] == 400
    api.store.free_override_mb = 100
    code, e = call(api, "POST", "/v1/capture", {"count": 1})
    assert code == 507 and e["error"] == "storage_full"


def test_photo_point_burst_on_mission_item_reached(api):
    class Reached:
        seq = 2

        def get_type(self):
            return "MISSION_ITEM_REACHED"

        def get_srcComponent(self):
            return 1
    call(api, "PUT", "/v1/session",
         {"mission_id": "m2", "photo_points": [{"seq": 2, "burst_n": 3}]})
    t0 = time.monotonic()
    for cb in api.client.listeners:
        cb(Reached(), t0)
    wait_photos(api, 3)
    trig = [p for p in api.store.photos.values() if p.trigger ==
            "photo_point"]
    assert len(trig) == 3 and all(p.point_seq == 2 for p in trig)


def test_full_resolution(tmp_path):
    img = SimCamera().capture("x")
    assert img.size == FULL == (2592, 1944)
