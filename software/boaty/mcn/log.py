"""C10 session log: structured JSON lines, UTC (MCN-D50, SWE-008).

One file per session. Every row has t_utc, kind and whatever fields the
caller adds: commands, approvals, missions, LLM I/O, validator results,
helm events, RSSI. The PIN is never logged (MCN-D61).
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

FORBIDDEN_KEYS = {"pin", "api_key", "token"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class SessionLog:
    def __init__(self, path: Path | str | None = None, clock=utc_now):
        self.path = Path(path) if path else None
        self.clock = clock
        self.rows: list[dict] = []
        self._lock = threading.Lock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, kind: str, **fields) -> dict:
        for k in list(fields):
            if k.lower() in FORBIDDEN_KEYS:
                fields[k] = "<redacted>"
        row = {"t_utc": self.clock(), "kind": kind, **fields}
        line = json.dumps(row, default=str, separators=(",", ":"))
        with self._lock:
            self.rows.append(row)
            if self.path:
                with self.path.open("a") as f:
                    f.write(line + "\n")
        return row

    def of(self, kind: str) -> list[dict]:
        return [r for r in self.rows if r["kind"] == kind]
