"""Adult PIN (IF-12, MCN-D14, D61).

6 digits. A correct PIN unlocks adult actions for 10 minutes (or until the
session ends). After 5 wrong entries in a row, entry is locked for 5
minutes. Only a salted PBKDF2 hash is kept, in a 0600 settings file
outside the repository. The PIN is never logged, shown or spoken.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

UNLOCK_S = 600
MAX_FAILS = 5
LOCKOUT_S = 300
ITER = 200_000
SETTINGS = Path(os.environ.get("BOATY_SETTINGS",
                               Path.home() / ".config" / "boaty" /
                               "settings.json"))


def _hash(pin: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, ITER).hex()


def valid_format(pin: str) -> bool:
    return len(pin) == 6 and pin.isdigit()


@dataclass
class UnlockResult:
    ok: bool
    token: str | None = None
    message: str = ""


class PinLock:
    def __init__(self, pin_hash: str, salt_hex: str, clock):
        self._hash, self._salt = pin_hash, bytes.fromhex(salt_hex)
        self.clock = clock
        self.fails = 0
        self.locked_until = 0.0
        self._tokens: dict[str, float] = {}

    @classmethod
    def from_pin(cls, pin: str, clock) -> "PinLock":
        if not valid_format(pin):
            raise ValueError("the PIN must be 6 digits")
        salt = secrets.token_bytes(16)
        return cls(_hash(pin, salt), salt.hex(), clock)

    @classmethod
    def load(cls, clock, path: Path = SETTINGS) -> "PinLock":
        d = json.loads(Path(path).read_text())
        return cls(d["pin_hash"], d["pin_salt"], clock)

    def save(self, path: Path = SETTINGS) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        d = json.loads(path.read_text()) if path.exists() else {}
        d.update(pin_hash=self._hash, pin_salt=self._salt.hex())
        path.write_text(json.dumps(d))
        os.chmod(path, 0o600)

    def unlock(self, pin: str) -> UnlockResult:
        now = self.clock()
        if now < self.locked_until:
            return UnlockResult(False, message=f"Locked for "
                                f"{int(self.locked_until - now) + 1} s")
        if valid_format(pin) and hmac.compare_digest(
                _hash(pin, self._salt), self._hash):
            self.fails = 0
            tok = secrets.token_urlsafe(24)
            self._tokens[tok] = now + UNLOCK_S
            return UnlockResult(True, tok)
        self.fails += 1
        if self.fails >= MAX_FAILS:
            self.fails = 0
            self.locked_until = now + LOCKOUT_S
            return UnlockResult(False, message="Too many tries: locked for "
                                "5 minutes")
        return UnlockResult(False, message=f"Wrong PIN "
                            f"({MAX_FAILS - self.fails} tries left)")

    def valid(self, token: str | None) -> bool:
        exp = self._tokens.get(token or "")
        return exp is not None and self.clock() < exp

    def change(self, token: str, old: str, new: str) -> bool:
        if not self.valid(token) or not valid_format(new) or \
                not hmac.compare_digest(_hash(old, self._salt), self._hash):
            return False
        salt = secrets.token_bytes(16)
        self._hash, self._salt = _hash(new, salt), salt
        self._tokens.clear()
        return True

    def end_session(self) -> None:
        self._tokens.clear()
