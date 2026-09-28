# Datasheets

Vendor datasheets for the Key Component List (BOATY-KCL-001, section 9).

Fetch them with `python3 docs/kcl/src/fetch_datasheets.py` from a machine with
ordinary internet access. The script saves each file as `<DS-id>_<name>` and
records its SHA-256 in `MANIFEST.csv`. If a vendor changes a datasheet, the new
copy is saved alongside as `.new` for review instead of overwriting.

The build environment the KCL was written in could not reach these vendor sites.
