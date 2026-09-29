"""Boaty Mk1 software."""
import os

# IF-02 is MAVLink 2. pymavlink otherwise starts on MAVLink 1 and only
# upgrades after hearing a MAVLink 2 packet, which drops mission_type and
# other extension fields from anything sent before that.
os.environ.setdefault("MAVLINK20", "1")
