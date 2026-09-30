"""Boaty design FMEA (BOATY-FMEA-001) as data.

Each row: failure mode of an item/function, its effect, Severity (S),
cause, Occurrence (O), controls (prevention; detection in operation),
Detection by planned verification before the lake (D), tests that
exercise it (IDs from the SSS-SIM test catalogue) and actions.
check() enforces: every S >= 8 row has a test; all test and action
references exist; action rules are applied.
"""
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DOCS / "sss" / "src"))
import sss_data as SD  # noqa: E402

SEVERITY = [
    (10, "Injury to a person, or fire"),
    (9, "Boat leaves the inclusion fence under power, or risk of collision "
        "with a person"),
    (8, "Boat unrecoverable, or wildlife harmed or disturbed"),
    (7, "Boat stops or drifts inside the fence; manual recovery needed"),
    (6, "Uncommanded behaviour, contained; boat returns"),
    (5, "Mission aborted; boat returns home safely"),
    (4, "Mission degraded (no photos, no plan → templates)"),
    (3, "Minor inconvenience (reboot, re-plan)"),
    (2, "Cosmetic or record gap"),
    (1, "No effect"),
]
OCCURRENCE = [
    (8, "Expected most sessions"), (6, "Frequent: several times a season"),
    (5, "Occasional"), (4, "Likely during Mk1's life"),
    (3, "Possible, but unlikely"), (2, "Remote"), (1, "Practically nil")]
DETECTION = [
    (2, "Certain: an automated test exercises it directly"),
    (3, "High: a scripted scenario or rig test targets it"),
    (5, "Moderate: inspection, analysis or an indirect test"),
    (7, "Low: likely to show only in pool or lake use"),
    (9, "Very low: unlikely to be found before use"),
    (10, "None")]
RULES = ["Action required if S ≥ 9, whatever O and D are, unless a "
         "direct test verifies the control (D ≤ 3): then the test stands "
         "in for the action (the rule the build checks; SDR RID-13)",
         "Action required if RPN = S × O × D ≥ 100",
         "Action required if D ≥ 7 and S ≥ 7",
         "Every row with S ≥ 8 must have at least one test"]

# (id, subsystem, item / function, failure mode, effect, S, cause, O,
#  prevention, detection in operation, D, tests, actions)
ROWS = [
    # ---------------- helm and navigation
    ("FM-01", "HLM", "GNSS position", "No fix", "Motors stop (FS-004); "
     "boat drifts inside the fence", 7, "Sky blocked, module or cable "
     "fault", 3, "Mast mounting; M10 multi-constellation", "EKF failsafe",
     3, ["SC-04", "L2-03"], []),
    ("FM-02", "HLM", "GNSS position", "Position jump (glitch)", "False "
     "breach, or wrong steering near the fence", 9, "Multipath off water, "
     "reflections", 4, "EKF glitch rejection; B6 position-jump HOLD "
     "(MCP-D35)", "EKF innovation checks; B6 jump detector", 5,
     ["SC-20", "SC-13"], ["A-01", "A-30"]),
    ("FM-03", "HLM", "GNSS position", "Frozen but reported valid", "Helm "
     "navigates blind; could leave the fence", 9, "Receiver hang, data line "
     "fault", 2, "GNSS data-age checks", "EKF failsafe", 5, ["SC-21",
                                                           "L2-04"],
     ["A-01"]),
    ("FM-04", "HLM", "Heading", "Compass disturbed by motor current",
     "Curved tracks or circling", 6, "Current loops near the compass", 6,
     "Mast mount ≥ 150 mm; interference calibration", "EKF yaw checks; "
     "GNSS-velocity yaw fallback", 3, ["SC-22", "L2-05"], ["A-02"]),
    ("FM-05", "HLM", "Heading", "Compass orientation wrong", "Boat drives "
     "the wrong way; RTL also wrong; persistent breach", 9, "Parameter or "
     "mounting error", 3, "Parameter baseline check", "EKF consistency "
     "once moving", 3, ["SC-22", "SC-38", "L2-06"], ["A-03"]),
    ("FM-06", "HLM", "State estimate", "EKF diverges", "Erratic control; "
     "failsafe HOLD", 7, "Sensor fault, vibration", 2, "Stable firmware, "
     "mounting", "EKF failsafe", 3, ["SC-04"], []),
    ("FM-07", "HLM", "Flight controller", "Firmware crash / reboot "
     "mid-mission", "Outputs stop; boots disarmed; drifts", 7, "Firmware "
     "fault", 2, "Pinned stable release", "Heartbeat loss alarm", 5,
     ["SC-23", "L2-07"], []),
    ("FM-08", "HLM", "Flight controller supply", "Brownout on a thrust step "
     "or near empty", "Reboot as FM-07, during the very RTL the battery "
     "failsafe started", 7, "Pack sag below the FC's minimum input (Issue "
     "D: the F405-TE's 9 V floor, KCL KF-01; O 3 → 5)", 5, "PWR-D10/D12",
     "Logs", 3, ["L2-08", "L2-09"], ["A-21"]),
    ("FM-09", "HLM", "Configuration", "Parameters differ from baseline",
     "A failsafe doesn't fire as specified", 9, "Stale or edited "
     "parameters", 4, "Baseline file (SAF-007)", "Mismatch blocks arming "
     "(MCN-D45)", 2, ["SC-24"], []),
    ("FM-10", "HLM", "Fence", "Fence not loaded or disabled", "No fence "
     "protection", 9, "Upload skipped or failed", 3, "Pre-arm fence check",
     "Arming refused", 2, ["SC-25"], []),
    ("FM-11", "MCN", "Site data", "Coordinates swapped or wrong site",
     "Fence in the wrong place", 9, "GeoJSON [lon, lat] order error, file "
     "mix-up", 3, "Site linter", "Pre-arm: home inside fence", 3,
     ["SC-26"], ["A-04"]),
    ("FM-12", "MCN", "Site data", "Fence doesn't match the real shore "
     "(imagery offset)", "Boat reaches bank or reeds inside its 'fence'",
     7, "Satellite image offset, drawing error", 5, "5 m margin", "Operator "
     "watching", 7, ["R-01"], ["A-05"]),
    ("FM-13", "HLM", "RTL path", "RTL crosses an exclusion zone", "Island "
     "or nesting area approached", 8, "Straight-line RTL; no path planning "
     "configured (found at SDR, RID-01)", 2, "Dijkstra path planning round "
     "zones (OA_TYPE 2) with slide avoidance (HLM-D19)", "Exclusion breach "
     "→ stop", 2, ["SC-27"], []),
    ("FM-14", "HLM", "Fence", "Persistent breach doesn't stop the motors",
     "Boat keeps pushing at the shore", 8, "No native mechanism (V-14)", 3,
     "Interim HOLD from MCP and Mission Control", "Breach alarm", 5,
     ["SC-28"], ["A-18"]),
    ("FM-15", "HLM", "Battery state", "Charge over-estimated", "Late RTL; "
     "dies before home; drifts", 7, "Wrong capacity, sensor calibration", 4,
     "Calibration (PWR-D13)", "mAh failsafe only", 3, ["SC-39", "L2-09"],
     ["A-06"]),
    ("FM-16", "HLM", "Stuck detection", "Doesn't trigger in weed",
     "Motors keep driving into weed; battery drains", 7, "Boat creeps above "
     "the speed threshold", 5, "Crash check (V-05)", "Battery failsafe "
     "eventually", 5, ["SC-05", "L3-02"], ["A-07"]),
    # ---------------- propulsion and power
    ("FM-17", "PRP", "Thruster", "One motor or ESC dead or fouled", "Boat "
     "circles; can't navigate or RTL", 7, "Motor failure, weed, connector",
     4, "Keyed connectors, guards", "None native", 7, ["SC-29"], ["A-08"]),
    ("FM-18", "PRP", "Motor wiring", "Direction or channel reversed",
     "Spins or drives backwards on the first command", 9, "Build error", 4,
     "IF-05 mapping", "First-motion check (A-03)", 2, ["L2-01", "SC-38"],
     ["A-03"]),
    ("FM-19", "PRP", "ESC", "Doesn't stop on signal loss", "Runaway if the "
     "helm dies", 9, "ESC configuration", 3, "ESC failsafe setting", "-",
     2, ["L2-10"], []),
    ("FM-20", "PRP", "ESC", "Restarts at non-neutral when signal returns",
     "Sudden jolt", 6, "ESC configuration", 3, "Neutral re-arm", "-", 3,
     ["L2-10"], []),
    ("FM-21", "PRP", "Prop guard", "Guard damaged", "Finger injury risk at "
     "recovery", 10, "Impact, handling", 2, "8 mm probe design", "Checklist "
     "inspection", 5, ["B-01"], ["A-09"]),
    ("FM-22", "PWR", "Key switch", "MOSFET fails short (rail always live)",
     "Latent: arming protection is software-only", 6, "Component failure",
     2, "Rated part", "Checklist rail test (A-10)", 5, ["L2-02", "L2-13"],
     ["A-10"]),
    ("FM-23", "PWR", "Battery", "Thermal runaway or fire in the box",
     "Fire, injury", 10, "Cell damage, short, BMS fault; salvaged cells "
     "(Issue C: O 1 → 2)", 2, "BMS, fuse, hard cells, off-boat charging",
     "None in operation", 7, ["B-02", "B-07"], ["A-11", "A-20"]),
    ("FM-24", "HUL", "Box sealing", "Water ingress", "Shorts: sudden stop "
     "or erratic behaviour", 7, "Gland or lid seal", 4, "Glands, dunk test",
     "Moisture sensor → RTL", 3, ["SC-10", "B-03"], []),
    ("FM-25", "PWR", "Harness", "Fuse blows or connector pulls", "Total "
     "power loss; drifts", 7, "Overload, vibration", 2, "Rated fuse, strain "
     "relief", "Heartbeat loss", 3, ["B-04"], []),
    # ---------------- mission computer
    ("FM-26", "MCP", "Mission computer", "Crash or SD corruption", "No "
     "photos; B4-B6 absent; mission still ends in RTL", 5, "Power cut, SD "
     "wear", 4, "Read-only root", "Mission Control sees MCP silent", 2,
     ["SC-07", "L1-08"], []),
    ("FM-27", "MCP", "Boat services", "Wrong command sent (bug)", "Unwanted "
     "mode change; stuck in GUIDED", 6, "Software bug", 3, "Command filter; "
     "bounded GUIDED (V-11)", "Helm mode visible", 3, ["SC-06", "SC-30"],
     []),
    ("FM-28", "MCP", "UART link", "Traffic floods the UART", "GCS heartbeats "
     "delayed → false link-loss HOLD", 5, "Stream rates too high", 3, "Rate "
     "budget (IF-04)", "Latency logging", 3, ["L1-05"], []),
    ("FM-29", "MCP", "Camera", "Camera fails", "No photos", 4, "Ribbon, "
     "module", 3, "Strain relief", "Health: camera_ok", 2, ["B-05"], []),
    ("FM-30", "MCP", "Clock", "Wrong time before GNSS", "Photo and log "
     "times wrong", 2, "No RTC, no internet", 5, "GNSS time sync", "Flagged "
     "timestamps", 3, ["B-06"], []),
    # ---------------- mission control
    ("FM-31", "MCN", "Mission Control", "Crash or power bank dies "
     "mid-mission", "No UI, no STOP; boat returns via B4", 5, "Software, "
     "battery", 4, "Power budget, autostart", "Helm GCS failsafe", 2,
     ["SC-03", "L1-06"], []),
    ("FM-32", "MCN", "Panel", "STOP button fails", "Can't stop from the "
     "panel (web STOP remains)", 7, "Wiring, switch", 2, "Quality switch",
     "Checklist button test (A-13)", 3, ["L1-02"], ["A-13"]),
    ("FM-33", "MCN", "Panel", "GO pressed by accident", "Mission starts "
     "before the adult is ready", 6, "Child curiosity", 4, "1 s hold; "
     "adult arming", "State shown and spoken", 2, ["L1-02"], []),
    ("FM-34", "MCN", "Validator", "Accepts a mission crossing a boundary",
     "Exclusion approached; helm fence still protects", 8, "Software bug",
     2, "95% branch coverage", "Helm fence", 2, ["SC-31"], ["A-14"]),
    ("FM-35", "MCN", "Read-back", "Mismatch not detected", "Uploaded "
     "mission differs from approved", 7, "Canonical-form bug", 2, "Contract "
     "tests", "-", 2, ["SC-32"], []),
    ("FM-36", "MCN", "Planner", "Plausible but unintended plan approved",
     "Longer or different mission than wanted", 4, "Adult approves without "
     "reading", 5, "Spoken summary, map", "Visible on the map", 5,
     ["SC-33"], ["A-15"]),
    ("FM-37", "MCN", "Planner", "Odd or adversarial instruction", "Request "
     "to chase ducks etc.", 6, "Child phrasing, injection", 3, "Intent "
     "vocabulary, site names only", "Validator", 3, ["SC-33"], []),
    ("FM-38", "MCN", "Internet", "No internet", "Templates only", 3,
     "No mobile signal", 6, "Offline templates", "UI message", 2, ["P-01"],
     []),
    ("FM-39", "MCN", "Link", "Link flaps at the range edge", "Repeated "
     "HOLD/continue in MANUAL", 5, "Range, geometry", 6, "Pole antenna",
     "RSSI display", 3, ["SC-34", "L1-07"], []),
    ("FM-40", "MCN", "Link", "Commands delayed > 1 s", "STOP late", 7,
     "Congestion, interference", 3, "Traffic budget", "Latency logging", 3,
     ["SC-34", "L1-03", "L2-11"], []),
    ("FM-41", "MCN", "GCS identity", "Two ground stations connected",
     "Conflicting commands", 6, "QGC left running", 3, "MC-014 procedure",
     "-", 5, ["SC-37"], ["A-16"]),
    # ---------------- operations and people
    ("FM-42", "OPS", "Launch", "Launched with wind away from the bank",
     "A dead boat drifts away", 7, "Procedure not followed", 4, "Checklist",
     "Operator", 5, ["R-01"], ["A-19"]),
    ("FM-43", "OPS", "Other users", "Swimmer or paddler near the boat",
     "Collision risk (slow boat, guarded props)", 9, "Shared water", 3,
     "OPS-003/004, low speed, guards", "Operator lookout", 7, ["R-01"],
     ["A-17"]),
    ("FM-44", "OPS", "Wildlife", "Nesting area approached", "Disturbance",
     8, "Exclusions missing or too small", 2, "OPS-005 exclusions; 15 m "
     "nest stand-off enforced by the site linter (MCN-D65, CR-07); photo "
     "stops only outside it", "Operator", 3, ["R-01", "SC-26", "SC-27"],
     []),
    ("FM-45", "OPS", "Handling", "Child handles a pod with the key in",
     "Prop injury risk", 10, "Supervision lapse", 2, "Guards; adult-only "
     "arming", "Key-out rule (A-09)", 5, ["B-01"], ["A-09"]),
    ("FM-46", "MCN", "Home", "Home set wrongly", "RTL goes to the wrong "
     "place", 6, "Armed before GNSS settled", 3, "Home shown before GO",
     "Map", 3, ["SC-35"], []),
    ("FM-48", "MCN", "Adult unlock", "Child learns or guesses the PIN "
     "(Issue C)", "Could arm or approve without an adult. Motors still need "
     "the magnetic key.", 6, "PIN seen or shared", 3, "6 digits, lockout, "
     "never shown or spoken; the magnetic key physically gates the motors",
     "Checklist; approval log", 3, ["L1-10"], []),
    ("FM-47", "MCN", "Mission upload", "Upload interrupted (partial "
     "mission)", "Wrong mission executed", 6, "Link drop mid-transfer", 4,
     "Transfer protocol", "Read-back (VAL-010)", 2, ["SC-36", "SC-32"], []),
    # ---------------- found in simulation (Issue D)
    ("FM-49", "MCP", "B7 heading check", "Wind drift read as a reversed "
     "compass", "Nuisance HOLD with a wrong diagnosis; boat drifts downwind",
     5, "Wind stronger than the boat's thrust blows it backwards at RTL "
     "start (far beyond ENV-002)", 2, "Wind limit and launch-point "
     "procedure (A-19)", "Alarm names the check", 3, ["SC-28"], []),
    ("FM-50", "MCP", "B5 weed-shedding", "Dead motor treated as weed",
     "Futile astern bursts, then HOLD with a 'stuck' alarm instead of "
     "'motor fault'", 4, "The crash check cannot tell weed from a dead "
     "motor", 4, "Ends in HOLD + alarm either way", "Adult inspects on "
     "recovery", 3, ["SC-29"], []),
    ("FM-51", "MCP", "Boat services", "Command sent before the helm "
     "reports the mode", "Filter refuses it: the first second of each "
     "weed burst is lost", 4, "Heartbeat (1 Hz) lags the mode change", 8,
     "-", "Filter refusal log", 2, ["SC-06"], ["A-22"]),
    ("FM-52", "MCP", "B5 astern burst", "Boat pivots instead of backing "
     "out", "Turns into the weed; may foul the second pod", 6, "Negative "
     "body-frame velocity target: Rover turns round and drives forwards "
     "(specification error, ICD Issue D)", 10, "-", "None before "
     "simulation", 7, ["SC-06"], ["A-23"]),
    ("FM-53", "HLM", "Modes", "Arms into MANUAL instead of HOLD", "The "
     "boat is armed in a mode that obeys stick input; surprise for the "
     "adult", 5, "RC mode switch overrides INITIAL_MODE (firmware "
     "defaults)", 8, "-", "Mode shown at Mission Control", 3, ["SC-40"],
     ["A-24"]),
    # ---------------- Issue E: Mission Control in the simulator (slice 3)
    ("FM-54", "MCN", "Validator", "A far-away waypoint stalls validation",
     "Planning hangs for about a minute; no plan shown", 3, "Legs sampled "
     "every 1 m regardless of length (0° N 0° E: 5,800 km)", 5, "-",
     "Unit test found it", 3, ["SC-31"], ["A-25"]),
    ("FM-55", "MCN", "Helm interface", "Parameter values lost in transfer",
     "False baseline differences block arming on a good boat", 3, "A few "
     "of ~1,300 PARAM_VALUE messages dropped on a busy link", 6, "-",
     "Arming refused with a list of names", 2, ["SC-24"], ["A-26"]),
    ("FM-56", "MCN", "Session", "A boat-service stop is announced wrongly "
     "or not at all", "Adult not told why the boat stopped; child hears "
     "'stuck in weed' repeatedly", 5, "The mode change arrives before the "
     "service's reason text", 6, "-", "Map shows HOLD", 5, ["SC-43"],
     ["A-27"]),
    ("FM-57", "MCN", "Session", "Return home not recognised", "No 'coming "
     "home' or 'I'm back', no auto-disarm at home", 4, "The final RTL item "
     "runs in AUTO; the mode never becomes RTL", 10, "-", "Seen in the "
     "first end-to-end run", 3, ["SC-41"], ["A-28"]),
    ("FM-58", "MCP", "B5 weed-shedding", "Free test misjudges the boat",
     "Freed boat held with a 'still stuck' alarm; or a boat with a dead "
     "motor 'freed' again and again and never stopped", 6, "Free test used "
     "ground-speed magnitude, so astern drift left by the burst counted as "
     "moving; no limit on repeat episodes", 6, "-", "Found by SC-06 "
     "intermittency and MCN-D60", 4, ["SC-06", "SC-29", "SC-43"],
     ["A-29"]),
    ("FM-59", "HLM", "RTL path", "RTL stalls short of home near an "
     "exclusion", "Boat stops inside the fence, not home; adult must "
     "drive it back", 6, "Planner leg passes close to a zone and fence "
     "avoidance set to 'stop' halts the boat; or the planner finds no "
     "path", 2, "AVOID_BEHAVE slide; OA_MARGIN_MAX > FENCE_MARGIN + corner "
     "cut (HLM-D19)", "Mission Control shows RTL with no progress; "
     "operator", 3, ["SC-27"], []),
    ("FM-60", "MCN", "Home", "Boat re-armed away from the launch point",
     "Home resets to where it was re-armed, maybe mid-lake; RTL goes "
     "there", 7, "Adult disarms and re-arms on the water (e.g. after a "
     "STOP)", 3, "Arm at the jetty (CL-13); VAL-004 home sanity check "
     "before approval", "Mission Control refuses the plan and says why",
     2, ["SC-35", "SC-09"], []),
]

ACTIONS = [
    ("A-01", "Confirm GNSS glitch and freeze protection parameters; add "
     "SC-20/21", "HLM", "SSS-HLM Issue B", ["FM-02", "FM-03"]),
    ("A-02", "Measure compass interference on rig L2 before the hull "
     "layout is frozen", "HLM", "Rig L2", ["FM-04"]),
    ("A-03", "Add a first-motion heading check: in the first 10 s of any "
     "driven mode, GNSS course vs heading differs > 45° → HOLD + alarm",
     "MCN / MCP", "SSS-MCN/MCP Issue B", ["FM-05", "FM-18"]),
    ("A-04", "Site linter: home inside the fence; site within 1 km of the "
     "configured reference; coordinate-order sanity", "MCN", "SSS-MCN "
     "Issue B", ["FM-11"]),
    ("A-05", "Fence survey procedure: walk the launch bank with a GNSS "
     "reference to check imagery offset before the first mission at a "
     "site", "OPS", "Operations manual", ["FM-12"]),
    ("A-06", "Add voltage thresholds as a backstop to the mAh battery "
     "failsafe", "HLM", "SSS-HLM Issue B", ["FM-15"]),
    ("A-07", "Second stuck detector in the MCP: throttle high and progress "
     "along track low for 10 s → HOLD", "MCP", "SSS-MCP Issue B",
     ["FM-16"]),
    ("A-08", "Navigation-divergence watchdog in the MCP: cross-track > 10 m "
     "or heading error > 60° for 20 s → HOLD + alarm", "MCP",
     "SSS-MCP Issue B", ["FM-17"]),
    ("A-09", "Checklist and procedure: key out before anyone touches the "
     "boat; lift only by the handle or hoop; inspect guards", "OPS",
     "Operations manual", ["FM-21", "FM-45"]),
    ("A-10", "Checklist step: key out → confirm motor rail reads 0 V on "
     "screen", "MCN", "SSS-MCN Issue B", ["FM-22"]),
    ("A-11", "Box temperature sensor with alarm and RTL above 60 °C; "
     "battery inspection before each session", "MCP / OPS",
     "SSS-MCP Issue B", ["FM-23"]),
    ("A-13", "Checklist button test: each crew button pressed, LED and "
     "sound confirm", "MCN", "SSS-MCN Issue B", ["FM-32"]),
    ("A-14", "Property-based validator tests against an independent "
     "geometry implementation", "SIM", "SSS-SIM Issue B (done: SIM-D09)",
     ["FM-34"]),
    ("A-15", "Plan preview shows duration and distance prominently before "
     "approval", "MCN", "SSS-MCN Issue B", ["FM-36"]),
    ("A-16", "C7 detects a foreign system-255 heartbeat and refuses to "
     "operate", "MCN", "SSS-MCN Issue B", ["FM-41"]),
    ("A-17", "Operator is the dedicated lookout; brief 'STOP if in doubt'; "
     "no missions while people are within 50 m of the planned route",
     "OPS", "Operations manual", ["FM-43"]),
    ("A-18", "Resolve V-14; if there's no native mechanism, specify the "
     "interim HOLD path formally", "HLM", "SSS-HLM Issue B", ["FM-14"]),
]
ACTIONS.append(
    ("A-19", "Site file lists the preferred launch point per wind "
     "direction; the checklist asks 'is the wind blowing towards us?' and "
     "suggests the launch point", "MCN / OPS", "SSS-MCN Issue B; "
     "operations manual", ["FM-42"]))
ACTIONS.append(
    ("A-20", "Salvaged-cell acceptance tests and records (capacity, "
     "internal resistance, self-discharge, matching, visual)", "PWR",
     "SSS-PWR Issue B", ["FM-23"]))
ACTIONS += [
    ("A-21", "Flight controller that runs from 7 V (CR-04) and a motor "
     "power limit so sag near empty cannot brown out any supply", "HLM / "
     "PWR", "SSS-HLM/PWR Issue C-D", ["FM-08"]),
    ("A-22", "Services wait until the helm reports the mode before sending "
     "mode-dependent commands", "MCP", "SSS-MCP Issue C", ["FM-51"]),
    ("A-23", "Astern bursts by SET_ATTITUDE_TARGET thrust with zero yaw "
     "rate; the filter allows only that form", "MCP", "SSS-MCP Issue C; ICD "
     "Issue E", ["FM-52"]),
    ("A-24", "Boot and arm into HOLD; no RC mode switch; RC receiver "
     "ignored", "HLM", "SSS-HLM Issue D", ["FM-53"]),
    ("A-25", "Validator checks each leg's ends before sampling it",
     "MCN", "SSS-MCN Issue D", ["FM-54"]),
    ("A-26", "Fetch dropped parameters again by index before comparing",
     "MCN", "SSS-MCN Issue D; ICD Issue F", ["FM-55"]),
    ("A-27", "Take the reason from the service event; announce an "
     "unexplained HOLD after 1 s; weed once per episode", "MCN",
     "SSS-MCN Issue D", ["FM-56"]),
    ("A-28", "Follow mission progress by item sequence", "MCN",
     "SSS-MCN Issue D; ICD Issue F", ["FM-57"]),
    ("A-29", "Free = forward speed along the heading > 0.2 m/s for 1 s "
     "within 8 s; more than 3 episodes in 2 min: HOLD + 'repeatedly "
     "stuck'; a failed mode switch is reported as 'no control'", "MCP",
     "SSS-MCP Issue D", ["FM-58"]),
    ("A-30", "B6 holds (latched, no automatic RTL) when the helm's position "
     "jumps further than the boat could move: a sustained GNSS offset "
     "otherwise took the boat 12 m outside the fence (SC-20)", "MCP",
     "SSS-MCP Issue E", ["FM-02"]),
]
# A-12 intentionally unused (merged into A-13 during review).

RESIDUAL = [
    ("FM-43", "Swimmer or paddler near the boat. No sensor detects people. "
     "Relies on procedure, low speed, guarded props and the operator "
     "lookout. Accepted for Mk1 with A-17."),
    ("FM-31", "If Mission Control dies, the Wi-Fi access point dies with "
     "it, so there's no remote STOP. The boat returns by itself (B4 at "
     "60 s). Accepted: severity 5."),
    ("FM-23", "Battery fire can't be detected early on board. Mitigated by "
     "hard cells, BMS, fuse and off-boat charging (occurrence 1), plus "
     "A-11. Accepted."),
    ("Common cause", "The fence and the failsafes both run on the flight "
     "controller, so a flight-controller logic fault is a common cause. "
     "Mitigations: a pinned stable firmware, ESC stop on signal loss, the "
     "shore physically bounds the lake, a short mission time, and operator "
     "STOP. Accepted for Mk1. A future independent guardian (SAF-005) "
     "would remove it."),
]


def rpn(r):
    return r[5] * r[7] * r[10]


def needs_action(r):
    s, o, d = r[5], r[7], r[10]
    return s >= 9 or s * o * d >= 100 or (d >= 7 and s >= 7)


def check():
    tests = {t[0]: t for t in SD.TESTS}
    ids = [r[0] for r in ROWS]
    assert len(ids) == len(set(ids))
    acts = {a[0] for a in ACTIONS}
    for r in ROWS:
        for t in r[11]:
            assert t in tests, (r[0], t)
        for a in r[12]:
            assert a in acts, (r[0], a)
        if r[5] >= 8:
            assert r[11], (r[0], "S>=8 without a test")
        if needs_action(r) and not r[12]:
            # an action is not needed if a direct test exists (D <= 3)
            assert r[10] <= 3 and r[11], (r[0], "needs action or test")
    for a in ACTIONS:
        for fm in a[4]:
            assert fm in ids, (a[0], fm)
    # test catalogue references to FM rows must exist
    for t in SD.TESTS:
        for ref in t[5]:
            if ref.startswith("FM-"):
                assert ref in ids, (t[0], ref)
    return len(ROWS)


if __name__ == "__main__":
    print(check(), "failure modes OK")
    for r in sorted(ROWS, key=rpn, reverse=True)[:10]:
        print(r[0], r[5], r[7], r[10], rpn(r))


# ---------------------------------------------------------------- Issue B
# Where each action went, and ratings after the incorporated actions.
STATUS = {
    "A-01": ("Incorporated", ["HLM-D39"]),
    "A-02": ("Incorporated", ["HLM-D41"]),
    "A-03": ("Incorporated", ["MCP-D22", "MCN-D60"]),
    "A-04": ("Incorporated", ["MCN-D53"]),
    "A-05": ("Incorporated", ["OP-01"]),
    "A-06": ("Incorporated", ["HLM-D40"]),
    "A-07": ("Incorporated", ["MCP-D23"]),
    "A-08": ("Incorporated", ["MCP-D24"]),
    "A-09": ("Incorporated", ["OP-05", "OP-09", "OP-11", "CL-09"]),
    "A-10": ("Incorporated", ["MCN-D54"]),
    "A-11": ("Incorporated", ["MCP-D26", "OP-04", "CL-07"]),
    "A-13": ("Incorporated", ["MCN-D55"]),
    "A-14": ("Incorporated", ["SIM-D09"]),
    "A-15": ("Incorporated", ["MCN-D56"]),
    "A-16": ("Incorporated", ["MCN-D57"]),
    "A-17": ("Incorporated", ["OP-10", "CL-03", "CL-17", "K-06"]),
    "A-18": ("Incorporated; V-14 answered (no native mechanism)",
             ["HLM-D24", "MCN-D59", "MCP-D30"]),
    "A-19": ("Incorporated", ["MCN-D58", "OP-06", "CL-06"]),
    "A-20": ("Incorporated", ["PWR-D20", "PWR-D21"]),
    "A-21": ("Incorporated", ["HLM-D02", "HLM-D43", "PWR-D22"]),
    "A-22": ("Incorporated", ["MCP-D32"]),
    "A-23": ("Incorporated", ["MCP-D18", "MCP-D19"]),
    "A-24": ("Incorporated", ["HLM-D05"]),
    "A-25": ("Incorporated", ["MCN-D39"]),
    "A-26": ("Incorporated", ["MCN-D45"]),
    "A-27": ("Incorporated", ["MCN-D60"]),
    "A-28": ("Incorporated", ["MCN-D62"]),
    "A-29": ("Incorporated", ["MCP-D34"]),
    "A-30": ("Incorporated", ["MCP-D35"]),
}
# FM id -> (O, D) after incorporated actions (S unchanged)
POST = {
    "FM-02": (4, 2), "FM-03": (2, 3), "FM-04": (4, 3), "FM-05": (2, 2),
    "FM-11": (2, 3), "FM-14": (3, 2), "FM-15": (2, 3), "FM-16": (4, 3),
    "FM-17": (4, 2), "FM-18": (3, 2), "FM-22": (2, 3), "FM-23": (1, 5),
    "FM-32": (1, 3), "FM-12": (2, 5), "FM-21": (1, 5), "FM-45": (1, 5),
    "FM-43": (2, 7), "FM-36": (3, 5), "FM-41": (3, 1), "FM-42": (2, 5),
    # Issue D: simulator evidence and slice-2 fixes
    "FM-08": (1, 3), "FM-51": (1, 2), "FM-52": (1, 2), "FM-53": (1, 2),
    # Issue E: Mission Control scenarios pass (slice 3)
    "FM-09": (4, 1), "FM-10": (3, 1), "FM-34": (1, 2), "FM-35": (2, 1),
    "FM-54": (1, 2), "FM-55": (1, 2), "FM-56": (2, 2), "FM-57": (1, 2),
    "FM-58": (2, 3),
    # SC-33 run live: 39/39, every must-decline declined
    "FM-37": (2, 2),
}


def rpn_after(r):
    o, d = POST.get(r[0], (r[7], r[10]))
    return r[5] * o * d


def check_b():
    derived = {d["id"] for ss in SD.SUBSYSTEMS.values()
               for d in SD.all_derived(ss)}
    sys.path.insert(0, str(DOCS / "ops" / "src"))
    import ops_data as OPS  # noqa: E402
    derived |= OPS.ids()
    assert set(STATUS) == {a[0] for a in ACTIONS}
    for a, (st, ids) in STATUS.items():
        for i in ids:
            assert i in derived, (a, i)
        if st.startswith("Incorporated"):
            assert ids, a
    return True
