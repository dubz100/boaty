"""Boaty System Requirements Specification: the requirement set.

Single source of truth. build_srs.py renders the requirement tables, the
verification matrix and the traceability matrix from this file, and
check() enforces basic integrity (unique IDs, valid codes, full trace).

Codes
  priority      M = Must, S = Should, C = Could
  verification  T = Test, D = Demonstration, I = Inspection, A = Analysis,
                S = Simulation
  stage         SIM, BENCH, POOL, LAKE (first stage the requirement is
                verified at)
"""

STAKEHOLDER_NEEDS = [
    ("STK-01", "Never lose the boat",
     "The boat returns, or stays findable and reachable from our bank, "
     "whatever fails."),
    ("STK-02", "Plain-English instructions",
     "The crew can say what they want (\"explore the bay, photograph some "
     "ducks, then come back\") and the boat does it."),
    ("STK-03", "Photos of ducks",
     "The boat comes back with good photos of ducks and a record of the "
     "voyage."),
    ("STK-04", "A build a 4-year-old can join",
     "Modular, chunky, colourful parts he can assemble and customise, "
     "including building on it with DUPLO."),
    ("STK-05", "Affordable",
     "Around £100 cash for Mk1, reusing the Raspberry Pi 5 and Ultimaker "
     "printer."),
    ("STK-06", "Safe for people and wildlife",
     "No harm to the child, other water users or wildlife."),
    ("STK-07", "Welcome at the lake",
     "Operation is acceptable to Cambridge Sport Lakes Trust and other "
     "users of Milton Country Park."),
    ("STK-08", "Python-first and extensible",
     "Software the parent can read, change and extend in Python, including "
     "a future pure-Python helm."),
]

# ---------------------------------------------------------------- helpers
SECTIONS = []


def section(key, title, intro):
    SECTIONS.append(dict(key=key, title=title, intro=intro, reqs=[]))


def R(rid, text, pri, ver, stage, trace, note=None):
    SECTIONS[-1]["reqs"].append(dict(id=rid, text=text, pri=pri, ver=ver,
                                     stage=stage, trace=trace, note=note))


# ---------------------------------------------------------------- modes
section("MOD", "Operating modes",
        "The boat's behaviour is defined by a small set of modes (see "
        "section 2.3). These are the only states the system may "
        "be in.")
R("MOD-001", "The system shall implement exactly these boat modes: "
  "DISARMED, HOLD, MANUAL, AUTO and RTL, as defined in section 2.3.",
  "M", "I,S", "SIM", ["STK-01", "STK-06"])
R("MOD-002", "On power-up the boat shall enter DISARMED, with both motors "
  "inhibited.", "M", "T", "BENCH", ["STK-06"])
R("MOD-003", "Arming shall require two deliberate adult actions: the arming "
  "switch on the boat set to ARM, and arming confirmed at Mission Control.",
  "M", "D", "BENCH", ["STK-06"])
R("MOD-004", "The system shall refuse to arm unless every pre-arm check "
  "(PRE-001 to PRE-008) passes, and shall state the failing check in plain "
  "language at Mission Control.", "M", "T", "SIM", ["STK-01", "STK-06"])
R("MOD-005", "When an AUTO mission completes, the boat shall enter RTL. On "
  "reaching home (within the waypoint acceptance radius) it shall enter "
  "HOLD.", "M", "S,T", "SIM", ["STK-01"])
R("MOD-006", "While armed, the operator shall be able to command HOLD, RTL, "
  "MANUAL or STOP from Mission Control at any time, overriding AUTO.",
  "M", "T", "SIM", ["STK-01", "STK-06"])
R("MOD-007", "Every mode change shall be shown and announced at Mission "
  "Control within 2 s, whatever caused it.", "S", "T", "SIM",
  ["STK-01", "STK-04"])
R("MOD-008", "The boat shall disarm automatically after 60 s in HOLD at "
  "home with no operator input, and announce it.", "C", "S", "SIM",
  ["STK-06"])

# ---------------------------------------------------------------- pre-arm
section("PRE", "Pre-arm checks",
        "Checks the helm and Mission Control perform before arming is "
        "allowed (MOD-004).")
R("PRE-001", "GNSS shall have a 3D fix with at least 8 satellites and HDOP "
  "no greater than 1.5.", "M", "T", "BENCH", ["STK-01"])
R("PRE-002", "A geofence shall be loaded and enabled, and home shall lie "
  "inside the inclusion fence and outside all exclusion zones.",
  "M", "T", "SIM", ["STK-01", "STK-07"])
R("PRE-003", "Battery state of charge shall be at least 80%.", "M", "T",
  "BENCH", ["STK-01"])
R("PRE-004", "The heading sensor shall report healthy and calibrated.",
  "M", "T", "BENCH", ["STK-01"])
R("PRE-005", "For AUTO: a mission that has passed validation and operator "
  "approval shall be loaded, and read back from the helm to match "
  "(VAL-010).", "M", "T", "SIM", ["STK-01", "STK-02"])
R("PRE-006", "The pre-launch checklist (OPS-001) shall be complete and "
  "signed off at Mission Control for this session.", "M", "D", "POOL",
  ["STK-06", "STK-07"])
R("PRE-007", "The independent safety layer (SAF-001) shall report healthy.",
  "M", "T", "BENCH", ["STK-01"])
R("PRE-008", "Logging shall be active on the helm and Mission Control, each "
  "with at least 1 GB free.", "M", "T", "BENCH", ["STK-01"])

# ---------------------------------------------------------------- navigation
section("NAV", "Navigation and control", "")
R("NAV-001", "The boat shall steer by differential thrust from two "
  "thrusters, and be able to go forward and in reverse.", "M", "D", "POOL",
  ["STK-01"])
R("NAV-002", "Cruise speed in calm water shall be 1.0 m/s ± 0.2 m/s.",
  "M", "T", "LAKE", ["STK-03", "STK-06"])
R("NAV-003", "Speed through the water shall be limited to 1.5 m/s in every "
  "mode.", "M", "T", "POOL", ["STK-06", "STK-07"])
R("NAV-004", "In AUTO the boat shall pass within the acceptance radius of "
  "each waypoint. The radius is configurable from 1 to 10 m, default 3 m.",
  "M", "S,T", "SIM", ["STK-02"])
R("NAV-005", "Cross-track error between waypoints shall be no more than "
  "3 m RMS in wind up to 3 m/s.", "S", "T", "LAKE", ["STK-01", "STK-02"])
R("NAV-006", "In HOLD with station-keeping, the boat shall stay within 5 m "
  "of the hold point in wind up to 3 m/s.", "S", "T", "LAKE",
  ["STK-01", "STK-03"])
R("NAV-007", "In RTL the boat shall navigate to home without entering any "
  "exclusion zone or leaving the inclusion fence.", "M", "S,T", "SIM",
  ["STK-01", "STK-06"])
R("NAV-008", "Above 0.3 m/s the heading estimate shall use GNSS course as "
  "well as the magnetometer, so a disturbed compass cannot alone cause a "
  "wrong course.", "S", "S,T", "SIM", ["STK-01"])

# ---------------------------------------------------------------- geofence
section("FEN", "Geofence",
        "The geofence keeps the boat inside a known safe area of water. "
        "It is enforced by the independent safety layer (SAF-001).")
R("FEN-001", "The system shall support one inclusion polygon of 3 to 70 "
  "vertices and up to 10 exclusion zones, each a polygon or circle.",
  "M", "S", "SIM", ["STK-01", "STK-06"])
R("FEN-002", "Fences shall be drawn on a map at Mission Control, stored "
  "per site with a name, and version-controlled.", "M", "D", "SIM",
  ["STK-01", "STK-07"])
R("FEN-003", "Mission Control shall show a 5 m guide inside the drawn "
  "inclusion fence, and warn if any home or waypoint falls within it.",
  "S", "D", "SIM", ["STK-01"])
R("FEN-004", "The fence shall be enforced in every armed mode, including "
  "MANUAL.", "M", "S,T", "SIM", ["STK-01", "STK-06"])
R("FEN-005", "On a fence breach the boat shall enter RTL within 1 s of the "
  "breach.", "M", "S,T", "SIM", ["STK-01"])
R("FEN-006", "If the boat stays outside the inclusion fence for more than "
  "30 s, or gets more than 10 m outside it, the motors shall stop (HOLD, "
  "no thrust) and an alarm shall sound at Mission Control.",
  "M", "S", "SIM", ["STK-01", "STK-06"])
R("FEN-007", "Fence and exclusion zones shall not be changed while the "
  "boat is armed.", "M", "T", "SIM", ["STK-01"])

# ---------------------------------------------------------------- failsafes
section("FS", "Failsafes",
        "Automatic responses to faults, summarised in the table at the "
        "end of this section. "
        "Thresholds are the accepted baseline (Issue B). They change only "
        "through an SRS revision backed by trial evidence.")
R("FS-001", "Low battery: when estimated state of charge falls to 35%, the "
  "boat shall enter RTL. At 15% it shall continue RTL at reduced speed and "
  "sound an alarm.", "M", "S,T", "SIM", ["STK-01"])
R("FS-002", "Link loss in MANUAL: with no command link for 3 s the boat "
  "shall enter HOLD, and after 10 s it shall enter RTL. (3 s by CR-05: the "
  "autopilot's fastest link-loss failsafe, measured in simulation.)", "M",
  "S,T", "SIM", ["STK-01"])
R("FS-003", "Link loss in AUTO: the boat shall continue the mission. If the "
  "link is still lost after 60 s it shall enter RTL.", "M", "S,T", "SIM",
  ["STK-01"])
R("FS-004", "Position loss: if the GNSS fix is lost, HDOP exceeds 2.5 or "
  "the position estimate is unhealthy for 3 s, the motors shall stop "
  "(HOLD, no thrust). After 10 s of healthy position the boat shall enter "
  "RTL.", "M", "S", "SIM", ["STK-01"])
R("FS-005", "Stuck detection: if commanded thrust is at least 50% and "
  "ground speed stays below 0.1 m/s for 5 s, the boat shall enter HOLD and "
  "alarm.", "M", "S,T", "POOL", ["STK-01"])
R("FS-006", "Weed-shedding: after a stuck detection the boat shall try up "
  "to 3 short reverse bursts, then resume its previous mode if free, or "
  "stay in HOLD if not.", "S", "T", "POOL", ["STK-01"])
R("FS-007", "Mission computer failure: if the helm receives no mission "
  "computer heartbeat for 3 s, it shall complete the loaded mission and "
  "RTL on its own.", "M", "S,T", "SIM", ["STK-01"])
R("FS-008", "Helm failure: if motor commands stop arriving from the helm, "
  "the motors shall stop within 1 s.", "M", "T", "BENCH",
  ["STK-01", "STK-06"])
R("FS-009", "STOP: pressing STOP at Mission Control shall stop both motors "
  "within 1 s, whatever the mode.", "M", "T", "BENCH", ["STK-06"])
R("FS-010", "Water ingress: a moisture sensor in the electronics box shall "
  "trigger RTL and an alarm.", "S", "T", "BENCH", ["STK-01"])
R("FS-011", "When several failsafes are active, the most conservative "
  "response shall win: motors stopped over RTL over continuing the "
  "mission.", "M", "S", "SIM", ["STK-01", "STK-06"])
R("FS-012", "Every failsafe event shall be logged, and announced at "
  "Mission Control within 2 s if the link is up.", "M", "S,T", "SIM",
  ["STK-01"])
R("FS-013", "No single failure shall cause the boat to leave the inclusion "
  "fence under its own power. This is shown by FMEA (SAF-007) and by "
  "simulated fault injection.", "M", "A,S", "SIM", ["STK-01", "STK-06"])

# ---------------------------------------------------------------- safety arch
section("SAF", "Safety architecture",
        "How the safety functions are protected from the rest of the "
        "system. These requirements hold for both software routes "
        "(section 2.4).")
R("SAF-001", "Fence and failsafe functions shall run on a processor "
  "separate from the mission computer and Mission Control. That processor "
  "shall run bare-metal firmware or an RTOS, not a general-purpose "
  "operating system.", "M", "I", "BENCH", ["STK-01", "STK-08"])
R("SAF-002", "Those functions shall keep working with the mission "
  "computer, Mission Control and the radio link all failed.", "M", "S,T",
  "SIM", ["STK-01"])
R("SAF-003", "The mission computer and Mission Control shall command the "
  "helm only through the helm interface (SWE-002). They shall not be able "
  "to disable the fence or failsafes while armed.", "M", "I,T", "SIM",
  ["STK-01", "STK-08"])
R("SAF-004", "Output from the language model shall never be sent to the "
  "helm as a command. Only mission objects that have passed validation "
  "(VAL-001) may reach the helm.", "M", "I,T", "SIM", ["STK-01", "STK-02"])
R("SAF-005", "Route B only: a MicroPython guardian with its own GNSS shall "
  "pass motor commands through only while the helm heartbeat is fresh "
  "(under 0.5 s) and the boat is inside the fence. Otherwise it shall stop "
  "the motors or run its own return-home routine.", "M", "T", "BENCH",
  ["STK-01", "STK-08"],
  note="Not applicable from Issue B: Route A (ArduPilot) selected. "
       "Retained for a possible Mk2 Python helm.")
R("SAF-006", "A failure modes and effects analysis (FMEA) shall be done "
  "before the first lake trial and updated after any change to hardware "
  "or safety software.", "M", "A", "SIM", ["STK-01", "STK-06"])
R("SAF-007", "Safety parameters (fence, failsafe thresholds, speed limits) "
  "shall be version-controlled. The values loaded on the helm shall be "
  "checked against the committed baseline at pre-arm.", "S", "T", "SIM",
  ["STK-01"])

# ---------------------------------------------------------------- missions
section("MIS", "Missions",
        "A mission is a structured, versioned plan the helm can execute. "
        "Missions can come from the language model, templates or the map "
        "editor. All of them go through the same validator (section 5.9).")
R("MIS-001", "The system shall support these mission elements: waypoint, "
  "area survey (lawnmower pattern over a polygon, with lane spacing), "
  "photo point (hold, then take N photos), and return home.", "M", "S",
  "SIM", ["STK-02", "STK-03"])
R("MIS-002", "Every mission shall end with return home.", "M", "S", "SIM",
  ["STK-01"])
R("MIS-003", "Planned mission duration shall not exceed 20 min "
  "(configurable up to 30 min). Planned energy shall not exceed 50% of "
  "usable battery energy.", "M", "A,S", "SIM", ["STK-01"])
R("MIS-004", "Missions shall be represented in a documented JSON schema "
  "with a version number.", "M", "I", "SIM", ["STK-02", "STK-08"])
R("MIS-005", "Offline templates shall be available without internet, at "
  "least: 'Explore the bay', 'Duck patrol' (survey with photo points) and "
  "'Lap of the bay'.", "M", "D", "SIM", ["STK-02", "STK-04"])
R("MIS-006", "An adult shall be able to create and edit missions on the "
  "map at Mission Control.", "S", "D", "SIM", ["STK-02"])

# ---------------------------------------------------------------- NL
section("NLI", "Natural-language instructions", "")
R("NLI-001", "Mission Control shall accept instructions as typed text.",
  "M", "D", "SIM", ["STK-02"])
R("NLI-002", "Mission Control shall accept spoken instructions through a "
  "microphone, using push-to-talk on the TALK button.", "S", "D", "SIM", ["STK-02", "STK-04"])
R("NLI-003", "Instructions shall be turned into a mission through the "
  "Claude API. The request shall include the site context: fence, "
  "exclusion zones, home, battery state, time and energy limits, and the "
  "mission schema.", "M", "T", "SIM", ["STK-02"])
R("NLI-004", "The language model's reply shall be constrained to the "
  "mission schema (structured output or tool use). A malformed reply shall "
  "be rejected and retried at most twice. After that the user shall be "
  "offered the templates.", "M", "T", "SIM", ["STK-02", "STK-01"])
R("NLI-005", "The proposed mission shall be shown on the map with a "
  "one-sentence plain-language summary, which shall also be spoken aloud.",
  "M", "D", "SIM", ["STK-02", "STK-04"])
R("NLI-006", "Requests the boat must not or cannot do (for example leaving "
  "the fence, chasing animals, going to another lake) shall be declined in "
  "child-friendly words, with a safe alternative offered.", "M", "T", "SIM",
  ["STK-02", "STK-06"])
R("NLI-007", "With mobile data available, a plan shall be displayed within "
  "20 s of the instruction.", "S", "T", "LAKE", ["STK-02"])
R("NLI-008", "The API key shall be stored only on Mission Control and "
  "shall never be committed to the repository.", "M", "I", "SIM",
  ["STK-08"])

# ---------------------------------------------------------------- validator
section("VAL", "Mission validation",
        "A deterministic Python validator stands between every mission "
        "source and the helm. It is the main safeguard against a bad plan, "
        "wherever the plan came from.")
R("VAL-001", "Every mission, from any source, shall pass the validator "
  "before upload. There shall be no other path for uploading missions to "
  "the helm.", "M", "I,T", "SIM", ["STK-01", "STK-02"])
R("VAL-002", "Every waypoint, and every leg sampled at 1 m intervals or "
  "finer, shall be inside the inclusion fence by at least 3 m and outside "
  "every exclusion zone by at least 3 m.", "M", "T", "SIM",
  ["STK-01", "STK-06"])
R("VAL-003", "The mission shall meet the duration and energy limits in "
  "MIS-003.", "M", "T", "SIM", ["STK-01"])
R("VAL-004", "The mission shall start within 10 m of home and end with "
  "return home.", "M", "T", "SIM", ["STK-01"])
R("VAL-005", "Commanded speeds shall be within NAV-003. Each hold shall be "
  "60 s or less. The photo count shall fit in the free camera storage. The "
  "waypoint count shall be within the helm's limit.", "M", "T", "SIM",
  ["STK-01", "STK-03"])
R("VAL-006", "The validator shall be pure Python with no network access "
  "and no randomness. It shall have a unit-test suite that includes "
  "adversarial missions, with at least 95% branch coverage.", "M", "T",
  "SIM", ["STK-01", "STK-08"])
R("VAL-007", "Each rejection shall be reported in plain language, naming "
  "the rule broken and where on the map.", "M", "D", "SIM", ["STK-02"])
R("VAL-008", "After validation, an adult shall approve the mission at "
  "Mission Control. GO shall stay disabled until then.", "M", "T", "SIM",
  ["STK-01", "STK-06"])
R("VAL-009", "Any change to an approved mission shall void the approval.",
  "M", "T", "SIM", ["STK-01"])
R("VAL-010", "After upload, the mission shall be read back from the helm "
  "and compared with the approved mission by checksum before GO is "
  "enabled.", "M", "T", "SIM", ["STK-01"])

# ---------------------------------------------------------------- camera
section("CAM", "Camera and photos", "")
R("CAM-001", "The boat shall carry a forward-looking camera that captures "
  "still images of at least 2 MP (M) and at least 5 MP (S).", "M", "I,T",
  "BENCH", ["STK-03"])
R("CAM-002", "Capture modes shall be: interval (every 2 to 30 s), at "
  "photo points, and on command.", "M", "T", "BENCH", ["STK-03"])
R("CAM-003", "Every photo shall be tagged with UTC time, position, heading "
  "and mission ID.", "M", "T", "BENCH", ["STK-03"])
R("CAM-004", "Local storage shall hold at least 500 photos. Full storage "
  "shall not affect navigation or safety.", "M", "T", "BENCH",
  ["STK-03", "STK-01"])
R("CAM-005", "A duck (about 0.3 m long) at 5 m shall span at least 40 "
  "pixels in the image.", "S", "A,T", "POOL", ["STK-03"])
R("CAM-006", "The lens shall be shielded from spray and cleanable on the "
  "bank without tools.", "S", "I", "POOL", ["STK-03"])
R("CAM-007", "After a mission, photos shall transfer to Mission Control "
  "automatically when in range, with 200 photos taking 5 min or less.",
  "S", "T", "POOL", ["STK-03"])
R("CAM-008", "Mission Control may show a low-rate live view from the "
  "camera.", "C", "D", "POOL", ["STK-04"])

# ---------------------------------------------------------------- detection
section("DET", "Duck finding and captain's log", "")
R("DET-001", "After a mission, the system shall identify photos containing "
  "waterfowl, with at least 80% precision on a test set of lake photos.",
  "S", "T", "LAKE", ["STK-03"])
R("DET-002", "The system shall produce a captain's log: up to 6 best "
  "photos, a map of the route, distance, duration, ducks seen, and a short "
  "child-friendly story of the voyage.", "S", "D", "LAKE",
  ["STK-03", "STK-04"])
R("DET-003", "An upgraded mission computer may detect waterfowl on board "
  "in real time and trigger 'pause and look' (hold and take a burst of "
  "photos).", "C", "T", "POOL", ["STK-03"])
R("DET-004", "If DET-003 is implemented, 'pause and look' shall hold "
  "position and shall never steer towards the detected animal.", "M", "S,T",
  "SIM", ["STK-06"], note="Conditional on DET-003.")

# ---------------------------------------------------------------- mission control
section("MC", "Mission Control (bank station)",
        "The Raspberry Pi 5 based ground station: the only interface the "
        "crew uses.")
R("MC-001", "Mission Control shall run on the owned Raspberry Pi 5 and "
  "operate for at least 2.5 h from a USB-C power bank.", "M", "T", "BENCH",
  ["STK-05"])
R("MC-002", "It shall have four physical push buttons, each at least "
  "30 mm across, in distinct colours with icons: GO (green), COME HOME "
  "(yellow), STOP (red) and TALK (blue, microphone).", "M", "I", "BENCH", ["STK-04", "STK-06"])
R("MC-003", "STOP and COME HOME shall always be active while armed. GO "
  "shall be active only when a validated, approved and verified mission is "
  "loaded and the boat is armed in HOLD.", "M", "T", "SIM",
  ["STK-01", "STK-06"])
R("MC-004", "GO shall require a 1 s press-and-hold, to prevent accidental "
  "starts.", "S", "T", "BENCH", ["STK-06"])
R("MC-005", "The display shall show, updated at least once a second: a map "
  "with the boat's position, heading and track; fence, exclusions, home "
  "and mission; battery %, link status, mode and mission time remaining.",
  "M", "D", "SIM", ["STK-01", "STK-02"])
R("MC-006", "The display shall be readable in daylight. A tablet or phone "
  "used as the display is acceptable.", "S", "D", "LAKE", ["STK-01"])
R("MC-007", "Mission Control shall give spoken announcements of mode "
  "changes, failsafes and mission events in child-friendly words.",
  "S", "D", "SIM", ["STK-04"])
R("MC-008", "Adult-only functions (arming, fence editing, parameter "
  "changes, mission approval) shall be protected by a PIN or key switch.",
  "M", "T", "SIM", ["STK-06"])
R("MC-009", "The last known position and track shall stay displayed after "
  "link loss, in a 'find my boat' view.", "M", "T", "SIM", ["STK-01"])
R("MC-010", "Mission Control shall host the pre-launch checklist (OPS-001) "
  "and record who signed it off, and when.", "M", "D", "SIM",
  ["STK-06", "STK-07"])
R("MC-011", "Everything except natural-language planning and cloud photo "
  "analysis shall work without internet access.", "M", "T", "SIM",
  ["STK-01", "STK-02"])
R("MC-012", "An adult shall be able to drive the boat in MANUAL from "
  "Mission Control, using an on-screen joystick or a gamepad.", "S", "D",
  "POOL", ["STK-01"])
R("MC-013", "The Mission Control case shall resist splashes (IPX4 "
  "intent).", "S", "I", "BENCH", ["STK-01"])
R("MC-015", "Mission Control shall have a photo-review mode the crew can "
  "use: large thumbnails, stepped through with the buttons, and ducks "
  "highlighted.", "S", "D", "SIM", ["STK-03", "STK-04"])
R("MC-014", "QGroundControl or MAVProxy shall be usable as a "
  "backup ground station.", "S", "D", "SIM", ["STK-01"])

# ---------------------------------------------------------------- comms
section("COM", "Communications", "")
R("COM-001", "The boat-to-bank link shall use licence-exempt 2.4 GHz Wi-Fi "
  "within UK power limits.", "M", "I", "BENCH", ["STK-07"])
R("COM-002", "Link range shall be at least 100 m line of sight over water, "
  "with the boat antenna at least 150 mm above the water.", "M", "T",
  "LAKE", ["STK-01"])
R("COM-003", "Within range: telemetry at 1 Hz or faster, and command "
  "latency of 1 s or less (95th percentile).", "M", "T", "POOL",
  ["STK-01"])
R("COM-004", "Link quality shall be shown at Mission Control and logged.",
  "S", "D", "POOL", ["STK-01"])
R("COM-005", "Mission Control shall reach the internet through a phone "
  "hotspot. Losing internet shall not affect the boat link.", "M", "T",
  "POOL", ["STK-01", "STK-02"])
R("COM-006", "The link shall be secured with WPA2 or better and "
  "non-default credentials. The boat shall accept commands only from the "
  "authenticated Mission Control.", "M", "T", "BENCH",
  ["STK-01", "STK-06"])
R("COM-007", "An independent manual-override radio link (e.g. ExpressLRS) "
  "may be added.", "C", "D", "POOL", ["STK-01"])

# ---------------------------------------------------------------- recovery
section("REC", "Recoverability and locating",
        "Passive measures that work with no power and no software.")
R("REC-001", "The boat shall stay afloat, carrying its maximum payload, "
  "with the electronics box flooded and any two hull segments breached.",
  "M", "T", "POOL", ["STK-01"])
R("REC-002", "At least 50% of the visible top surface shall be fluorescent "
  "orange or yellow.", "M", "I", "BENCH", ["STK-01"])
R("REC-003", "A flag at least 100 × 60 mm shall fly with its top at least "
  "300 mm above the waterline.", "M", "I", "BENCH", ["STK-01"])
R("REC-004", "An LED beacon shall be visible from 100 m in overcast "
  "daylight, with flash patterns showing armed, failsafe and low-battery "
  "states.", "S", "T", "LAKE", ["STK-01"])
R("REC-005", "A recovery hoop of at least 60 mm internal diameter shall be "
  "fitted to the mast. It shall withstand a 50 N pull, and the boat shall "
  "tow by it without capsizing.", "M", "T", "POOL", ["STK-01"])
R("REC-006", "The hull shall carry an 'If found' label with a contact "
  "phone number.", "M", "I", "BENCH", ["STK-01", "STK-07"])
R("REC-007", "A Bluetooth item tracker may be carried in the hull.", "C",
  "I", "BENCH", ["STK-01"])

# ---------------------------------------------------------------- mechanical
section("MEC", "Mechanical", "")
R("MEC-001", "The boat shall be a twin-hull catamaran no more than 650 mm "
  "long, 400 mm wide and 500 mm high (including mast).", "M", "I", "BENCH",
  ["STK-04", "STK-05"])
R("MEC-002", "Ready-to-sail mass, excluding payload, shall be no more than "
  "1.8 kg.", "M", "T", "BENCH", ["STK-01"])
R("MEC-003", "The boat shall carry at least 300 g of payload on the deck "
  "with at least 50 mm of freeboard.", "M", "T", "POOL", ["STK-04"])
R("MEC-004", "Static heel shall be 10° or less with 300 g at the deck edge. "
  "The boat shall not capsize in full-speed turns or in 100 mm waves.",
  "M", "T", "POOL", ["STK-01"])
R("MEC-005", "Every printed part shall fit a 200 × 200 × 200 mm build "
  "volume (Ultimaker).", "M", "I", "BENCH", ["STK-05"])
R("MEC-006", "Wetted and exposed printed parts shall be PETG or ASA. Hull "
  "segments shall be filled with closed-cell foam.", "M", "I", "BENCH",
  ["STK-01"])
R("MEC-007", "Hull segments, thruster pods, mast, electronics box and "
  "DUPLO deck shall be removable and refittable by hand, without tools.",
  "M", "D", "BENCH", ["STK-04"])
R("MEC-008", "Swapping a thruster pod shall take under 2 min. Pod "
  "connectors shall be waterproof and keyed.", "S", "D", "BENCH",
  ["STK-04"])
R("MEC-009", "The deck plate shall carry LEGO DUPLO-compatible studs. "
  "Genuine bricks shall grip firmly and be removable by a 4-year-old.",
  "M", "T", "BENCH", ["STK-04"])
R("MEC-010", "Propellers shall be guarded so that an 8 mm diameter probe "
  "cannot touch a blade.", "M", "T", "BENCH", ["STK-06"])
R("MEC-011", "Thruster pods shall include weed-shedding features: a swept "
  "leading edge and a guard shape that sheds weed.", "S", "T", "LAKE",
  ["STK-01"])
R("MEC-012", "The electronics box shall let in no water after 30 min at "
  "0.3 m depth. Every cable entry shall go through a gland.", "M", "T",
  "BENCH", ["STK-01"])
R("MEC-013", "The GNSS and compass shall be mounted at least 150 mm from "
  "motor and power wiring.", "M", "I", "BENCH", ["STK-01"])
R("MEC-014", "The boat shall fit in a car boot and have a carry handle for "
  "one adult hand.", "S", "I", "BENCH", ["STK-05"])
R("MEC-015", "Fasteners shall be stainless steel or plastic.", "S", "I",
  "BENCH", ["STK-01"])

# ---------------------------------------------------------------- power
section("PWR", "Electrical and power", "")
R("PWR-001", "Propulsion and avionics shall run from one removable 3S "
  "(nominal 11.1 V) lithium battery of 25 to 50 Wh.", "M", "I", "BENCH",
  ["STK-05"])
R("PWR-002", "The battery shall be protected against over-discharge, "
  "over-current and short circuit (BMS or equivalent).", "M", "I,T",
  "BENCH", ["STK-06"])
R("PWR-003", "A main fuse shall sit within 50 mm of the battery positive, "
  "rated no more than twice the maximum continuous current.", "M", "I",
  "BENCH", ["STK-06"])
R("PWR-004", "A waterproof main power switch shall be operable without "
  "opening the electronics box.", "M", "I", "BENCH", ["STK-06"])
R("PWR-005", "Avionics shall have a separate regulated 5 V supply. A full "
  "reverse-to-forward thrust step shall not reset or brown out the helm.",
  "M", "T", "BENCH", ["STK-01"])
R("PWR-006", "Battery voltage and current shall be measured, logged and "
  "used for state of charge and failsafes.", "M", "T", "BENCH",
  ["STK-01"])
R("PWR-007", "The battery shall be removed from the boat for charging, and "
  "charged only off-boat.", "M", "I", "BENCH", ["STK-06"])
R("PWR-008", "All power connectors shall be polarised and keyed, with no "
  "two same-type connectors doing different jobs.", "M", "I", "BENCH",
  ["STK-06"])
R("PWR-009", "Endurance at cruise speed from a full battery at 15 °C shall "
  "be at least 40 min (M), with a target of 60 min (S).", "M", "T", "LAKE",
  ["STK-01", "STK-03"])
R("PWR-010", "Electronics in the sealed box shall run for 60 min at 30 °C "
  "ambient in direct sun without fault or throttling.", "M", "T", "BENCH",
  ["STK-01"])
R("PWR-011", "A power budget shall be kept up to date alongside the "
  "design.", "S", "A", "BENCH", ["STK-01"])

# ---------------------------------------------------------------- software
section("SWE", "Software", "")
R("SWE-001", "All project-written software shall be Python: CPython 3.11+ "
  "on Linux and MicroPython on microcontrollers. Third-party firmware "
  "(ArduPilot, ESC firmware) is excluded.", "M", "I", "SIM", ["STK-08"])
R("SWE-002", "A Python helm interface shall provide: arm, disarm, set "
  "mode, upload mission, read mission back, start, hold, return home, "
  "stop, set fence, and a status stream.", "M", "I,T", "SIM", ["STK-08"])
R("SWE-003", "Mission-level code shall run unchanged against any helm "
  "implementation, selected by configuration: first ArduPilot over MAVLink, "
  "later a Python helm.", "M", "T", "SIM", ["STK-08"])
R("SWE-004", "The whole system shall run in simulation (helm simulator and "
  "simulated camera) on the Pi 5 or a laptop, with Mission Control "
  "software unchanged.", "M", "D", "SIM", ["STK-08", "STK-01"])
R("SWE-005", "Each failsafe requirement (FS-001 to FS-013) shall have an "
  "automated simulation scenario.", "M", "T", "SIM", ["STK-01"])
R("SWE-006", "Source, configuration and safety parameters shall live in "
  "this git repository, with a tagged release for each lake trial.",
  "M", "I", "SIM", ["STK-08"])
R("SWE-007", "Unit tests (pytest), linting (ruff) and type checking (mypy) "
  "shall run automatically on every push.", "S", "I", "SIM", ["STK-08"])
R("SWE-008", "All components shall timestamp in UTC, taken from GNSS where "
  "available.", "S", "T", "BENCH", ["STK-01"])
R("SWE-009", "Mission Control software shall start automatically within "
  "60 s of power-on.", "S", "T", "BENCH", ["STK-04"])

# ---------------------------------------------------------------- logging
section("LOG", "Logging and data", "")
R("LOG-001", "The helm shall log position, attitude, mode, commands, "
  "battery and failsafe events at 5 Hz or faster.", "M", "T", "BENCH",
  ["STK-01"])
R("LOG-002", "Mission Control shall log: all commands, sign-offs and "
  "approvals; each mission as approved (JSON); language model requests and "
  "replies; and validator results.", "M", "T", "SIM", ["STK-01", "STK-08"])
R("LOG-003", "The logs shall be enough to replay any trip on a map, "
  "including every failsafe event.", "M", "D", "SIM", ["STK-01"])
R("LOG-004", "Photos shall be stored locally and never published "
  "automatically. Photos go to cloud services only if an adult enables "
  "cloud analysis for that session.", "M", "I,T", "SIM", ["STK-07"])
R("LOG-005", "Logs and photos may be backed up at home and kept for at "
  "least 12 months.", "C", "I", "SIM", ["STK-03"])

# ---------------------------------------------------------------- environment
section("ENV", "Environment", "")
R("ENV-001", "The system shall operate in air at 0 to 35 °C and in fresh "
  "water at 2 to 25 °C.", "M", "A,T", "LAKE", ["STK-01"])
R("ENV-002", "The boat shall make at least 0.5 m/s headway into a 5.4 m/s "
  "wind (top of Beaufort 3).", "M", "T", "LAKE", ["STK-01"])
R("ENV-003", "The boat shall operate in waves up to 100 mm.", "M", "T",
  "LAKE", ["STK-01"])
R("ENV-004", "The boat should keep operating in light rain. Heavy rain is "
  "outside the operating envelope.", "S", "T", "POOL", ["STK-01"])
R("ENV-005", "The boat shall keep operating in sparse surface weed, "
  "recovering through FS-005 and FS-006.", "S", "T", "LAKE", ["STK-01"])
R("ENV-006", "Exposed parts shall keep their function over two seasons of "
  "outdoor use.", "C", "I", "LAKE", ["STK-05"])

# ---------------------------------------------------------------- child
section("CHD", "Child suitability",
        "Design rules for everything the 4-year-old crew member handles.")
R("CHD-001", "No child-handled part shall fit wholly inside the EN 71-1 "
  "small-parts cylinder.", "M", "T", "BENCH", ["STK-04", "STK-06"])
R("CHD-002", "Child-handled parts shall have rounded edges (radius at "
  "least 0.5 mm) and no pinch points.", "M", "I", "BENCH",
  ["STK-04", "STK-06"])
R("CHD-003", "The battery, electronics and propellers shall not be "
  "reachable without tools or an adult action.", "M", "I", "BENCH",
  ["STK-06"])
R("CHD-004", "'Child tier' assembly (hull segments, pods, deck, flag) "
  "shall need no tools and be doable with small hands.", "M", "D", "BENCH",
  ["STK-04"])
R("CHD-005", "The crew controls (GO, COME HOME, STOP, TALK) shall be usable "
  "without reading, by colour and icon alone.", "M", "D", "BENCH",
  ["STK-04"])
R("CHD-006", "No child-accessible surface shall exceed 48 °C.", "S", "T",
  "BENCH", ["STK-06"])

# ---------------------------------------------------------------- site & ops
section("OPS", "Site and operations",
        "Rules for how and where the system is used. They are verified by "
        "inspecting the checklist and the permission.")
R("OPS-001", "The pre-launch checklist shall cover at least: site "
  "permission and conditions; no swim session, course or algae notice; "
  "wind at Beaufort 3 or less, blowing towards the launch bank where "
  "possible; battery charged; box sealed and latched; props and guards; "
  "fence and exclusions reviewed on the map; recovery kit present; beacon "
  "working.", "M", "I", "POOL", ["STK-06", "STK-07", "STK-01"])
R("OPS-002", "Written permission from Cambridge Sport Lakes Trust shall be "
  "obtained before any operation at Milton Country Park, and its "
  "conditions followed.", "M", "I", "LAKE", ["STK-07"])
R("OPS-003", "There shall be no operation during swim sessions or "
  "watersports courses, or while a blue-green algae warning is posted.",
  "M", "I", "LAKE", ["STK-06", "STK-07"])
R("OPS-004", "Exclusion zones shall keep the boat at least 20 m from "
  "occupied angling swims and other water users. If anyone comes within "
  "20 m of the boat, the operator shall command RTL or HOLD.", "M", "I",
  "LAKE", ["STK-06", "STK-07"])
R("OPS-005", "Islands, reed beds and known nesting areas shall be "
  "exclusion zones. No mission shall aim to approach or follow wildlife.",
  "M", "I", "LAKE", ["STK-06"])
R("OPS-006", "At Milton, the Mk1 inclusion fence shall stay within 100 m "
  "of the launch point until at least 5 successful lake missions have "
  "been logged.", "S", "I", "LAKE", ["STK-01", "STK-07"])
R("OPS-007", "An adult operator shall be present and in control "
  "throughout. The child shall never be unsupervised near the water.",
  "M", "I", "POOL", ["STK-06"])
R("OPS-008", "The recovery kit shall include a telescopic pole of at least "
  "3 m with a landing net, and a casting rod with a weighted line. Nobody "
  "shall enter the water to recover the boat.", "M", "I", "LAKE",
  ["STK-01", "STK-06"])
R("OPS-009", "Trials shall progress: simulation, then bench, then paddling "
  "pool or small water, then lake. Each failsafe shall be demonstrated "
  "before the first lake trial.", "M", "I", "LAKE", ["STK-01"])
R("OPS-010", "Batteries shall be charged under supervision in a fire-safe "
  "bag, and stored at storage voltage.", "M", "I", "BENCH", ["STK-06"])

R("OPS-011", "A spares kit shall be taken to every session: spare "
  "propellers, a spare fuse, cable ties, a microfibre lens cloth and a "
  "towel.", "S", "I", "LAKE", ["STK-01"])
R("OPS-012", "Before the first lake trial, the operator shall rehearse "
  "every contingency scenario in section 3.5 in simulation.", "M", "D",
  "SIM", ["STK-01", "STK-06"])

# ---------------------------------------------------------------- constraints
section("CON", "Cost and constraints", "")
R("CON-001", "The Mk1 bill of materials shall not exceed £185, excluding "
  "items already owned (Pi 5, printer, tools, charger, phone, power "
  "bank). The target is £180.", "M", "A", "BENCH", ["STK-05"])
R("CON-002", "The owned Raspberry Pi 5 and Ultimaker printer shall be "
  "used.", "M", "I", "BENCH", ["STK-05"])
R("CON-003", "Purchased components shall be available from UK retailers "
  "or common online marketplaces.", "S", "I", "BENCH", ["STK-05"])
R("CON-004", "Purchased electronics shall carry CE or UKCA marking where "
  "such products are normally marked.", "S", "I", "BENCH", ["STK-07"])


# ---------------------------------------------------------------- tables
MODES = [
    ("DISARMED", "Motors inhibited. Power-on state. Safe to handle.",
     "Adult arms (MOD-003) with pre-arm checks passed."),
    ("HOLD", "Armed. Keeps station near the hold point. After a STOP or a "
     "position/stuck failsafe the motors are off and the boat drifts.",
     "GO → AUTO; COME HOME → RTL; adult → MANUAL or DISARMED."),
    ("MANUAL", "Adult drives from Mission Control. Fence still enforced.",
     "Adult → HOLD, AUTO or RTL; failsafes → HOLD or RTL."),
    ("AUTO", "Executes the loaded, validated mission.",
     "Mission end → RTL; failsafes → RTL or HOLD; STOP → HOLD (motors off)."),
    ("RTL", "Returns home inside the fence, avoiding exclusions.",
     "Arrival → HOLD; failsafes → HOLD; STOP → HOLD (motors off)."),
]

FAILSAFES = [
    ("Fence breach", "Position outside inclusion / inside exclusion",
     "RTL within 1 s", "FEN-005"),
    ("Far outside fence", "> 30 s outside, or > 10 m outside",
     "Motors stop, alarm", "FEN-006"),
    ("Low battery", "SoC ≤ 35%", "RTL", "FS-001"),
    ("Critical battery", "SoC ≤ 15%", "Continue RTL slowly, alarm", "FS-001"),
    ("Link loss (MANUAL)", "No link 3 s / 10 s", "HOLD, then RTL", "FS-002"),
    ("Link loss (AUTO)", "No link 60 s", "Continue, then RTL", "FS-003"),
    ("Position loss", "No fix, HDOP > 2.5 or unhealthy for 3 s",
     "Motors stop; RTL after 10 s healthy", "FS-004"),
    ("Stuck / weed", "Thrust ≥ 50%, speed < 0.1 m/s for 5 s",
     "HOLD, alarm, up to 3 reverse bursts", "FS-005/006"),
    ("Mission computer down", "No heartbeat 3 s",
     "Helm completes mission and RTL", "FS-007"),
    ("Helm down", "Motor commands stop", "Motors stop ≤ 1 s", "FS-008"),
    ("STOP pressed", "Operator", "Motors stop ≤ 1 s", "FS-009"),
    ("Water in box", "Moisture sensor", "RTL, alarm", "FS-010"),
]

TBDS = [
    ("TBD-01", "<b>Closed (Issue B).</b> Software route A selected: "
     "ArduPilot Rover helm, with Python above it.", "SAF-005, SWE-003, "
     "MC-014", "Owner, 28 Sep 2026"),
    ("TBD-02", "Which Milton lake, the launch point and home-bay "
     "coordinates.", "OPS-006, FEN-002", "Site visit"),
    ("TBD-03", "Cambridge Sport Lakes Trust permission and conditions.",
     "OPS-002, OPS-003", "Email the Trust"),
    ("TBD-04", "<b>Closed (Issue C).</b> Pi 5 is the Wi-Fi AP; phone "
     "USB-tethered for internet (ADD DD-06).", "COM-001, COM-005",
     "ADD Issue B"),
    ("TBD-05", "<b>Closed (Issue C).</b> On-device speech-to-text and "
     "text-to-speech on the Pi 5 (ADD DD-07).", "NLI-002", "ADD Issue B"),
    ("TBD-06", "<b>Closed (Issue C).</b> Web UI on phone or tablet "
     "(ADD DD-08).", "MC-005, MC-006", "ADD Issue B"),
    ("TBD-07", "<b>Closed (Issue C).</b> 3S Li-ion 18650 pack with BMS "
     "(ADD DD-09).", "PWR-001", "ADD Issue B"),
    ("TBD-08", "<b>Closed (Issue B).</b> Failsafe thresholds, timings and "
     "safety numbers accepted as the baseline. Trials may propose "
     "changes via SRS revision.", "FS-001 to FS-013, OPS-004/006, "
     "MEC-010", "Owner, 28 Sep 2026"),
]

GLOSSARY = [
    ("Helm", "The part of the system that steers and enforces the fence: "
     "ArduPilot on a flight controller (Route A) or a Python autopilot plus "
     "guardian (Route B)."),
    ("Mission computer", "The on-boat companion computer: camera, photos, "
     "link bridge, higher-level behaviour."),
    ("Mission Control", "The Raspberry Pi 5 bank station with GO, COME HOME, "
     "STOP and TALK buttons."),
    ("Guardian", "Route B only: an independent MicroPython microcontroller "
     "that gates motor commands."),
    ("Geofence", "An inclusion polygon the boat must stay inside, plus "
     "exclusion zones it must stay out of."),
    ("RTL", "Return To Launch: navigate home and hold."),
    ("HOLD", "Stay put: station-keeping, or motors off after STOP or some "
     "failsafes."),
    ("SoC", "State of charge of the battery, in %."),
    ("HDOP", "Horizontal dilution of precision, a GNSS quality measure. "
     "Lower is better."),
    ("MAVLink", "The message protocol spoken by ArduPilot and ground "
     "stations."),
    ("SITL", "Software In The Loop: ArduPilot running as a simulator."),
    ("FMEA", "Failure Modes and Effects Analysis."),
    ("Operator", "The responsible adult."),
    ("Crew", "The 4-year-old co-pilot."),
]


def all_reqs():
    for s in SECTIONS:
        yield from s["reqs"]


def check():
    ids = [r["id"] for r in all_reqs()]
    assert len(ids) == len(set(ids)), "duplicate IDs"
    stk = {s[0] for s in STAKEHOLDER_NEEDS}
    for r in all_reqs():
        assert r["pri"] in "MSC", r["id"]
        assert all(v in "TDIAS" for v in r["ver"].split(",")), r["id"]
        assert r["stage"] in ("SIM", "BENCH", "POOL", "LAKE"), r["id"]
        assert r["trace"] and set(r["trace"]) <= stk, r["id"]
    covered = {t for r in all_reqs() for t in r["trace"]}
    assert covered == stk, f"untraced needs: {stk - covered}"
    return len(ids)


if __name__ == "__main__":
    print(check(), "requirements OK")
