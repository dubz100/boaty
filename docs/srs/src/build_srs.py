"""Build the Boaty System Requirements Specification PDF.

Run:  python3 docs/srs/src/figures.py && python3 docs/srs/src/build_srs.py
Writes docs/srs/Boaty_System_Requirements_Specification.pdf
"""
from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                Spacer, Table, TableStyle)
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents

import requirements as REQ

HERE = Path(__file__).resolve().parent
FIG = HERE.parent / "figures"
OUT = HERE.parent / "Boaty_System_Requirements_Specification.pdf"

DOC_ID = "BOATY-SRS-001"
ISSUE = "Issue F (for review)"
DATE = "29 September 2026"
PREV = "28 September 2026"

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
ORANGE_T = colors.HexColor("#fdf0ea")
PRI_COL = {"M": colors.HexColor("#2a78d6"), "S": colors.HexColor("#1baf7a"),
           "C": colors.HexColor("#9a998f")}

S = {}
S["body"] = ParagraphStyle("body", fontName="DV", fontSize=9.2, leading=13,
                           textColor=INK, spaceAfter=5)
S["small"] = ParagraphStyle("small", parent=S["body"], fontSize=7.8,
                            leading=10.4, textColor=INK2)
S["cell"] = ParagraphStyle("cell", parent=S["body"], fontSize=7.8,
                           leading=10.2, spaceAfter=0)
S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="DVB")
S["cellc"] = ParagraphStyle("cellc", parent=S["cell"], alignment=1)
S["note"] = ParagraphStyle("note", parent=S["cell"], textColor=INK2,
                           fontSize=7.2, leading=9.4)
S["h1"] = ParagraphStyle("h1", fontName="DVB", fontSize=14.5, leading=18,
                         textColor=INK, spaceBefore=2, spaceAfter=8)
S["h2"] = ParagraphStyle("h2", fontName="DVB", fontSize=10.8, leading=14,
                         textColor=INK, spaceBefore=9, spaceAfter=4)
S["caption"] = ParagraphStyle("cap", parent=S["small"], spaceBefore=3,
                              spaceAfter=10)
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=11,
                             bulletIndent=2, spaceAfter=2.5)
S["title"] = ParagraphStyle("title", fontName="DVB", fontSize=28, leading=33)
S["sub"] = ParagraphStyle("sub", fontName="DV", fontSize=12.5, leading=17,
                          textColor=INK2)
S["toc1"] = ParagraphStyle("toc1", fontName="DVB", fontSize=9.4, leading=15)
S["toc2"] = ParagraphStyle("toc2", fontName="DV", fontSize=8.6, leading=12.5,
                           leftIndent=14)


def P(t, st="body"):
    return Paragraph(t, S[st])


def H1(t):
    p = Paragraph(t, S["h1"])
    p._toc = (0, t)
    return p


def H2(t):
    p = Paragraph(t, S["h2"])
    p._toc = (1, t)
    return p


def bullets(items):
    return [Paragraph(t, S["bullet"], bulletText="•") for t in items]


def fig(name, width_mm, caption):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(FIG / name)).getSize()
    img = Image(str(FIG / name), width=width_mm * mm,
                height=width_mm * mm * ih / iw)
    return KeepTogether([img, P(caption, "caption")])


def table(rows, widths, header=True, style_extra=(), font="cell"):
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(c, S["cellb" if header and i == 0 else font])
                     if isinstance(c, str) else c for c in r])
    t = Table(data, colWidths=[w * mm for w in widths],
              repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
          ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
          ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), TINT),
               ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK2)]
    t.setStyle(TableStyle(st + list(style_extra)))
    return t


def callout(text, color=BLUE, bg=BLUE_T):
    t = Table([[Paragraph(text, S["body"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def pri_tag(p):
    c = PRI_COL[p].hexval()[2:]
    return Paragraph(f'<font color="#{c}"><b>{p}</b></font>', S["cellc"])


# ------------------------------------------------------------------ doc
class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=20 * mm,
                         rightMargin=20 * mm, topMargin=18 * mm,
                         bottomMargin=22 * mm,
                         title="Boaty - System Requirements Specification",
                         author="Project Boaty", subject=DOC_ID)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width,
                      self.height, id="f")
        self.addPageTemplates([
            PageTemplate("cover", [frame], onPage=self.cover),
            PageTemplate("body", [frame], onPage=self.furniture)])

    @staticmethod
    def cover(c, d):
        c.saveState()
        c.setFillColor(BLUE)
        c.rect(0, 0, 8 * mm, A4[1], stroke=0, fill=1)
        c.restoreState()

    @staticmethod
    def furniture(c, d):
        c.saveState()
        c.setFont("DV", 7.3)
        c.setFillColor(INK2)
        c.drawString(20 * mm, 12 * mm,
                     f"{DOC_ID}  ·  System Requirements Specification  ·  {ISSUE}")
        c.drawRightString(190 * mm, 12 * mm, f"page {d.page}")
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
        c.restoreState()

    def afterFlowable(self, f):
        if hasattr(f, "_toc"):
            level, text = f._toc
            key = f"h{id(f)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))


# ------------------------------------------------------------------ content
def build():
    n_req = REQ.check()
    reqs = list(REQ.all_reqs())
    pri = Counter(r["pri"] for r in reqs)
    st = []
    from reportlab.platypus import NextPageTemplate

    # ---------------- cover
    st += [Spacer(1, 45 * mm), P("PROJECT BOATY", "small"), Spacer(1, 3 * mm),
           P("System Requirements<br/>Specification", "title"),
           Spacer(1, 6 * mm),
           P("Mk1 mini autonomous boat: modular GPS catamaran with Mission "
             "Control", "sub"),
           Spacer(1, 14 * mm),
           table([["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                  ["Status", "Issue E: owner decisions incorporated"],
                  ["Basis", "Concept Selection Report v1.1 (Concept G)"],
                  ["Includes", "System overview, ConOps, ConUse, requirements, "
                   "verification and traceability"],
                  ["Content", f"{n_req} requirements: {pri['M']} Must, "
                              f"{pri['S']} Should, {pri['C']} Could"]],
                 [32, 90], header=False, font="cell"),
           NextPageTemplate("body"), PageBreak()]

    # ---------------- document control + TOC
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    st += [P("Document control", "h1"),
           table([["Issue", "Date", "Change", "By"],
                  ["A", PREV, "First issue, for review. Includes the Concept of "
                   "Operations (section 3) and Concept of Use (section 4).",
                   "Claude (drafted)"],
                  ["B", PREV, "Owner review: ArduPilot (Route A) selected, "
                   "TBD-01 closed, SAF-005 marked not applicable, MC-014 "
                   "applies unconditionally. Failsafe thresholds and safety "
                   "numbers accepted as baseline (TBD-08 closed).",
                   "Claude, owner decisions"],
                  ["C", PREV, "CR-01 accepted: CON-001 cap raised to £160 "
                   "(target £150). TBD-04 to TBD-07 closed by the "
                   "architecture decisions (ADD DD-06 to DD-09).",
                   "Claude, owner decisions"],
                  ["D", PREV, "Fourth crew button TALK (blue, microphone) "
                   "added for push-to-talk: MC-002, NLI-002, CHD-005 and "
                   "ConUse updated (ICD TBC-10).", "Claude, owner decision"],
                  ["E", PREV, "CR-03: CON-001 cap raised to £185 (target £180) "
                   "after real UK prices for a microSD flight controller "
                   "(ADD Issue E).", "Claude, owner decision"],
                  ["F", DATE, "CR-05: FS-002 link-loss HOLD relaxed from 2 s "
                   "to 3 s, the autopilot's native minimum measured in "
                   "simulation (software/results, SC-02). CR-04 (flight "
                   "controller change) needs no SRS change.",
                   "Claude, owner decision"]],
                 [16, 32, 90, 32]),
           Spacer(1, 4 * mm),
           table([["Role", "Name", "Signature / date"],
                  ["Author", "Claude, for Project Boaty", ""],
                  ["Reviewer / approver", "Project owner", ""]],
                 [45, 70, 55]),
           Spacer(1, 4 * mm),
           P("Review guidance: please check that every requirement is "
             "<i>right</i> (what you want), <i>complete</i> (nothing "
             "missing), <i>testable</i>, and has the right priority. Open "
             "items are listed in section 8.", "small"),
           Spacer(1, 6 * mm),
           P("Contents", "h1"), toc, PageBreak()]

    # ---------------- 1 introduction
    st += [H1("1. Introduction"),
           H2("1.1 Purpose"),
           P("This specification defines <b>what</b> the Boaty Mk1 system "
             "must do and how each requirement will be verified. It is the "
             "input to architecture design and the reference for testing. "
             "It deliberately says as little as possible about <i>how</i>. "
             "Design choices from the concept report appear only where they "
             "are real constraints."),
           H2("1.2 Scope"),
           P("<b>In scope:</b> the Mk1 boat (hulls, thruster pods, mast, "
             "electronics, helm, mission computer, camera), the Mission "
             "Control bank station (Raspberry Pi 5), the mission-planning "
             "and validation software, the simulation environment, and the "
             "operating procedures for use at Milton Country Park."),
           P("<b>Out of scope:</b> salt water, rivers with current, night "
             "operation, operation beyond the operator's sight, carrying "
             "anything other than DUPLO bricks and the camera, and the "
             "design of a pure-Python helm (only its requirements, if Route "
             "B is chosen)."),
           H2("1.3 Conventions"),
           table([["Term / code", "Meaning"],
                  ["<b>shall</b>", "Mandatory. Priority M (Must): Mk1 is not "
                   "complete without it."],
                  ["<b>should</b>", "Expected. Priority S (Should): include "
                   "unless there's a good, recorded reason not to."],
                  ["<b>may</b>", "Optional. Priority C (Could): a nice-to-have "
                   "or later upgrade."],
                  ["ID", "AREA-nnn, e.g. FS-004. IDs are never reused. "
                   "Deleted requirements are marked 'deleted'."],
                  ["Verification", "T Test, D Demonstration, I Inspection, "
                   "A Analysis, S Simulation"],
                  ["Stage", "First stage the requirement is verified at: SIM, "
                   "BENCH, POOL (paddling pool or small water), LAKE"],
                  ["Trace", "The stakeholder need(s) the requirement serves "
                   "(section 2.2)"]],
                 [32, 138]),
           H2("1.4 References"),
           table([["Ref", "Document"],
                  ["[1]", "Boaty Concept Selection Report v1.1, 28 Sep 2026 "
                   "(docs/concept)"],
                  ["[2]", "ArduPilot Rover documentation (geofence, failsafes, "
                   "SITL): ardupilot.org/rover"],
                  ["[3]", "BS EN 71-1, Safety of toys: mechanical and physical "
                   "properties (small-parts cylinder)"],
                  ["[4]", "Ofcom IR 2030, UK interface requirements for "
                   "licence-exempt short-range devices"],
                  ["[5]", "Wildlife and Countryside Act 1981 (protection of "
                   "wild birds and their nests)"],
                  ["[6]", "Cambridge Sport Lakes Trust: Milton Country Park "
                   "rules and conditions (to be obtained, TBD-03)"]],
                 [14, 156]),
           P("Terms and abbreviations are in Appendix A.", "small"),
           PageBreak()]

    # ---------------- 2 overview
    st += [H1("2. System overview"),
           H2("2.1 System context"),
           P("Boaty is two physical units: the <b>boat</b> and the "
             "<b>Mission Control</b> bank station. They are linked by Wi-Fi. "
             "The adult operator and the 4-year-old crew use Mission Control "
             "only. It reaches the Claude API through a phone hotspot to turn "
             "spoken or typed instructions into missions."),
           fig("context.png", 158, "Figure 1. System context."),
           H2("2.2 Stakeholder needs"),
           table([["ID", "Need", "Description"]] +
                 [[i, f"<b>{n}</b>", d] for i, n, d in REQ.STAKEHOLDER_NEEDS],
                 [18, 45, 107]),
           PageBreak(),
           H2("2.3 Operating modes"),
           table([["Mode", "Behaviour", "Leaves by"]] +
                 [[f"<b>{m}</b>", b, e] for m, b, e in REQ.MODES],
                 [24, 78, 68]),
           P("Table 1. Boat modes (MOD-001).", "caption"),
           fig("modes.png", 150, "Figure 2. Mode transitions."),
           H2("2.4 Design constraints carried from the concept"),
           *bullets([
               "Twin-hull catamaran, modular, 3D-printed on the owned "
               "Ultimaker; DUPLO-compatible deck.",
               "Two brains: fence and failsafes run on an independent "
               "processor (SAF-001). Everything the project writes is Python "
               "(SWE-001).",
               "<b>Software route decided (Issue B): Route A.</b> ArduPilot "
               "Rover is the helm, and everything the project writes sits "
               "above it in Python. SWE-003 keeps the helm interface open "
               "for a possible Mk2 Python helm. SAF-005 would then apply.",
           ]),
           H2("2.5 Assumptions and dependencies"),
           *bullets([
               "The Claude API and mobile data are available on the bank. "
               "When they are not, the offline templates are used "
               "(MIS-005).",
               "GNSS is available in the open at the lake, with no tree "
               "canopy over the operating area.",
               "Cambridge Sport Lakes Trust grants permission, possibly "
               "with conditions that add requirements (TBD-03).",
               "Prices and part availability as in the concept report, "
               "±20%.",
           ]),
           PageBreak()]

    # ---------------- 3 ConOps
    st += [H1("3. Concept of Operations (ConOps)"),
           P("The ConOps describes the system from an operational point of "
             "view: why it is operated, where, by whom, through which "
             "phases, and how normal and abnormal situations are handled. "
             "Section 4 then describes the same system from the users' "
             "point of view."),
           H2("3.1 Operational goal"),
           callout("Send a small, slow, unsinkable boat to explore a fenced "
                   "area of a lake on a plain-English instruction, "
                   "photograph the wildlife from a respectful distance, and "
                   "bring it back to the bank every time. Do it as a "
                   "shared parent-and-child activity that is safe, fun and "
                   "welcome at the lake."),
           Spacer(1, 3 * mm),
           H2("3.2 Operating sites and environment"),
           table([["Site", "Use", "Notes"],
                  ["Home (desk)", "Simulation, planning, software, "
                   "maintenance, charging", "SITL and simulated camera "
                   "(SWE-004)"],
                  ["Bath / paddling pool", "Float, trim, driving, stuck and "
                   "failsafe demonstrations", "POOL stage. Child's main "
                   "hands-on stage"],
                  ["Small private water (if available)", "First autonomous "
                   "missions within casting range", "Optional, before Milton"],
                  ["Milton Country Park lake (Todd's Pit or Dickerson's Pit, "
                   "TBD-02)", "Real missions in a fenced 'home bay'",
                   "Shared water: anglers, swimmers, watersports. Needs "
                   "permission (OPS-002)"]],
                 [50, 62, 58]),
           Spacer(1, 3 * mm),
           table([["Parameter", "Operating envelope", "Req."],
                  ["Water", "Fresh, still (lake or pond), waves ≤ 100 mm",
                   "ENV-003"],
                  ["Wind", "≤ 5.4 m/s (Beaufort 3)", "ENV-002"],
                  ["Air / water temperature", "0-35 °C / 2-25 °C", "ENV-001"],
                  ["Area", "Inside the site fence. At Milton, Mk1 within 100 m "
                   "of launch", "OPS-006"],
                  ["Mission", "≤ 20 min, ≤ 50% of usable energy", "MIS-003"],
                  ["Speed", "Cruise 1.0 m/s, never above 1.5 m/s",
                   "NAV-002/003"],
                  ["Light", "Daylight, boat in the operator's sight", "1.2"],
                  ["People", "No swim sessions or courses; ≥ 20 m from other "
                   "water users", "OPS-003/004"]],
                 [40, 100, 30]),
           P("Table 2. Operating envelope.", "caption"),
           H2("3.3 Roles and responsibilities"),
           table([["Role", "Who", "Responsibilities"],
                  ["Operator", "Parent", "Accountable for safety. Gets "
                   "permission. Runs the checklist. Arms, approves missions, "
                   "supervises the crew and the boat, commands recovery, "
                   "and never lets the child near the water unsupervised."],
                  ["Crew", "Son, age 4", "Builds and customises the boat, "
                   "gives the orders with TALK, presses GO / COME HOME / STOP, spots "
                   "the boat, reviews photos."],
                  ["Maintainer", "Parent", "Software, configuration, "
                   "charging, repairs, spares, logs and FMEA upkeep."],
                  ["Site owner", "Cambridge Sport Lakes Trust", "Grants "
                   "permission and sets conditions."],
                  ["Other water users", "Anglers, swimmers, paddlers",
                   "Not system users. The system and the operator keep "
                   "clear of them."]],
                 [26, 38, 106]),
           KeepTogether([H2("3.4 Operational phases"),
                         fig("phases.png", 165, "Figure 3. Operational "
                             "phases of a session.")]),
           table([["Phase", "Activities", "Boat mode", "Key reqs"],
                  ["Prepare (home)", "Charge the battery. Pull the tagged "
                   "release. Load the site fence. Rehearse the plan in "
                   "simulation. Pack the recovery and spares kits.",
                   "DISARMED", "SWE-006, OPS-010/011"],
                  ["Transport", "Boat in its carry cradle, battery "
                   "separate.", "Off", "MEC-014, PWR-007"],
                  ["Set up (bank)", "Check notices and other users. Power "
                   "up Mission Control and the boat. Crew fits the pods and "
                   "DUPLO crew. Complete the pre-launch checklist.",
                   "DISARMED", "OPS-001/003, PRE-006"],
                  ["Plan", "Crew gives the order. Mission generated, "
                   "validated, shown and approved, then uploaded and "
                   "verified.", "DISARMED", "NLI-*, VAL-*"],
                  ["Launch", "Place the boat on the water. Adult arms "
                   "(two-step). The boat holds.", "HOLD", "MOD-003/004, "
                   "PRE-*"],
                  ["Mission", "Crew holds GO. Boat runs the mission and "
                   "takes photos. Operator monitors. COME HOME and STOP "
                   "always available.", "AUTO → RTL", "MIS-*, FS-*, CAM-*"],
                  ["Recover", "Boat holds at home. Adult disarms and lifts "
                   "it out.", "HOLD → DISARMED", "MOD-005"],
                  ["Debrief", "Photos download. Captain's log made. Crew "
                   "finds the ducks.", "DISARMED", "CAM-007, DET-001/002"],
                  ["Maintain (home)", "Rinse and dry. Battery to storage. "
                   "Archive logs. Record issues. Update the FMEA if anything "
                   "changed.", "Off", "OPS-010, LOG-*, SAF-006"]],
                 [26, 82, 26, 36]),
           H2("3.5 Operational scenarios"),
           P("One normal scenario and the contingencies the system must "
             "handle. Each contingency is rehearsed in simulation before the "
             "first lake trial (OPS-012). The end state is always 'boat at "
             "home' or 'boat stopped inside the fence and recoverable'."),
           table([["#", "Scenario / trigger", "System response",
                   "Operator / crew action", "Reqs"],
                  ["OS-1", "<b>Duck patrol (normal).</b> Crew asks to "
                   "explore and photograph ducks.", "Plans, validates, "
                   "survey with photo points, RTL, HOLD.", "Approve; crew "
                   "holds GO; watch; disarm; debrief.", "MIS-001, VAL-*"],
                  ["OS-2", "<b>Manual drive</b> (pool or near bank).",
                   "Adult drives; fence and speed limits still apply.",
                   "Adult drives; crew spots.", "MC-012, FEN-004"],
                  ["OS-3", "<b>Link lost</b> mid-mission.", "Continues the "
                   "mission; RTL if still lost after 60 s.", "Watch; walk to "
                   "a better spot; wait at home point.", "FS-003, MC-009"],
                  ["OS-4", "<b>Low battery.</b>", "RTL at 35%; slow and "
                   "alarm at 15%.", "Watch it come home; end the session.",
                   "FS-001"],
                  ["OS-5", "<b>Stuck in weed.</b>", "HOLD, alarm, up to 3 "
                   "reverse bursts, then resume or stay.", "If still "
                   "stuck: COME HOME to retry, else recover by line.",
                   "FS-005/006, OPS-008"],
                  ["OS-6", "<b>Position loss</b> (GNSS).", "Motors stop; "
                   "RTL once healthy for 10 s.", "Watch; recover by line if "
                   "it doesn't recover.", "FS-004"],
                  ["OS-7", "<b>Fence breach</b> (wind, error).", "RTL within "
                   "1 s; motors stop if far outside.", "Watch; review logs "
                   "at home.", "FEN-005/006"],
                  ["OS-8", "<b>Person nearby</b>: angler, swimmer or "
                   "paddler within 20 m.", "No automatic detection.",
                   "Operator presses COME HOME or STOP.", "OPS-004, FS-009"],
                  ["OS-9", "<b>Dead in the water</b> (total power loss).",
                   "Passive: floats, flag and hi-vis visible.", "Wait for "
                   "drift to the bank; pole and net, or cast a line over "
                   "the hoop.", "REC-001..005, OPS-008"],
                  ["OS-10", "<b>No internet.</b>", "Natural-language "
                   "planning unavailable; offline templates offered.",
                   "Pick a template with the crew.", "MIS-005, MC-011"],
                  ["OS-11", "<b>Mission computer crash.</b>", "Helm "
                   "completes the mission and RTL; no photos.", "Reboot "
                   "after recovery; check logs.", "FS-007, SAF-002"]],
                 [12, 38, 46, 50, 24]),
           H2("3.6 Support concept"),
           *bullets([
               "<b>Maintenance:</b> rinse and dry the motors after every "
               "session. Check props, guards and seals. Motors and props are "
               "cheap consumables. Keep spares at home and a field kit in "
               "the bag (OPS-011).",
               "<b>Software:</b> changes are made and tested in simulation "
               "at home, and a tagged release is taken to the lake. No "
               "field edits to safety parameters (SAF-007, SWE-006).",
               "<b>Training:</b> the operator learns and rehearses in "
               "simulation (OPS-012). The crew learns by playing with "
               "Mission Control in simulation mode at home.",
               "<b>Records:</b> logs, photos and captain's logs are archived "
               "per session. Incidents feed the FMEA.",
           ]),
           H2("3.7 Evolution"),
           P("Mk1 grows by earned steps: a bigger fence after 5 good "
             "missions (OPS-006); on-board duck spotting (DET-003); an "
             "independent radio (COM-007); and, if chosen, the pure-Python "
             "helm behind the same interface (SWE-003)."),
           PageBreak()]

    # ---------------- 4 ConUse
    st += [H1("4. Concept of Use (ConUse)"),
           P("The ConUse describes how each user interacts with the system: "
             "who they are, the principles that shape the interaction, what "
             "they can touch and say, and the use cases they perform."),
           H2("4.1 User profiles"),
           table([["User", "Profile", "Needs from the interaction"],
                  ["Operator", "Adult. Mechanical engineer, confident with "
                   "electronics and Python. Attention is split between a "
                   "4-year-old, the bank and the boat.", "Glanceable status, "
                   "loud alarms, few steps, nothing hidden. Firm control of "
                   "anything hazardous. Full logs afterwards."],
                  ["Crew", "Age 4. Can't read yet. Short attention (about "
                   "20 min). Loves building, big buttons and ducks. Needs "
                   "to feel it's his boat.", "Big colourful controls, "
                   "immediate sound and light feedback, simple spoken "
                   "language, and a guaranteed happy ending: photos."],
                  ["Onlookers", "Curious park visitors, other children.",
                   "Nothing to operate. The boat is clearly supervised, "
                   "slow, and labelled (REC-006)."]],
                 [22, 76, 72]),
           H2("4.2 Interaction principles"),
           *bullets([
               "<b>Safe whatever the crew presses.</b> COME HOME and STOP "
               "can never cause harm. GO works only when an adult has made "
               "it safe (MC-003, VAL-008).",
               "<b>No reading needed.</b> Colour, icon, position and voice "
               "carry every crew interaction (CHD-005).",
               "<b>Adult gate on hazards.</b> Arming, fences, approvals and "
               "parameters need the adult key or PIN (MC-008).",
               "<b>The system talks.</b> Every mode change and event is "
               "spoken in child-friendly words (MC-007).",
               "<b>Always end on a win.</b> Short missions that come home "
               "with photos, and a captain's log to look at (MIS-003, "
               "DET-002).",
           ]),
           H2("4.3 Mission Control: what the crew can touch and say"),
           fig("panel.png", 130, "Figure 4. Mission Control panel concept "
               "(layout indicative)."),
           table([["Control", "What it does", "Available when", "Feedback",
                   "Why it's safe"],
                  ["<b>GO</b> (green, ▶)", "Starts the approved mission",
                   "Armed in HOLD with an approved, verified mission",
                   "Light on; \"Off we go!\"", "Adult pre-approved; "
                   "hold 1 s"],
                  ["<b>COME HOME</b> (yellow, house)", "RTL", "Any armed "
                   "mode", "\"Coming home!\"", "RTL stays inside the fence"],
                  ["<b>STOP</b> (red, ■)", "Motors off, boat drifts",
                   "Any time", "\"Stopping!\"", "Removes energy"],
                  ["<b>TALK</b> (blue, mic)", "Hold to speak an order",
                   "DISARMED or HOLD", "Plan shown on the map and spoken",
                   "Validator plus adult approval"],
                  ["<b>DUPLO deck</b>", "Crew, cargo, lookout", "Boat "
                   "disarmed", "It's his", "Away from props and "
                   "electronics"],
                  ["<b>Adult key / PIN</b>", "Arm, approve, fence, "
                   "settings", "Operator only", "Screen and voice",
                   "Gates every hazard"]],
                 [30, 34, 36, 34, 36]),
           H2("4.4 Use cases"),
           table([["UC", "Use case", "Actor", "Main flow", "Reqs"],
                  ["UC-01", "Plan a mission by voice", "Crew + operator",
                   "Crew speaks, then the plan appears and is spoken. "
                   "Operator approves. Upload and read-back.",
                   "NLI-*, VAL-*"],
                  ["UC-02", "Start a mission", "Crew", "Adult arms, then the "
                   "crew holds GO. The boat departs and the system "
                   "announces it.", "MC-003/004, MOD-006"],
                  ["UC-03", "Call the boat home", "Crew or operator",
                   "Press COME HOME. RTL, then HOLD at home.",
                   "MC-003, NAV-007"],
                  ["UC-04", "Emergency stop", "Anyone at the panel",
                   "Press STOP. Motors stop within 1 s.", "FS-009"],
                  ["UC-05", "Drive manually", "Operator", "Select MANUAL "
                   "and drive with the joystick or gamepad; fence "
                   "enforced.", "MC-012, FEN-004"],
                  ["UC-06", "Set up the site fence", "Operator", "Draw the "
                   "inclusion fence and exclusions on the map, then save "
                   "and commit.", "FEN-001..003"],
                  ["UC-07", "Pre-launch checklist", "Operator (crew "
                   "helps)", "Step through the items and sign off. Arming "
                   "is then allowed.", "OPS-001, PRE-006"],
                  ["UC-08", "Review photos and captain's log", "Crew + "
                   "operator", "Photos download. Ducks highlighted. "
                   "Captain's log read aloud.", "CAM-007, DET-002, MC-015"],
                  ["UC-09", "Build and customise", "Crew (operator "
                   "helps)", "Clip hull segments and pods together, then "
                   "build on the DUPLO deck.", "MEC-007/009, CHD-*"],
                  ["UC-10", "Practise in simulation", "Operator + crew",
                   "Mission Control in sim mode with the same buttons and "
                   "voice.", "SWE-004, OPS-012"],
                  ["UC-11", "Charge and maintain", "Operator", "Battery "
                   "out, charged in the fire-safe bag, rinse and dry, "
                   "archive logs.", "PWR-007, OPS-010"]],
                 [13, 32, 25, 74, 26]),
           Spacer(1, 3 * mm),
           fig("sequence.png", 150, "Figure 5. UC-01 and UC-02 in detail: "
               "from spoken instruction to captain's log. The validator "
               "(orange) and the helm (blue) are the safety gates."),
           H2("4.5 A day at the lake: a use story"),
           P("Saturday morning at Milton. The notice board shows no algae "
             "warning and no swim session, and the wind is light and "
             "blowing towards the bank. Dad works through the checklist on "
             "the screen while his son clips the orange pods on with the big "
             "thumb-screws and sits two DUPLO ducks on the deck as 'lookouts'. "
             "He presses the talk button: <i>\"Go and find the real ducks and "
             "take pictures!\"</i> A few seconds later a blue path appears on "
             "the map and the box says, <i>\"I'll explore the bay for ten "
             "minutes, take twenty pictures, then come home.\"</i> Dad checks "
             "the route, turns the key and approves it. The boat goes in the "
             "water, Dad arms it, and his son holds the green button until "
             "it says <i>\"Off we go!\"</i>"),
           P("Halfway round, the boat stops and says <i>\"I'm stuck in some "
             "weed, trying to wiggle free.\"</i> It reverses twice and carries "
             "on. An angler sets up nearby, so Dad lets his son press the "
             "yellow house: <i>\"Coming home!\"</i> The boat returns and "
             "waits by the bank. Back at the car they flick through the "
             "photos on the screen. Three have ducks, and the captain's log "
             "tells the story of the voyage."),
           PageBreak()]

    # ---------------- 3 requirements
    st += [H1("5. Requirements"),
           P(f"{n_req} requirements in {len(REQ.SECTIONS)} areas. Columns: "
             "priority (Pri), verification method (Ver), first verification "
             "stage (Stage), and the stakeholder needs served (Trace, STK- "
             "prefix omitted).", "small")]
    for i, sec in enumerate(REQ.SECTIONS, start=1):
        block = [H2(f"5.{i} {sec['title']} ({sec['key']})")]
        if sec["intro"]:
            block.append(P(sec["intro"]))
        rows = [["ID", "Requirement", "Pri", "Ver", "Stage", "Trace"]]
        for r in sec["reqs"]:
            txt = [Paragraph(r["text"], S["cell"])]
            if r["note"]:
                txt.append(Paragraph(r["note"], S["note"]))
            rows.append([Paragraph(f"<b>{r['id']}</b>", S["cell"]), txt,
                         pri_tag(r["pri"]), r["ver"].replace(",", ", "),
                         r["stage"],
                         ", ".join(t[4:] for t in r["trace"])])
        st += block + [table(rows, [17, 101, 9, 13, 13, 17])]
        if sec["key"] == "FS":
            st += [Spacer(1, 3 * mm),
                   KeepTogether([
                       table([["Condition", "Detection", "Response", "Req."]] +
                             [list(f) for f in REQ.FAILSAFES],
                             [34, 58, 52, 26]),
                       P("Table 3. Failsafe summary (initial thresholds, "
                         "TBD-08).", "caption")])]
    st.append(PageBreak())

    # ---------------- 4 verification
    stages = ["SIM", "BENCH", "POOL", "LAKE"]
    methods = ["T", "D", "I", "A", "S"]
    grid = {(s, m): 0 for s in stages for m in methods}
    for r in reqs:
        for m in r["ver"].split(","):
            grid[(r["stage"], m)] += 1
    st += [H1("6. Verification"),
           H2("6.1 Approach"),
           P("Each requirement is verified at the earliest stage that can "
             "prove it. It is then re-checked at later stages when the "
             "hardware or software it depends on changes. A stage is passed "
             "only when all its Must requirements are verified. <b>No lake "
             "trial happens until every SIM, BENCH and POOL Must requirement "
             "has passed</b> (OPS-009)."),
           table([["Stage", "Where", "What it proves"],
                  ["SIM", "Laptop / Pi 5", "Logic, modes, failsafes, "
                   "validator, Mission Control (SWE-004/005)"],
                  ["BENCH", "Workshop", "Hardware, electrical, ingress, "
                   "child-suitability, timings"],
                  ["POOL", "Paddling pool, then small private water",
                   "Buoyancy, stability, driving, stuck detection, link, "
                   "photos"],
                  ["LAKE", "Milton Country Park (with permission)",
                   "Performance, range, endurance, environment, "
                   "end-to-end missions"]],
                 [20, 55, 95]),
           H2("6.2 Verification summary"),
           table([["Stage"] + ["Test", "Demo", "Inspect", "Analysis", "Sim"] +
                  ["Reqs"]] +
                 [[s] + [str(grid[(s, m)] or "-") for m in methods] +
                  [f"<b>{sum(1 for r in reqs if r['stage'] == s)}</b>"]
                  for s in stages],
                 [30, 22, 22, 22, 22, 22, 30]),
           P("Counts of verification methods by first stage. A requirement "
             "can have more than one method.", "caption"),
           H2("6.3 Requirements by first verification stage")]
    for s in stages:
        ids = [r["id"] for r in reqs if r["stage"] == s]
        st.append(P(f"<b>{s} ({len(ids)}):</b> {', '.join(ids)}", "small"))
    st.append(PageBreak())

    # ---------------- 5 traceability
    areas = [s["key"] for s in REQ.SECTIONS]
    stk = [s[0] for s in REQ.STAKEHOLDER_NEEDS]
    rows = [["Area"] + [s[4:] for s in stk]]
    for sec in REQ.SECTIONS:
        row = [sec["key"]]
        for k in stk:
            n = sum(1 for r in sec["reqs"] if k in r["trace"])
            row.append(str(n) if n else "")
        rows.append(row)
    rows.append(["<b>Total</b>"] +
                [f"<b>{sum(1 for r in reqs if k in r['trace'])}</b>"
                 for k in stk])
    shade = []
    for ri, row in enumerate(rows[1:-1], start=1):
        for ci, v in enumerate(row[1:], start=1):
            if v:
                n = int(v)
                shade.append(("BACKGROUND", (ci, ri), (ci, ri),
                              colors.HexColor("#cfe1f6" if n < 4 else
                                              "#9cc3ee" if n < 8 else
                                              "#6aa3e3")))
    st += [H1("7. Traceability"),
           P("Every stakeholder need is covered by at least one requirement, "
             "and every requirement traces to at least one need. The build "
             "script checks both automatically. The matrix counts "
             "requirements per area and need."),
           table(rows, [26] + [18] * len(stk),
                 style_extra=shade + [("ALIGN", (1, 0), (-1, -1), "CENTER")]),
           Spacer(1, 2 * mm),
           P(" · ".join(f"<b>{i[4:]}</b> {n}" for i, n, _ in
                        REQ.STAKEHOLDER_NEEDS), "caption"),
           H2("7.1 Requirements per need")]
    for i, n, _ in REQ.STAKEHOLDER_NEEDS:
        ids = [r["id"] for r in reqs if i in r["trace"]]
        st.append(P(f"<b>{i} {n} ({len(ids)}):</b> {', '.join(ids)}",
                    "small"))
    st.append(PageBreak())

    # ---------------- 6 open items
    st += [H1("8. Open items (TBD)"),
           table([["ID", "Open item", "Affects", "Resolved by"]] +
                 [list(t) for t in REQ.TBDS], [16, 86, 38, 30]),
           Spacer(1, 5 * mm),
           callout("<b>Next:</b> the Architecture Design Document "
                   "(BOATY-ADD-001) allocates every requirement to a "
                   "subsystem, closes TBD-04 to TBD-07, and defines the "
                   "interfaces for the ICD and subsystem specifications."),
           Spacer(1, 6 * mm),
           H1("Appendix A. Glossary"),
           table([["Term", "Meaning"]] +
                 [[f"<b>{t}</b>", d] for t, d in REQ.GLOSSARY], [36, 134]),
           Spacer(1, 6 * mm),
           H1("Appendix B. Requirement statistics"),
           table([["Area", "Title", "Must", "Should", "Could", "Total"]] +
                 [[s["key"], s["title"]] +
                  [str(sum(1 for r in s["reqs"] if r["pri"] == p) or "-")
                   for p in "MSC"] + [str(len(s["reqs"]))]
                  for s in REQ.SECTIONS] +
                 [["", "<b>Total</b>", f"<b>{pri['M']}</b>",
                   f"<b>{pri['S']}</b>", f"<b>{pri['C']}</b>",
                   f"<b>{n_req}</b>"]],
                 [16, 78, 19, 19, 19, 19],
                 style_extra=[("ALIGN", (2, 0), (-1, -1), "CENTER")]),
           ]

    doc = Doc(OUT)
    doc.multiBuild(st)
    print("wrote", OUT, f"({n_req} requirements)")


if __name__ == "__main__":
    build()
