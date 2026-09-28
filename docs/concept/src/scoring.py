"""Concept scoring matrix (single source of truth for the report and chart)."""

# Criterion weights (sum to 1). Reliability is weighted highest because
# "we cannot lose it" is the one hard requirement.
WEIGHTS = {"cost": 0.25, "fun": 0.25, "intel": 0.20, "rel": 0.30}

CONCEPTS = [
    dict(id="A", short="Hacked GPS bait boat",
         name="Buy a GPS bait boat and hack it",
         how="Commercial carp-fishing bait boat (already has GPS return-home); "
             "add a camera and try to script it.",
         pros="Proven hull, sealed, built-in return-home.",
         cons="£150-300 before mods; closed firmware; little for your son to build.",
         cost=1, fun=2, intel=3, rel=5),
    dict(id="B", short="Tethered boat",
         name="Tethered 'dog-on-a-lead' boat",
         how="Simple RC/auto boat on a 30-50 m floating line reeled from the bank.",
         pros="Cheapest; can literally always be pulled back.",
         cons="Tether snags reeds/weed and ducks; 'explore' limited to a circle; "
              "little autonomy to learn.",
         cost=5, fun=2, intel=1, rel=4),
    dict(id="C", short="Scratch-built autopilot",
         name="Scratch-built Pi/ESP32 boat, our own autopilot",
         how="Raspberry Pi or ESP32 with GPS, write navigation and failsafes "
             "ourselves.",
         pros="Cheap, maximum learning, total control.",
         cons="Every failsafe is our own untested code - the riskiest way to "
              "meet 'never lose it'.",
         cost=5, fun=4, intel=4, rel=2),
    dict(id="D", short="ArduPilot airboat",
         name="Airboat (air propellers) on ArduPilot",
         how="Flat-bottom hull, two above-water fans, skid steering.",
         pros="Weed-proof, no underwater seals, simple.",
         cons="Loud (scares the ducks we want to photograph), blown about by "
              "wind, exposed spinning props near small fingers.",
         cost=4, fun=4, intel=4, rel=3),
    dict(id="E", short="Paddle-wheel explorer",
         name="Paddle-wheel steamer style on ArduPilot",
         how="Twin side paddle wheels driven by geared DC motors.",
         pros="Hugely fun mechanically, weed-tolerant, charming.",
         cons="Slow, heavy, big to print; poor into wind; gearbox wear.",
         cost=3, fun=5, intel=3, rel=3),
    dict(id="F", short="Converted RC toy boat",
         name="Convert a cheap RC toy boat",
         how="£30 RC speedboat with a flight controller squeezed inside.",
         pros="Quick start, ready-made hull.",
         cons="Tiny, not sealed, too fast, no room for camera/batteries; "
              "nothing modular to build.",
         cost=4, fun=2, intel=4, rel=3),
    dict(id="G", short="Modular GPS catamaran",
         name="Modular 3D-printed catamaran, ArduPilot + camera 'mission brain'",
         how="Foam-filled printed twin hulls, clip-on thruster pods, ArduPilot "
             "Rover on a cheap flight controller, ESP32-S3 camera as Wi-Fi/photo "
             "companion.",
         pros="Proven failsafes & geofence, fully modular build, quiet, "
              "stable camera platform, clear upgrade path.",
         cons="Tight on £100; weed around submerged props needs a guard; "
              "more build effort.",
         cost=4, fun=5, intel=5, rel=4, chosen=True),
]


def weighted_scores(weights=WEIGHTS):
    return {c["id"]: sum(c[k] * w for k, w in weights.items()) for c in CONCEPTS}


def sensitivity():
    """Winner when each weight in turn is doubled (then re-normalised)."""
    out = {}
    for k in WEIGHTS:
        w = dict(WEIGHTS)
        w[k] *= 2
        tot = sum(w.values())
        w = {kk: v / tot for kk, v in w.items()}
        s = weighted_scores(w)
        out[k] = max(s, key=s.get)
    return out


if __name__ == "__main__":
    print(weighted_scores())
    print(sensitivity())
