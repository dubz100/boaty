"""C3 web UI (IF-12, MCN-D14, D16, D17, D26, D56, D61).

Served on port 8000 by Mission Control to the tablet on the boat network
and the phone on the USB tether. Standard library only, so it runs offline
on the Pi 5 with nothing to install (MCN-D07). The page is one file with no
external assets; the map is drawn from the site file, not from tiles.

    GET  /                 the page
    GET  /api/state        session snapshot (JSON)
    GET  /ws               WebSocket: the snapshot pushed at >= 1 Hz
    POST /api/instruction  {"text"}                 typed instruction
    POST /api/template     {"id", "area"}
    POST /api/button       {"button", "event"}     on-screen panel
    POST /api/unlock       {"pin"} -> {"ok", "token"}
    Adult (Authorization: Bearer <token>):
    POST /api/approve, /api/arm, /api/command {"cmd"}, /api/drive
         {"throttle", "turn"}, /api/checklist {"item", "ok", "by"},
         /api/mission {Mission v1}
"""
from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .models import Mission
from .panel import Button

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
PUSH_HZ = 2.0


def ws_accept(key: str) -> str:
    return base64.b64encode(hashlib.sha1((key + WS_GUID).encode())
                            .digest()).decode()


def ws_frame(text: str) -> bytes:
    data = text.encode()
    n = len(data)
    if n < 126:
        head = struct.pack("!BB", 0x81, n)
    elif n < 65536:
        head = struct.pack("!BBH", 0x81, 126, n)
    else:
        head = struct.pack("!BBQ", 0x81, 127, n)
    return head + data


class WebUI:
    def __init__(self, session, host: str = "0.0.0.0", port: int = 8000,
                 push_hz: float = PUSH_HZ):
        self.session, self.host, self.port = session, host, port
        self.push_hz = push_hz
        self.httpd: ThreadingHTTPServer | None = None
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    def start(self) -> "WebUI":
        ui = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *args):
                pass

            def do_GET(self):
                ui._get(self)

            def do_POST(self):
                ui._post(self)

        self.httpd = ThreadingHTTPServer((self.host, self.port), H)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    # ------------------------------------------------------------------
    def _send(self, h, code: int, obj=None, ctype="application/json"):
        body = b"" if obj is None else (
            obj if isinstance(obj, bytes) else
            json.dumps(obj, default=str).encode())
        h.send_response(code)
        h.send_header("Content-Type", ctype)
        h.send_header("Content-Length", str(len(body)))
        h.send_header("Cache-Control", "no-store")
        h.end_headers()
        h.wfile.write(body)

    def _get(self, h) -> None:
        path = h.path.split("?")[0]
        if path == "/":
            return self._send(h, 200, PAGE.encode(), "text/html; charset=utf-8")
        if path == "/api/state":
            return self._send(h, 200, self.session.snapshot())
        if path == "/ws" and h.headers.get("Upgrade", "").lower() == \
                "websocket":
            return self._ws(h)
        return self._send(h, 404, {"error": "not_found"})

    def _ws(self, h) -> None:
        key = h.headers.get("Sec-WebSocket-Key", "")
        h.send_response(101, "Switching Protocols")
        h.send_header("Upgrade", "websocket")
        h.send_header("Connection", "Upgrade")
        h.send_header("Sec-WebSocket-Accept", ws_accept(key))
        h.end_headers()
        h.wfile.flush()
        h.close_connection = True
        period = 1.0 / self.push_hz
        try:
            while not self._stop.is_set():
                h.wfile.write(ws_frame(json.dumps(self.session.snapshot(),
                                                  default=str)))
                h.wfile.flush()
                time.sleep(period)
        except (OSError, socket.error):
            return

    def _post(self, h) -> None:
        n = int(h.headers.get("Content-Length") or 0)
        try:
            body = json.loads(h.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._send(h, 400, {"error": "bad_request"})
        auth = h.headers.get("Authorization", "")
        tok = auth[7:] if auth.startswith("Bearer ") else None
        s = self.session
        path = h.path.split("?")[0]
        try:
            if path == "/api/instruction":
                text = str(body.get("text", ""))[:1000]
                threading.Thread(target=s.instruct, args=(text, "text"),
                                 daemon=True).start()
                return self._send(h, 202, {"planning": True})
            if path == "/api/template":
                out = s.choose_template(body["id"], body.get("area"))
                return self._send(h, 200, {"ok": out.ok, "child": out.child,
                                           "adult": out.adult})
            if path == "/api/button":
                b = Button(body["button"])
                ev = body.get("event", "press")
                if ev not in ("press", "held", "release"):
                    raise ValueError("event")
                s.button(b, ev)
                return self._send(h, 200, {"state": s.state.value})
            if path == "/api/unlock":
                r = s.unlock(str(body.get("pin", "")))
                return self._send(h, 200 if r.ok else 403,
                                  {"ok": r.ok, "token": r.token,
                                   "message": r.message})
            if path == "/api/approve":
                ok, msg = s.approve(tok)
                return self._send(h, 200 if ok else 409, {"ok": ok,
                                                          "message": msg})
            if path == "/api/arm":
                ok, why = s.arm(tok)
                return self._send(h, 200 if ok else 409, {"ok": ok,
                                                          "reasons": why})
            if path == "/api/command":
                ok, msg = s.command(tok, str(body.get("cmd")))
                return self._send(h, 200 if ok else 409, {"ok": ok,
                                                          "message": msg})
            if path == "/api/drive":
                s.drive(tok, float(body.get("throttle", 0)),
                        float(body.get("turn", 0)))
                return self._send(h, 200, {"ok": True})
            if path == "/api/checklist":
                sg = s.sign(tok, body["item"], bool(body.get("ok")),
                            str(body.get("by", "adult"))[:40],
                            str(body.get("note", ""))[:200])
                return self._send(h, 200, sg.__dict__)
            if path == "/api/mission":
                out = s.edit_mission(tok, Mission.model_validate(body))
                return self._send(h, 200, {"ok": out.ok, "adult": out.adult})
        except PermissionError:
            return self._send(h, 401, {"error": "adult_pin_needed"})
        except (KeyError, ValueError, TypeError) as e:
            return self._send(h, 400, {"error": "bad_request",
                                       "message": str(e)[:200]})
        return self._send(h, 404, {"error": "not_found"})


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Boaty Mission Control</title>
<style>
:root{--bg:#fff;--ink:#111;--muted:#555;--line:#ccd;--go:#1b7f3a;--home:#c98a00;
--stop:#c62828;--talk:#1d5fbf;--water:#e8f3ff;--card:#f6f7f9}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#101418;
--ink:#f2f4f7;--muted:#aab;--line:#334;--water:#12263a;--card:#1a2027}}
:root[data-theme="dark"]{--bg:#101418;--ink:#f2f4f7;--muted:#aab;--line:#334;
--water:#12263a;--card:#1a2027}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:18px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{display:flex;gap:12px;align-items:center;padding:10px 16px;
border-bottom:2px solid var(--line);flex-wrap:wrap}
h1{font-size:22px;margin:0}.pill:empty{display:none}.pill{padding:4px 10px;border-radius:99px;
background:var(--card);font-weight:700}
main{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:16px;
padding:16px}@media(max-width:800px){main{grid-template-columns:1fr}}
section{background:var(--card);border-radius:12px;padding:12px}
h2{font-size:19px;margin:4px 0 8px}svg{width:100%;height:auto;
background:var(--water);border-radius:10px}
.btns{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
button{font:inherit;font-weight:700;padding:14px 8px;border-radius:12px;
border:3px solid var(--line);background:var(--bg);color:var(--ink);
min-height:56px;cursor:pointer}button.lit{border-color:currentColor}
.go{color:var(--go)}.home{color:var(--home)}.stop{color:var(--stop)}
.talk{color:var(--talk)}.big{font-size:26px;font-weight:800}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input,select{font:inherit;padding:10px;border-radius:10px;border:2px solid
var(--line);background:var(--bg);color:var(--ink);min-width:0;flex:1}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.stat{background:var(--bg);border-radius:10px;padding:8px}
.stat b{display:block;font-size:24px}.alert{color:var(--stop);font-weight:700}
ul{padding-left:20px;margin:6px 0}.muted{color:var(--muted)}
</style></head><body>
<header><h1>Boaty</h1><span class="pill" id="state">…</span>
<span class="pill" id="mode">…</span><span class="pill" id="batt">…</span>
<span class="pill" id="link">…</span><span class="pill" id="left"></span></header>
<main>
<div>
<section><svg id="map" viewBox="0 0 400 300" role="img"
 aria-label="Map of the pond with the boat"></svg></section>
<section><h2>Panel</h2><div class="btns">
<button class="talk" data-b="TALK">TALK</button>
<button class="go" data-b="GO">GO ▶</button>
<button class="home" data-b="COME_HOME">COME HOME</button>
<button class="stop" data-b="STOP">STOP ■</button></div>
<p class="big" id="said"></p></section>
</div>
<div>
<section><h2>Plan</h2>
<div class="row"><input id="text" placeholder="Where shall Boaty go?"
 aria-label="Instruction"><button id="send">Plan</button></div>
<div class="row" id="templates"></div>
<div id="preview"></div><p id="plantext"></p><ul id="viol" class="alert"></ul>
</section>
<section><h2>Grown-ups</h2>
<div class="row"><input id="pin" type="password" inputmode="numeric"
 autocomplete="off" maxlength="6" aria-label="Adult PIN" placeholder="PIN">
<button id="unlock">Unlock</button></div>
<div class="row" style="margin-top:8px">
<button id="approve">Approve plan</button><button id="arm">Arm</button>
<button data-c="hold">Hold</button><button data-c="rtl">Come home</button>
<button data-c="manual">Manual</button><button data-c="resume">Resume</button>
<button class="stop" data-c="stop">Stop</button></div>
<ul id="checklist"></ul><ul id="blockers" class="alert"></ul>
<ul id="alerts" class="alert"></ul></section>
</div></main>
<script>
let tok=null,S=null;const $=id=>document.getElementById(id);
async function post(p,b){const h={'Content-Type':'application/json'};
if(tok)h.Authorization='Bearer '+tok;const r=await fetch(p,{method:'POST',
headers:h,body:JSON.stringify(b||{})});let j={};try{j=await r.json()}catch(e){}
if(r.status==401){tok=null}return j}
document.querySelectorAll('[data-b]').forEach(el=>{const b=el.dataset.b;
if(b=='GO'){let t;el.onpointerdown=()=>{post('/api/button',{button:b,event:'press'});
t=setTimeout(()=>post('/api/button',{button:b,event:'held'}),1000)};
el.onpointerup=el.onpointerleave=()=>clearTimeout(t)}
else if(b=='TALK'){el.onpointerdown=()=>post('/api/button',{button:b,event:'press'});
el.onpointerup=()=>post('/api/button',{button:b,event:'release'})}
else el.onclick=()=>post('/api/button',{button:b,event:'press'})});
document.querySelectorAll('[data-c]').forEach(el=>el.onclick=()=>
post('/api/command',{cmd:el.dataset.c}));
$('send').onclick=()=>{post('/api/instruction',{text:$('text').value});$('text').value=''};
$('unlock').onclick=async()=>{const j=await post('/api/unlock',{pin:$('pin').value});
$('pin').value='';tok=j.ok?j.token:null;if(!j.ok)alert(j.message)};
$('approve').onclick=async()=>{const j=await post('/api/approve');if(!j.ok)alert(j.message||'PIN needed')};
$('arm').onclick=async()=>{const j=await post('/api/arm');if(!j.ok)alert((j.reasons||['PIN needed']).join('\n'))};
function proj(s){const pts=s.site.fence.concat([s.site.home]);let la=pts.map(p=>p[0]),
lo=pts.map(p=>p[1]);const k=Math.cos(la[0]*Math.PI/180),x0=Math.min(...lo)*k,
x1=Math.max(...lo)*k,y0=Math.min(...la),y1=Math.max(...la),
sc=Math.min(380/(x1-x0),280/(y1-y0));return p=>[10+(p[1]*k-x0)*sc,290-(p[0]-y0)*sc]}
function draw(s){const P=proj(s),poly=a=>a.map(p=>P(p).join(',')).join(' ');
let g=`<polygon points="${poly(s.site.fence)}" fill="none" stroke="#1d5fbf"
 stroke-width="2" stroke-dasharray="6 4"/>`;
s.site.exclusions.forEach(e=>g+=`<polygon points="${poly(e)}" fill="#c6282855"/>`);
s.site.circles.forEach(c=>{const [x,y]=P(c),[x2]=P([c[0],c[1]+c[2]/(111320*Math.cos(c[0]*Math.PI/180))]);
g+=`<circle cx="${x}" cy="${y}" r="${Math.abs(x2-x)}" fill="#c6282855"/>`});
if(s.plan&&s.plan.points.length){g+=`<polyline points="${poly([s.site.home].concat(s.plan.points.map(p=>[p[0],p[1]])).concat([s.site.home]))}"
 fill="none" stroke="#c98a00" stroke-width="2"/>`;
s.plan.points.filter(p=>p[2]=='photo_point').forEach(p=>{const [x,y]=P(p);g+=`<circle cx="${x}" cy="${y}" r="5" fill="#c98a00"/>`})}
if(s.track.length>1)g+=`<polyline points="${poly(s.track)}" fill="none" stroke="#e8590c" stroke-width="3"/>`;
const [hx,hy]=P(s.site.home);g+=`<rect x="${hx-6}" y="${hy-6}" width="12" height="12" fill="#1b7f3a"/>`;
const b=s.helm.lat!=null?s.helm:s.last_known;if(b&&b.lat!=null){const [x,y]=P([b.lat,b.lon]);
const h=(b.heading||0);g+=`<g transform="translate(${x},${y}) rotate(${h})"><polygon points="0,-11 7,8 -7,8"
 fill="${s.helm.link_ok?'#111':'#888'}" stroke="#fff" stroke-width="1.5"/></g>`}
$('map').innerHTML=g}
function render(s){S=s;$('state').textContent=s.state;$('mode').textContent=s.helm.mode;
$('batt').textContent='🔋 '+Math.round(s.helm.battery_pct)+'%';
$('link').textContent=s.helm.link_ok?'link ok':'NO LINK';
$('left').textContent=s.time_left_s!=null?Math.ceil(s.time_left_s/60)+' min left':'';
document.querySelectorAll('[data-b]').forEach(el=>el.classList.toggle('lit',!!s.leds[el.dataset.b]));
$('said').textContent=s.said.length?s.said[s.said.length-1]:'';
const p=s.plan;$('preview').innerHTML=p&&p.preview?`<div class="stats">
<div class="stat">Time<b>${Math.ceil(p.preview.duration_s/60)} min</b></div>
<div class="stat">Distance<b>${Math.round(p.preview.distance_m)} m</b></div>
<div class="stat">Photos<b>${p.preview.photos}</b></div>
<div class="stat">Furthest from home<b>${Math.round(p.preview.furthest_m)} m</b></div></div>`:'';
$('plantext').textContent=p?p.child:'';
$('viol').innerHTML=p?p.violations.map(v=>`<li>${v.rule}: ${v.message_for_adult}</li>`).join(''):'';
const ar=$('area')?$('area').value:null;
$('templates').innerHTML=(p&&p.offer_templates||s.state=='IDLE')?s.templates.map(t=>
`<button onclick="post('/api/template',{id:'${t.id}',area:$('area').value})">${t.name}</button>`).join('')+
`<select id="area">${s.templates[0].areas.map(a=>`<option ${a==ar?'selected':''}>${a}</option>`).join('')}</select>`:'';
$('checklist').innerHTML=Object.entries(s.checklist).map(([k,c])=>`<li>
<label><input type="checkbox" ${c.ok?'checked':''} onchange="post('/api/checklist',
{item:'${k}',ok:this.checked})"> ${c.label}</label>${c.by?` <span class="muted">(${c.by})</span>`:''}</li>`).join('');
$('blockers').innerHTML=s.arm_blockers.map(b=>`<li>${b}</li>`).join('');
$('alerts').innerHTML=s.alerts.slice(-4).map(a=>`<li>${a}</li>`).join('');draw(s)}
function connect(){const ws=new WebSocket((location.protocol=='https:'?'wss':'ws')+'://'+location.host+'/ws');
ws.onmessage=e=>render(JSON.parse(e.data));ws.onclose=()=>setTimeout(connect,1000)}
fetch('/api/state').then(r=>r.json()).then(render);connect();
</script></body></html>
"""
