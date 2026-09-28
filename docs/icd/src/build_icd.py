"""Build the Boaty Interface Control Document PDF.

Run:  python3 docs/icd/src/figures.py && python3 docs/icd/src/build_icd.py
Writes docs/icd/Boaty_Interface_Control_Document.pdf

Interface identities (name, ends, type, medium, requirements) come from the
ADD (docs/add/src/architecture.py) so the two documents cannot drift. This
file adds the detailed definitions.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
sys.path.insert(0, str(DOCS / "common"))
sys.path.insert(0, str(DOCS / "add" / "src"))

import architecture as A  # noqa: E402
from pdfdoc import (BLUE_T, GREEN_T, ORANGE, ORANGE_T, H1, H2, INK2,  # noqa
                    TINT, Doc, KeepTogether, PageBreak, Paragraph, S, Spacer,
                    bullets, callout, colors, control_and_contents, cover,
                    fig, mm, table, P)
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.platypus import Table, TableStyle, XPreformatted  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402

pdfmetrics.registerFont(TTFont(
    "DVM", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
S["code"] = ParagraphStyle("code", fontName="DVM", fontSize=6.9, leading=8.9,
                           textColor=colors.HexColor("#1f1f1d"))

FIG = HERE.parent / "figures"
OUT = HERE.parent / "Boaty_Interface_Control_Document.pdf"
DOC_ID = "BOATY-ICD-001"
ISSUE = "Issue D (for review)"
DATE = "28 September 2026"

IFS = {i[0]: i for i in A.INTERFACES}
NAMES = {s[0]: s[1] for s in A.SUBSYSTEMS} | A.EXTERNALS
OWNER = {"IF-01": "MCN", "IF-02": "MCN", "IF-03": "MCP", "IF-04": "MCP",
         "IF-05": "HLM", "IF-06": "PWR", "IF-07": "PWR", "IF-08": "PWR",
         "IF-09": "HLM", "IF-10": "MCN", "IF-11": "MCN", "IF-12": "MCN",
         "IF-13": "MCN", "IF-14": "MCN", "IF-15": "MCN", "IF-16": "HUL",
         "IF-17": "PRP", "IF-18": "HUL", "IF-19": "HUL", "IF-20": "HUL",
         "IF-21": "SIM", "IF-22": "HLM"}

TBC = []          # filled as sections are built: (id, text, interface)
VERIF = []        # (interface, method, stage, evidence)


def tbc(iface, text, closed=None):
    """Register a to-be-confirmed item. Closed items keep their number."""
    tid = f"TBC-{len(TBC) + 1:02d}"
    if closed:
        TBC.append((tid, f"<b>Closed.</b> {closed} (was: {text})", iface))
        return f'<font color="#9a998f">({tid} closed)</font>'
    TBC.append((tid, text, iface))
    return f'<font color="#eb6834"><b>[{tid}]</b></font>'


def code(text):
    t = Table([[XPreformatted(text.strip("\n"), S["code"])]],
              colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def F(name, w, cap):
    return fig(FIG / name, w, cap)


def header(iid, extra=""):
    i = IFS[iid]
    a, b = NAMES.get(i[2], i[2]), NAMES.get(i[3], i[3])
    ends = a if i[2] == i[3] else f"{a} ↔ {b}"
    t = table([["Interface", f"<b>{iid} {i[1]}</b>", "Owner",
                f"{OWNER[iid]} ({NAMES[OWNER[iid]]})"],
               ["Between", ends, "Type", i[4]],
               ["Medium", i[5], "Requirements", i[7]]],
              [22, 76, 24, 48], header=False,
              style_extra=[("BACKGROUND", (0, 0), (0, -1), TINT),
                           ("BACKGROUND", (2, 0), (2, -1), TINT)])
    return [KeepTogether([H2(f"{iid} {i[1]}"), t, Spacer(1, 3 * mm)])]


def verify(iid, rows):
    for method, stage, ev in rows:
        VERIF.append((iid, method, stage, ev))
    return [KeepTogether([P("<b>Verification</b>", "body"),
                          table([["Method", "Stage", "Evidence / pass "
                                  "criterion"]] + [list(r) for r in rows],
                                [22, 18, 130])]),
            Spacer(1, 5 * mm)]


def sub(t):
    return P(f"<b>{t}</b>", "body")


# ======================================================================
def section_network():
    st = [H1("4. Network and data interfaces"),
          F("network.png", 165, "Figure 1. Network topology and addressing "
            "(IF-01, IF-04, IF-10).")]

    # ---------------- IF-01
    st += header("IF-01")
    st += [sub("Radio and link layer"),
           table([["Parameter", "Value"],
                  ["Standard / band", "IEEE 802.11n, 2.4 GHz, 20 MHz channel"],
                  ["Channel", "Fixed; chosen on site from 1, 6 or 11 by a "
                   "scan at set-up (least occupied). Stored per site."],
                  ["Access point", "Mission Control USB adapter (wlan1), "
                   "hostapd. Pi 5 internal Wi-Fi unused."],
                  ["SSID / security", "boaty-mc (hidden: no) / WPA2-PSK "
                   "(WPA3-SAE if both ends support it), 20+ character "
                   "passphrase, not the default"],
                  ["Transmit power", "Default regulatory maximum for GB "
                   "(country code GB in hostapd and wpa_supplicant)"],
                  ["Antennas", "Bank: ≈5 dBi omni on the adapter, optional "
                   "2 m pole. Boat: Pi Zero 2W on-board antenna, box lid "
                   "≥ 150 mm above water."]], [45, 125]),
           Spacer(1, 2 * mm),
           sub("Addressing (IPv4)"),
           table([["Host", "Interface", "Address", "Notes"],
                  ["Mission Control", "wlan1", "192.168.50.1/24",
                   "DHCP server for .100-.150; no default route on wlan1"],
                  ["Mission computer", "wlan0", "192.168.50.10", "Static; "
                   "hostname boaty-mcp"],
                  ["Tablet (optional)", "Wi-Fi", "192.168.50.100-150",
                   "DHCP"],
                  ["Mission Control", "usb0", "Phone-assigned", "See IF-10"]],
                 [34, 22, 34, 80]),
           Spacer(1, 2 * mm),
           sub("Ports and traffic"),
           table([["Flow", "Protocol / port", "Direction", "Rate"],
                  ["MAVLink (IF-02)", "UDP 14550 on Mission Control",
                   "Router on boat is the client", "≈ 2-4 kB/s"],
                  ["Photo & health API (IF-03)", "HTTP TCP 8080 on MCP",
                   "Mission Control is the client", "Bursty, up to link "
                   "rate"],
                  ["Web UI (IF-12)", "HTTP TCP 8000 on Mission Control",
                   "Tablet/phone is the client", "Low"]],
                 [38, 48, 50, 34]),
           Spacer(1, 2 * mm),
           sub("Security and error handling"),
           *bullets([
               "The MCP firewall (nftables) accepts inbound TCP 8080 only "
               "from 192.168.50.1 and drops everything else. MAVLink leaves "
               "the boat only towards 192.168.50.1:14550.",
               "Link loss is expected and never unsafe. Behaviour is defined "
               "by FS-002/003 on the helm and B4 on the MCP. Mission Control "
               "shows 'link lost' within 3 s (no HEARTBEAT) and keeps the "
               "last known position (MC-009).",
               "Signal quality: MCP reports its RSSI in /v1/health (IF-03). "
               "Mission Control also logs the AP's per-station RSSI once a "
               "second (COM-004).",
           ])]
    st += verify("IF-01", [
        ("Test", "BENCH", "Association, addressing and firewall rules checked "
         "with a script; ports reachable only as listed"),
        ("Test", "LAKE", "≥ 100 m over water with telemetry ≥ 1 Hz and "
         "command latency ≤ 1 s at the 95th percentile (COM-002/003, V-08)")])

    # ---------------- IF-02
    st += header("IF-02")
    st += [F("mavlink.png", 150, "Figure 2. MAVLink identities and routing "
             "(IF-02, IF-04)."),
           sub("Identities"),
           table([["Node", "System ID", "Component ID", "MAV_TYPE"],
                  ["ArduPilot Rover (helm)", "1", "1 (AUTOPILOT1)",
                   "SURFACE_BOAT (11)"],
                  ["Mission Control", "255", "190 (MISSIONPLANNER)",
                   "GCS (6)"],
                  ["Mission computer services", "1", "191 "
                   "(ONBOARD_COMPUTER)", "ONBOARD_CONTROLLER (18)"],
                  ["QGroundControl backup (MC-014)", "255", "190", "GCS (6)"]],
                 [52, 24, 48, 46]),
           P("The helm is configured with SYSID_MYGCS = 255, so only "
             "heartbeats from system 255 count as ground-station presence "
             "for the GCS failsafe. The mission computer's heartbeats "
             "(system 1, component 191) do not mask a lost bank link "
             "(V-06). Only one GCS is connected at a time.", "small"),
           sub("Telemetry the helm sends (requested with "
               "MAV_CMD_SET_MESSAGE_INTERVAL, 511)"),
           table([["Message (ID)", "Rate", "Used for"],
                  ["HEARTBEAT (0)", "1 Hz", "Mode (custom_mode), armed flag, "
                   "link presence"],
                  ["SYS_STATUS (1)", "1 Hz", "Sensor health, battery "
                   "summary"],
                  ["GLOBAL_POSITION_INT (33)", "4 Hz", "Map position, "
                   "heading, speed (MC-005)"],
                  ["GPS_RAW_INT (24)", "1 Hz", "Fix type, satellites, HDOP "
                   "(PRE-001)"],
                  ["BATTERY_STATUS (147)", "1 Hz", "Voltage, current, % "
                   "remaining; instance 1 = motor rail (V-13)"],
                  ["VFR_HUD (74)", "2 Hz", "Ground speed, throttle"],
                  ["MISSION_CURRENT (42)", "1 Hz", "Progress; mission time "
                   "remaining"],
                  ["MISSION_ITEM_REACHED (46)", "Event", "Photo points "
                   "(also consumed by MCP)"],
                  ["NAV_CONTROLLER_OUTPUT (62)", "1 Hz", "Cross-track error "
                   "(NAV-005)"],
                  ["EKF_STATUS_REPORT (193)", "1 Hz", "Estimator health "
                   "(FS-004)"],
                  ["FENCE_STATUS (162)", "1 Hz", "Breach state and count"],
                  ["STATUSTEXT (253)", "Event", "Failsafe and pre-arm "
                   "reasons, turned into plain language (MOD-004)"]],
                 [54, 16, 100]),
           Spacer(1, 2 * mm),
           sub("Commands Mission Control sends"),
           table([["Action", "Message / command", "Parameters", "Allowed "
                   "when"],
                  ["Arm", "COMMAND_LONG: COMPONENT_ARM_DISARM (400)",
                   "p1 = 1", "State APPROVED, adult PIN unlocked, pre-arm OK"],
                  ["Disarm", "COMMAND_LONG 400", "p1 = 0", "HOLD at home or "
                   "after STOP"],
                  ["Force disarm", "COMMAND_LONG 400", "p1 = 0, p2 = 21196",
                   "Only if normal disarm refused after STOP"],
                  ["Set mode", "COMMAND_LONG: DO_SET_MODE (176)", "p1 = 1 "
                   "(custom), p2 = mode number", "See mode table"],
                  ["Enable fence", "COMMAND_LONG: DO_FENCE_ENABLE (207)",
                   "p1 = 1", "After fence upload, before arming"],
                  ["Stream rates", "COMMAND_LONG: SET_MESSAGE_INTERVAL (511)",
                   "p1 = msg id, p2 = interval µs", "On connect"],
                  ["Manual drive", "MANUAL_CONTROL (69)", "x = throttle, "
                   "r = turn (−1000..1000), 10 Hz", "MANUAL (STEERING) only; "
                   "adult"],
                  ["Parameter read", "PARAM_REQUEST_LIST (21) / PARAM_VALUE "
                   "(22)", "-", "On connect (SAF-007 baseline check)"],
                  ["Parameter write", "PARAM_SET (23)", "-", "<b>Disarmed "
                   "only</b>; refused by C7 when armed (SAF-003)"]],
                 [22, 52, 44, 52]),
           Spacer(1, 2 * mm),
           sub("Rover mode numbers used (custom_mode)"),
           table([["SRS mode", "ArduPilot mode", "Number"],
                  ["MANUAL", "STEERING", "3"], ["HOLD (motors off)", "HOLD",
                                                "4"],
                  ["HOLD (station-keeping)", "LOITER", "5"],
                  ["(weed-shedding only, IF-04)", "GUIDED", "15"],
                  ["AUTO", "AUTO", "10"], ["RTL", "RTL", "11"]],
                 [60, 60, 50]),
           P("Mode numbers follow ArduPilot Rover's published list "
             + tbc("IF-02", "Confirm Rover mode numbers against the "
                   "firmware version flashed (SITL check).") + ".", "small"),
           F("sequence.png", 140, "Figure 3. Fence and mission upload, "
             "read-back, arming and start (VAL-010, MOD-003)."),
           sub("Mission and fence transfer"),
           *bullets([
               "Standard MAVLink mission protocol, integer items: "
               "MISSION_COUNT (44), MISSION_REQUEST_INT (51), "
               "MISSION_ITEM_INT (73), MISSION_ACK (47). mission_type 1 = "
               "fence, 0 = mission. The fence is uploaded first.",
               "Fence items: FENCE_POLYGON_VERTEX_INCLUSION (5001, p1 = "
               "vertex count), FENCE_POLYGON_VERTEX_EXCLUSION (5002), "
               "FENCE_CIRCLE_EXCLUSION (5004, p1 = radius m), "
               "FENCE_RETURN_POINT (5000) = home.",
               "Mission items: seq 0 is home (ArduPilot convention; "
               "overwritten by the helm on arming). Then items as mapped "
               "in IF-13, in MAV_FRAME_GLOBAL_RELATIVE_ALT_INT (6), altitude "
               "0. The last item is NAV_RETURN_TO_LAUNCH (20).",
               "Read-back: MISSION_REQUEST_LIST (43) per type. The items "
               "returned are canonicalised (IF-13) and hashed. GO is "
               "enabled only if the hash equals the approved mission's "
               "(VAL-010). Seq 0 (home) is excluded from the hash.",
           ]),
           sub("Timing and error handling"),
           table([["Case", "Rule"],
                  ["COMMAND_ACK", "Expected ≤ 1 s. Up to 3 attempts at 1 s "
                   "intervals, then HelmError('no response') (IF-14)."],
                  ["MAV_RESULT ≠ ACCEPTED (0)", "Raise CommandRejected with "
                   "the result code and the latest STATUSTEXT, spoken in "
                   "plain words (MOD-004)."],
                  ["Mission transfer", "Per-item timeout 1.5 s; ≤ 3 retries "
                   "per item; whole transfer ≤ 20 s or abort and report."],
                  ["STOP latency budget", "Button → C1 ≤ 50 ms; C7 → radio "
                   "≤ 50 ms; link ≤ 300 ms; helm mode change ≤ 100 ms. "
                   "Total ≤ 0.5 s, against FS-009's 1 s."],
                  ["Heartbeat loss", "No HEARTBEAT from system 1 for 3 s → "
                   "'link lost' in the UI; keep resending commands only if "
                   "the user presses again."]], [40, 130])]
    st += verify("IF-02", [
        ("Simulation", "SIM", "Automated SITL suite: every command in the "
         "table accepted or rejected as specified; read-back hash matches; "
         "mode numbers confirmed"),
        ("Test", "POOL", "STOP → motors stopped ≤ 1 s, measured on video "
         "with an on-screen timestamp (FS-009)")])

    # ---------------- IF-04
    st += header("IF-04")
    st += [sub("Physical"),
           table([["Parameter", "Value"],
                  ["Signal levels", "3.3 V TTL UART, both ends (no level "
                   "shifting)"],
                  ["Wiring", "FC TX → Pi GPIO15 (RXD, pin 10); FC RX ← Pi "
                   "GPIO14 (TXD, pin 8); GND ↔ pin 6. No power conductor "
                   "(each side is powered separately, IF-07/IF-08)."],
                  ["Port", "FC SERIAL2 (TELEM2 pads) " + tbc(
                      "IF-04", "Confirm which UART is free on the chosen "
                      "F405 board.")],
                  ["Settings", "115200 baud, 8N1, no flow control. "
                   "SERIAL2_PROTOCOL = 2 (MAVLink 2)."],
                  ["Pi side", "/dev/serial0 on the PL011 UART "
                   "(dtoverlay=disable-bt), serial console disabled"],
                  ["Cable", "≤ 200 mm, inside the electronics box"]],
                 [34, 136]),
           P("115200 baud carries ≈ 11 kB/s against ≈ 4 kB/s of expected "
             "traffic, so the link runs at under 40% load.", "small"),
           sub("mavlink-router configuration (B1)"),
           code("""
[General]
TcpServerPort = 0            # no TCP server
ReportStats = false

[UartEndpoint helm]
Device = /dev/serial0
Baud = 115200

[UdpEndpoint missioncontrol]
Mode = Normal                # client: sends to the bank
Address = 192.168.50.1
Port = 14550

[UdpEndpoint local]
Mode = Server                # B2-B6 connect here
Address = 127.0.0.1
Port = 14560
"""),
           sub("What boat-side services (component 191) may send"),
           table([["Service", "Messages / commands", "Constraint"],
                  ["B4 link watchdog", "DO_SET_MODE → RTL (11)", "Only if "
                   "mode is AUTO and no system-255 HEARTBEAT for 60 s "
                   "(FS-003)"],
                  ["B5 weed-shedding", "DO_SET_MODE → GUIDED (15); "
                   "SET_POSITION_TARGET_LOCAL_NED (84) velocity-only in "
                   "MAV_FRAME_BODY_NED (8); DO_SET_MODE → HOLD (4) or back "
                   "to the previous mode", "Only after a helm stuck event. "
                   "≤ 0.5 m/s astern, ≤ 2 s per burst, ≤ 3 bursts, targets "
                   "at 10 Hz. Relies on V-11."],
                  ["B6 health", "DO_SET_MODE → RTL (11); STATUSTEXT",
                   "Moisture detected, or box temperature > 60 °C"],
                  ["B7 navigation monitor", "DO_SET_MODE → HOLD (4); "
                   "STATUSTEXT", "First-motion heading error > 45°; "
                   "no progress along track at high throttle for 10 s; "
                   "cross-track > 10 m or heading error > 60° for 20 s "
                   "(FMEA A-03/07/08)"],
                  ["B2 camera", "None (listens only)", "Reads "
                   "GLOBAL_POSITION_INT, MISSION_ITEM_REACHED, SYSTEM_TIME"],
                  ["All", "Never: arm/disarm, PARAM_SET, fence or mission "
                   "upload, AUTO, MANUAL, STEERING", "Enforced by a message "
                   "filter in the services' shared MAVLink client library"]],
                 [26, 72, 72]),
           P("A boat-side request that the helm rejects is logged and not "
             "retried more than twice.", "small")]
    st += verify("IF-04", [
        ("Inspection", "BENCH", "Wiring and serial settings against this "
         "section; loopback test at 115200 with no errors over 10 min"),
        ("Simulation", "SIM", "B4, B5 and B6 behaviours in SITL, including "
         "killing B5 mid-burst (V-11)"),
        ("Test", "SIM", "The filter library refuses every forbidden command "
         "(unit tests)")])

    # ---------------- IF-03
    st += header("IF-03")
    st += [P("A small HTTP/JSON API served by the mission computer on TCP "
             "8080. Mission Control is the only client. Every request "
             "carries <font name='DVM'>Authorization: Bearer "
             "&lt;token&gt;</font>, a 32-byte random token provisioned on "
             "both computers at set-up. Timestamps are ISO 8601 UTC. "
             "Coordinates are WGS84 decimal degrees."),
           table([["Endpoint", "Purpose", "Response"],
                  ["GET /v1/health", "Health snapshot", "200 Health"],
                  ["PUT /v1/session", "Set the capture policy for the next "
                   "mission", "200 Session"],
                  ["GET /v1/photos?mission=&lt;id&gt;&amp;since=&lt;utc&gt;",
                   "List photos", "200 [Photo]"],
                  ["GET /v1/photos/&lt;id&gt;", "Full image", "200 "
                   "image/jpeg"],
                  ["GET /v1/photos/&lt;id&gt;/thumb", "320 px thumbnail",
                   "200 image/jpeg"],
                  ["POST /v1/photos/ack", "Confirm photos safely copied "
                   "(allows later deletion)", "204"],
                  ["POST /v1/capture", "Take photos now: {count 1-10, "
                   "interval_s 0.5-5}", "202"],
                  ["POST /v1/shutdown", "Clean shutdown before power-off "
                   "(R-04)", "202"]], [56, 74, 40]),
           Spacer(1, 2 * mm),
           code("""
Health  = {"status": "ok"|"degraded"|"fault", "uptime_s": int,
           "cpu_temp_c": float, "throttled": bool, "storage_free_mb": int,
           "photos_unsynced": int, "moisture": bool, "camera_ok": bool,
           "mavlink_ok": bool, "rssi_dbm": int, "box_temp_c": float,
           "sw_version": str}
Session = {"mission_id": uuid, "interval_s": 0 | 2..30,
           "photo_points": [{"seq": int, "burst_n": 1..10}]}
Photo   = {"id": str, "mission_id": uuid, "taken_utc": str,
           "lat": float, "lon": float, "heading_deg": float,
           "trigger": "interval"|"photo_point"|"command",
           "point_seq": int|null, "bytes": int, "sha256": str,
           "width": int, "height": int}
Error   = {"error": "bad_request"|"not_found"|"busy"|"storage_full",
           "message": str}                       # with 4xx/5xx status
"""),
           *bullets([
               "Images: JPEG, 2592 × 1944 (5 MP), quality 85, ≈ 1.5-2.5 MB. "
               "Geotags come from the latest GLOBAL_POSITION_INT, which "
               "must be under 0.5 s old, otherwise lat/lon are null.",
               "Capture triggers: every interval_s during AUTO. At a photo "
               "point, burst_n photos starting ≤ 0.5 s after "
               "MISSION_ITEM_REACHED for that seq. On POST /v1/capture.",
               "Sync: thumbnails first, then full images. 200 photos in "
               "≤ 5 min near the bank (CAM-007) needs ≈ 11 Mbit/s. "
               "Mission Control verifies each sha256 before calling ack.",
               "Photos are never deleted before ack. With storage full the "
               "service stops capturing and returns 507 storage_full; "
               "navigation is unaffected (CAM-004).",
           ])]
    st += verify("IF-03", [
        ("Test", "BENCH", "Contract tests: every endpoint, error and auth "
         "case; the SIM camera stub passes the same suite (IF-21)"),
        ("Test", "POOL", "200-photo sync ≤ 5 min with the boat ≤ 10 m from "
         "the bank; hashes verified")])

    # ---------------- IF-10
    st += header("IF-10")
    st += [table([["Parameter", "Value"],
                  ["Physical", "Phone USB cable to a Pi 5 USB port; phone "
                   "set to 'USB tethering' (Android) or 'Personal Hotspot' "
                   "with USB (iPhone)"],
                  ["Link", "RNDIS/NCM (Android) or ipheth (iPhone), seen "
                   "as usb0; address by DHCP from the phone (typically "
                   "192.168.42.x Android, 172.20.10.x iPhone)"],
                  ["Routing", "Default route via usb0 only. No forwarding "
                   "between usb0 and wlan1 (ip_forward = 0), so nothing on "
                   "the boat network can reach the internet."],
                  ["Allowed outbound", "HTTPS 443 to api.anthropic.com; NTP "
                   "(optional). Everything else is blocked by nftables."],
                  ["Inbound from phone", "HTTP 8000 (web UI) only"],
                  ["Loss of uplink", "NL planning and cloud photo analysis "
                   "are unavailable. The UI shows 'no internet: templates "
                   "only' (MC-011). Boat link unaffected (COM-005)."]],
                 [34, 136])]
    st += verify("IF-10", [
        ("Test", "BENCH", "With both phone types if available: tether up, "
         "API reachable, boat network cannot reach the internet, unplugging "
         "the phone leaves the boat link intact")])

    # ---------------- IF-11
    st += header("IF-11")
    st += [P("Mission Control calls the Claude API through the official "
             "Anthropic Python SDK (<font name='DVM'>anthropic</font>). "
             "Two request types. Both use structured outputs, so the "
             "response is schema-valid JSON rather than free text. The "
             "planner and the validator check it again anyway."),
           table([["Field", "Mission intent request", "Photo log request "
                   "(opt-in)"],
                  ["Endpoint", "POST /v1/messages", "POST /v1/messages"],
                  ["Model", "claude-opus-5", "claude-opus-5"],
                  ["Thinking / effort", "adaptive / medium "
                   "(tune against NLI-007)", "adaptive / medium"],
                  ["max_tokens", "16000", "16000"],
                  ["Output", "output_config.format = JSON schema of Intent "
                   "v1 (IF-13)", "JSON schema of PhotoLog v1"],
                  ["System prompt", "Fixed, versioned, cached "
                   "(cache_control). Role, the intent vocabulary, safety "
                   "rules, child-friendly summary style.", "Fixed, versioned, "
                   "cached"],
                  ["User content", "Site context JSON (names of areas and "
                   "landmarks, sizes, battery %, limits) + transcript, "
                   "clearly delimited as data", "Up to 20 thumbnails "
                   "(base64 JPEG, long edge 1024 px) + photo IDs"],
                  ["Refusal fallback", "fallbacks = 'default' "
                   "(beta server-side-fallback-2026-07-01)", "Same"],
                  ["Client timeout / retries", "20 s / SDK default 2 "
                   "retries (429, 5xx, connection)", "60 s / 2"]],
                 [30, 72, 68]),
           Spacer(1, 2 * mm),
           sub("Response handling"),
           table([["Outcome", "Action"],
                  ["stop_reason = end_turn", "Parse JSON, validate against "
                   "Intent v1 (pydantic), pass to the planner"],
                  ["Schema or planner failure", "Retry once, with the error "
                   "appended as data; then offer templates (NLI-004)"],
                  ["stop_reason = refusal (after fallbacks)", "Say 'I can't "
                   "plan that one - shall we pick an adventure?' and offer "
                   "templates"],
                  ["stop_reason = max_tokens", "Retry once, then templates"],
                  ["HTTP error after SDK retries / timeout", "Templates; log "
                   "the request ID"]], [58, 112]),
           Spacer(1, 2 * mm),
           sub("Data minimisation (LOG-004)"),
           *bullets([
               "<b>Never sent:</b> audio (speech is transcribed on the "
               "Pi 5), coordinates (the model sees named areas and "
               "landmarks only; the planner owns geometry), the API key "
               "(stored only in the Mission Control keyring, NLI-008).",
               "Photos are sent only when an adult has enabled cloud "
               "analysis for the session. Otherwise the captain's log uses "
               "on-device heuristics only.",
               "Each request's ID, token usage and cost estimate are logged "
               "(LOG-002).",
           ])]
    st += verify("IF-11", [
        ("Test", "SIM", "Recorded evaluation set of ≥ 30 instructions "
         "(including ones that must be declined): 100% schema-valid; every "
         "must-decline declined; plan shown ≤ 20 s on mobile data "
         "(NLI-003..007)"),
        ("Inspection", "SIM", "Captured request bodies contain no "
         "coordinates or audio; photo requests only with cloud analysis "
         "enabled")])
    return st


# ======================================================================
def section_software():
    st = [H1("5. Software contracts")]

    # ---------------- IF-13
    st += header("IF-13")
    st += [P("Three JSON documents, each carrying a <font name='DVM'>"
             "schema</font> field for versioning. A breaking change bumps "
             "the major version. Readers reject unknown major versions. "
             "The schemas are kept as pydantic models in the repository; "
             "this section is their normative summary."),
           sub("Intent v1: produced by the Claude API, consumed by the "
               "planner"),
           code("""
{"schema": "boaty.intent/1",
 "summary_for_child": str (<= 140 chars, spoken aloud),
 "speed": "slow" | "normal",
 "steps": [ 1..8 of:
   {"op": "explore",     "area": <area name>, "coverage": "light"|"medium"|"thorough"}
   {"op": "visit",       "landmark": <landmark name>, "photos": 1..10, "hold_s": 5..60}
   {"op": "photo_stops", "n": 1..6, "near": <landmark name> | null}
   {"op": "lap",         "area": <area name>}
   {"op": "return_home"}              # must be the last step
 ],
 "declined": null | {"reason_for_child": str}}  # set instead of steps
"""),
           P("Names must match the site file (IF-15), by name or alias. "
             "Anything else is a planner failure.", "small"),
           sub("Mission v1: produced by the planner, checked by the "
               "validator, uploaded by the helm interface"),
           code("""
{"schema": "boaty.mission/1", "id": uuid, "created_utc": str,
 "source": "voice"|"text"|"template"|"map", "site": str,
 "site_version": <git commit of the site file>,
 "home": {"lat": float, "lon": float},
 "cruise_mps": 0.6..1.2,
 "items": [ {"seq": 1.., "kind": "waypoint"|"photo_point"|"speed"|"rtl",
             "lat": float|null, "lon": float|null,
             "hold_s": int|null, "photos": int|null, "speed_mps": float|null} ],
 "estimates": {"distance_m": float, "duration_s": int, "energy_wh": float},
 "capture": {"interval_s": 0|2..30},
 "checksum": "sha256:<hex>"}
"""),
           table([["kind", "MAVLink item (IF-02)", "Fields"],
                  ["waypoint", "NAV_WAYPOINT (16)", "x = lat×1e7, y = "
                   "lon×1e7; p2 acceptance radius = 3 m (NAV-004)"],
                  ["photo_point", "NAV_LOITER_TIME (19)", "p1 = hold_s; "
                   "position as above; photos → Session.photo_points "
                   "(IF-03)"],
                  ["speed", "DO_CHANGE_SPEED (178)", "p2 = speed_mps "
                   "(≤ 1.5, NAV-003)"],
                  ["rtl", "NAV_RETURN_TO_LAUNCH (20)", "Must be last "
                   "(MIS-002)"]], [24, 50, 96]),
           P("<b>Canonical form and checksum:</b> the items list, "
             "serialised as JSON with sorted keys and no whitespace. "
             "lat/lon are rendered as integers ×1e7 and floats rounded to "
             "2 decimal places. The checksum is its SHA-256. The helm "
             "interface computes the same form from the read-back items "
             "(VAL-010).", "small"),
           sub("ValidationResult v1: produced by the validator"),
           code("""
{"schema": "boaty.validation/1", "mission_id": uuid, "ok": bool,
 "violations": [ {"rule": "VAL-002", "message_for_adult": str,
                  "message_for_child": str, "item_seq": int|null,
                  "at": {"lat": float, "lon": float} | null} ],
 "checked_utc": str, "validator_version": str}
""")]
    st += verify("IF-13", [
        ("Test", "SIM", "Schema round-trip tests; validator suite ≥ 95% "
         "branch coverage with adversarial missions (VAL-006); checksum "
         "equal for upload and read-back in SITL")])

    # ---------------- IF-14
    st += header("IF-14")
    st += [P("The only way Mission Control code commands a helm (SAF-003, "
             "SWE-002/003). Mk1 has one implementation, "
             "<font name='DVM'>ArduPilotHelm</font> (pymavlink over IF-02). "
             "A future Python helm implements the same protocol."),
           code("""
class Helm(Protocol):
    def connect(self, timeout_s: float = 10) -> None
    def status(self) -> HelmStatus                    # latest snapshot, never blocks
    def subscribe(self, cb: Callable[[HelmEvent], None]) -> None

    def upload_fence(self, fence: Fence) -> None      # disarmed only
    def upload_mission(self, m: Mission) -> None      # disarmed only
    def read_back(self) -> tuple[Fence, list[MissionItem]]
    def verify(self, m: Mission) -> bool              # checksum equality (VAL-010)

    def arm(self) -> None                             # raises PreArmFailed(reasons)
    def disarm(self, force: bool = False) -> None
    def start_mission(self) -> None                   # AUTO
    def hold(self) -> None                            # LOITER: station-keeping
    def stop(self) -> None                            # HOLD (motors off), then disarm
    def return_home(self) -> None                     # RTL
    def manual(self) -> None                          # STEERING; adult only
    def drive(self, throttle: float, turn: float) -> None  # -1..1, send >= 5 Hz

@dataclass(frozen=True)
class HelmStatus:
    t_utc: datetime; link_ok: bool; armed: bool; mode: SrsMode
    lat: float | None; lon: float | None; heading_deg: float | None
    speed_mps: float; battery_pct: float; battery_v: float; rail_v: float
    gps_fix: int; sats: int; hdop: float; ekf_ok: bool; fence_breached: bool
    mission_seq: int | None; mission_total: int | None

HelmEvent = ModeChanged | FailsafeEvent | ArrivedHome | Breach | Text | LinkChange
Exceptions: HelmError > {NoResponse, CommandRejected(code, text), PreArmFailed(reasons),
            NotAllowedWhileArmed, TransferFailed}
"""),
           *bullets([
               "Thread-safe. Blocking calls honour the IF-02 timeouts. "
               "status() is served from a cache refreshed by the telemetry "
               "stream.",
               "stop() is idempotent and has the highest priority: it "
               "pre-empts any call in progress.",
               "Upload and parameter calls raise NotAllowedWhileArmed when "
               "armed.",
               "SrsMode maps from ArduPilot modes as in the IF-02 table. "
               "GUIDED appears only during weed-shedding and is shown as "
               "HOLD.",
           ])]
    st += verify("IF-14", [
        ("Test", "SIM", "Contract test suite run against ArduPilotHelm on "
         "SITL; the same suite is the acceptance test for any future "
         "helm")])

    # ---------------- IF-15
    st += header("IF-15")
    st += [P("One GeoJSON (RFC 7946) FeatureCollection per site, in "
             "<font name='DVM'>sites/&lt;site&gt;.geojson</font>, committed "
             "to git (FEN-002). Coordinates are [lon, lat] in WGS84."),
           table([["properties.role", "Geometry", "Other properties",
                   "Rules"],
                  ["fence_inclusion", "Polygon", "-", "Exactly one; ≤ 70 "
                   "vertices; drawn ≥ 5 m inside the waterline (FEN-003)"],
                  ["exclusion", "Polygon or Point", "radius_m (Point), "
                   "reason", "≤ 10 in total; inside the inclusion "
                   "(FEN-001, OPS-005)"],
                  ["home", "Point", "name", "≥ 1; inside the inclusion, "
                   "outside exclusions (PRE-002)"],
                  ["area", "Polygon", "name, aliases[]", "e.g. 'home bay'; "
                   "inside the inclusion"],
                  ["landmark", "Point or Polygon", "name, aliases[], "
                   "keep_out_m", "e.g. 'the island' with keep_out_m = 10; "
                   "photo stops are placed at ≥ keep_out_m"],
                  ["launch", "Point", "name, good_wind_from[] (compass "
                   "sectors, e.g. ['W', 'SW'])", "Issue C (FMEA A-19): the "
                   "checklist suggests a launch point whose wind blows "
                   "towards the bank"]],
                 [26, 26, 38, 80]),
           Spacer(1, 2 * mm),
           code("""
{"type": "FeatureCollection",
 "properties": {"site": "milton-todds-pit", "version": 3, "wifi_channel": 6,
                "max_distance_from_home_m": 100},
 "features": [
  {"type": "Feature", "properties": {"role": "home", "name": "jetty"},
   "geometry": {"type": "Point", "coordinates": [0.16xx, 52.24xx]}}, ...]}
"""),
           P("Coordinates are shown as placeholders. The real site file "
             "is drawn on the map once TBD-02 (which lake) is resolved.",
             "small")]
    st += verify("IF-15", [
        ("Test", "SIM", "Site-file linter: schema, geometric rules above, "
         "and fence round-trip through IF-02 in SITL")])

    # ---------------- IF-21
    st += header("IF-21")
    st += [code("""
sim_vehicle.py -v Rover -f motorboat-skid \\
    --custom-location=<home lat>,<home lon>,0,<heading> \\
    --add-param-file=params/boaty-mk1.parm --out=udp:127.0.0.1:14550
python -m boaty.sim.camera_stub --port 8080 --images tests/images/ducks/
"""),
           *bullets([
               "SITL presents the same MAVLink as IF-02 on UDP 14550. The "
               "camera stub implements IF-03 exactly and reads positions "
               "from SITL, so Mission Control runs unmodified with its "
               "host set to 127.0.0.1 (SWE-004).",
               "The frame name is " + tbc("IF-21", "Confirm a skid-steer "
                                         "boat frame name in the SITL "
                                         "version used (V-12).") +
               ". The parameter file is the same controlled file flashed "
               "to the real helm, plus SIM_* overrides.",
               "Fault injection for SWE-005 uses SITL simulation "
               "parameters (GPS failure, battery drain, added drag) and "
               "network impairment (dropping UDP 14550) " +
               tbc("IF-21", "Map each FS scenario to specific SIM_* "
                   "parameters for the SITL version used.") + ".",
           ])]
    st += verify("IF-21", [
        ("Demonstration", "SIM", "A full mission from voice to captain's log "
         "in simulation; every FS scenario runs in CI")])
    return st


# ======================================================================
def section_electrical():
    st = [H1("6. Electrical interfaces")]

    st += header("IF-05")
    st += [table([["Parameter", "Value"],
                  ["Protocol", "DShot300, bidirectional ('3D') ESC mode. "
                   "Fallback: PWM 1000-2000 µs, 50 Hz, neutral 1500 µs, "
                   "deadband ± 25 µs " + tbc("IF-05", "Confirm the chosen "
                                              "ESC supports DShot and 3D "
                                              "mode.")],
                  ["Channel map", "FC output 1 = left (ThrottleLeft), "
                   "output 2 = right (ThrottleRight)"],
                  ["Sense", "Positive = forward thrust on both sides"],
                  ["Wiring", "Signal + GND twisted pair, ≤ 150 mm; no power "
                   "from the ESCs to the FC"],
                  ["Loss of signal", "ESC stops the motor ≤ 1 s after "
                   "pulses stop (FS-008, V-09)"],
                  ["Update", "Helm output loop ≥ 50 Hz"]], [34, 136])]
    st += verify("IF-05", [
        ("Test", "BENCH", "Direction and mapping with props off; "
         "signal-loss stop time measured by pulling the signal lead "
         "(V-09)")])

    st += header("IF-06")
    st += [table([["Parameter", "Value"],
                  ["Voltage", "3S Li-ion: 9.0-12.6 V operating (BMS cut-off "
                   "≈ 7.5 V)"],
                  ["Current", "≤ 8 A continuous per ESC (estimate), ≤ 25 A "
                   "total peak for 100 ms " + tbc("IF-06", "Measure motor "
                                                  "current on the bench "
                                                  "and re-rate.")],
                  ["Protection", "20 A blade fuse ≤ 50 mm from the battery "
                   "positive (PWR-003)"],
                  ["Key switch", "Normally-open reed switch on the lid. "
                   "Magnet present → MOSFET on → motor rail live. Magnet "
                   "absent → gate pulled down → rail off (fails safe). "
                   "MOSFET ≥ 40 A, R<sub>DS(on)</sub> ≤ 10 mΩ."],
                  ["Rail sense", "Divider 10 kΩ / 1 kΩ to the FC's second "
                   "voltage input (≤ 1.2 V at 12.6 V). Arming blocked below "
                   "9.0 V " + tbc("IF-06", "Confirm arming can be gated on "
                                  "the second battery monitor (V-13).")],
                  ["Connectors", "XT30 per ESC; battery XT60; polarised, "
                   "with no same-type connector used for another function "
                   "(PWR-008)"],
                  ["Wire", "16 AWG battery → bus; 18 AWG bus → ESC; "
                   "silicone insulation"]], [34, 136])]
    st += verify("IF-06", [
        ("Test", "BENCH", "Key out → rail < 0.5 V within 100 ms; key in → "
         "rail = battery − 0.2 V; arming refused with key out; fuse and "
         "connector inspection")])

    st += header("IF-07")
    st += [table([["Parameter", "Value"],
                  ["Supply", "FC powered from the main bus (after the fuse "
                   "and main switch, before the key) via its own "
                   "3-6S input regulator"],
                  ["Sensing", "Analogue voltage and current from the power "
                   "module to the FC battery-monitor pins; scale factors "
                   "calibrated on the bench"],
                  ["Accuracy", "Voltage ± 1%, current ± 5% after "
                   "calibration; mAh consumed used for SoC (FS-001)"],
                  ["Also", "Second monitor = motor-rail sense (IF-06)"]],
                 [34, 136])]
    st += verify("IF-07", [
        ("Test", "BENCH", "Compare with a multimeter at 3 loads; SoC "
         "tracks a measured discharge within 5%")])

    st += header("IF-08")
    st += [table([["Parameter", "Value"],
                  ["Source", "Main bus before the key switch, so the MCP "
                   "can sync photos with motors off"],
                  ["Regulator", "Buck, 5.1 V ± 2%, ≥ 3 A continuous, "
                   "ripple ≤ 50 mV p-p, input 7-14 V"],
                  ["Connection", "Pi GPIO header pin 2 (5 V) and pin 6 "
                   "(GND), keyed 2-pin connector"],
                  ["Transients", "Output stays ≥ 4.85 V through a full "
                   "reverse-to-forward thrust step (PWR-005)"],
                  ["Shutdown", "POST /v1/shutdown (IF-03) before the main "
                   "switch is turned off; the root filesystem is read-only, "
                   "so an unplanned power cut is survivable (R-04)"]],
                 [34, 136])]
    st += verify("IF-08", [
        ("Test", "BENCH", "Scope the 5 V rail during thrust steps; 50 "
         "power-cut cycles without filesystem damage")])

    st += header("IF-09")
    st += [table([["Parameter", "Value"],
                  ["Device", "WS2812-type ring, 8 LEDs, at the mast head"],
                  ["Drive", "FC output configured as NeoPixel. 330 Ω "
                   "series resistor. Data cable ≤ 400 mm inside the mast "
                   "tube."],
                  ["Power", "5 V from the FC's 5 V pad, brightness capped "
                   "so the draw is ≤ 250 mA"],
                  ["Patterns", "ArduPilot notify patterns: armed, "
                   "failsafe, low battery. Documented in the helm spec "
                   "after bench observation (REC-004)."],
                  ["Level", "3.3 V data into 5 V LEDs " + tbc(
                      "IF-09", "Check reliable data at 3.3 V; add a level "
                      "shifter if not.")]], [34, 136])]
    st += verify("IF-09", [
        ("Test", "BENCH / LAKE", "Each state shows its pattern on the "
         "bench; visible at 100 m in overcast daylight (REC-004)")])

    st += header("IF-22")
    st += [table([["Parameter", "Value"],
                  ["Module", "u-blox M10 GNSS with magnetometer, on the "
                   "mast head ≥ 150 mm from power wiring (MEC-013)"],
                  ["GNSS", "UART at 3.3 V to an FC serial port set to GPS. "
                   "ArduPilot auto-configures the receiver (baud, "
                   "5-10 Hz)."],
                  ["Compass", "I2C to the FC; external compass with the "
                   "orientation set in parameters " + tbc(
                       "IF-22", "Confirm the compass chip, I2C address and "
                       "orientation for the chosen module.")],
                  ["Power", "5 V from the FC, ≈ 50 mA"],
                  ["Cable", "≤ 450 mm through the mast tube; the module "
                   "connector is strain-relieved at the mast head"]],
                 [34, 136])]
    st += verify("IF-22", [
        ("Test", "BENCH", "3D fix outdoors, ≥ 8 satellites, HDOP ≤ 1.5 "
         "(PRE-001); compass heading within 10° of a reference with the "
         "motors running")])
    return st


# ======================================================================
def section_hmi():
    st = [H1("7. Human-machine interface")]
    st += header("IF-12")
    st += [sub("Panel hardware (Pi 5 GPIO, BCM numbering)"),
           table([["Signal", "GPIO (pin)", "Electrical", "Behaviour"],
                  ["GO button (green, ▶)", "17 (11)", "Input, pull-up, "
                   "active-low", "Press-and-hold 1.0 ± 0.1 s (MC-004)"],
                  ["COME HOME (yellow, house)", "27 (13)", "Input, pull-up",
                   "Acts on press"],
                  ["STOP (red, ■)", "22 (15)", "Input, pull-up", "Acts on "
                   "press; edge detected ≤ 50 ms"],
                  ["TALK (blue, mic) " + tbc(
                      "IF-12", "Owner to confirm a fourth 'TALK' button: "
                      "MC-002 names three, but push-to-talk (NLI-002) needs "
                      "a trigger a 4-year-old can find.",
                      closed="Owner approved the TALK button; MC-002 now "
                      "names four buttons (SRS Issue D)"),
                   "24 (18)", "Input, pull-up", "Hold to talk, release to "
                   "send (NLI-002)"],
                  ["(GPIO 23 spare)", "23 (16)", "-", "Was the adult key "
                   "switch; replaced by the web-UI PIN (Issue D, ADD DD-17)"],
                  ["Button LEDs (4)", "5, 6, 13, 19 (29, 31, 33, 35)",
                   "Output via N-MOSFET to 5 V LEDs", "Lit = available now"]],
                 [42, 30, 44, 54]),
           P("Debounce 30 ms in software. Buttons are ≥ 30 mm arcade "
             "buttons with 5 V LEDs (MC-002).", "small"),
           F("states.png", 165, "Figure 4. Session states in the session "
             "manager (C1), which decide what each button does."),
           sub("Button behaviour by session state"),
           table([["State", "GO", "COME HOME", "STOP", "TALK"],
                  ["IDLE / DEBRIEF", "'Not yet!'", "-", "-", "Plan"],
                  ["PLAN_READY / APPROVED", "'Ask a grown-up to arm'", "-",
                   "-", "Re-plan"],
                  ["ARMED (HOLD)", "<b>Start mission</b>", "RTL", "Stop + "
                   "disarm", "-"],
                  ["MISSION", "-", "<b>RTL</b>", "<b>Stop</b>", "-"],
                  ["RETURNING", "-", "-", "<b>Stop</b>", "-"],
                  ["MANUAL (adult)", "-", "RTL", "Stop", "-"]],
                 [40, 36, 30, 30, 34]),
           P("'-' = ignored, with a short 'not now' sound. Button LEDs show "
             "which buttons do something right now.", "small"),
           sub("Audio"),
           table([["Item", "Value"],
                  ["Microphone", "USB, 16 kHz mono; captured only while TALK "
                   "is held; audio is never stored or sent"],
                  ["Speaker", "USB audio, ≈ 3 W; volume set in the UI"],
                  ["Speech in / out", "On-device STT and TTS (ADD DD-07)"]],
                 [34, 136]),
           Spacer(1, 2 * mm),
           table([["Event", "Spoken phrase (examples)"],
                  ["Plan ready", "The plan's summary_for_child, then 'Ask a "
                   "grown-up to check it'"],
                  ["Mission start", "'Off we go!'"],
                  ["Photo point", "'Taking pictures!'"],
                  ["COME HOME / RTL", "'Coming home!'"],
                  ["STOP", "'Stopping!'"],
                  ["Failsafe", "Child: 'I need to come home now.' Adult "
                   "screen: the reason (FS-012)."],
                  ["Stuck", "'I'm stuck in some weed, trying to wiggle "
                   "free.'"],
                  ["Home", "'I'm back! Let's look at the pictures.'"]],
                 [34, 136]),
           sub("Web UI"),
           *bullets([
               "Served at http://192.168.50.1:8000 (tablet on the AP) and "
               "on the usb0 address (phone). The address is spoken at "
               "start-up.",
               "Pages: Map (live), Plan (preview and approval), Checklist, "
               "Fence editor, Photos, Settings. Adult pages need the PIN.",
               "<b>Adult PIN (MC-008):</b> 6 digits, set by the owner. "
               "Unlock lasts 10 min or until the session ends. After 5 wrong "
               "entries, locked out for 5 min. The PIN is entered on the "
               "adult's device and never spoken. It unlocks software only: "
               "motor power still needs the magnetic arming key.",
               "State pushed to the browser over a WebSocket at ≥ 1 Hz "
               "(MC-005).",
           ])]
    st += verify("IF-12", [
        ("Test", "BENCH", "Automated test of the state × button table with "
         "SITL; GO hold timing; STOP detection ≤ 50 ms"),
        ("Demonstration", "POOL", "The crew uses GO, COME HOME and STOP "
         "without reading (CHD-005)")])
    return st


# ======================================================================
def section_mechanical():
    st = [H1("8. Mechanical interfaces"),
          P("Dimensions marked TBC are fixed by CAD and test prints and "
            "then entered here. Printed parts are PETG unless stated. Load "
            "cases use a design mass of 2.1 kg (boat plus 300 g payload) "
            "and a safety factor of 3.")]

    st += header("IF-16")
    st += [table([["Feature", "Definition"],
                  ["Section envelope", "90 mm wide × 100 mm deep at the "
                   "joint " + tbc("IF-16", "Final hull lines from CAD.")],
                  ["Flange", "6 mm thick; mating faces flat to 0.3 mm"],
                  ["Alignment", "2 × Ø8 mm printed dowels, 10 mm "
                   "engagement"],
                  ["Fastening", "2 × printed thumb-screws, M12 coarse "
                   "printed thread, Ø35 mm knurled knob, captive (cannot "
                   "be fully removed) so there are no small loose parts "
                   "(CHD-001)"],
                  ["Load case", "Boat supported at bow and stern only; the "
                   "joint carries 3 × design weight without separation or "
                   "cracking"],
                  ["Sealing", "Not required (foam-filled, REC-001). "
                   "Optional 1 mm EPDM gasket."]], [34, 136])]
    st += verify("IF-16", [
        ("Test", "BENCH", "Load test on two joined segments; the crew "
         "assembles a joint by hand (CHD-004)")])

    st += header("IF-17")
    st += [table([["Feature", "Definition"],
                  ["Mount", "60° dovetail, 20 mm wide × 40 mm long, on the "
                   "hull transom; 0.3 mm clearance"],
                  ["Retention", "Spring-loaded printed latch, released by "
                   "an adult with a firm two-finger press. No separate pin "
                   "(no loose parts)."],
                  ["Loads", "Thrust ≤ 10 N per pod × 3; lateral impact 20 "
                   "N at the pod tip"],
                  ["Connector", "Keyed 3-pole IP68 circular connector "
                   "(motor phases), ≥ 10 A " + tbc(
                       "IF-17", "Select the connector part number.")],
                  ["Guard", "Prop fully shrouded; an 8 mm probe cannot "
                   "touch a blade (MEC-010)"],
                  ["Swap time", "< 2 min, no tools (MEC-008)"]],
                 [34, 136])]
    st += verify("IF-17", [
        ("Test", "BENCH", "Pull test, probe test, timed swap")])

    st += header("IF-18")
    st += [table([["Feature", "Definition"],
                  ["Box", "Clip-lock food box, internal ≥ 180 × 110 × 70 mm "
                   + tbc("IF-18", "Choose the box; freeze the saddle.")],
                  ["Saddle", "Printed cradle on the crossbeam rail with 2 "
                   "over-centre printed latches; adult removal without "
                   "tools"],
                  ["Glands", "4 × PG7 (cable Ø3-6.5 mm) on the aft face, "
                   "25 mm pitch; hand-tight + ¼ turn"],
                  ["Key dock", "Printed cup on the lid over the reed switch; "
                   "the magnet key on a lanyard; lid label 'KEY'"],
                  ["Ingress", "No water after 30 min at 0.3 m (MEC-012)"]],
                 [34, 136])]
    st += verify("IF-18", [
        ("Test", "BENCH", "Submersion test with tissue indicator inside")])

    st += header("IF-19")
    st += [table([["Feature", "Definition"],
                  ["Tube", "Ø16 mm aluminium or carbon; GNSS top ≈ 450 mm "
                   "above the waterline, total height ≤ 500 mm (MEC-001)"],
                  ["Socket", "Printed, 50 mm deep, on the rail; retained by "
                   "a captive thumb-screw"],
                  ["Carries", "GNSS/compass (top), flag (top ≥ 300 mm above "
                   "the waterline), recovery hoop (Ø ≥ 60 mm internal), "
                   "LED ring"],
                  ["Loads", "50 N tow on the hoop (REC-005) → ≈ 15 N·m at "
                   "the socket; design for 30 N·m"],
                  ["Separation", "GNSS ≥ 150 mm from motor and power wiring "
                   "(MEC-013)"]], [34, 136])]
    st += verify("IF-19", [
        ("Test", "POOL", "50 N hoop pull; tow the boat by the hoop without "
         "capsize")])

    st += header("IF-20")
    st += [table([["Feature", "Definition"],
                  ["Grid", "DUPLO-compatible studs, 16.0 mm pitch, 6 × 8 "
                   "studs (96 × 128 mm)"],
                  ["Stud", "Nominal Ø9.4 mm × 4.5 mm high " + tbc(
                      "IF-20", "Tune stud diameter and height by test "
                      "prints against genuine bricks.")],
                  ["Grip", "A 2×2 brick stays on at 45° tilt and with 0.5 g "
                   "shake. A 4-year-old can remove it (MEC-009)."],
                  ["Mount", "Clips onto the box-lid frame; removable for "
                   "box access"]], [34, 136])]
    st += verify("IF-20", [
        ("Test", "BENCH", "Tilt and shake test; crew removal test")])
    return st


# ======================================================================
def build():
    A.check()
    body = (section_network() + section_software() + section_electrical() +
            section_hmi() + section_mechanical())

    st = cover("Interface Control<br/>Document",
               "Mk1 interfaces IF-01 to IF-22: definitions, timing, error "
               "handling and verification",
               [["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                ["Status", "For review by the project owner"],
                ["Parent", "BOATY-ADD-001 Issue E (interface register, "
                 "section 5)"],
                ["Content", f"{len(A.INTERFACES)} interfaces, "
                 f"{len(VERIF)} verification entries, "
                 f"{sum(1 for t in TBC if 'Closed' not in t[1])} open items "
                 "to be confirmed"]])
    st += control_and_contents(
        [["A", DATE, "First issue, for review.", "Claude (drafted)"],
         ["B", DATE, "TBC-10 closed: TALK button approved and defined in "
          "IF-12.", "Claude, owner decision"],
         ["C", DATE, "FMEA actions: B7 navigation monitor added to the "
          "IF-04 allowed-commands table; box_temp_c added to IF-03 "
          "Health; B6 over-temperature trigger; IF-15 'launch' role with "
          "wind sectors.", "Claude, FMEA Issue B"],
         ["D", DATE, "Adult unlock by PIN on the web UI replaces the panel "
          "key switch (ADD DD-17, CR-03).", "Claude, owner decision"]],
        "Review guidance: check that each interface is complete enough to "
        "build and test against. Items marked [TBC-nn] are known gaps with "
        "an owner; they're listed in section 9.")

    # ---- 1-3
    rows = [["ID", "Interface", "Between", "Type", "Owner", "Section"]]
    sec_of = {}
    for n, ids in [("4", ["IF-01", "IF-02", "IF-04", "IF-03", "IF-10",
                          "IF-11"]),
                   ("5", ["IF-13", "IF-14", "IF-15", "IF-21"]),
                   ("6", ["IF-05", "IF-06", "IF-07", "IF-08", "IF-09",
                          "IF-22"]),
                   ("7", ["IF-12"]),
                   ("8", ["IF-16", "IF-17", "IF-18", "IF-19", "IF-20"])]:
        for i in ids:
            sec_of[i] = n
    assert set(sec_of) == set(IFS), set(IFS) ^ set(sec_of)
    for i in A.INTERFACES:
        a, b = i[2], i[3]
        rows.append([f"<b>{i[0]}</b>", i[1],
                     a if a == b else f"{a} ↔ {A.EXTERNALS.get(b, b)}",
                     i[4], OWNER[i[0]], sec_of[i[0]]])
    st += [H1("1. Introduction"),
           H2("1.1 Purpose and scope"),
           P("This document defines every Mk1 interface in the ADD's "
             "interface register in enough detail to build, integrate and "
             "test each side independently. For each interface it gives the "
             "owner, the definitions (signals, messages, fields, "
             "dimensions), the timing and error behaviour, and how the "
             "interface is verified. Interfaces internal to a third-party "
             "product (ArduPilot internals, the Claude API itself) are "
             "referenced, not re-specified."),
           H2("1.2 Ownership"),
           P("Each interface has one owning subsystem. The owner maintains "
             "the definition here and approves changes. The other side "
             "conforms. A change to a definition goes through an ICD "
             "revision before implementation, and the interface's "
             "verification is re-run."),
           H2("1.3 References"),
           table([["Ref", "Document"],
                  ["[1]", "BOATY-SRS-001 Issue D; BOATY-ADD-001 Issue D; "
                   "BOATY-FMEA-001 Issue B"],
                  ["[2]", "MAVLink common message set and mission protocol "
                   "(mavlink.io)"],
                  ["[3]", "ArduPilot Rover documentation: modes, failsafes, "
                   "fence, SITL (ardupilot.org/rover)"],
                  ["[4]", "Claude API documentation: Messages API, "
                   "structured outputs, refusals and fallbacks "
                   "(platform.claude.com)"],
                  ["[5]", "RFC 7946 GeoJSON; RFC 8259 JSON; IEEE 802.11n"],
                  ["[6]", "mavlink-router (github.com/mavlink-router)"]],
                 [14, 156]),
           H2("2. Common conventions"),
           table([["Topic", "Convention"],
                  ["Units", "SI. Speed m/s, distance m, angles degrees "
                   "(0-360, true north, clockwise), voltage V, current A, "
                   "energy Wh"],
                  ["Position", "WGS84 decimal degrees. MAVLink integers are "
                   "degrees × 1e7. GeoJSON order is [lon, lat]."],
                  ["Time", "UTC everywhere; ISO 8601 strings in JSON; GNSS "
                   "time where available (SWE-008)"],
                  ["Text", "UTF-8 JSON, no trailing commas, unknown fields "
                   "ignored within a major version"],
                  ["Versioning", "Schemas carry 'schema': 'boaty.&lt;name&gt;/"
                   "&lt;major&gt;'. APIs are versioned in the path (/v1)."],
                  ["Logging", "Every interface failure is logged with a UTC "
                   "timestamp and interface ID (LOG-002)"]], [30, 140]),
           H2("3. Interface summary"),
           table(rows, [14, 42, 40, 24, 16, 16]),
           Spacer(1, 6 * mm)]
    st += body

    # ---- 9 TBC + 10 verification
    st += [Spacer(1, 6 * mm), H1("9. Items to be confirmed"),
           P("Known gaps. Each closes by the method shown and is then "
             "entered in the relevant section in the next issue."),
           table([["ID", "Item", "Interface"]] + [list(t) for t in TBC],
                 [16, 136, 18]),
           Spacer(1, 5 * mm),
           H1("10. Interface verification summary"),
           table([["Interface", "Method", "Stage", "Evidence / pass "
                   "criterion"]] + [list(v) for v in VERIF],
                 [18, 24, 18, 110])]

    doc = Doc(OUT, DOC_ID, "Interface Control Document", ISSUE)
    doc.multiBuild(st)
    print("wrote", OUT, f"({len(TBC)} TBCs, {len(VERIF)} verification rows)")


if __name__ == "__main__":
    build()
