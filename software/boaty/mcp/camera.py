"""B2 camera service and photo store (MCP-D10, MCP-D11, MCP-D13, IF-03).

Captures on three triggers: every interval_s while in AUTO, a burst at each
photo point (within 0.5 s of MISSION_ITEM_REACHED) and on command. Every
photo carries UTC time, lat/lon/heading (null if the position is more than
0.5 s old) and the mission ID, in EXIF and in the index. A thumbnail is made
at capture time.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import queue
import shutil
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from .client import ServiceClient

log = logging.getLogger(__name__)
AUTO = 10
MIN_FREE_MB = 500
FULL = (2592, 1944)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------------------
class SimCamera:
    """Renders a simple scene (sky, water, a caption) instead of a sensor."""

    def __init__(self, size=FULL):
        self.size = size
        self.ok = True

    def capture(self, caption: str = "") -> Image.Image:
        w, h = self.size
        img = Image.new("RGB", (w, h), (120, 170, 210))
        d = ImageDraw.Draw(img)
        d.rectangle([0, h * 0.45, w, h], fill=(40, 90, 110))
        d.text((w * 0.03, h * 0.05), caption, fill=(255, 255, 255))
        return img


class PiCamera:
    """The OV5647 via picamera2 on the Pi Zero (not exercised in SITL)."""

    def __init__(self, size=FULL):
        from picamera2 import Picamera2       # only on the Pi
        self.cam = Picamera2()
        self.cam.configure(self.cam.create_still_configuration(
            main={"size": size}))
        self.cam.start()
        self.ok = True

    def capture(self, caption: str = "") -> Image.Image:
        return self.cam.capture_image("main")


# ---------------------------------------------------------------------------
@dataclass
class Photo:
    id: str
    mission_id: str | None
    taken_utc: str
    lat: float | None
    lon: float | None
    heading_deg: float | None
    trigger: str
    point_seq: int | None
    bytes: int
    sha256: str
    width: int
    height: int
    acked: bool = False


def _dms(value: float):
    v = abs(value)
    d = int(v)
    m = int((v - d) * 60)
    s = round((v - d - m / 60) * 3600, 4)
    return (float(d), float(m), float(s))


def jpeg_with_exif(img: Image.Image, p: Photo) -> bytes:
    exif = img.getexif()
    exif[0x0132] = p.taken_utc[:19].replace("-", ":").replace("T", " ")
    exif[0x010E] = json.dumps({"mission_id": p.mission_id,
                               "trigger": p.trigger,
                               "point_seq": p.point_seq})
    if p.lat is not None and p.lon is not None:
        gps = exif.get_ifd(0x8825)
        gps[1] = "N" if p.lat >= 0 else "S"
        gps[2] = _dms(p.lat)
        gps[3] = "E" if p.lon >= 0 else "W"
        gps[4] = _dms(p.lon)
        if p.heading_deg is not None:
            gps[16] = "T"
            gps[17] = float(p.heading_deg)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, exif=exif)
    return buf.getvalue()


class PhotoStore:
    def __init__(self, root: Path, min_free_mb: int = MIN_FREE_MB,
                 reserve_mb: int = 5000):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.min_free_mb = min_free_mb
        self.reserve_mb = reserve_mb
        self.lock = threading.Lock()
        self.index_path = self.root / "index.jsonl"
        self.photos: dict[str, Photo] = {}
        if self.index_path.exists():
            for line in self.index_path.read_text().splitlines():
                ph = Photo(**json.loads(line))
                self.photos[ph.id] = ph
        self.free_override_mb: int | None = None      # tests

    def free_mb(self) -> int:
        if self.free_override_mb is not None:
            return self.free_override_mb
        return int(shutil.disk_usage(self.root).free / 1e6)

    def full(self) -> bool:
        return self.free_mb() < self.min_free_mb

    def add(self, img: Image.Image, p: Photo) -> Photo:
        data = jpeg_with_exif(img, p)
        p.bytes, p.sha256 = len(data), hashlib.sha256(data).hexdigest()
        p.width, p.height = img.size
        thumb = img.copy()
        thumb.thumbnail((320, 320))
        tbuf = io.BytesIO()
        thumb.save(tbuf, "JPEG", quality=80)
        with self.lock:
            (self.root / f"{p.id}.jpg").write_bytes(data)
            (self.root / f"{p.id}.thumb.jpg").write_bytes(tbuf.getvalue())
            self.photos[p.id] = p
            self._write_index()
        return p

    def _write_index(self) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(asdict(ph)) + "\n"
                               for ph in self.photos.values()))
        tmp.replace(self.index_path)

    def list(self, mission: str | None = None, since: str | None = None):
        with self.lock:
            out = [p for p in self.photos.values()
                   if (mission is None or p.mission_id == mission)
                   and (since is None or p.taken_utc > since)]
        return sorted(out, key=lambda p: p.taken_utc)

    def path(self, pid: str, thumb: bool = False) -> Path | None:
        if pid not in self.photos:
            return None
        return self.root / (f"{pid}.thumb.jpg" if thumb else f"{pid}.jpg")

    def ack(self, ids) -> int:
        n = 0
        with self.lock:
            for i in ids:
                if i in self.photos and not self.photos[i].acked:
                    self.photos[i].acked = True
                    n += 1
            self._write_index()
        return n

    def unsynced(self) -> int:
        return sum(1 for p in self.photos.values() if not p.acked)


# ---------------------------------------------------------------------------
class CameraService:
    """B2. Listens only (IF-04): its client never sends commands."""
    name = "B2"

    def __init__(self, client: ServiceClient, store: PhotoStore,
                 camera=None, max_pos_age_s: float = 0.5):
        self.c, self.v, self.clock = client, client.view, client.clock
        self.store, self.camera = store, camera or SimCamera()
        self.max_pos_age_s = max_pos_age_s
        self.session = {"mission_id": None, "interval_s": 0,
                        "photo_points": []}
        self.q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._last_interval = None
        self._seen_reached = 0
        self.captured: list[tuple[float, str, str]] = []  # (t, trigger, id)
        client.on_message(self._on_msg)

    def start(self) -> "CameraService":
        for fn in (self._worker, self._timer):
            threading.Thread(target=fn, daemon=True).start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self.q.put(None)

    def set_session(self, s: dict) -> dict:
        iv = int(s.get("interval_s", 0))
        if iv != 0 and not 2 <= iv <= 30:
            raise ValueError("interval_s must be 0 or 2..30")
        pts = [{"seq": int(p["seq"]), "burst_n": int(p.get("burst_n", 1))}
               for p in s.get("photo_points", [])]
        if any(not 1 <= p["burst_n"] <= 10 for p in pts):
            raise ValueError("burst_n must be 1..10")
        self.session = {"mission_id": s.get("mission_id") or str(uuid.uuid4()),
                        "interval_s": iv, "photo_points": pts}
        return self.session

    def request(self, trigger: str, count: int = 1, interval_s: float = 0.5,
                point_seq: int | None = None) -> None:
        for i in range(count):
            self.q.put((trigger, point_seq, i * interval_s))

    # ------------------------------------------------------------------
    def _on_msg(self, m, now) -> None:
        if m.get_type() == "MISSION_ITEM_REACHED" and m.get_srcComponent() \
                == 1:
            for p in self.session["photo_points"]:
                if p["seq"] == m.seq:
                    self.request("photo_point", p["burst_n"], 0.5, m.seq)

    def _timer(self) -> None:
        while not self._stop.is_set():
            iv = self.session["interval_s"]
            now = self.clock.now()
            if iv and self.v.armed and self.v.mode == AUTO:
                if self._last_interval is None or now - self._last_interval \
                        >= iv:
                    self._last_interval = now
                    self.request("interval")
            else:
                self._last_interval = None
            self.clock.sleep(0.1)

    def _worker(self) -> None:
        while not self._stop.is_set():
            job = self.q.get()
            if job is None:
                return
            trigger, seq, delay = job
            if delay:
                self.clock.sleep(delay)
            if self.store.full():
                log.warning("storage full: capture skipped")
                continue
            try:
                self._capture(trigger, seq)
            except Exception:  # noqa: BLE001
                self.camera.ok = False
                log.exception("capture failed")

    def _capture(self, trigger: str, seq: int | None) -> Photo:
        v, now = self.v, self.clock.now()
        fresh = v.lat is not None and now - v.pos_t <= self.max_pos_age_s
        pid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + \
            "-" + uuid.uuid4().hex[:6]
        p = Photo(id=pid, mission_id=self.session["mission_id"],
                  taken_utc=utc_now(),
                  lat=v.lat if fresh else None, lon=v.lon if fresh else None,
                  heading_deg=v.heading if fresh else None, trigger=trigger,
                  point_seq=seq, bytes=0, sha256="", width=0, height=0)
        img = self.camera.capture(f"{trigger} {seq or ''} {p.lat} {p.lon}")
        self.store.add(img, p)
        self.captured.append((now, trigger, pid))
        return p
