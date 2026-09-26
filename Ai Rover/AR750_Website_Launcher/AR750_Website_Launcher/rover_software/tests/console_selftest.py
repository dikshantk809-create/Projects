"""End to end check of the AR-750 console against the real server.

Run it from the menu: AR-750.bat, choice 4. It starts a throwaway copy of the
rover on port 8091 with its own empty data folder, so nothing you have set up
is touched - the login is back to admin / agrirover for that one run - checks
every URL and every button, writes the report, and shuts the copy down again.

It checks every URL the console's front end actually calls, and every field the
front end actually reads out of the answers, then writes _selftest_report.txt.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import socket
import ssl  # noqa: F401  (imported so a proxy-less urllib import never trips)
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:%s" % (sys.argv[1] if len(sys.argv) > 1 else "8091")
HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "last_selftest_report.txt")

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

lines = []
passed = failed = 0


def say(mark, name, detail=""):
    global passed, failed
    if mark == "ok":
        passed += 1
        lines.append("  PASS  %-34s %s" % (name, detail))
    else:
        failed += 1
        lines.append("  FAIL  %-34s %s" % (name, detail))


def get(path, want_json=True, limit=None):
    req = urllib.request.Request(BASE + path, headers={"Accept": "*/*"})
    with opener.open(req, timeout=20) as r:
        code = r.status
        raw = r.read(limit) if limit else r.read()
    if want_json:
        return code, json.loads(raw.decode("utf-8"))
    return code, raw


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=20) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def need(obj, keys, where):
    """Every key the console actually reads must be present."""
    missing = [k for k in keys if k not in obj]
    if missing:
        say("no", where, "missing: " + ", ".join(missing))
    else:
        say("ok", where, "%d fields" % len(keys))
    return not missing


def check(name, fn):
    try:
        fn()
    except Exception as e:
        say("no", name, "%s: %s" % (type(e).__name__, e))


# --------------------------------------------------------------- the checks
lines.append("AR-750 console self test")
lines.append("run at %s against %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), BASE))
lines.append("")
lines.append("SIGNING IN")


def t_health():
    code, j = get("/api/health")
    say("ok" if code == 200 and j.get("ok") else "no", "GET /api/health", str(j))


def t_login_page():
    code, raw = get("/login", want_json=False)
    ok = code == 200 and b"AgriRover" in raw and b"/static/style.css" in raw
    say("ok" if ok else "no", "GET /login", "%d, %d bytes" % (code, len(raw)))


def t_login():
    code, j = post("/api/login", {"username": "admin", "password": "agrirover"})
    say("ok" if j.get("ok") else "no", "POST /api/login", str(j)[:90])


def t_index():
    code, raw = get("/", want_json=False)
    ok = (code == 200 and b'id="p-live"' in raw and b'id="p-alerts"' in raw
          and b'/static/app.js' in raw)
    say("ok" if ok else "no", "GET / (the console)", "%d, %d bytes" % (code, len(raw)))


def t_static():
    for f, needle in (("style.css", b"--amber"), ("app.js", b"function draw"),
                      ("charts.js", b"global.Chart")):
        code, raw = get("/static/" + f, want_json=False)
        ok = code == 200 and needle in raw
        say("ok" if ok else "no", "GET /static/" + f, "%d, %d bytes" % (code, len(raw)))


for f in (t_health, t_login_page, t_login, t_index, t_static):
    check(f.__name__, f)

lines.append("")
lines.append("WHAT THE LIVE PAGE READS")


def t_state():
    code, s = get("/api/state")
    need(s, ["mode", "estop", "estop_reason", "sim", "spray_armed", "auto_spray",
             "lamps_on", "rc_live", "drive", "telemetry", "steering", "drive_hw",
             "boom", "probe_hw", "mission", "pending", "plants", "alerts", "log",
             "ai_ready", "ai_reason", "recording", "returning", "speed_limit",
             "next_patrol", "fitted"], "/api/state top level")
    need(s.get("telemetry", {}),
         ["battery_v", "battery_pct", "current_a", "soil_pct", "tank_pct",
          "tank_ml", "heading_deg", "speed_mps", "distance_m", "x_m", "y_m",
          "range_front_cm", "turn_radius_mm", "cpu_temp_c", "uptime_s",
          "odometry_measured"], "  telemetry")
    need(s.get("steering", {}),
         ["max_wheel_deg", "min_turn_radius_mm", "turning_circle_mm"], "  steering")
    need(s.get("boom", {}),
         ["pump_on", "sections", "used_ml", "remaining_ml", "duty",
          "target_l_per_ha"], "  boom")
    need(s.get("probe_hw", {}), ["state", "moving", "travel_mm", "fitted"],
         "  probe_hw")
    need(s.get("drive_hw", {}), ["driver", "steer_us"], "  drive_hw")
    need(s.get("mission", {}),
         ["running", "step", "plants_done", "plants_target", "sprayed_ml",
          "message"], "  mission")
    say("ok", "  mode is", str(s.get("mode")) + ", sim=" + str(s.get("sim")))


def t_ws():
    """The live path. If this fails the page falls back to polling, which the
    link chip says out loud, so it is worth knowing which one you are on."""
    import base64 as b64
    host, port = "127.0.0.1", int(BASE.rsplit(":", 1)[1])
    cookie = "; ".join("%s=%s" % (c.name, c.value) for c in jar)
    key = b64.b64encode(os.urandom(16)).decode()
    req = ("GET /ws HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\nCookie: %s\r\n\r\n"
           % (host, port, key, cookie))
    s = socket.create_connection((host, port), timeout=15)
    s.sendall(req.encode())
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = s.recv(4096)
        if not chunk:
            break
        head += chunk
    if b"101" not in head.split(b"\r\n")[0]:
        s.close()
        say("no", "WS /ws handshake", head.split(b"\r\n")[0].decode(errors="replace"))
        return
    say("ok", "WS /ws handshake", "101 Switching Protocols")
    # read one frame and make sure it really is a snapshot
    body = head.split(b"\r\n\r\n", 1)[1]
    deadline = time.time() + 8
    while len(body) < 4 and time.time() < deadline:
        body += s.recv(65536)
    if len(body) < 2:
        s.close()
        say("no", "WS /ws first frame", "nothing arrived in 8 s")
        return
    ln = body[1] & 0x7F
    off = 2
    if ln == 126:
        ln = int.from_bytes(body[2:4], "big")
        off = 4
    elif ln == 127:
        ln = int.from_bytes(body[2:10], "big")
        off = 10
    while len(body) < off + ln and time.time() < deadline:
        body += s.recv(65536)
    s.close()
    try:
        snap = json.loads(body[off:off + ln].decode("utf-8"))
        say("ok", "WS /ws first frame",
            "%d bytes, mode=%s" % (ln, snap.get("mode")))
    except Exception as e:
        say("no", "WS /ws first frame", str(e))


def t_cam():
    """Only the first few KB: it is an endless multipart stream.

    JPEG when OpenCV is installed, PNG when it is not - both are pictures."""
    code, raw = get("/cam/front", want_json=False, limit=9000)
    kind = ("JPEG" if b"\xff\xd8\xff" in raw
            else "PNG" if b"\x89PNG" in raw else "nothing")
    ok = code == 200 and b"--frame" in raw and kind != "nothing"
    say("ok" if ok else "no", "GET /cam/front",
        "%d, %s in the first %d bytes" % (code, kind, len(raw)))


for f in (t_state, t_ws, t_cam):
    check(f.__name__, f)

lines.append("")
lines.append("EVERY OTHER PAGE")


def t_field():
    code, j = get("/api/field")
    say("ok" if j.get("ok") else "no", "GET /api/field",
        "%d plants" % len(j.get("plants", [])))


def t_history():
    code, j = get("/api/history?days=14")
    ok = "days" in j and "problems" in j
    say("ok" if ok else "no", "GET /api/history",
        "%d days, %d problem kinds" % (len(j.get("days", [])),
                                       len(j.get("problems", []))))


def t_samples():
    code, j = get("/api/samples?hours=2")
    rows = j.get("samples", [])
    say("ok" if "samples" in j else "no", "GET /api/samples", "%d rows" % len(rows))
    if rows:
        need(rows[0], ["ts", "battery_v", "battery_pct", "soil_pct", "tank_pct"],
             "  a sample row")


def t_missions():
    code, j = get("/api/missions")
    say("ok" if j.get("ok") else "no", "GET /api/missions",
        "%d runs" % len(j.get("missions", [])))


def t_recordings():
    code, j = get("/api/recordings")
    say("ok" if j.get("ok") else "no", "GET /api/recordings",
        "%d recordings" % len(j.get("recordings", [])))


def t_alerts():
    code, j = get("/api/alerts")
    say("ok" if j.get("ok") else "no", "GET /api/alerts  (new Alerts page)",
        "%d alerts" % len(j.get("alerts", [])))


def t_photos():
    code, j = get("/api/photos?limit=400")
    say("ok" if j.get("ok") else "no", "GET /api/photos  (new gallery)",
        "%d photos" % len(j.get("photos", [])))


def t_me():
    code, j = get("/api/me")
    say("ok" if j.get("ok") else "no", "GET /api/me",
        "signed in as " + str(j.get("user", {}).get("name")))


def t_patrols():
    code, j = get("/api/patrols")
    ok = "patrols" in j and "day_names" in j
    say("ok" if ok else "no", "GET /api/patrols",
        "%d patrols" % len(j.get("patrols", [])))


def t_settings():
    code, j = get("/api/settings")
    need(j, ["settings", "user", "fitted", "why", "steering"], "GET /api/settings")
    st = j.get("settings", {})
    groups = ["drive.", "boom.", "probe.", "ai.", "safety.", "record.", "notify."]
    have = [g for g in groups if any(k.startswith(g) for k in st)]
    say("ok" if len(have) == len(groups) else "no", "  settings groups",
        "%d of %d, %d settings" % (len(have), len(groups), len(st)))


def t_csv():
    code, raw = get("/api/report.csv", want_json=False)
    say("ok" if code == 200 else "no", "GET /api/report.csv",
        "%d, %d bytes" % (code, len(raw)))


def t_zip():
    code, raw = get("/api/photoset.zip", want_json=False)
    ok = code == 200 and raw[:2] == b"PK"
    say("ok" if ok else "no", "GET /api/photoset.zip", "%d, %d bytes" % (code, len(raw)))


for f in (t_field, t_history, t_samples, t_missions, t_recordings, t_alerts,
          t_photos, t_me, t_patrols, t_settings, t_csv, t_zip):
    check(f.__name__, f)

lines.append("")
lines.append("BUTTONS THAT ACTUALLY DO SOMETHING")


def t_commands():
    for cmd, args in [("mode", {"mode": "IDLE"}), ("speed_limit", {"value": 0.5}),
                      ("lamps", {"on": True}), ("lamps", {"on": False}),
                      ("probe_soil", {}), ("mark_home", {}),
                      ("spray_arm", {"on": False}), ("clear_alerts", {}),
                      ("record", {"on": False})]:
        code, j = post("/api/command", {"cmd": cmd, "args": args})
        say("ok" if j.get("ok") else "no", "POST command " + cmd, str(j)[:70])


def t_estop_cycle():
    code, j = post("/api/command", {"cmd": "estop", "args": {"reason": "self test"}})
    say("ok" if j.get("ok") else "no", "POST command estop", str(j)[:60])
    code, s = get("/api/state")
    say("ok" if s.get("estop") else "no", "  state says it stopped",
        "estop=%s, mode=%s" % (s.get("estop"), s.get("mode")))
    code, j = post("/api/command", {"cmd": "clear_estop", "args": {}})
    code, s = get("/api/state")
    say("ok" if not s.get("estop") else "no", "  and it clears again",
        "estop=%s, mode=%s" % (s.get("estop"), s.get("mode")))


def t_unknown_command():
    code, j = post("/api/command", {"cmd": "definitely_not_a_command", "args": {}})
    say("ok" if j.get("ok") is False else "no", "unknown command is refused",
        str(j)[:70])


def t_patrol_roundtrip():
    code, j = post("/api/patrols", {"name": "_selftest", "at": "05:00",
                                    "days": "0,1", "plants": 3, "spray": False,
                                    "enabled": True})
    pid = j.get("id")
    say("ok" if pid else "no", "POST /api/patrols (add)", "id=%s" % pid)
    code, j = get("/api/patrols")
    found = [p for p in j.get("patrols", []) if p.get("name") == "_selftest"]
    say("ok" if found else "no", "  it comes back in the list",
        "%d patrols now" % len(j.get("patrols", [])))
    if pid:
        post("/api/patrols", {"delete": pid})
        code, j = get("/api/patrols")
        gone = not [p for p in j.get("patrols", []) if p.get("name") == "_selftest"]
        say("ok" if gone else "no", "  and deletes again", "")


def t_settings_write():
    code, j = post("/api/settings", {"changes": {"drive.speed_limit": 0.55}})
    ok = j.get("ok") and not j.get("refused")
    say("ok" if ok else "no", "POST /api/settings (a real value)", str(j.get("refused")))
    code, j = post("/api/settings", {"changes": {"drive.speed_limit": 99}})
    say("ok" if j.get("refused") else "no", "  and an out of range one is refused",
        str(j.get("refused"))[:70])


def t_auth_wall():
    """Signed out, nothing private may answer."""
    plain = urllib.request.build_opener()
    for path in ("/api/state", "/api/field", "/api/settings"):
        try:
            plain.open(BASE + path, timeout=10)
            say("no", "signed out " + path, "ANSWERED WITHOUT A LOGIN")
        except urllib.error.HTTPError as e:
            say("ok" if e.code == 401 else "no", "signed out " + path,
                "%d" % e.code)
        except Exception as e:
            say("no", "signed out " + path, str(e))


def ws_open():
    """A signed-in websocket, handshake done. Returns the socket."""
    import base64 as b64
    host, port = "127.0.0.1", int(BASE.rsplit(":", 1)[1])
    cookie = "; ".join("%s=%s" % (c.name, c.value) for c in jar)
    key = b64.b64encode(os.urandom(16)).decode()
    s = socket.create_connection((host, port), timeout=15)
    s.sendall(("GET /ws HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
               "Sec-WebSocket-Version: 13\r\nCookie: %s\r\n\r\n"
               % (host, port, key, cookie)).encode())
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = s.recv(4096)
        if not chunk:
            break
        head += chunk
    if b"101" not in head.split(b"\r\n")[0]:
        s.close()
        raise RuntimeError(head.split(b"\r\n")[0].decode(errors="replace"))
    return s


def ws_send(s, obj):
    """One masked text frame, the way a browser sends it."""
    data = json.dumps(obj).encode()
    mask = os.urandom(4)
    n = len(data)
    head = bytes([0x81]) + (bytes([0x80 | n]) if n < 126
                            else bytes([0x80 | 126]) + n.to_bytes(2, "big"))
    s.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def t_remote_page():
    code, raw = get("/", want_json=False)
    ok = code == 200 and b'id="p-remote"' in raw and b'id="rmStick"' in raw
    say("ok" if ok else "no", "GET / has the Remote page", "%d" % code)


def t_servos():
    """The arm and the camera's pan servo, from the phone's point of view."""
    code, s = get("/api/state")
    sv = s.get("servos") or {}
    if not need(sv, ["live", "reason", "joints", "poses"], "  state.servos"):
        return
    names = [j.get("name") for j in sv["joints"]]
    say("ok" if "pan" in names and len(names) >= 2 else "no", "  joints listed",
        ", ".join(names))
    post("/api/command", {"cmd": "mode", "args": {"mode": "MANUAL"}})
    code, j = post("/api/command", {"cmd": "servo", "args": {"name": "pan", "deg": 60}})
    say("ok" if j.get("ok") else "no", "POST command servo (pan 60)", str(j)[:60])
    # a slow joint shows the walk: asked for 60 degrees away, half a second
    # later it must be on its way and not yet there
    slow = [x for x in sv["joints"] if x["name"] != "pan"]
    if slow:
        j0 = slow[0]
        post("/api/command", {"cmd": "servo_relax", "args": {"name": j0["name"]}})
        to = j0["park"] + (60 if j0["park"] + 60 <= j0["max"] else -60)
        post("/api/command", {"cmd": "servo", "args": {"name": j0["name"], "deg": to}})
        time.sleep(0.5)
        code, s = get("/api/state")
        jj = [x for x in s["servos"]["joints"] if x["name"] == j0["name"]][0]
        between = min(j0["park"], to) < jj["deg"] < max(j0["park"], to)
        say("ok" if between and jj["target"] == to else "no",
            "  it walks there, it does not jump",
            "%s at %s on the way from %s to %s" % (j0["name"], jj["deg"], j0["park"], to))
    code, j = post("/api/command", {"cmd": "servo", "args": {"name": "pan", "deg": 999}})
    code, s = get("/api/state")
    pan = [x for x in s["servos"]["joints"] if x["name"] == "pan"][0]
    say("ok" if pan["target"] <= pan["max"] else "no", "  past its limit is clamped",
        "asked 999, target %s (max %s)" % (pan["target"], pan["max"]))
    code, j = post("/api/command", {"cmd": "servo", "args": {"name": "nose", "deg": 10}})
    say("ok" if j.get("ok") is False else "no", "  a joint that is not there is refused",
        str(j)[:60])
    if sv["poses"]:
        code, j = post("/api/command", {"cmd": "servo_pose", "args": {"pose": sv["poses"][0]}})
        say("ok" if j.get("ok") else "no", "POST command servo_pose", sv["poses"][0])
    post("/api/command", {"cmd": "estop", "args": {"reason": "self test"}})
    code, j = post("/api/command", {"cmd": "servo", "args": {"name": "pan", "deg": 90}})
    say("ok" if j.get("ok") is False else "no", "  refused during an emergency stop",
        str(j)[:60])
    post("/api/command", {"cmd": "clear_estop", "args": {}})
    code, j = post("/api/command", {"cmd": "servo_relax", "args": {}})
    code, s = get("/api/state")
    asleep = not any(x["awake"] for x in s["servos"]["joints"])
    say("ok" if j.get("ok") and asleep else "no", "POST command servo_relax",
        "all limp" if asleep else "still holding")


def t_arm_and_modes_page():
    code, raw = get("/", want_json=False)
    ok = (code == 200 and b'id="p-arm"' in raw and b'id="armDraw"' in raw
          and b'data-mode="AUTO"' in raw and b'id="rmTabArm"' in raw)
    say("ok" if ok else "no", "GET / has the Arm page and the mode buttons", "%d" % code)


def t_saved_poses():
    """Teach it a pose, get it back, and forget it again."""
    post("/api/command", {"cmd": "mode", "args": {"mode": "MANUAL"}})
    post("/api/command", {"cmd": "servo", "args": {"name": "shoulder", "deg": 70}})
    time.sleep(0.3)
    code, j = post("/api/command", {"cmd": "servo_pose_save", "args": {"name": "selftest pose"}})
    code, s = get("/api/state")
    sv = s.get("servos") or {}
    ok = j.get("ok") and "selftest pose" in (sv.get("saved_poses") or []) \
        and "selftest pose" in (sv.get("poses") or [])
    say("ok" if ok else "no", "POST servo_pose_save keeps a new pose", str(j)[:60])
    code, j = post("/api/command", {"cmd": "servo_pose_save", "args": {"name": "park"}})
    say("ok" if j.get("ok") is False else "no", "  a built-in name is refused", str(j)[:60])
    post("/api/command", {"cmd": "servo", "args": {"name": "shoulder", "deg": 120}})
    code, j = post("/api/command", {"cmd": "servo_pose", "args": {"pose": "selftest pose"}})
    code, s = get("/api/state")
    sh = [x for x in s["servos"]["joints"] if x["name"] == "shoulder"][0]
    say("ok" if j.get("ok") and abs(sh["target"] - 70) < 0.6 else "no",
        "  the saved pose moves the arm back", "target %s" % sh["target"])
    code, j = post("/api/command", {"cmd": "servo_pose_delete", "args": {"name": "selftest pose"}})
    code, s = get("/api/state")
    gone = "selftest pose" not in (s["servos"].get("saved_poses") or [])
    say("ok" if j.get("ok") and gone else "no", "POST servo_pose_delete forgets it", str(j)[:60])
    code, j = post("/api/command", {"cmd": "servo_pose_delete", "args": {"name": "park"}})
    say("ok" if j.get("ok") is False else "no", "  a built-in pose cannot be deleted", str(j)[:60])
    post("/api/command", {"cmd": "servo_relax", "args": {}})


def t_ai_mode():
    """AI mode: it drives itself, slowly when it cannot see, arm locked."""
    code, j = post("/api/command", {"cmd": "mode", "args": {"mode": "AUTO"}})
    code, s = get("/api/state")
    say("ok" if j.get("ok") and s.get("mode") == "AUTO" else "no", "AI mode (AUTO) switches on",
        s.get("mode", "?"))
    cap = s.get("auto_blind_cap")
    blind = not (s.get("fitted") or {}).get("range")
    say("ok" if isinstance(cap, (int, float)) and 0.1 <= cap <= 1 else "no",
        "  state says how fast it may go without a range sensor", str(cap))
    code, j = post("/api/command", {"cmd": "servo", "args": {"name": "shoulder", "deg": 90}})
    say("ok" if j.get("ok") is False else "no", "  the arm is locked while it drives itself",
        str(j.get("error", ""))[:50])
    if blind:
        time.sleep(0.8)
        code, s = get("/api/state")
        thr = abs(float((s.get("drive") or {}).get("throttle", 0)))
        say("ok" if thr <= cap + 0.001 else "no", "  it never goes faster than that", "throttle %s" % thr)
    code, j = post("/api/command", {"cmd": "mode", "args": {"mode": "MANUAL"}})
    code, s = get("/api/state")
    say("ok" if s.get("mode") == "MANUAL" and not (s.get("mission") or {}).get("running")
        else "no", "Manual takes over and stops the row", s.get("mode", "?"))
    post("/api/command", {"cmd": "estop", "args": {}})
    code, j = post("/api/command", {"cmd": "mode", "args": {"mode": "AUTO"}})
    say("ok" if j.get("ok") is False and "stop" in str(j.get("error", "")).lower() else "no",
        "  AI mode says why it refuses during a stop", str(j.get("error", ""))[:50])
    post("/api/command", {"cmd": "clear_estop", "args": {}})
    post("/api/command", {"cmd": "mode", "args": {"mode": "IDLE"}})


def t_ws_drive():
    """The phone's stick drives over the websocket."""
    post("/api/command", {"cmd": "mode", "args": {"mode": "MANUAL"}})
    s = ws_open()
    try:
        for _ in range(4):
            ws_send(s, {"cmd": "drive", "throttle": 0.5, "steer": 0.0})
            time.sleep(0.12)
        code, st = get("/api/state")
        moving = float((st.get("drive") or {}).get("throttle", 0)) > 0
        say("ok" if moving else "no", "WS drive message reaches the wheels",
            "throttle=%s" % (st.get("drive") or {}).get("throttle"))
        ws_send(s, {"cmd": "drive", "throttle": 0, "steer": 0})
    finally:
        s.close()
    # and the dead man: no message for a second and it stops by itself
    time.sleep(1.3)
    code, st = get("/api/state")
    stopped = float((st.get("drive") or {}).get("throttle", 1)) == 0
    say("ok" if stopped else "no", "  it stops when the messages stop",
        "throttle=%s" % (st.get("drive") or {}).get("throttle"))
    post("/api/command", {"cmd": "mode", "args": {"mode": "IDLE"}})


for f in (t_commands, t_estop_cycle, t_unknown_command, t_patrol_roundtrip,
          t_settings_write, t_auth_wall):
    check(f.__name__, f)

lines.append("")
lines.append("THE PHONE REMOTE")
for f in (t_remote_page, t_arm_and_modes_page, t_servos, t_saved_poses, t_ai_mode, t_ws_drive):
    check(f.__name__, f)

lines.append("")
lines.append("=" * 62)
lines.append("  %d passed, %d failed" % (passed, failed))
lines.append("=" * 62)

out = "\n".join(lines)
print(out)
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(out + "\n")
print("\nwritten to %s" % REPORT)
sys.exit(1 if failed else 0)
