"""Read ArduPilot .parm files (the controlled parameter baseline, SAF-007)."""
from __future__ import annotations

from pathlib import Path


def read_parm(path: str | Path) -> dict[str, float]:
    """Parse 'NAME value  # comment' lines. Later duplicates win."""
    out: dict[str, float] = {}
    for n, raw in enumerate(Path(path).read_text().splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.replace(",", " ").split()
        if len(parts) != 2:
            raise ValueError(f"{path}:{n}: expected 'NAME value', got {raw!r}")
        out[parts[0]] = float(parts[1])
    return out


def read_many(paths) -> dict[str, float]:
    merged: dict[str, float] = {}
    for p in paths:
        merged.update(read_parm(p))
    return merged


def differences(expected: dict[str, float], actual: dict[str, float],
                tol: float = 1e-4) -> dict[str, tuple[float, float | None]]:
    """Parameters whose live value differs from the baseline (SC-24)."""
    diff = {}
    for name, want in expected.items():
        got = actual.get(name)
        if got is None or abs(got - want) > tol * max(1.0, abs(want)):
            diff[name] = (want, got)
    return diff
