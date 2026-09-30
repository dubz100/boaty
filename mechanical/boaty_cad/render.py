"""A small orthographic z-buffer renderer for the MDD figures and the
top-view hi-vis area (REC-D01). Flat shading plus depth-edge outlines."""
from __future__ import annotations

import math

import numpy as np

PALETTE = {"hivis": (1.0, 0.36, 0.02), "yellow": (1.0, 0.83, 0.12),
           "grey": (0.60, 0.62, 0.66), "alu": (0.80, 0.82, 0.85),
           "black": (0.22, 0.22, 0.24), "clear": (0.72, 0.85, 0.95),
           "green": (0.25, 0.66, 0.30), "white": (0.95, 0.95, 0.93),
           "red": (0.85, 0.12, 0.12), "foam": (0.55, 0.75, 0.95)}


def mesh(shape, tol: float = 0.4) -> np.ndarray:
    vs, ts = shape.tessellate(tol, 0.3)
    v = np.array([x.toTuple() for x in vs])
    return v[np.array(ts)] if ts else np.zeros((0, 3, 3))


def view_matrix(azim: float, elev: float) -> np.ndarray:
    """Rows: screen right, screen up, towards the viewer."""
    a, e = math.radians(azim), math.radians(elev)
    fwd = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a),
                    math.sin(e)])                     # towards the viewer
    up0 = np.array([0, 0, 1.0])
    right = np.cross(up0, fwd)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([0, -1.0, 0]) if fwd[2] > 0 else np.array(
            [0, 1.0, 0])
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    return np.array([right, up, fwd])


def render(parts: list[tuple[np.ndarray, str]], azim: float, elev: float,
           px: float = 0.5, pad: int = 20, light=(0.4, -0.3, 0.85),
           ids: bool = False):
    """parts: [(triangles (n,3,3), colour name)]. Returns an RGB image
    (and the per-pixel part index if ids)."""
    R = view_matrix(azim, elev)
    L = np.array(light, float)
    L /= np.linalg.norm(L)
    allv = np.concatenate([t.reshape(-1, 3) for t, _ in parts if len(t)])
    s = allv @ R.T
    lo, hi = s.min(0), s.max(0)
    W = int((hi[0] - lo[0]) / px) + 2 * pad
    H = int((hi[1] - lo[1]) / px) + 2 * pad
    depth = np.full((H, W), -np.inf)
    col = np.ones((H, W, 3))
    pid = np.full((H, W), -1, int)
    for k, (tris, cname) in enumerate(parts):
        if not len(tris):
            continue
        base = np.array(PALETTE.get(cname, PALETTE["grey"]))
        sc = tris @ R.T                                   # (n,3,3)
        nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        ok = ln > 1e-12
        nrm[ok] /= ln[ok, None]
        # light fixed to the camera so every view reads the same way
        shade = np.abs((nrm @ R.T) @ L) * 0.75 + 0.25
        X = (sc[..., 0] - lo[0]) / px + pad
        Y = (hi[1] - sc[..., 1]) / px + pad
        Z = sc[..., 2]
        for t in np.nonzero(ok)[0]:
            x, y, z = X[t], Y[t], Z[t]
            x0, x1 = int(max(math.floor(x.min()), 0)), int(
                min(math.ceil(x.max()), W - 1))
            y0, y1 = int(max(math.floor(y.min()), 0)), int(
                min(math.ceil(y.max()), H - 1))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5,
                                 np.arange(y0, y1 + 1) + 0.5)
            d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
            l2 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
            l3 = 1 - l1 - l2
            m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            if not m.any():
                continue
            zz = l1 * z[0] + l2 * z[1] + l3 * z[2]
            sub = depth[y0:y1 + 1, x0:x1 + 1]
            upd = m & (zz > sub)
            sub[upd] = zz[upd]
            col[y0:y1 + 1, x0:x1 + 1][upd] = base * shade[t]
            pid[y0:y1 + 1, x0:x1 + 1][upd] = k
    # outlines where the depth jumps or the part changes
    edge = np.zeros((H, W), bool)
    fin = np.isfinite(depth)
    dd = np.where(fin, depth, -1e6)
    for ax in (0, 1):
        g = np.abs(np.diff(dd, axis=ax)) > 4.0
        p = np.diff(pid, axis=ax) != 0
        e = g | p
        if ax == 0:
            edge[1:, :] |= e
        else:
            edge[:, 1:] |= e
    col[edge] = col[edge] * 0.25
    return (col, pid) if ids else col
