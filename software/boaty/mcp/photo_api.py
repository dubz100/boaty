"""B3 photo and health server (ICD IF-03, MCP-D14).

HTTP/JSON on TCP 8080; Mission Control is the only client. Every request
must carry "Authorization: Bearer <token>" (a 32-byte random token
provisioned on both computers). Standard library only, so it runs unchanged
on the Pi Zero.
"""
from __future__ import annotations

import hmac
import json
import logging
import threading
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

log = logging.getLogger(__name__)
SW_VERSION = "0.2.0-slice2"


class PhotoApi:
    def __init__(self, camera, token: str, health=None, host: str = "0.0.0.0",
                 port: int = 8080, system=None, on_shutdown=None):
        """camera: CameraService; health: object with snapshot() (B6);
        system: callable returning cpu_temp_c, throttled, rssi_dbm."""
        self.camera, self.store = camera, camera.store
        self.token = token.encode()
        self.health = health
        self.system = system or (lambda: {"cpu_temp_c": 45.0,
                                          "throttled": False,
                                          "rssi_dbm": -55})
        self.on_shutdown = on_shutdown or (lambda: None)
        self.started = time.monotonic()
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                log.debug(fmt, *args)

            def do_GET(self):
                api._dispatch(self, "GET")

            def do_PUT(self):
                api._dispatch(self, "PUT")

            def do_POST(self):
                api._dispatch(self, "POST")

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.port = self.httpd.server_address[1]

    def start(self) -> "PhotoApi":
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    # ------------------------------------------------------------------
    def health_json(self) -> dict:
        v = self.camera.v
        now = self.camera.clock.now()
        mav_ok = v.helm_heartbeat_t is not None and \
            now - v.helm_heartbeat_t < 3.0
        b6 = self.health.snapshot() if self.health else {
            "moisture": False, "box_temp_c": None}
        sysinfo = self.system()
        free = self.store.free_mb()
        status = "ok"
        if not (mav_ok and self.camera.camera.ok) or self.store.full() or \
                sysinfo["throttled"]:
            status = "degraded"
        if b6["moisture"] or (b6["box_temp_c"] or 0) > 60:
            status = "fault"
        return {"status": status,
                "uptime_s": int(time.monotonic() - self.started),
                "cpu_temp_c": sysinfo["cpu_temp_c"],
                "throttled": sysinfo["throttled"],
                "storage_free_mb": free,
                "photos_unsynced": self.store.unsynced(),
                "moisture": b6["moisture"], "camera_ok": self.camera.camera.ok,
                "mavlink_ok": mav_ok, "rssi_dbm": sysinfo["rssi_dbm"],
                "box_temp_c": b6["box_temp_c"], "sw_version": SW_VERSION}

    @staticmethod
    def _photo_json(p) -> dict:
        d = asdict(p)
        d.pop("acked", None)
        return d

    def _dispatch(self, h: BaseHTTPRequestHandler, method: str) -> None:
        auth = h.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not hmac.compare_digest(
                auth[7:].encode(), self.token):
            return self._send(h, 401, {"error": "unauthorized",
                                       "message": "bearer token required"})
        url = urlparse(h.path)
        parts = [p for p in url.path.split("/") if p]
        body = None
        if method in ("PUT", "POST"):
            n = int(h.headers.get("Content-Length") or 0)
            raw = h.rfile.read(n) if n else b""
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return self._error(h, 400, "bad_request", "invalid JSON")
        try:
            return self._route(h, method, parts, parse_qs(url.query), body)
        except ValueError as e:
            return self._error(h, 400, "bad_request", str(e))

    def _route(self, h, method, parts, q, body):
        if parts[:1] != ["v1"]:
            return self._error(h, 404, "not_found", "unknown path")
        p = parts[1:]
        if method == "GET" and p == ["health"]:
            return self._send(h, 200, self.health_json())
        if method == "PUT" and p == ["session"]:
            return self._send(h, 200, self.camera.set_session(body))
        if method == "GET" and p == ["photos"]:
            mission = q.get("mission", [None])[0]
            since = q.get("since", [None])[0]
            return self._send(h, 200, [self._photo_json(x) for x in
                                       self.store.list(mission, since)])
        if method == "GET" and len(p) in (2, 3) and p[0] == "photos" and \
                (len(p) == 2 or p[2] == "thumb"):
            path = self.store.path(p[1], thumb=len(p) == 3)
            if path is None or not path.exists():
                return self._error(h, 404, "not_found", "no such photo")
            data = path.read_bytes()
            h.send_response(200)
            h.send_header("Content-Type", "image/jpeg")
            h.send_header("Content-Length", str(len(data)))
            h.end_headers()
            h.wfile.write(data)
            return None
        if method == "POST" and p == ["photos", "ack"]:
            ids = body.get("ids") if isinstance(body, dict) else None
            if not isinstance(ids, list):
                raise ValueError("ids must be a list")
            self.store.ack(ids)
            return self._send(h, 204, None)
        if method == "POST" and p == ["capture"]:
            count = int(body.get("count", 1))
            iv = float(body.get("interval_s", 1.0))
            if not 1 <= count <= 10 or not 0.5 <= iv <= 5:
                raise ValueError("count 1-10, interval_s 0.5-5")
            if self.store.full():
                return self._error(h, 507, "storage_full",
                                   "capture stopped: storage full")
            self.camera.request("command", count, iv)
            return self._send(h, 202, {"queued": count})
        if method == "POST" and p == ["shutdown"]:
            self.on_shutdown()
            return self._send(h, 202, {"shutting_down": True})
        return self._error(h, 404, "not_found", "unknown path")

    def _error(self, h, code, err, msg):
        return self._send(h, code, {"error": err, "message": msg})

    @staticmethod
    def _send(h, code, obj):
        h.send_response(code)
        if obj is None:
            h.send_header("Content-Length", "0")
            h.end_headers()
            return None
        data = json.dumps(obj).encode()
        h.send_header("Content-Type", "application/json")
        h.send_header("Content-Length", str(len(data)))
        h.end_headers()
        h.wfile.write(data)
        return None
