"""Download the 'To fetch' entries of the KCL datasheet register.

Run:  python3 docs/kcl/src/fetch_datasheets.py

Files land in docs/kcl/datasheets/ as <DS-id>_<name>. Each download's SHA-256
is recorded in docs/kcl/datasheets/MANIFEST.csv. If a file already exists and
its hash differs from a fresh download, the script reports it rather than
overwriting, so a datasheet can't silently change.
"""
import csv
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kcl_data as K  # noqa: E402

OUT = HERE.parent / "datasheets"
MANIFEST = OUT / "MANIFEST.csv"


def local_name(ds_id, url):
    tail = url.rstrip("/").rsplit("/", 1)[-1] or "index"
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", tail)
    if "." not in tail:
        tail += ".html"
    return f"{ds_id}_{tail}"


def main():
    OUT.mkdir(exist_ok=True)
    known = {}
    if MANIFEST.exists():
        with MANIFEST.open() as f:
            known = {r["file"]: r for r in csv.DictReader(f)}
    rows, failed, changed = dict(known), [], []
    for ds_id, _, doc, url, status in K.DATASHEETS:
        if status != "To fetch":
            continue
        name = local_name(ds_id, url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent":
                                                       "boaty-kcl/1"})
            data = urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:  # noqa: BLE001
            failed.append((ds_id, url, str(e)))
            continue
        sha = hashlib.sha256(data).hexdigest()
        path = OUT / name
        if name in known and known[name]["sha256"] != sha:
            changed.append((ds_id, name))
            path = OUT / (name + ".new")
        path.write_bytes(data)
        rows[name] = {"file": name, "id": ds_id, "url": url, "sha256": sha,
                      "bytes": len(data)}
        print(f"ok      {ds_id} {name} ({len(data)} bytes)")
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, ["file", "id", "url", "sha256", "bytes"])
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: r["file"]):
            w.writerow(r)
    for ds_id, url, err in failed:
        print(f"FAILED  {ds_id} {url}: {err}")
    for ds_id, name in changed:
        print(f"CHANGED {ds_id} {name}: saved as {name}.new; review before "
              "replacing")
    return 1 if failed or changed else 0


if __name__ == "__main__":
    sys.exit(main())
