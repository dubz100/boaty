"""C8: the boat's photo API client, photo sync and the captain's log.

BoatApi is Mission Control's side of ICD IF-03. sync() copies a mission's
photos (thumbnails first, then full images), checks each full image's
sha256 against the boat's record, and only then acknowledges it, so the
boat may later delete it (MCN-D47). Photos stay on Mission Control; nothing
is published or sent anywhere.

captains_log() writes the child's trip story as HTML (MCN-D49): up to six
photos (photo-point photos first), a route map, distance, duration and a
short story.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .models import Mission


class ApiError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:200]}")
        self.status = status


class BoatApi:
    def __init__(self, base_url: str, token: str, timeout: float = 10.0):
        self.base, self.token, self.timeout = base_url.rstrip("/"), token, \
            timeout

    def _req(self, method: str, path: str, body=None) -> bytes:
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method)
        r.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, e.read().decode(errors="replace")) from None

    def health(self) -> dict:
        return json.loads(self._req("GET", "/v1/health"))

    def set_session(self, m: Mission) -> dict:
        pts = [{"seq": i.seq, "burst_n": i.photos} for i in m.items
               if i.kind == "photo_point"]
        return json.loads(self._req("PUT", "/v1/session", {
            "mission_id": m.id, "interval_s": m.capture.interval_s,
            "photo_points": pts}))

    def photos(self, mission_id: str | None = None) -> list[dict]:
        q = f"?mission={mission_id}" if mission_id else ""
        return json.loads(self._req("GET", "/v1/photos" + q))

    def thumb(self, pid: str) -> bytes:
        return self._req("GET", f"/v1/photos/{pid}/thumb")

    def full(self, pid: str) -> bytes:
        return self._req("GET", f"/v1/photos/{pid}")

    def ack(self, ids: list[str]) -> None:
        self._req("POST", "/v1/photos/ack", {"ids": ids})


@dataclass
class SyncReport:
    listed: int = 0
    copied: int = 0
    verified: int = 0
    acked: int = 0
    bad_hash: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def sync(api: BoatApi, mission_id: str, dest: Path, log=None) -> SyncReport:
    log = log or (lambda *a, **k: None)
    dest = Path(dest)
    (dest / "thumbs").mkdir(parents=True, exist_ok=True)
    rep = SyncReport()
    listing = api.photos(mission_id)
    rep.listed = len(listing)
    (dest / "photos.json").write_text(json.dumps(listing, indent=1))
    for p in listing:                                  # thumbnails first
        t = dest / "thumbs" / f"{p['id']}.jpg"
        if not t.exists():
            try:
                t.write_bytes(api.thumb(p["id"]))
            except (ApiError, OSError) as e:
                rep.errors.append(f"thumb {p['id']}: {e}")
    good = []
    for p in listing:
        f = dest / f"{p['id']}.jpg"
        try:
            data = f.read_bytes() if f.exists() else api.full(p["id"])
        except (ApiError, OSError) as e:
            rep.errors.append(f"photo {p['id']}: {e}")
            continue
        if hashlib.sha256(data).hexdigest() != p["sha256"]:
            rep.bad_hash.append(p["id"])
            f.unlink(missing_ok=True)
            continue
        if not f.exists():
            f.write_bytes(data)
            rep.copied += 1
        rep.verified += 1
        good.append(p["id"])
    if good:
        api.ack(good)
        rep.acked = len(good)
    log("photo_sync", mission_id=mission_id, **rep.__dict__)
    return rep


# ---------------------------------------------------------------------------
# Captain's log


def pick_photos(listing: list[dict], n: int = 6) -> list[dict]:
    """Photo-point photos first (one per point), then spread the rest."""
    firsts, seen = [], set()
    for p in listing:
        if p.get("trigger") == "photo_point" and p.get("point_seq") not in seen:
            seen.add(p.get("point_seq"))
            firsts.append(p)
    rest = [p for p in listing if p not in firsts]
    need = max(0, n - len(firsts))
    if need and rest:
        step = max(1, len(rest) // need)
        firsts += rest[::step][:need]
    return firsts[:n]


def _route_svg(track: list[tuple[float, float]], fence, home,
               w: int = 320, h: int = 240) -> str:
    pts = list(track) + list(fence) + [home]
    if not pts:
        return ""
    lat0 = sum(p[0] for p in pts) / len(pts)
    k = math.cos(math.radians(lat0))
    xs = [p[1] * k for p in pts]
    ys = [p[0] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = min((w - 20) / max(x1 - x0, 1e-9), (h - 20) / max(y1 - y0, 1e-9))

    def xy(p):
        return (10 + (p[1] * k - x0) * s, h - 10 - (p[0] - y0) * s)

    def path(ps, closed=False):
        c = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(xy, ps))
        return c + (f" {c.split()[0]}" if closed and c else "")
    hx, hy = xy(home)
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="Route map">'
            f'<polyline points="{path(fence, True)}" fill="#e6f4ff" '
            f'stroke="#3a7bd5" stroke-dasharray="4 3"/>'
            f'<polyline points="{path(track)}" fill="none" stroke="#e8590c" '
            f'stroke-width="2"/>'
            f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="5" fill="#2b8a3e"/>'
            f'</svg>')


def story(distance_m: float, duration_s: float, n_photos: int,
          ducks: int | None, places: list[str]) -> str:
    bits = [f"Today Boaty sailed {distance_m:.0f} metres in "
            f"{max(1, round(duration_s / 60))} minutes."]
    if places:
        bits.append("We visited " + ", ".join(places[:-1]) +
                    (" and " if len(places) > 1 else "") + places[-1] + ".")
    bits.append(f"Boaty took {n_photos} pictures.")
    if ducks:
        bits.append(f"We spotted {ducks} duck{'s' if ducks != 1 else ''}!")
    bits.append("Then Boaty came all the way home. Well done, captain!")
    return " ".join(bits)


def captains_log(dest: Path, mission: Mission, listing: list[dict],
                 track: list[tuple[float, float]], fence, duration_s: float,
                 places: list[str], ducks: int | None = None) -> Path:
    dist = sum(_hav(a, b) for a, b in zip(track, track[1:]))
    chosen = pick_photos(listing)
    imgs = "".join(
        f'<figure><img src="{html.escape(p["id"])}.jpg" alt="Photo '
        f'{i + 1}" width="300"><figcaption>{html.escape(p["taken_utc"][11:16])}'
        f"</figcaption></figure>" for i, p in enumerate(chosen))
    body = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Captain's log</title>"
        "<style>body{font:18px/1.5 system-ui,sans-serif;margin:16px;"
        "background:#fff;color:#111}figure{display:inline-block;margin:6px}"
        "img{max-width:100%;border-radius:8px}</style>"
        "<h1>Captain's log</h1><p>"
        f"{html.escape(story(dist, duration_s, len(listing), ducks, places))}"
        "</p>"
        f"{_route_svg(track, fence, (mission.home.lat, mission.home.lon))}"
        f"<p>Distance {dist:.0f} m · {duration_s / 60:.1f} min · "
        f"{len(listing)} photos</p>{imgs}</html>")
    out = Path(dest) / "captains-log.html"
    out.write_text(body)
    return out


def _hav(a, b) -> float:
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * \
        math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))
