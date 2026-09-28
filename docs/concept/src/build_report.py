"""Build the Boaty concept-selection report PDF.

Run:  python3 docs/concept/src/figures.py && python3 docs/concept/src/build_report.py
Writes docs/concept/Boaty_Concept_Selection_Report.pdf
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from scoring import CONCEPTS, WEIGHTS, sensitivity, weighted_scores

HERE = Path(__file__).resolve().parent
FIG = HERE.parent / "figures"
OUT = HERE.parent / "Boaty_Concept_Selection_Report.pdf"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DV", FONT_DIR / "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", FONT_DIR / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV",
                              boldItalic="DVB")

INK = colors.HexColor("#0b0b0b")
INK2 = colors.HexColor("#52514e")
RULE = colors.HexColor("#d9d8d0")
TINT = colors.HexColor("#f4f3ee")
BLUE = colors.HexColor("#2a78d6")
BLUE_T = colors.HexColor("#e8f1fb")
ORANGE = colors.HexColor("#eb6834")

VERSION = "v1.0 - 28 September 2026"

# ------------------------------------------------------------------ styles
S = {}
S["body"] = ParagraphStyle("body", fontName="DV", fontSize=9.4, leading=13.4,
                           textColor=INK, spaceAfter=5)
S["small"] = ParagraphStyle("small", parent=S["body"], fontSize=8,
                            leading=10.6, textColor=INK2)
S["cell"] = ParagraphStyle("cell", parent=S["body"], fontSize=8, leading=10.4,
                           spaceAfter=0)
S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="DVB")
S["h1"] = ParagraphStyle("h1", fontName="DVB", fontSize=15, leading=19,
                         textColor=INK, spaceBefore=4, spaceAfter=8)
S["h2"] = ParagraphStyle("h2", fontName="DVB", fontSize=11, leading=14,
                         textColor=INK, spaceBefore=9, spaceAfter=4)
S["caption"] = ParagraphStyle("cap", parent=S["small"], spaceBefore=3,
                              spaceAfter=10)
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=11,
                             bulletIndent=2, spaceAfter=2.5)
S["title"] = ParagraphStyle("title", fontName="DVB", fontSize=30, leading=35,
                            textColor=INK)
S["sub"] = ParagraphStyle("sub", fontName="DV", fontSize=13, leading=18,
                          textColor=INK2)
S["callout"] = ParagraphStyle("callout", parent=S["body"], fontSize=9.6,
                              leading=14, spaceAfter=0)


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(t, S["bullet"], bulletText="•") for t in items]


def fig(name, width_mm, caption=None):
    img = Image(str(FIG / name))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = width_mm * mm
    img.drawHeight = width_mm * mm * ratio
    parts = [img]
    if caption:
        parts.append(P(caption, "caption"))
    return KeepTogether(parts)


def table(rows, widths, header=True, zebra=True, bold_first_col=False,
          highlight_row=None):
    data = []
    for i, r in enumerate(rows):
        row = []
        for j, c in enumerate(r):
            if isinstance(c, str):
                st = "cellb" if (header and i == 0) or (bold_first_col and j == 0) \
                    else "cell"
                c = Paragraph(c, S[st])
            row.append(c)
        data.append(row)
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), TINT),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK2)]
    if highlight_row is not None:
        style += [("BACKGROUND", (0, highlight_row), (-1, highlight_row), BLUE_T)]
    t.setStyle(TableStyle(style))
    return t


def callout(text, color=BLUE, bg=BLUE_T):
    t = Table([[Paragraph(text, S["callout"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


# ------------------------------------------------------------------ page furniture
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(INK2)
    canvas.drawString(20 * mm, 12 * mm, "Boaty - Concept Selection Report")
    canvas.drawRightString(190 * mm, 12 * mm, f"{VERSION}   ·   page {doc.page}")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


def on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BLUE)
    canvas.rect(0, 0, 8 * mm, A4[1], stroke=0, fill=1)
    canvas.restoreState()


# ------------------------------------------------------------------ budget data
CORE_BOM = [
    ("Flight controller, F405-class with ArduPilot firmware support "
     "(e.g. SpeedyBee F405 Mini / Matek class - confirm on ArduPilot's board list)", 25),
    ("GPS + compass module, u-blox M10 class", 14),
    ("Seeed XIAO ESP32-S3 Sense (camera, microSD slot, Wi-Fi with external antenna)", 14),
    ("microSD card, 32 GB", 4),
    ("2 × brushless outrunner motor, 2204-2208 size (runs submerged in fresh water)", 12),
    ("2 × bidirectional ESC, 20-30 A (BLHeli_S / AM32 '3D mode')", 10),
    ("Battery: 3S Li-ion pack (3 × 18650 + BMS) or 3S 2200 mAh LiPo", 15),
    ("IP67 clip-lock food box + 4 × PG7 cable glands + inline blade fuse", 6),
    ("Closed-cell foam (XPS offcut / pipe lagging), hi-vis tape, LED beacon", 5),
]
STOCK = ("PETG filament (~0.6 kg), M3 fasteners & heat-set inserts, wire, XT30 "
         "connectors, solder, silicone sealant, 3S balance charger")
UPGRADES = [
    ("Raspberry Pi Zero 2W + Camera Module 3", "£40",
     "On-board duck detection, 'pause and look' behaviour, much better photos."),
    ("ExpressLRS handheld transmitter + receiver", "£55-70",
     "Independent second link for manual override; longer range than Wi-Fi."),
    ("Bluetooth item tracker (AirTag / SmartTag) inside the box", "£25-30",
     "Belt-and-braces 'where is it' if everything else fails."),
    ("Airboat thruster-pod module (2 × 2205 + 5\" props + printed guards)", "£10",
     "Swap-in module for weedy ponds. A fun second propulsion experiment."),
]


# ------------------------------------------------------------------ story
def build():
    scores = weighted_scores()
    sens = sensitivity()
    chosen = next(c for c in CONCEPTS if c.get("chosen"))
    core_total = sum(p for _, p in CORE_BOM)
    batt = next(p for d, p in CORE_BOM if d.startswith("Battery"))

    st = []

    # ---------------- cover
    st += [Spacer(1, 48 * mm),
           P("PROJECT BOATY", "small"),
           Spacer(1, 3 * mm),
           P("A mini autonomous boat<br/>for a dad-and-son build", "title"),
           Spacer(1, 6 * mm),
           P("Concept Selection Report: options considered, the recommended "
             "concept, and what we need to decide before architecture design.",
             "sub"),
           Spacer(1, 16 * mm),
           callout(
               "<b>Recommendation:</b> build <b>Concept G, a modular 3D-printed "
               "GPS catamaran</b>. It has two brains: an off-the-shelf "
               "<b>ArduPilot</b> autopilot that enforces a geofence and brings "
               "the boat home, and a small <b>camera 'mission brain'</b> that "
               "takes the photos. Instructions like <i>\"explore the pond, "
               "photograph some ducks, then come back\"</i> are turned into a "
               "checked mission on the laptop before launch. Estimated cash "
               f"spend <b>≈£{core_total}</b> (≈£{core_total - batt} if you "
               "already own a 3S battery)."),
           Spacer(1, 60 * mm),
           P(f"Prepared for: Project Boaty (father and son)<br/>"
             f"Status: for review<br/>Version: {VERSION}", "small"),
           PageBreak()]

    # ---------------- 1 summary
    st += [P("1. Summary", "h1"),
           P("We want a small boat that a child can help design and build, that "
             "can be sent off with a plain-English instruction, and that "
             "<b>will not be lost in the lake</b>. The target budget is £100. "
             "Seven concepts were scored against cost, fun, intelligence and "
             "reliability. Reliability was weighted highest because it is the "
             "only hard requirement."),
           P(f"<b>Concept G, the modular GPS catamaran</b>, scored "
             f"{scores['G']:.2f}/5. The next best was {scores['D']:.2f}. G "
             "stays the winner if any single criterion's weight is doubled. "
             "It wins because it separates the <i>clever</i> part from the "
             "<i>safe</i> part:"),
           *bullets([
               "<b>Safety brain.</b> ArduPilot Rover, open-source autopilot "
               "firmware used on thousands of boats and rovers. Geofence, "
               "return-to-launch, battery and lost-link failsafes, and stuck "
               "detection are mature, configurable features, so we don't have "
               "to write them.",
               "<b>Mission brain.</b> A £14 ESP32-S3 camera board acts as the "
               "Wi-Fi link and takes photos. It can only <i>ask</i> the "
               "autopilot to do things, and the autopilot still enforces the "
               "fence. Bugs in our own code cannot take the boat out of the "
               "pond.",
               "<b>Modular mechanical build.</b> Printed hull segments, "
               "clip-on thruster pods, a mast kit and an M3-grid 'Meccano "
               "rail' deck. Your son can design and swap his own modules.",
               "<b>Unsinkable by construction.</b> Foam-filled hulls float "
               "even if everything leaks, and a catamaran is very hard to "
               "capsize.",
           ]),
           Spacer(1, 3 * mm),
           table([
               ["Key figure", "Estimate", "Basis"],
               ["Size", "≈600 × 340 mm, mast ≈300 mm",
                "Fits a car boot; hull segments ≤200 mm fit a typical print bed"],
               ["Mass", "≈1.4 kg", "Section 5.7 weight budget"],
               ["Cruise speed", "≈1 m/s (walking pace)",
                "Slow is quieter, safer and gives sharper photos"],
               ["Endurance", "≥60 min (to be proven)",
                "≈26 Wh usable, ≈10 W cruise; missions planned at ≤20 min"],
               ["Link range", "≈100-200 m over water (Wi-Fi)",
                "Link not needed for safety: failsafes live on the boat"],
               ["Cash spend", f"≈£{core_total}",
                "Section 5.6; filament and fasteners from workshop stock"],
           ], [30, 50, 90]),
           PageBreak()]

    # ---------------- 2 requirements
    st += [P("2. What 'good' looks like", "h1"),
           P("The brief turned into criteria, each with a measurable test and "
             "a weight for scoring:"),
           table([
               ["Criterion", "Weight", "What we are really asking", "Pass test"],
               ["Reliability<br/>(can't lose it)", f"{WEIGHTS['rel']:.0%}",
                "Does the boat come back, or stay findable and reachable, "
                "whatever fails: link, battery, GPS, software, weed, wind?",
                "No single failure leaves the boat unrecoverable. Every failure "
                "mode ends in 'returns', 'holds inside the fence' or 'drifts "
                "to our bank'."],
               ["Cost", f"{WEIGHTS['cost']:.0%}",
                "Around £100 cash for a working Mk1. Upgrades can come later.",
                "Core bill of materials ≤≈£105 at current UK/AliExpress prices."],
               ["Fun (build)", f"{WEIGHTS['fun']:.0%}",
                "Is there a real, modular mechanical build a child can own "
                "parts of, and keep modifying?",
                "At least 4 swappable modules; child-designed parts possible "
                "with Tinkercad-level CAD."],
               ["Intelligence", f"{WEIGHTS['intel']:.0%}",
                "Can we say \"explore this pond, take pictures of ducks, "
                "come back\" and have it happen?",
                "Plain-English request becomes a validated mission, runs "
                "hands-off, and returns tagged duck photos."],
           ], [27, 15, 64, 64]),
           Spacer(1, 4 * mm),
           P("Assumptions", "h2"),
           *bullets([
               "Calm inland fresh water: a park pond or small lake, roughly "
               "50-300 m across. Not rivers with current, not the sea.",
               "Operated from the bank by an adult, with the child as "
               "co-pilot. Nobody enters the water to recover it.",
               "3D printer (PETG), soldering and general workshop tools are "
               "available, and software/electronics are within your comfort "
               "zone.",
               "Prices are September 2026 estimates from typical UK and "
               "AliExpress sellers. Treat them as ±20%.",
           ]),
           PageBreak()]

    # ---------------- 3 concepts
    st += [P("3. Concepts considered", "h1"),
           P("Seven genuinely different ways to meet the brief. Each was "
             "scored 1 (poor) to 5 (excellent) per criterion."),
           ]
    rows = [["", "Concept", "How it works", "Strengths", "Weaknesses"]]
    hl = None
    for i, c in enumerate(CONCEPTS, start=1):
        rows.append([c["id"], f"<b>{c['name']}</b>", c["how"], c["pros"],
                     c["cons"]])
        if c.get("chosen"):
            hl = i
    st += [table(rows, [7, 32, 45, 40, 46], highlight_row=hl),
           P("Also ruled out early: an aerial drone (different regulations, "
             "and a crash over water means a lost drone) and a submarine "
             "(radio and GPS don't work underwater, which conflicts with the "
             "'can't lose it' requirement).", "small"),
           PageBreak()]

    # ---------------- 4 evaluation
    st += [P("4. Evaluation", "h1")]
    rows = [["Concept", "Cost", "Fun", "Intel.", "Reliab.", "Weighted"]]
    ordered = sorted(CONCEPTS, key=lambda c: -scores[c["id"]])
    for i, c in enumerate(ordered, start=1):
        rows.append([f"{c['id']}  {c['short']}", str(c["cost"]), str(c["fun"]),
                     str(c["intel"]), str(c["rel"]), f"<b>{scores[c['id']]:.2f}</b>"])
    rows.append(["<i>Weight</i>", f"{WEIGHTS['cost']:.0%}", f"{WEIGHTS['fun']:.0%}",
                 f"{WEIGHTS['intel']:.0%}", f"{WEIGHTS['rel']:.0%}", ""])
    st += [table(rows, [62, 20, 20, 20, 22, 26], highlight_row=1),
           Spacer(1, 4 * mm),
           fig("scores.png", 150,
               "Figure 1. Weighted scores. Concept G leads the runner-up by "
               "0.75 points."),
           P("Why G wins, and what nearly beat it", "h2"),
           *bullets([
               "<b>vs C (scratch-built autopilot):</b> the same fun and "
               "intelligence at a similar price, but C makes us write and "
               "prove every failsafe ourselves. G gives the learning at the "
               "<i>mission</i> level and borrows the safety level from a "
               "mature project. You can still write your own navigation later "
               "as an ArduPilot Lua script or companion code, with the fence "
               "still underneath it.",
               "<b>vs D (airboat):</b> D is weed-proof, which matters on "
               "ponds. But a fan is loud and the brief is to photograph "
               "ducks. G takes the good idea anyway: the airboat is offered "
               "as a swap-in thruster module for weedy water.",
               "<b>vs A (bait boat):</b> the most reliable out of the box, "
               "but over budget and closed. There's almost nothing for a "
               "young engineer to build.",
               "<b>vs B (tether):</b> it feels safe, but the line snags reeds, "
               "weed and wildlife, and a snagged tether is exactly how you "
               "end up losing a boat.",
           ]),
           P(f"<b>Sensitivity:</b> doubling any one weight (then "
             f"re-normalising) leaves the winner unchanged "
             f"({', '.join(f'{k}: {v}' for k, v in sens.items())}).", "small"),
           PageBreak()]

    # ---------------- 5 chosen concept
    st += [P("5. The recommended concept: Boaty Mk1", "h1"),
           P("5.1 Overview", "h2"),
           P("A 600 mm catamaran. It has two foam-filled printed hulls joined "
             "by two crossbeams that carry a sealed electronics box and a "
             "mast. Two clip-on thruster pods at the stern steer by "
             "differential thrust (no rudder), so it can turn on the spot and "
             "reverse, which also helps shake off weed. A forward-looking "
             "camera sits on the front of the box. The GPS and compass sit up "
             "the mast, away from motor currents."),
           fig("sketch.png", 150, "Figure 2. Concept sketch (indicative "
               "proportions; detail design follows in the architecture phase)."),
           PageBreak(),
           P("5.2 Mechanical design and modularity", "h2"),
           P("The build is designed as a kit of modules with standard "
             "interfaces, so it can be taken apart, improved and re-combined "
             "like Meccano:"),
           table([
               ["Module", "Design intent", "Interface"],
               ["Hull segments (×6)",
                "≤200 mm long to fit common print beds. PETG, 3 perimeters. "
                "Filled with closed-cell foam so buoyancy never depends on "
                "being watertight.",
                "Bolted flanges, M3 heat-set inserts, silicone bead"],
               ["Crossbeams (×2)",
                "Printed or aluminium box section with a 10 mm M3 hole grid "
                "along the top (the 'Meccano rail'). Anything can bolt on "
                "anywhere.", "M3 clamps to hull bosses"],
               ["Electronics box",
                "Off-the-shelf clip-lock food box. Cheaper and more reliably "
                "sealed than a printed box. All wires go through PG7 glands. "
                "A printed tray inside holds the boards.",
                "Printed saddle on the rail"],
               ["Thruster pods (×2)",
                "Submerged outrunner motor on a printed strut with a printed "
                "prop inside a weed guard. Clip on and off for maintenance or "
                "a swap to the airboat module.",
                "Dovetail + pin on hull transom; 3-pin waterproof connector"],
               ["Mast kit",
                "GPS/compass on top, flag, recovery hoop, LED beacon. "
                "Printed sockets on a carbon or aluminium tube.",
                "Socket on rail"],
               ["Payload bay",
                "Free rail space for your son's own modules: a lookout "
                "figure, a second camera, a water thermometer, a crane...",
                "M3 grid"],
           ], [30, 100, 40]),
           Spacer(1, 3 * mm),
           P("Why submerged motors? Brushless outrunners run happily under "
             "fresh water; ROV hobbyists do it routinely. That means no shaft "
             "seals or stuffing tubes, which are the classic leak point. "
             "Rinse and dry after use; the motors are cheap consumables at "
             "about £6 each."),
           P("5.3 Two brains: clever and safe, kept apart", "h2"),
           P("This is the key architectural idea, carried forward into the "
             "next phase. The <b>safety brain</b> (ArduPilot on the flight "
             "controller) steers the motors and has the final say: fence, "
             "failsafes and return-to-launch. The <b>mission brain</b> "
             "(ESP32-S3) handles Wi-Fi, photos and higher-level behaviour. "
             "It talks to the autopilot over MAVLink, the same protocol the "
             "ground station uses, so it can request waypoints or a pause "
             "but <b>cannot override the geofence</b>."),
           fig("blocks.png", 160, "Figure 3. Concept-level block diagram. "
               "Detailed interfaces are for the architecture phase."),
           PageBreak(),
           P("5.4 Intelligence: from 'drive it' to 'go and find ducks'", "h2"),
           P("The intelligence is built up in levels. Each level is useful on "
             "its own and is a milestone to celebrate:"),
           table([
               ["Level", "What it does", "How"],
               ["0  Drive", "Manual driving from a phone.",
                "QGroundControl virtual joystick over Wi-Fi."],
               ["1  Go there", "Waypoints, survey patterns, return home.",
                "ArduPilot AUTO missions planned on the map in QGroundControl."],
               ["2  Just ask", "\"Explore the pond, take pictures of some "
                "ducks, then come back.\"",
                "Laptop app sends the request, the pond outline and the fence "
                "to Claude. It returns a structured mission (route, photo "
                "points, time limit). A validator <i>we</i> write checks it "
                "before upload."],
               ["3  Captain's log", "Picks the duck photos and writes up the "
                "voyage.",
                "After return, a vision model sorts the photos, flags the "
                "ducks and writes a short log for your son."],
               ["4  Spot & look", "Notices ducks in real time, pauses and "
                "takes a burst of photos, then carries on.",
                "Upgrade: Pi Zero 2W running a small bird detector. Pausing "
                "is a request to ArduPilot, still inside the fence."],
           ], [26, 58, 86]),
           Spacer(1, 3 * mm),
           callout("<b>Design rule: the language model proposes, our "
                   "validator checks, ArduPilot enforces.</b> The AI never "
                   "drives the boat directly. A mission is uploaded only if "
                   "every waypoint is inside the fence, the planned time "
                   "fits within half the battery, the photo count is "
                   "sensible, and the mission ends in return-to-launch. "
                   "Your son sees the plan on the map and presses GO.",
                   ORANGE, colors.HexColor("#fdf0ea")),
           Spacer(1, 3 * mm),
           fig("mission.png", 140, "Figure 4. What \"explore this pond, take "
               "some pictures of ducks, then come back\" might become: a "
               "survey route inside the fence, photo points, and RTL. The "
               "nesting island is fenced out. We don't chase wildlife."),
           PageBreak(),
           P("5.5 Can't-lose-it strategy", "h2"),
           P("Reliability is designed in as independent layers. Any one layer "
             "can fail and the next still saves the boat:"),
           fig("layers.png", 160),
           table([
               ["Failure", "What the boat does", "ArduPilot feature"],
               ["Drives towards the bank / off the map", "Stops at the fence, "
                "returns home", "Polygon fence, action = RTL"],
               ["Battery getting low", "Returns home with ≥30% left",
                "Battery failsafe (voltage and mAh used)"],
               ["Wi-Fi link lost", "Finishes the leg, then returns home",
                "GCS failsafe, action = RTL"],
               ["GPS or compass goes bad", "Stops motors and holds",
                "EKF failsafe, action = Hold"],
               ["Wrapped in weed, not moving", "Stops (optionally reverses to "
                "shed weed), alerts us", "Crash/stuck check + Lua script"],
               ["Mission-brain crash", "Autopilot carries on the mission and "
                "returns home", "Mission lives on the flight controller"],
               ["Everything dead", "Floats, drifts downwind to our bank, "
                "beacon flashing", "Physics + choosing the launch bank"],
           ], [48, 62, 60]),
           Spacer(1, 3 * mm),
           P("<b>Recovery kit on the bank:</b> a telescopic pole with a "
             "landing net for near-bank rescues, and a spinning rod with a "
             "weighted float line cast over the mast hoop for anything "
             "further out. First autonomous trials happen in a small pond "
             "where every point is within casting range.", "body"),
           PageBreak()]

    # budget
    rows = [["#", "Item", "£ (approx.)"]]
    for i, (d, p) in enumerate(CORE_BOM, start=1):
        rows.append([str(i), d, f"{p}"])
    rows.append(["", "<b>Core cash spend</b>", f"<b>≈{core_total}</b>"])
    rows.append(["", f"<i>…if you already own a 3S battery</i>",
                 f"<i>≈{core_total - batt}</i>"])
    rows.append(["", f"Workshop stock (not counted): {STOCK}", "-"])
    st += [P("5.6 Budget", "h2"),
           P(f"Core Mk1 build: everything needed for Levels 0-3 of the "
             f"intelligence ladder. The estimate lands at ≈£{core_total}, "
             f"within about 5% of the £100 target. The software (ArduPilot, "
             f"QGroundControl, Python) is free. The Claude API costs a few "
             f"pence per mission plan."),
           table(rows, [8, 136, 26]),
           Spacer(1, 5 * mm),
           P("Optional upgrades (later, when Mk1 has earned them)", "h2"),
           table([["Upgrade", "£", "What it adds"]] +
                 [list(u) for u in UPGRADES], [62, 18, 90]),
           P("Cost-down levers if needed: a cheaper F405 clone (-£8); "
             "brushed motors with a dual brushed ESC (-£6, less efficient); "
             "salvaged 18650 cells (-£8, test capacity first).", "small"),
           P("5.7 Sanity-check numbers", "h2"),
           table([
               ["Check", "Working", "Result"],
               ["Mass", "Hulls + foam 500 g, box + electronics 250 g, battery "
                "150 g, pods 150 g, beams + mast 200 g, misc 150 g",
                "≈1.4 kg"],
               ["Draft", "1.4 L displaced over 2 hulls ≈ 600 × 90 mm "
                "waterplane, Cwp≈0.7", "≈25-30 mm"],
               ["Reserve buoyancy", "Hull volume ≈2 × 600×90×100 mm × 0.6 "
                "≈ 6.5 L vs 1.4 L needed", "≈4.5×"],
               ["Endurance", "3S 18650 ≈33 Wh, 80% usable ≈26 Wh; cruise "
                "≈8 W propulsion + ≈2.5 W electronics",
                "≈2.5 h theoretical; claim ≥60 min"],
               ["Mission length", "100 × 60 m pond, 10 m lane spacing ≈ "
                "600 m at 1 m/s", "≈10 min + photo pauses"],
               ["Position accuracy", "M10 GPS typically 1.5-3 m", "Fence 5 m "
                "inside bank"],
           ], [32, 100, 38]),
           P("All to be verified in the bath, then the paddling pool, then "
             "the pond. Early test data feeds the architecture phase.",
             "small"),
           PageBreak()]

    # ---------------- 6 roadmap
    st += [P("6. How your son gets involved: build roadmap", "h1"),
           P("Each phase ends with something that works and a reason to "
             "celebrate. The simulator phase means the software can be "
             "played with at the kitchen table before any plastic is "
             "printed."),
           table([
               ["Phase", "What we do", "Son's role", "Done when"],
               ["0  Simulator",
                "Run ArduPilot SITL + QGroundControl on the laptop, using the "
                "real pond from satellite imagery.",
                "Draws the fence, plans missions, 'crashes' the virtual boat "
                "on purpose to watch failsafes fire.",
                "Virtual boat completes a mission and returns home."],
               ["1  Hulls",
                "Print hull segments, foam-fill, bath float test, measure "
                "draft and add ballast.",
                "Archimedes experiment: predict the draft, then measure it. "
                "Paints the livery.",
                "Floats level at predicted draft with test weights."],
               ["2  Power & drive",
                "Thruster pods, ESCs, battery, flight controller. Driven "
                "manually from the phone.",
                "Assembles pods, tests clip-on/clip-off, first drive in a "
                "paddling pool.",
                "Drives, turns on the spot, reverses."],
               ["3  Autonomy",
                "GPS, compass calibration, fence, failsafes. Small-pond "
                "trials with deliberate failsafe tests.",
                "Mission commander: runs the pre-launch checklist.",
                "Every failsafe in section 5.5 demonstrated on the water."],
               ["4  Camera & AI",
                "ESP32 photo capture, natural-language mission app, "
                "captain's log.",
                "Gives the orders, reviews photos, names the ducks.",
                "\"Explore, photograph ducks, come back\" works end to end."],
               ["5  His module",
                "Open-ended: he designs a module for the rail.",
                "Designer: sketch, Tinkercad, print, fit.",
                "His module sails."],
           ], [22, 55, 50, 43]),
           Spacer(1, 4 * mm),
           P("7. Risks and mitigations", "h1"),
           table([
               ["Risk", "Likelihood / impact", "Mitigation"],
               ["Weed fouls the props", "High / medium",
                "Weed guards, reverse-to-clear routine, stuck detection → "
                "Hold, airboat module for weedy ponds, and survey the pond "
                "first."],
               ["Water gets into the electronics", "Medium / medium",
                "Sealed food box + glands, silica gel, and a 'dunk test' "
                "before every season. Foam hulls mean flooding can't sink it."],
               ["Compass interference → poor steering", "Medium / low",
                "GPS/compass up the mast, twisted power leads, calibrate on "
                "site, compare against GPS course."],
               ["Budget creep", "Medium / low",
                "Core BOM frozen for Mk1. Upgrades only after Phase 4."],
               ["Wi-Fi range shorter than hoped", "Medium / low",
                "Safety doesn't depend on it. External antenna, ELRS "
                "upgrade available."],
               ["Wind stronger than the boat", "Low / medium",
                "Wind limit in the checklist (no trips above a light breeze), "
                "and launch from the downwind bank."],
               ["Lithium battery fault", "Low / high",
                "BMS or LiPo checker, inline fuse, charge in a LiPo bag, "
                "never charge unattended, and store at storage voltage."],
           ], [44, 30, 96]),
           PageBreak()]

    # ---------------- 8 rules
    st += [P("8. Rules, wildlife and good manners", "h1"),
           *bullets([
               "<b>Permission.</b> Many park and council ponds have byelaws "
               "on model boats, and some have a model-boat club with set "
               "times. Check who owns the water and ask first. A friendly "
               "local club is also a great place for trials.",
               "<b>Wildlife.</b> The Wildlife and Countryside Act 1981 "
               "protects wild birds and their nests. The mission design "
               "never chases birds, keeps well clear of islands and reed "
               "beds (fenced out), and avoids approaching nesting areas in "
               "the breeding season (roughly March to August). Photos are "
               "taken from a respectful distance. Ducks that swim up to the "
               "boat on their own are a bonus.",
               "<b>Radio.</b> 2.4 GHz Wi-Fi and ExpressLRS are licence-exempt "
               "in the UK at normal power levels. Avoid cheap 433 MHz "
               "'telemetry radios' sold at powers above UK limits.",
               "<b>People.</b> Nobody goes into the water to fetch the boat. "
               "Adult supervision at the bank at all times.",
           ]),
           Spacer(1, 3 * mm),
           P("9. Decisions and inputs needed before architecture design", "h1"),
           P("To make the architecture concrete, it would help to know:"),
           table([
               ["#", "Question", "Why it matters"],
               ["1", "Which pond(s)? Rough size, weed, islands, launch "
                "points, and whether model boats are allowed.",
                "Sets fence geometry, range needs, propulsion choice "
                "(submerged vs airboat pod)."],
               ["2", "Your son's age and what he's most excited by (building, "
                "driving, coding, photos?).",
                "Tunes the module split and which parts he designs himself."],
               ["3", "Existing kit: 3S battery and charger, RC transmitter, "
                "Raspberry Pi, print bed size?",
                "Changes the budget and the link design."],
               ["4", "OK to use the Claude API from a laptop for mission "
                "planning (needs internet on the bank, e.g. phone hotspot), or "
                "prefer offline planning at home?",
                "Decides the ground-side software architecture."],
               ["5", "Happy with ArduPilot as the safety core?",
                "It's the backbone of the reliability argument. The "
                "alternative is concept C."],
           ], [8, 92, 70]),
           Spacer(1, 6 * mm),
           callout("<b>Next step: architecture design.</b> Detailed "
                   "electrical schematic and power budget; MAVLink interfaces "
                   "between the brains; ArduPilot parameter set (fence, "
                   "failsafes, skid-steer tuning); CAD layout and hull lines; "
                   "the mission-planner app and its validator; and a test "
                   "plan for each failsafe."),
           ]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm,
                            rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=22 * mm,
                            title="Boaty - Concept Selection Report",
                            author="Project Boaty",
                            subject="Mini autonomous boat concept selection")
    doc.build(st, onFirstPage=on_cover, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
