"""Boaty Operations Manual (BOATY-OPS-001) as data.

The pre-launch checklist here is the single source for the checklist that
Mission Control hosts (MCN-D13). check() confirms every SRS operations
requirement (OPS-001..012) and every procedural FMEA action is covered.
"""

# ---------------------------------------------------------------- roles
ROLES = [
    ("Operator (adult)", "In charge of safety from packing to unpacking. "
     "Holds the magnetic arming key and the PIN. Is the lookout during every "
     "mission. Makes every go / no-go call."),
    ("Crew (age 4)", "Builds and decorates the boat, gives the orders with "
     "TALK, presses GO, COME HOME and STOP, spots the boat, finds the ducks. "
     "Never goes near the water's edge alone."),
]

GOLDEN_RULES = [
    ("People first, boat second.", "If anyone could get hurt, forget the "
     "boat. It floats and it can wait.", ["OPS-007"]),
    ("Nobody goes in the water.", "Not for the boat, not for anything. Use "
     "the pole, the net or the casting line.", ["OPS-008"]),
    ("Key out before hands on.", "Pull the magnetic key before anyone "
     "touches the boat, and keep it until the boat is on the water.",
     ["A-09"]),
    ("The operator is the lookout.", "Eyes on the boat and the water for "
     "the whole mission. If in doubt, STOP.", ["A-17", "OPS-004"]),
    ("Never on shared water without permission.", "Milton means the "
     "Trust's permission and its conditions.", ["OPS-002"]),
]

# ---------------------------------------------------------------- kit
KIT = [
    ("Boat", ["Boat (hulls, pods fitted, mast, flag)", "DUPLO crew",
              "Magnetic arming key on its lanyard (operator's pocket)"]),
    ("Bank station", ["Mission Control box", "USB-C power bank (charged)",
                      "Phone + USB cable (tether and screen)",
                      "Antenna pole kit (if V-08 showed it's needed)"]),
    ("Battery", ["Boat battery in a fire-safe bag, charged the day before, "
                 "carried separately from the boat"]),
    ("Recovery kit", ["Telescopic pole ≥ 3 m with landing net",
                      "Casting rod with weighted float line",
                      "Throw towel"]),
    ("Spares kit", ["Spare props", "Spare 20 A fuse", "Cable ties",
                    "Microfibre lens cloth", "Towel", "Small screwdriver "
                    "(adult use)"]),
    ("People", ["Drinks and snacks", "Hand gel or wipes (algae)",
                "Sun hats / waterproofs"]),
]

# ---------------------------------------------------------------- procedures
PROCEDURES = [
    dict(id="OP-01", title="Setting up a new site (once per site)",
         when="Before the first session at any water", who="Operator",
         purpose="Make sure the fence matches the real water, and that we're "
                 "allowed and welcome there.",
         steps=[
             ("Get written permission from the landowner. At Milton, email "
              "Cambridge Sport Lakes Trust and record their conditions in "
              "the site notes.", ["OPS-002"]),
             ("Draw the site on the map at home: inclusion fence 5 m inside "
              "the waterline, home points, areas and landmarks.",
              ["FEN-002", "FEN-003"]),
             ("Add exclusion zones over islands, reed beds and angling "
              "swims (≥ 20 m clearance). Put a circle of at least 15 m "
              "radius round every nest structure (duck house, nest raft) "
              "and tag it wildlife = nest; the site check refuses less. "
              "Photos of birds are taken only from outside these circles.",
              ["OPS-004", "OPS-005"]),
             ("Keep the first fence within 100 m of the launch point. Grow "
              "it only after 5 successful missions logged at this site.",
              ["OPS-006"]),
             ("<b>Fence survey walk.</b> On the first visit, walk the launch "
              "bank carrying the boat's GNSS (or the phone) with logging on. "
              "Compare the logged track with the drawn waterline. If they "
              "differ by more than 3 m, shift the fence and record the "
              "offset in the site file.", ["A-05"]),
             ("Mark launch points and the wind directions each suits (wind "
              "blowing towards that bank).", ["A-19"]),
             ("Run the site linter. It must pass before the site can be "
              "used.", ["MCN-D53"]),
         ],
         notes="Redo the survey walk if the water level has changed a lot or "
               "the boat ever reaches the bank inside its fence."),
    dict(id="OP-02", title="Trial progression", when="Once, from first "
         "power-up to first lake mission", who="Operator",
         purpose="Never find a problem on the lake that we could have found "
                 "at home.",
         steps=[
             ("Simulation: every failsafe scenario passes (SC-01 to SC-13), "
              "and the FMEA scenarios run.", ["OPS-009", "SWE-005"]),
             ("Bench rigs L1 and L2: STOP, key, ESC signal loss and "
              "brownout tests pass.", ["OPS-009"]),
             ("Paddling pool: floats level, drives, stops, stuck detection, "
              "photo sync, crew controls.", ["OPS-009"]),
             ("Small private water (if available): first autonomous "
              "missions within casting range.", ["OPS-009"]),
             ("Lake: only when every SIM, BENCH and POOL Must requirement "
              "has passed, and OP-03 is done.", ["OPS-009", "OPS-012"]),
         ], notes=None),
    dict(id="OP-03", title="Rehearsal at home", when="Before the first "
         "lake trial, then each spring", who="Operator (and crew)",
         purpose="Practise every contingency where mistakes are free.",
         steps=[
             ("Start the simulator in rehearsal mode with the real panel.",
              ["SIM-D05"]),
             ("Work through every contingency card (section 6) at least "
              "once: recognise it, act, recover.", ["OPS-012"]),
             ("Let the crew practise TALK, GO, COME HOME and STOP on the "
              "virtual lake.", ["OPS-012"]),
         ], notes=None),
    dict(id="OP-04", title="The day before", when="Every session",
         who="Operator",
         purpose="Arrive with a healthy battery, the right software and the "
                 "right kit.",
         steps=[
             ("<b>Battery inspection:</b> no swelling, dents, wrapper damage "
              "or smell. Cell voltages balanced within 0.05 V. Pack at room "
              "temperature. Any doubt: don't use it.", ["A-11", "PWR-D20"]),
             ("Charge on a balance charger, in the fire-safe bag, on a "
              "non-flammable surface, attended. Never charge in the boat.",
              ["OPS-010", "PWR-007"]),
             ("Software: use the tagged release only. Run the simulator "
              "suite if anything changed.", ["SWE-006"]),
             ("Check the forecast: wind at the lake ≤ Beaufort 3, no "
              "storms.", ["OPS-001"]),
             ("Pack the kit lists (section 3), including the recovery and "
              "spares kits.", ["OPS-008", "OPS-011"]),
         ], notes=None),
    dict(id="OP-05", title="Transport", when="Every session", who="Operator",
         purpose="Arrive with nothing broken or live.",
         steps=[
             ("Battery in its fire-safe bag, separate from the boat.",
              ["PWR-007"]),
             ("Magnetic key in the operator's pocket, never on the boat.",
              ["A-09", "MOD-003"]),
             ("Boat in its cradle with the mast removed.", ["MEC-014"]),
         ], notes=None),
    dict(id="OP-06", title="Setting up on the bank", when="Every session",
         who="Operator, crew helping",
         purpose="Decide whether today is a go, and set up safely.",
         steps=[
             ("Read the notice boards: no swim session, no watersports "
              "course, no algae warning. If any, go home and try another "
              "day.", ["OPS-003"]),
             ("Look at the water: who else is here? Keep ≥ 20 m from "
              "anglers' lines and other users.", ["OPS-004"]),
             ("Check the wind. Choose the launch point the site file "
              "suggests for today's wind, so a stopped boat drifts to us.",
              ["A-19", "OPS-001"]),
             ("Set up Mission Control a few metres back from the edge. "
              "Plug in the phone and start the app.", ["OPS-007"]),
             ("Crew fits the pods and the DUPLO crew. <b>Key stays in the "
              "operator's pocket.</b>", ["A-09", "CHD-004"]),
             ("Fit the battery, close and latch the box, main switch on.",
              ["MEC-012"]),
             ("Work through the pre-launch checklist on screen (section 5). "
              "Every item must be ticked before arming is possible.",
              ["OPS-001", "PRE-006"]),
         ], notes=None),
    dict(id="OP-07", title="Crew briefing", when="Every session, before "
         "planning", who="Operator to crew",
         purpose="Four buttons, four rules, in words a 4-year-old knows.",
         steps=[
             ("Show the four buttons (see the crew card): blue TALK to tell "
              "the boat, green GO to start, yellow house to come home, red "
              "STOP.", ["CHD-005"]),
             ("Rule 1: we stay behind the line (a rope or bag marks it).",
              ["OPS-007"]),
             ("Rule 2: only grown-ups touch the boat when it's on the "
              "water.", ["A-09"]),
             ("Rule 3: if you're worried, press the red button. Nobody will "
              "be cross.", ["FS-009"]),
             ("Rule 4: we never go in the water, even for the boat.",
              ["OPS-008"]),
         ], notes=None),
    dict(id="OP-08", title="Planning the mission", when="Every mission",
         who="Crew speaks, operator approves",
         purpose="Turn the crew's idea into a safe plan.",
         steps=[
             ("Crew holds TALK and says what the boat should do.",
              ["NLI-002"]),
             ("Listen to the summary and look at the map: duration, "
              "distance, photo count, furthest point from home.",
              ["MCN-D56", "NLI-005"]),
             ("Check the route stays well clear of other people and "
              "wildlife. If anyone is within 50 m of the route, change the "
              "plan or wait.", ["A-17", "OPS-005"]),
             ("Approve with the PIN (never read the PIN aloud). No internet: "
              "choose a template with the crew.", ["VAL-008", "MIS-005"]),
         ], notes=None),
    dict(id="OP-09", title="Launch and arming", when="Every mission",
         who="Operator",
         purpose="Get the boat on the water with nobody's hands near a "
                 "prop.",
         steps=[
             ("Carry the boat by the handle, put it on the water at the "
              "chosen launch point, and step back.", ["A-09"]),
             ("Only now insert the magnetic key into its dock.", ["A-09",
                                                                  "MOD-003"]),
             ("Arm at Mission Control. Check home is shown in the right "
              "place.", ["MOD-003", "FM-46"]),
             ("Crew holds GO for a second: 'Off we go!'", ["MC-004"]),
         ], notes=None),
    dict(id="OP-10", title="During the mission: the lookout",
         when="Whole mission", who="Operator",
         purpose="Be the eyes the boat doesn't have.",
         steps=[
             ("Watch the boat and the water around it all the time. Hand "
              "the phone to nobody.", ["A-17"]),
             ("Anyone (swimmer, paddler, dog, angler's line) within 20 m of "
              "the boat or 50 m of its route: press COME HOME, or STOP if "
              "closer.", ["OPS-004", "A-17"]),
             ("Birds with young, or the boat heading for reeds or nests: "
              "COME HOME.", ["OPS-005"]),
             ("Keep the crew behind the line. Being with the child comes "
              "before watching the boat.", ["OPS-007"]),
             ("Anything strange (circling, wrong direction, alarms): STOP "
              "first, think second (section 6).", ["FM-17", "FM-05"]),
         ], notes=None),
    dict(id="OP-11", title="Recovering the boat", when="End of every "
         "mission", who="Operator",
         purpose="Get the boat out with the motors dead.",
         steps=[
             ("Boat waits by the bank at home (HOLD). Disarm at Mission "
              "Control.", ["MOD-005"]),
             ("<b>Pull the magnetic key</b> and pocket it, then lift the "
              "boat by the handle or hoop. Never by a pod.", ["A-09"]),
             ("Look at the guards and props: cracked guard = no more "
              "missions today.", ["A-09", "MEC-010"]),
         ], notes=None),
    dict(id="OP-12", title="After the session", when="Every session",
         who="Operator, crew for photos",
         purpose="Leave the boat, battery and records ready for next time.",
         steps=[
             ("Let photos sync and make the captain's log together.",
              ["DET-002"]),
             ("Rinse pods and hulls with clean water and dry the motors. "
              "Everyone washes hands.", ["OPS-003"]),
             ("Main switch off only after Mission Control says the mission "
              "computer has shut down.", ["IF-08"]),
             ("Battery out, home in the fire-safe bag. Within a day, "
              "storage-charge it (≈ 3.7 V/cell).", ["OPS-010"]),
             ("Download logs. Note anything odd as an incident (OP-14).",
              ["LOG-003"]),
         ], notes=None),
    dict(id="OP-13", title="Maintenance", when="See table", who="Operator",
         purpose="Catch wear before it catches us.", steps=[], notes=None),
    dict(id="OP-14", title="Incidents and learning", when="Whenever "
         "something unexpected happens", who="Operator",
         purpose="Every surprise makes Boaty safer.",
         steps=[
             ("Write down what happened, when, and what the logs show.",
              ["LOG-003"]),
             ("Check it against the FMEA. New failure mode or worse than "
              "rated? Update the FMEA and add a test.", ["SAF-006"]),
             ("Anything involving people or wildlife: pause lake sessions "
              "until it's understood.", ["OPS-004", "OPS-005"]),
         ], notes=None),
]

# ---------------------------------------------------------------- checklist
# (id, group, text, how checked, refs) — Mission Control hosts this (MCN-D13)
CHECKLIST = [
    ("CL-01", "Site and people", "Permission held and today's conditions "
     "met", "Operator", ["OPS-002"]),
    ("CL-02", "Site and people", "No swim session, watersports course or "
     "algae warning", "Operator", ["OPS-003"]),
    ("CL-03", "Site and people", "Nobody within 50 m of the planned area; "
     "anglers' swims excluded", "Operator", ["OPS-004", "A-17"]),
    ("CL-04", "Site and people", "Wildlife exclusions reviewed on the map",
     "Operator", ["OPS-005"]),
    ("CL-05", "Weather", "Wind Beaufort 3 or less (small waves, few white "
     "horses)", "Operator", ["OPS-001"]),
    ("CL-06", "Weather", "Wind blowing towards our bank; launch point "
     "chosen", "Operator (suggested by the app)", ["A-19", "OPS-001"]),
    ("CL-07", "Boat", "Battery inspected and ≥ 80% charged", "Operator + "
     "automatic", ["A-11", "PRE-003"]),
    ("CL-08", "Boat", "Box sealed and latched; glands tight", "Operator",
     ["OPS-001", "MEC-012"]),
    ("CL-09", "Boat", "Guards intact; props free; pods latched",
     "Operator", ["A-09", "MEC-010"]),
    ("CL-10", "Boat", "Flag, hoop and beacon fitted and working", "Operator",
     ["OPS-001", "REC-003"]),
    ("CL-11", "Boat", "Key-out rail test passed", "Automatic", ["MCN-D54"]),
    ("CL-12", "Bank", "Button test passed (TALK, GO, COME HOME, STOP)",
     "Automatic", ["MCN-D55"]),
    ("CL-13", "System", "Fence and exclusions reviewed; boat at the jetty "
     "when armed (the helm takes home from where it is armed; Mission "
     "Control refuses a plan more than 10 m from the site's home)",
     "Operator", ["OPS-001", "PRE-002", "VAL-004"]),
    ("CL-14", "System", "Parameters match baseline; ≥ 8 satellites; link "
     "good", "Automatic", ["SAF-007", "PRE-001"]),
    ("CL-15", "Recovery", "Recovery kit on the bank (pole and net, casting "
     "rod and line)", "Operator", ["OPS-008", "OPS-001"]),
    ("CL-16", "Recovery", "Spares kit on the bank", "Operator",
     ["OPS-011"]),
    ("CL-17", "People", "Adult operator present and acting as lookout; crew "
     "briefed", "Operator", ["OPS-007", "A-17"]),
    ("CL-18", "System", "Anything else talking to the boat closed "
     "(QGroundControl, a second tablet): Mission Control refuses to arm "
     "while it hears one", "Operator", ["MCN-D57"]),
]

# ---------------------------------------------------------------- contingencies
# (id, situation, you'll notice, operator, crew, refs)
CONTINGENCY = [
    ("K-01", "Link lost", "'Link lost' on screen and spoken; last position "
     "frozen on the map", "Stay put or move to a better spot. In a mission, "
     "the boat carries on, then comes home by itself after 60 s. Driving "
     "manually, it stops, then comes home after 10 s.", "Watch for the flag",
     ["FS-002", "FS-003"]),
    ("K-02", "Low battery", "'Coming home: battery low'", "Let it come "
     "home. End the session.", "Wave it in", ["FS-001"]),
    ("K-03", "Stuck in weed", "'I'm stuck, trying to wiggle free'", "Wait "
     "for up to three wiggles. Still stuck: COME HOME to retry, else "
     "recover by line (K-07). Stuck in clear water with no weed in sight? "
     "Suspect a dead motor: the boat can't tell the two apart. Recover and "
     "inspect the pods.", "Spot the boat", ["FS-005", "FS-006", "FM-50"]),
    ("K-04", "Boat stopped: position lost", "'I've lost my way, stopping'",
     "Wait up to a minute. It goes home once GPS is back. If not, recover "
     "(K-07).", "-", ["FS-004"]),
    ("K-05", "At or beyond the fence", "Fence alarm; boat heading home",
     "Let it return. If wind keeps it outside, it stops itself after 30 s "
     "or 10 m out ('outside fence' alarm): recover it (K-07). If it's "
     "pushed against the bank, STOP and recover.", "-",
     ["FEN-005", "FEN-006", "MCP-D30"]),
    ("K-06", "Person or animal near the boat", "You see them first: "
     "the boat can't", "COME HOME, or STOP if close. Wait until clear.",
     "Press STOP if asked", ["OPS-004", "A-17"]),
    ("K-07", "Boat dead in the water", "Stopped; no response; beacon may "
     "be dark", "It floats. Wait for the wind to bring it to our bank. Pole "
     "and net if within reach. Otherwise cast the weighted line beyond the "
     "boat and reel it in so the line catches the mast and hoop. <b>Never "
     "wade.</b>", "Stay behind the line", ["OPS-008", "REC-005"]),
    ("K-08", "No internet", "'Templates only'", "Choose a template with "
     "the crew.", "Pick an adventure", ["MIS-005"]),
    ("K-09", "Mission Control dead", "Screen and buttons dead", "The boat "
     "comes home by itself after 60 s. Restart the box. Recover as "
     "normal.", "-", ["FS-003"]),
    ("K-10", "Water or heat in the box", "'Water in the box' or 'too hot' "
     "alarm; boat returning", "Let it return, key out, battery out, dry or "
     "cool, and investigate before the next mission.", "-",
     ["FS-010", "A-11"]),
    ("K-11", "Boat behaving strangely", "Circling, going the wrong way, "
     "or a navigation alarm", "STOP. Look before resuming: pods, weed, "
     "compass. A 'heading check' alarm in strong wind may be the wind "
     "blowing the boat backwards, not the compass: check the wind first. "
     "Resume only with the PIN if you understand why.", "Press STOP if "
     "asked", ["FM-17", "FM-05", "FM-49", "MCN-D60"]),
    ("K-12", "Battery hot, swollen, smoking or smelling",
     "Heat, hissing, smoke", "Keep everyone away, especially the crew. "
     "Don't touch it. If it's on land and burning, let it burn out on a "
     "non-flammable surface or cool it with lots of water from a distance. "
     "Call 999 if fire spreads.", "Go with a grown-up, away from it",
     ["FM-23", "OPS-010"]),
]

MAINTENANCE = [
    ("Every session", "Rinse and dry pods and motors; inspect guards; check "
                      "box seal; battery inspection (OP-04)", ["A-09",
                                                               "A-11"]),
    ("Monthly (in season)", "Replace worn props; check thumb-screws and "
                            "latches; clean camera window; check the SD card "
                            "health report", ["MEC-007"]),
    ("Each season", "Box dunk test; re-measure pack capacity (PWR-D21); "
                    "change the PIN; re-run the full simulator suite; "
                    "review the FMEA", ["PWR-D21", "SAF-006", "MCN-D61"]),
    ("After any change", "New firmware, parameters or code: tagged "
                         "release, full simulator suite, rig retest of "
                         "anything touched", ["SWE-006", "SAF-007"]),
]

CREW_CARD = [
    ("TALK", "Blue, microphone", "Hold it and tell Boaty what to do."),
    ("GO", "Green, arrow", "Hold it to start. Only when the grown-up "
                           "says."),
    ("COME HOME", "Yellow, house", "Boaty comes back to us."),
    ("STOP", "Red, square", "Boaty stops. Press it any time you're "
                            "worried."),
]


# ---------------------------------------------------------------- check
def all_refs():
    refs = set()
    for _, _, r in GOLDEN_RULES:
        refs |= set(r)
    for p in PROCEDURES:
        for _, r in p["steps"]:
            refs |= set(r)
    for c in CHECKLIST:
        refs |= set(c[4])
    for k in CONTINGENCY:
        refs |= set(k[5])
    for m in MAINTENANCE:
        refs |= set(m[2])
    return refs


def ids():
    return ({p["id"] for p in PROCEDURES} | {c[0] for c in CHECKLIST} |
            {k[0] for k in CONTINGENCY})


def where(ref):
    """Procedure/checklist/card IDs that cite ref."""
    out = []
    for p in PROCEDURES:
        if any(ref in r for _, r in p["steps"]):
            out.append(p["id"])
    out += [c[0] for c in CHECKLIST if ref in c[4]]
    out += [k[0] for k in CONTINGENCY if ref in k[5]]
    return out


def check():
    refs = all_refs()
    need = {f"OPS-{i:03d}" for i in range(1, 13)} | {"A-05", "A-09", "A-11",
                                                     "A-17", "A-19"}
    missing = need - refs
    assert not missing, sorted(missing)
    return len(PROCEDURES), len(CHECKLIST), len(CONTINGENCY)


if __name__ == "__main__":
    print(check())
