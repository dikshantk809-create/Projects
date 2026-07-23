#!/usr/bin/env python3
"""WorkLens AI - CENTRAL CLOUD (HQ dashboard).

Ek jagah se SAARE offices ka attendance + productivity dekho.
- Har office apne PC par edge app (app.py) chalata hai (AI wahin chalti hai).
- Har office apna data is HQ server ko bhejta hai (push).
- HQ ek hi screen par sab offices live dikhata hai.

Single-file Flask app (edge jaisa hi). Pehle laptop par test karo (port 8080),
phir kisi saste server par deploy karke PERMANENT URL pao (guide dekho).
"""
from __future__ import annotations

import os
import json
import secrets
import datetime as dt
import sqlite3
from contextlib import contextmanager

from flask import (Flask, request, jsonify, session, redirect,
                   render_template_string)

import accounts as A

DB = os.path.abspath(os.environ.get("WL_CLOUD_DB", "cloud.db"))
ACCT_DB = os.path.abspath(os.environ.get("WL_ACCOUNTS_DB", "cloud_accounts.db"))
ADMIN_PW = os.environ.get("WL_ADMIN_PASSWORD", "admin123")
ORG_NAME = os.environ.get("WL_ORG", "My Company")
PORT = int(os.environ.get("WL_PORT", "8080"))
ONLINE_SECS = 90          # office "online" agar itne second me data bheja ho


@contextmanager
def _db():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def init():
    A.init_db(ACCT_DB)
    if A.ensure_admin(ACCT_DB, "admin", ADMIN_PW, ORG_NAME):
        print(f"[cloud] HQ admin banaya - login: admin / (your WL_ADMIN_PASSWORD)")
    with _db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sites(
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id    INTEGER NOT NULL,
            name      TEXT NOT NULL,
            token     TEXT UNIQUE NOT NULL,
            created   TEXT NOT NULL,
            last_seen TEXT DEFAULT '',
            persons   INTEGER DEFAULT 0,
            phones    INTEGER DEFAULT 0,
            payload   TEXT DEFAULT '')""")


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


@app.before_request
def _guard():
    p = request.path
    if p.startswith("/login") or p.startswith("/static") or p.startswith("/api/ingest"):
        return
    if not session.get("auth"):
        return redirect("/login")


def _is_admin():
    return session.get("role") in ("owner", "admin")


# ---------------- auth ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        pw = request.form.get("password") or ""
        user = A.verify(ACCT_DB, u, pw)
        if user:
            session.update(auth=True, uid=user["id"], username=user["username"],
                           role=user["role"], org_id=user["org_id"], org_name=user["org_name"])
            return redirect("/")
        err = "Galat username ya password."
    return render_template_string(LOGIN, err=err)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- office (site) management ----------------
@app.route("/add_site", methods=["POST"])
def add_site():
    if not _is_admin():
        return jsonify({"ok": False, "msg": "Sirf admin/owner office add kar sakta hai."})
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "msg": "Office ka naam likho."})
    token = secrets.token_hex(16)
    with _db() as c:
        c.execute("""INSERT INTO sites(org_id, name, token, created) VALUES(?,?,?,?)""",
                  (session.get("org_id"), name, token, _now()))
    return jsonify({"ok": True, "msg": f"Office '{name}' add ho gaya.", "token": token})


@app.route("/delete_site", methods=["POST"])
def delete_site():
    if not _is_admin():
        return jsonify({"ok": False, "msg": "Sirf admin/owner office hata sakta hai."})
    d = request.get_json(silent=True) or {}
    with _db() as c:
        c.execute("DELETE FROM sites WHERE id=? AND org_id=?", (int(d.get("id", 0)), session.get("org_id")))
    return jsonify({"ok": True, "msg": "Office hata diya."})


@app.route("/api/sites")
def api_sites():
    org_id = session.get("org_id")
    out = []
    now = dt.datetime.now()
    with _db() as c:
        rows = c.execute("SELECT * FROM sites WHERE org_id=? ORDER BY id", (org_id,)).fetchall()
    for r in rows:
        online = False
        if r["last_seen"]:
            try:
                online = (now - dt.datetime.fromisoformat(r["last_seen"])).total_seconds() < ONLINE_SECS
            except Exception:
                online = False
        try:
            today = json.loads(r["payload"]) if r["payload"] else {}
        except Exception:
            today = {}
        out.append({"id": r["id"], "name": r["name"], "online": online,
                    "last_seen": r["last_seen"], "persons": r["persons"],
                    "phones": r["phones"], "today": today,
                    "token": r["token"] if _is_admin() else ""})
    totals = {"sites": len(out), "online": sum(1 for s in out if s["online"]),
              "persons": sum(s["persons"] for s in out if s["online"]),
              "phones": sum(s["phones"] for s in out if s["online"])}
    return jsonify({"ok": True, "sites": out, "totals": totals,
                    "me": {"username": session.get("username", ""), "role": session.get("role", ""),
                           "org": session.get("org_name", ""), "is_admin": _is_admin()}})


# ---------------- ingest (offices push here) ----------------
@app.route("/api/ingest", methods=["POST"])
def ingest():
    token = request.headers.get("X-Token", "") or (request.get_json(silent=True) or {}).get("token", "")
    d = request.get_json(silent=True) or {}
    with _db() as c:
        s = c.execute("SELECT id FROM sites WHERE token=?", (token,)).fetchone()
        if not s:
            return jsonify({"ok": False, "msg": "bad token"}), 401
        c.execute("UPDATE sites SET last_seen=?, persons=?, phones=?, payload=? WHERE id=?",
                  (_now(), int(d.get("persons", 0) or 0), int(d.get("phones", 0) or 0),
                   json.dumps(d.get("today", {}))[:20000], s["id"]))
    return jsonify({"ok": True})


@app.route("/")
def index():
    return HTML


LOGIN = """<!doctype html><html><head><meta charset="utf-8"><title>WorkLens AI - HQ</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#0f1623;font-family:Arial}
.box{background:#172033;padding:28px;border-radius:14px;border:1px solid #2a3550;width:300px}
h1{color:#e8edf5;font-size:18px;margin:0 0 2px} p{color:#9db4e0;font-size:12px;margin:0 0 16px}
input{width:100%;padding:11px;border-radius:8px;border:1px solid #2a3550;background:#0f1623;color:#fff;font-size:15px;box-sizing:border-box;margin-bottom:10px}
button{width:100%;padding:11px;border:0;border-radius:8px;background:#2f5597;color:#fff;font-size:15px;font-weight:bold;cursor:pointer}
.err{color:#ff9b9b;font-size:13px;margin-top:10px}</style></head>
<body><form class="box" method="POST" action="/login">
<h1>WorkLens AI &mdash; HQ</h1><p>Saare offices, ek jagah</p>
<input name="username" placeholder="Username (jaise admin)" value="admin" autofocus>
<input type="password" name="password" placeholder="Password">
<button type="submit">Enter</button>
<div class="err">{{err}}</div>
</form></body></html>"""


HTML = """<!doctype html><html><head><meta charset="utf-8"><title>WorkLens AI - HQ</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box} body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#0f1623;color:#e8edf5}
header{background:#1f3864;padding:14px 20px;font-size:20px;font-weight:bold;display:flex;justify-content:space-between;align-items:center}
header a{color:#9db4e0;font-size:13px;text-decoration:none}
.wrap{padding:18px;max-width:1100px;margin:0 auto}
.totals{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:18px}
.tot{flex:1;min-width:150px;background:#172033;border:1px solid #2a3550;border-radius:12px;padding:14px;text-align:center}
.tot b{display:block;font-size:30px;color:#5da0ff} .tot span{font-size:13px;color:#9db4e0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.site{background:#172033;border:1px solid #2a3550;border-radius:12px;padding:14px}
.site h3{margin:0 0 4px;font-size:16px;display:flex;justify-content:space-between;align-items:center}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px}
.on{background:#3fd07a}.off{background:#6b7a99}
.row{display:flex;gap:10px;margin:10px 0}
.stat{flex:1;background:#0f1623;border-radius:8px;padding:8px;text-align:center}
.stat b{display:block;font-size:20px}.stat span{font-size:11px;color:#9db4e0}
.muted{color:#6b7a99;font-size:12px} ul{list-style:none;margin:8px 0 0;padding:0}
li{padding:5px 4px;border-bottom:1px solid #222d44;font-size:13px;display:flex;justify-content:space-between}
.card{background:#172033;border:1px solid #2a3550;border-radius:12px;padding:14px;margin-bottom:18px}
input{width:100%;padding:10px;border-radius:8px;border:1px solid #2a3550;background:#0f1623;color:#fff;font-size:15px}
button{margin-top:10px;padding:10px 16px;border:0;border-radius:8px;background:#2f5597;color:#fff;font-weight:bold;cursor:pointer}
.tok{font-family:monospace;font-size:12px;color:#9ff0ad;word-break:break-all;background:#0f1623;padding:8px;border-radius:6px;margin-top:6px}
.del{background:#7a1f1f;padding:4px 12px;font-size:12px;margin:0}
</style></head><body>
<header><span>WorkLens <span style="color:#5da0ff">AI</span> &mdash; HQ <small style="font-weight:400;font-size:12px;color:#9db4e0;margin-left:6px">all offices, one place</small></span>
<span><span id="who" style="color:#9db4e0;font-size:13px;margin-right:14px"></span><a href="/logout">logout</a></span></header>
<div class="wrap">
  <div class="totals">
    <div class="tot"><b id="t_sites">0</b><span>offices</span></div>
    <div class="tot"><b id="t_online">0</b><span>online now</span></div>
    <div class="tot"><b id="t_persons">0</b><span>log abhi</span></div>
    <div class="tot"><b id="t_phones">0</b><span>phone abhi</span></div>
  </div>
  <div class="card" id="addcard" style="display:none">
    <h2 style="margin:0 0 10px;font-size:15px;color:#9db4e0">Naya office add karo</h2>
    <input id="sname" placeholder="Office ka naam, jaise Delhi Branch">
    <button onclick="addSite()">Add office (token milega)</button>
    <div id="amsg" style="font-size:13px;color:#9db4e0;margin-top:8px"></div>
    <div id="atok"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div id="empty" class="muted" style="display:none;padding:20px">Abhi koi office add nahi. Upar se ek office add karo, token copy karke us office ke run_app.bat me daalo.</div>
</div>
<script>
let shownAdd=false;
function fmt(ts){ if(!ts) return 'kabhi nahi'; try{return new Date(ts).toLocaleString();}catch(e){return ts;} }
async function tick(){
  try{
    const s=await (await fetch('/api/sites')).json();
    if(!s.ok) return;
    document.getElementById('who').textContent = s.me.username ? (s.me.username+' ('+s.me.role+')'+(s.me.org?' - '+s.me.org:'')) : '';
    document.getElementById('t_sites').textContent=s.totals.sites;
    document.getElementById('t_online').textContent=s.totals.online;
    document.getElementById('t_persons').textContent=s.totals.persons;
    document.getElementById('t_phones').textContent=s.totals.phones;
    if(s.me.is_admin && !shownAdd){shownAdd=true;document.getElementById('addcard').style.display='block';}
    const g=document.getElementById('grid'); g.innerHTML='';
    document.getElementById('empty').style.display = s.sites.length? 'none':'block';
    s.sites.forEach(st=>{
      const ppl = st.today && st.today.people ? st.today.people : {};
      let top=''; let names=Object.keys(ppl);
      if(names.length){ names.sort((a,b)=>(ppl[b].score||0)-(ppl[a].score||0));
        top = names.slice(0,3).map(n=>'<li><span>'+n+'</span><span>'+(ppl[n].score||0)+'%</span></li>').join(''); }
      const d=document.createElement('div'); d.className='site';
      d.innerHTML='<h3><span><span class="dot '+(st.online?'on':'off')+'"></span>'+st.name+'</span>'+
        (st.token?'<button class="del" onclick="delSite('+st.id+",'"+st.name.replace(/'/g,"")+"'"+')">remove</button>':'')+'</h3>'+
        '<div class="muted">'+(st.online?'online':'offline')+' &middot; last: '+fmt(st.last_seen)+'</div>'+
        '<div class="row"><div class="stat"><b>'+st.persons+'</b><span>log abhi</span></div>'+
        '<div class="stat"><b>'+st.phones+'</b><span>phone abhi</span></div>'+
        '<div class="stat"><b>'+names.length+'</b><span>aaj dikhe</span></div></div>'+
        (top?('<div class="muted">Aaj top productive:</div><ul>'+top+'</ul>'):'<div class="muted">Aaj ka data abhi nahi.</div>')+
        (st.token?('<div class="muted" style="margin-top:8px">Office token (run_app.bat me daalo):</div><div class="tok">'+st.token+'</div>'):'');
      g.appendChild(d);
    });
  }catch(e){}
}
async function addSite(){
  const n=document.getElementById('sname').value.trim(); const m=document.getElementById('amsg');
  if(!n){m.textContent='Office ka naam likho.';return;}
  m.textContent='Add kar raha hu...';
  try{const j=await (await fetch('/add_site',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})})).json();
    m.textContent=j.msg;
    if(j.ok){document.getElementById('sname').value='';
      document.getElementById('atok').innerHTML='<div class="muted" style="margin-top:8px">Is office ka token (copy karke us office ke run_app.bat me AICAM_CLOUD_TOKEN me daalo):</div><div class="tok">'+j.token+'</div>';
      tick();}
  }catch(e){m.textContent='Error - dobara try karo';}
}
async function delSite(id,name){
  if(!confirm("'"+name+"' office hata du?")) return;
  try{await fetch('/delete_site',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})}); tick();}catch(e){}
}
setInterval(tick,3000); tick();
</script></body></html>"""


if __name__ == "__main__":
    init()
    print(f"[cloud] WorkLens AI HQ -> http://localhost:{PORT}   (login: admin / WL_ADMIN_PASSWORD)")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
