#!/usr/bin/env python3
"""AI Office - ALL-IN-ONE local web app (advanced).

One file (run_app.bat) opens a web page with EVERYTHING:
  - live camera feed(s) with names + what each person is doing
  - UNKNOWN-PERSON ALERT: red banner + beep when an unrecognised face stays in view
  - LIVE CHARTS: activity breakdown + people-over-time
  - ADD A FACE: type a name, one click, saved forever (faces.pkl)
  - PASSWORD LOGIN + open on your PHONE (same Wi-Fi): http://<this-pc-ip>:8000
  - MULTI / CCTV CAMERA: set AICAM_SOURCE="0,rtsp://user:pass@cam-ip/stream,1"

No Docker, no other scripts.
"""
from __future__ import annotations
import os
import time
import threading
import secrets
import datetime as dt

import cv2
import numpy as np
from flask import (Flask, Response, request, jsonify, session,
                   redirect, render_template_string, send_file)

from aicam_platform.common import get_settings, get_logger
from aicam_platform.vision import Tracker, FaceEngine
from office_pipeline import BehaviorEstimator, phone_near_person, PERSON, PHONE
import worklens_extras as EX

try:
    import accounts as _acct          # optional: SQLite multi-user logins
except Exception as _e:               # if missing, we fall back to one shared password
    _acct = None

log = get_logger("app")
S = get_settings()
PASSWORD = os.environ.get("AICAM_PASSWORD", "office123")
# ----- multi-user accounts (database) -----
ACCOUNTS_DB = os.path.abspath(os.environ.get("AICAM_ACCOUNTS_DB", "accounts.db"))
MULTI_USER = False
if _acct is not None:
    try:
        _acct.init_db(ACCOUNTS_DB)
        if _acct.ensure_admin(ACCOUNTS_DB, "admin", PASSWORD, os.environ.get("AICAM_ORG", "My Office")):
            log.info("accounts.db created - first login: username 'admin' + your AICAM_PASSWORD")
        MULTI_USER = True
    except Exception as e:
        log.warning(f"accounts init failed, using single shared password: {e}")
LLM_URL = os.environ.get("AICAM_LLM_URL", "http://localhost:11434")  # local Ollama
_llm_model = None
REPORT_PATH = os.path.abspath("AI_Office_Report.xlsx")  # auto-saved Excel on this PC
# RTSP over TCP = far fewer corrupt frames / FFmpeg crashes than the default UDP
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
# Total AI inferences/sec to spread across all ON cameras (keeps the GPU sane when
# many cameras run at once). 1 cam -> fast; 8 cams -> each gets a smaller share.
_FPS_BUDGET = float(os.environ.get("AICAM_FPS_BUDGET", "40") or 40)
# Browser ko bhejne wale frame ki max width + JPEG quality (AI detection par asar NAHI -
# wo apne imgsz par chalta hai). Chhota display frame = encode + network + browser sab fast.
_DISP_W = int(os.environ.get("AICAM_DISPLAY_WIDTH", "960") or 960)
_JPG_Q = int(os.environ.get("AICAM_JPEG_QUALITY", "62") or 62)
# Build the camera list. If a DVR template (+count) is given, make channels 1..N
# from it; else use AICAM_SOURCE (comma-separated webcams / RTSP URLs).
_DVR = os.environ.get("AICAM_DVR", "").strip()
_CAM_COUNT = int(os.environ.get("AICAM_CAM_COUNT", "0") or 0)
if _DVR and _CAM_COUNT:
    SOURCES = [_DVR.replace("{ch}", str(c)) for c in range(1, _CAM_COUNT + 1)]
    NAMES = [f"Camera {c}" for c in range(1, _CAM_COUNT + 1)]
    if os.environ.get("AICAM_ADD_WEBCAM", "1") != "0":   # laptop webcam as an extra camera
        SOURCES.append("0")
        NAMES.append("Webcam (laptop)")
else:
    SOURCES = [s.strip() for s in str(S.source).split(",") if s.strip()] or ["0"]
    NAMES = [("Webcam (laptop)" if s == "0" else f"Camera {i + 1}") for i, s in enumerate(SOURCES)]
SOURCES.append(None)                       # extra slot for an uploaded VIDEO FILE (set at runtime)
NAMES.append("Video file (upload)")
N = len(SOURCES)
VIDEO_IDX = N - 1
CAM_STATE_FILE = os.path.abspath("cameras.json")
EX.init(log)
_recorder = EX.ClipRecorder(N)


def _load_enabled():
    try:
        import json
        with open(CAM_STATE_FILE) as f:
            return set(json.load(f).get("enabled", []))
    except Exception:
        return {0}   # default: only the first camera runs


def _save_enabled():
    try:
        import json
        with open(CAM_STATE_FILE, "w") as f:
            json.dump({"enabled": [i for i in range(N) if cams[i]["enabled"]]}, f)
    except Exception as e:
        log.debug(f"cam state save: {e}")


# ----- shared state -----
_lock = threading.Lock()
_enabled0 = _load_enabled()
cams = [{"jpeg": None, "people": [], "persons": 0, "phones": 0, "ok": False,
         "name": NAMES[i], "source": SOURCES[i], "enabled": (i in _enabled0)} for i in range(N)]
_enroll = None
_reset_ids = 0          # bumped when faces are cleared -> cam loops drop remembered identities
_alert = {"id": 0, "msg": "", "ts": ""}
_activity = {"working": 0, "idle": 0, "phone": 0, "walking": 0}
_history = []   # [[hh:mm:ss, total_persons], ...] capped

# Face recognition device: GPU (ctx 0) jab detection GPU par ho; AICAM_FACE_CTX se override
_face_ctx = int(os.environ.get("AICAM_FACE_CTX",
                               "0" if str(getattr(S, "device", "cpu")).lower() not in ("cpu", "") else "-1"))
faces = FaceEngine(ctx_id=_face_ctx, match_threshold=getattr(S, "face_threshold", 0.5)) if S.face_enabled else None
if faces is not None:
    try:
        log.info(f"loaded {faces.load(S.face_db)} enrolled face(s) from {S.face_db}")
    except Exception as e:
        log.warning(f"face db load: {e}")

_csv_lock = threading.Lock()
_csv = None
if S.csv_log:
    fresh = (not os.path.exists(S.csv_log)) or os.path.getsize(S.csv_log) == 0
    _csv = open(S.csv_log, "a", newline="", encoding="utf-8")
    if fresh:
        _csv.write("timestamp,camera_id,type,track_id,subject_id,activity,confidence,persons_in_frame,phones_in_frame\n")


def enrolled_names():
    return sorted(faces.gallery.keys()) if faces else []


def raise_alert(msg):
    with _lock:
        _alert["id"] += 1
        _alert["msg"] = msg
        _alert["ts"] = dt.datetime.now().strftime("%I:%M:%S %p")


def cam_loop(idx):
    global _enroll
    tracker = Tracker(model_path=S.model_path, tracker=S.tracker, device=S.device,
                      conf=S.conf, imgsz=S.imgsz, classes=[PERSON, PHONE])
    behavior = BehaviorEstimator()
    identity, votes, seen = {}, {}, {}
    local_reset = 0
    last_alert = 0.0
    last_tick = 0.0
    last_proc = 0.0
    frame_i = 0
    state = {"frame": None, "ok": False, "delay": 0.0}

    def _reader():
        # This thread OWNS the camera: open + read + release all here, so no other
        # thread ever touches it (prevents FFmpeg use-after-close crashes on toggle).
        cap = None
        cur = None
        while True:
            try:
                src_raw = cams[idx]["source"]
                want = cams[idx]["enabled"] and src_raw is not None
                if not want:
                    if cap is not None:
                        cap.release(); cap = None; cur = None
                    state["frame"] = None; state["ok"] = False
                    time.sleep(0.3); continue
                if cap is None or cur != src_raw:
                    if cap is not None:
                        cap.release()
                    cur = src_raw
                    is_file = not (str(src_raw).isdigit() or str(src_raw).lower().startswith("rtsp"))
                    s = int(src_raw) if str(src_raw).isdigit() else src_raw
                    cap = cv2.VideoCapture(s)
                    try:
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass
                    fps = cap.get(cv2.CAP_PROP_FPS) if is_file else 0
                    state["delay"] = (1.0 / fps) if (is_file and fps and fps > 1) else 0.0
                ok, f = cap.read()
                if not ok:
                    if cap is not None:
                        cap.release()
                    cap = None; cur = None; state["ok"] = False
                    time.sleep(0.3); continue
                state["frame"] = f; state["ok"] = True
                if state["delay"]:
                    time.sleep(state["delay"])   # pace a video FILE to real speed
            except Exception as ex:
                log.debug(f"cam {idx} reader: {ex}")
                try:
                    if cap is not None:
                        cap.release()
                except Exception:
                    pass
                cap = None; cur = None; state["ok"] = False
                time.sleep(0.3)

    threading.Thread(target=_reader, daemon=True).start()

    while True:
        if not cams[idx]["enabled"] or cams[idx]["source"] is None:
            with _lock:
                cams[idx].update(ok=False, jpeg=None, people=[], persons=0, phones=0)
            time.sleep(0.3)
            continue
        frame = state["frame"]
        if frame is None:
            with _lock:
                cams[idx]["ok"] = state["ok"]
            time.sleep(0.03)
            continue
        state["frame"] = None         # consume -> only ever process the latest frame
        # spread the GPU budget across however many cameras are ON right now
        if _FPS_BUDGET > 0:
            n_on = max(1, sum(1 for c in cams if c["enabled"] and c["source"] is not None))
            target = max(3.0, min(15.0, _FPS_BUDGET / n_on))
            _since = time.time() - last_proc
            if _since < 1.0 / target:
                time.sleep((1.0 / target) - _since)
        last_proc = time.time()
        frame_i += 1
        if _reset_ids != local_reset:          # faces were cleared -> forget remembered names
            identity.clear(); votes.clear(); seen.clear()
            local_reset = _reset_ids
        tracks = tracker.update(frame)
        persons = [t for t in tracks if t.cls_id == PERSON]
        phones = [t for t in tracks if t.cls_id == PHONE]

        # enrollment: only the camera the user picked captures the face
        with _lock:
            e = _enroll
        if e is not None and e.get("cam") == idx and not e["done"] and faces is not None:
            try:
                added = faces.enroll(e["name"], frame)
            except Exception as ex:
                added = False
                log.warning(f"enroll error: {ex}")
            if added:
                e["got"] += 1
                e["remaining"] -= 1
                if e["remaining"] <= 0:
                    e["done"] = True
            if e["done"]:
                try:
                    faces.save(S.face_db)
                except Exception as ex:
                    log.warning(f"save error: {ex}")

        # face recognition (~1/sec, only when someone is actually present)
        if persons and faces is not None and faces.gallery and frame_i % 15 == 0:
            try:
                for m in faces.recognize(frame):
                    if m.subject_id in (None, "unknown"):
                        continue
                    fx = (m.bbox[0] + m.bbox[2]) / 2
                    fy = (m.bbox[1] + m.bbox[3]) / 2
                    for t in persons:
                        x1, y1, x2, y2 = t.xyxy
                        if x1 <= fx <= x2 and y1 <= fy <= y2:
                            v = votes.setdefault(t.track_id, {})
                            v[m.subject_id] = v.get(m.subject_id, 0) + 1
                            best = max(v.items(), key=lambda kv: kv[1])
                            if best[1] >= 2:
                                identity[t.track_id] = best[0]
                            break
            except Exception as ex:
                log.debug(f"recognition skipped: {ex}")

        now = time.time()
        people, rows, unknown_sustained = [], [], False
        for t in persons:
            sid = identity.get(t.track_id, "unknown")
            disp = sid if sid != "unknown" else "Unknown"
            seen.setdefault(t.track_id, now)
            near = phone_near_person(t.xyxy, phones)
            act = behavior.update(t.track_id, t.foot, near)
            people.append({"name": disp, "doing": act})
            rows.append((t.track_id, sid, act, round(t.conf, 3)))
            if sid == "unknown" and now - seen[t.track_id] > 3.0:
                unknown_sustained = True
            x1, y1, x2, y2 = (int(v) for v in t.xyxy)
            color = (0, 0, 255) if act == "phone" else ((0, 165, 255) if disp == "Unknown" else (0, 200, 0))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{disp} - {act}", (x1, max(16, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
        for ph in phones:
            x1, y1, x2, y2 = (int(v) for v in ph.xyxy)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 255), 2)

        if unknown_sustained and now - last_alert > 10:
            last_alert = now
            raise_alert(f"Unknown person - {cams[idx]['name']}")
            with _lock:
                _aj = cams[idx]["jpeg"]
            EX.tg_send(f"WorkLens ALERT: Unknown person - {cams[idx]['name']} "
                       f"({dt.datetime.now().strftime('%I:%M %p')})", _aj)
            _recorder.trigger(idx, "unknown-person")

        # after-hours + restricted-zone alerts (Telegram + auto recording)
        if persons:
            if EX.is_after_hours() and not EX.throttled(f"ah{idx}", 60):
                _m = f"After-hours motion - {cams[idx]['name']}"
                raise_alert(_m)
                with _lock:
                    _aj = cams[idx]["jpeg"]
                EX.tg_send("WorkLens CRITICAL: " + _m, _aj)
                _recorder.trigger(idx, "after-hours")
            for _zn in EX.check_zones(idx, [t.foot for t in persons]):
                if not EX.throttled(f"zn{idx}-{_zn}", 60):
                    _m = f"Zone breach: {_zn} - {cams[idx]['name']}"
                    raise_alert(_m)
                    with _lock:
                        _aj = cams[idx]["jpeg"]
                    EX.tg_send("WorkLens CRITICAL: " + _m, _aj)
                    _recorder.trigger(idx, "zone-" + _zn)

        # per-second aggregation: activity totals, history, csv
        if now - last_tick >= 1.0:
            last_tick = now
            with _lock:
                for (_tid, _sid, act, _c) in rows:
                    if act in _activity:
                        _activity[act] += 1
                if idx == 0:
                    total = sum(c["persons"] for c in cams)
                    _history.append([dt.datetime.now().strftime("%H:%M:%S"), total])
                    if len(_history) > 40:
                        del _history[0]
            if _csv is not None:
                with _csv_lock:
                    ts = dt.datetime.now().isoformat()
                    for (tid, sid, act, conf) in rows:
                        _csv.write(f"{ts},{cams[idx]['name']},behavior,{tid},{sid},{act},"
                                   f"{conf},{len(persons)},{len(phones)}\n")
                    _csv.flush()

        if _DISP_W > 0 and frame.shape[1] > _DISP_W:
            _sc = _DISP_W / frame.shape[1]
            frame = cv2.resize(frame, (_DISP_W, max(2, int(frame.shape[0] * _sc))),
                               interpolation=cv2.INTER_AREA)
        ok2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPG_Q])
        if ok2:
            _jpgb = buf.tobytes()
            _recorder.add(idx, _jpgb)
            with _lock:
                cams[idx]["jpeg"] = _jpgb
                cams[idx]["people"] = people
                cams[idx]["persons"] = len(persons)
                cams[idx]["phones"] = len(phones)
                cams[idx]["ok"] = True


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


@app.before_request
def _guard():
    if (request.path == "/" or request.path.startswith("/login") or request.path.startswith("/static")
            or request.path in ("/manifest.json", "/sw.js") or request.path.startswith("/icon-")):
        return
    if not session.get("auth"):
        return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        pw = request.form.get("password") or ""
        user = _acct.verify(ACCOUNTS_DB, u, pw) if (_acct and MULTI_USER) else None
        if user:
            session.update(auth=True, uid=user["id"], username=user["username"],
                           role=user["role"], org_id=user["org_id"], org_name=user["org_name"])
            return redirect("/")
        if not MULTI_USER and pw == PASSWORD:        # fallback: single shared password
            session.update(auth=True, username="user", role="owner", org_name="My Office")
            return redirect("/")
        err = "Galat username ya password. Dobara try karo."
    return render_template_string(LOGIN, err=err, multi=MULTI_USER)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


def _is_admin():
    return session.get("role") in ("owner", "admin")


@app.route("/users")
def users_list():
    if not (_acct and MULTI_USER) or not _is_admin():
        return jsonify({"ok": False, "users": []})
    return jsonify({"ok": True, "users": _acct.list_users(ACCOUNTS_DB, session.get("org_id"))})


@app.route("/add_user", methods=["POST"])
def add_user_route():
    if not (_acct and MULTI_USER) or not _is_admin():
        return jsonify({"ok": False, "msg": "Sirf admin/owner naya user bana sakta hai."})
    d = request.get_json(silent=True) or {}
    role = d.get("role") if d.get("role") in ("admin", "manager", "staff") else "staff"
    ok, msg = _acct.add_user(ACCOUNTS_DB, session.get("org_id"),
                             d.get("username", ""), d.get("password", ""), role)
    return jsonify({"ok": ok, "msg": msg})


@app.route("/delete_user", methods=["POST"])
def delete_user_route():
    if not (_acct and MULTI_USER) or not _is_admin():
        return jsonify({"ok": False, "msg": "Sirf admin/owner user hata sakta hai."})
    d = request.get_json(silent=True) or {}
    if d.get("id") == session.get("uid"):
        return jsonify({"ok": False, "msg": "Apne aap ko delete nahi kar sakte."})
    try:
        _acct.delete_user(ACCOUNTS_DB, int(d.get("id")))
        return jsonify({"ok": True, "msg": "User hata diya."})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Nahi hua: {e}"})


@app.route("/")
def index():
    # Serve the WorkLens Command Center redesign (falls back to the classic UI).
    try:
        _wl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "WorkLens-Command-Center.html")
        with open(_wl, encoding="utf-8") as _f:
            return _f.read()
    except Exception:
        return HTML

@app.route("/classic")
def classic():
    return HTML


@app.route("/video/<int:i>")
def video(i):
    if i < 0 or i >= N:
        return "no camera", 404
    try:
        fps = float(request.args.get("fps", 15))
    except Exception:
        fps = 20.0
    delay = 1.0 / max(2.0, min(30.0, fps))

    def gen():
        last = None
        while True:
            with _lock:
                jpg = cams[i]["jpeg"]
            if jpg is None or jpg is last:
                # naya frame nahi aaya - dobara wahi mat bhejo (bandwidth + lag bachao)
                time.sleep(0.02)
                continue
            last = jpg
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            time.sleep(delay)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/video/all")
def video_all():
    """ALL enabled cameras tiled into ONE stream = a single browser connection.
    This is what fixes the lag + the toggle buttons when many cameras are ON
    (8 separate streams used to saturate the browser's ~6-connection limit)."""
    import math
    TW, TH = 480, 270           # each tile size

    def label(img, text):
        cv2.rectangle(img, (0, 0), (TW, 24), (20, 24, 32), -1)
        cv2.putText(img, text[:34], (8, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (180, 220, 255), 1, cv2.LINE_AA)
        return img

    def gen():
        while True:
            with _lock:
                items = [(c["name"], c["jpeg"], c["ok"]) for c in cams
                         if c["enabled"] and c["source"] is not None]
            tiles = []
            for name, jpg, ok in items:
                img = None
                if jpg:
                    img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    img = np.zeros((TH, TW, 3), np.uint8)
                    cv2.putText(img, "connecting...", (TW // 2 - 70, TH // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 130, 150), 2, cv2.LINE_AA)
                else:
                    img = cv2.resize(img, (TW, TH))
                tiles.append(label(img, name))
            if not tiles:
                blank = np.zeros((TH, TW, 3), np.uint8)
                cv2.putText(blank, "Koi camera ON nahi", (40, TH // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 130, 150), 2, cv2.LINE_AA)
                tiles = [blank]
            cols = 1 if len(tiles) == 1 else (2 if len(tiles) <= 4 else 3)
            rows = math.ceil(len(tiles) / cols)
            while len(tiles) < rows * cols:
                tiles.append(np.zeros((TH, TW, 3), np.uint8))
            grid = np.vstack([np.hstack(tiles[r * cols:(r + 1) * cols]) for r in range(rows)])
            ok2, buf = cv2.imencode(".jpg", grid, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok2:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
            time.sleep(0.12)        # ~8 fps mosaic (display only; AI runs separately)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/state")
def state():
    with _lock:
        all_people = []
        for c in cams:
            for p in c["people"]:
                all_people.append({**p, "camera": c["name"]})
        return jsonify({
            "cameras": [{"i": i, "name": c["name"], "ok": c["ok"], "enabled": c["enabled"],
                         "persons": c["persons"], "phones": c["phones"]} for i, c in enumerate(cams)],
            "people": all_people,
            "persons": sum(c["persons"] for c in cams if c["enabled"]),
            "phones": sum(c["phones"] for c in cams if c["enabled"]),
            "enrolled": enrolled_names(),
            "alert": dict(_alert),
            "activity": dict(_activity),
            "history": list(_history),
            "me": {"username": session.get("username", ""), "role": session.get("role", ""),
                   "org": session.get("org_name", ""), "is_admin": _is_admin(), "multi": MULTI_USER},
        })


@app.route("/set_camera", methods=["POST"])
def set_camera():
    d = request.get_json(silent=True) or {}
    i = d.get("i")
    if not isinstance(i, int) or i < 0 or i >= N:
        return jsonify({"ok": False, "msg": "galat camera"})
    with _lock:
        cams[i]["enabled"] = bool(d.get("on"))
    _save_enabled()
    return jsonify({"ok": True, "i": i, "on": cams[i]["enabled"]})


@app.route("/set_all_cameras", methods=["POST"])
def set_all_cameras():
    """Turn AI ON (or OFF) for ALL real cameras at once - whole office in one click.
    Skips the empty 'Video file' slot (no source until a video is uploaded)."""
    d = request.get_json(silent=True) or {}
    on = bool(d.get("on"))
    with _lock:
        for c in cams:
            if c["source"] is not None:
                c["enabled"] = on
    _save_enabled()
    return jsonify({"ok": True, "on": on,
                    "count": sum(1 for c in cams if c["enabled"])})


@app.route("/upload_video", methods=["POST"])
def upload_video():
    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify({"ok": False, "msg": "Koi video select nahi hui."})
    os.makedirs("uploads", exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or ".mp4"
    path = os.path.abspath(os.path.join("uploads", "office_video" + ext))
    try:
        f.save(path)
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Save nahi hui: {e}"})
    with _lock:
        cams[VIDEO_IDX]["source"] = path
        cams[VIDEO_IDX]["enabled"] = True
    _save_enabled()
    return jsonify({"ok": True, "i": VIDEO_IDX,
                    "msg": "Video aa gayi - ab analyse ho rahi hai. 'Video file' camera grid me dekho."})


@app.route("/enroll", methods=["POST"])
def enroll():
    global _enroll
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "msg": "Pehle naam likho."})
    if faces is None:
        return jsonify({"ok": False, "msg": "Face recognition band hai."})
    cam = d.get("cam")
    with _lock:
        if not isinstance(cam, int) or not (0 <= cam < N) or not cams[cam]["enabled"]:
            en = [i for i in range(N) if cams[i]["enabled"]]
            cam = en[0] if en else None
        if cam is None:
            return jsonify({"ok": False, "msg": "Pehle koi camera ON karo (Cameras card me)."})
        _enroll = {"name": name, "cam": cam, "remaining": 5, "got": 0, "done": False}
    for _ in range(140):
        time.sleep(0.05)
        with _lock:
            done = _enroll and _enroll["done"]
        if done:
            break
    with _lock:
        got = _enroll["got"] if _enroll else 0
        cam_name = cams[cam]["name"]
        _enroll = None
    if got > 0:
        return jsonify({"ok": True, "msg": f"'{name}' add ho gaya ({cam_name})!", "enrolled": enrolled_names()})
    return jsonify({"ok": False, "msg": f"Face nahi mila ({cam_name}). Saaf chehra, achhi roshni me dikhao."})


@app.route("/clear_faces", methods=["POST"])
def clear_faces():
    global _reset_ids
    if faces is None:
        return jsonify({"ok": False, "msg": "Face recognition band hai."})
    with _lock:
        faces.gallery = {}
        _reset_ids += 1
    try:
        if os.path.exists(S.face_db):
            os.remove(S.face_db)
    except Exception as e:
        log.warning(f"face db delete: {e}")
    return jsonify({"ok": True, "msg": "Saare faces delete ho gaye. Ab fresh enroll karo (Webcam se best)."})


@app.route("/report")
def report():
    try:
        from export_excel import build_report
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        build_report(S.csv_log or "events_log.csv", path)
        return send_file(path, as_attachment=True, download_name="AI_Office_Report.xlsx")
    except Exception as e:
        return f"Report banane me dikkat: {e}  (camera thodi der chalao, phir try karo)", 500


@app.route("/open_excel")
def open_excel():
    try:
        from export_excel import build_report
        build_report(S.csv_log or "events_log.csv", REPORT_PATH)
        try:
            os.startfile(REPORT_PATH)   # Windows: opens the file in Excel on this PC
        except AttributeError:
            return jsonify({"ok": False, "msg": "'Open' sirf Windows par; Download button use karo."})
        return jsonify({"ok": True, "msg": "Excel laptop par khul gaya."})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Nahi khul paya: {e} (camera thodi der chalao)"})


def _pick_model():
    """Use AICAM_LLM_MODEL if set+installed, else the first model Ollama has."""
    global _llm_model
    if _llm_model:
        return _llm_model
    import urllib.request
    import json as _json
    env = os.environ.get("AICAM_LLM_MODEL", "").strip()
    try:
        with urllib.request.urlopen(LLM_URL + "/api/tags", timeout=5) as r:
            tags = [m.get("name", "") for m in _json.loads(r.read()).get("models", [])]
        if env and any(env in t for t in tags):
            _llm_model = env
        elif tags:
            _llm_model = tags[0]
        else:
            _llm_model = env or "llama3.2"
    except Exception:
        _llm_model = env or "llama3.2"
    return _llm_model


def _parse_ts(series):
    """Parse the timestamp column robustly. Older CSV rows may carry a timezone
    suffix (+05:30 / Z) while newer ones don't - that 'mixed timezones' combo
    crashes pandas. Strip any tz suffix (keep the recorded wall-clock time) so
    every value parses the same way and nothing crashes."""
    import pandas as pd
    raw = series.astype(str).str.replace(r'([+-]\d{2}:?\d{2}|Z)\s*$', '', regex=True)
    return pd.to_datetime(raw, errors="coerce", format="mixed")


def _today_data():
    import pandas as pd
    path = S.csv_log or "events_log.csv"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    df = pd.read_csv(path)
    df["timestamp"] = _parse_ts(df["timestamp"])
    df = df.dropna(subset=["timestamp"])
    df = df[df["timestamp"].dt.date == dt.date.today()]
    if df.empty:
        return None
    df["Name"] = df["subject_id"].apply(
        lambda s: "Unknown" if (pd.isna(s) or str(s).strip().lower() in ("", "unknown")) else str(s))
    beh = df[df["type"] == "behavior"]
    if beh.empty:
        beh = df
    per = {}
    for name, g in beh.groupby("Name"):
        a = g["activity"].fillna("").astype(str).value_counts()
        w = int(a.get("working", 0)); ph = int(a.get("phone", 0))
        idl = int(a.get("idle", 0)); wk = int(a.get("walking", 0))
        active = max(1, w + ph + idl + wk)
        score = int(round(max(0.0, min(100.0, 100.0 * (w * 1.0 + wk * 0.3 - ph * 0.2) / active))))
        per[name] = {"present": round((g["timestamp"].max() - g["timestamp"].min()).total_seconds() / 60, 1),
                     "working": round(w / 60, 1), "phone": round(ph / 60, 1),
                     "idle": round(idl / 60, 1), "walking": round(wk / 60, 1), "score": score}
    return {"date": dt.date.today().strftime("%d %b %Y"), "people": per}


def _ollama(prompt):
    import urllib.request
    import json as _json
    body = _json.dumps({"model": _pick_model(), "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(LLM_URL + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return _json.loads(r.read()).get("response", "").strip()


def _plain_summary(data):
    """Readable summary built directly from the data (no LLM needed)."""
    ppl = data["people"]
    if not ppl:
        return "Aaj abhi tak kisi ko pehchaana nahi gaya."
    n = len(ppl)
    total_present = round(sum(d["present"] for d in ppl.values()), 1)
    total_phone = round(sum(d["phone"] for d in ppl.values()), 1)
    ranked = sorted(ppl.items(), key=lambda kv: kv[1]["score"], reverse=True)
    out = [f"{data['date']} ka summary:",
           f"- Total {n} log dikhe, sab milake {total_present} min office me rahe.",
           f"- Sabse productive: {ranked[0][0]} ({ranked[0][1]['score']}%)."]
    if n > 1:
        out.append(f"- Sabse kam productive: {ranked[-1][0]} ({ranked[-1][1]['score']}%).")
    heavy = [f"{nm} ({d['phone']} min)" for nm, d in ppl.items() if d["phone"] >= 3]
    if heavy:
        out.append("- Phone zyada use: " + ", ".join(heavy) + ".")
    elif total_phone == 0:
        out.append("- Phone ka zyada use nahi hua - achha!")
    out.append("")
    out.append("Har vyakti:")
    for nm, d in ranked:
        out.append(f"- {nm}: {d['present']} min present, {d['working']} min working, "
                   f"{d['phone']} min phone -> {d['score']}% productive.")
    return "\n".join(out)


@app.route("/recordings")
def recordings_page():
    return EX.recordings_html()


@app.route("/rec/<name>")
def rec_stream(name):
    gen = EX.clip_stream(name)
    if gen is None:
        return "recording nahi mili", 404
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/attendance")
def attendance_page():
    return EX.attendance_html(S.csv_log or "events_log.csv")


@app.route("/attendance.json")
def attendance_json():
    try:
        return jsonify({"ok": True, "rows": EX.attendance_rows(S.csv_log or "events_log.csv")})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


@app.route("/manifest.json")
def pwa_manifest():
    return Response(EX.MANIFEST, mimetype="application/manifest+json")


@app.route("/sw.js")
def pwa_sw():
    return Response(EX.SW_JS, mimetype="text/javascript")


@app.route("/icon-192.png")
def pwa_icon192():
    return Response(EX.icon_png(192), mimetype="image/png")


@app.route("/icon-512.png")
def pwa_icon512():
    return Response(EX.icon_png(512), mimetype="image/png")


@app.route("/summary")
def summary():
    try:
        data = _today_data()
    except ModuleNotFoundError as e:
        return jsonify({"ok": False, "text": f"Library missing ({e}). run_app.bat band karke dobara chalao."})
    except Exception as e:
        return jsonify({"ok": False, "text": f"Data padhne me dikkat: {e}"})
    if not data:
        return jsonify({"ok": False, "text": "Aaj ka koi data nahi. Camera thodi der chalao, phir try karo."})
    total_present = round(sum(d['present'] for d in data['people'].values()), 1)
    lines = [f"- {n}: present {d['present']}min, working {d['working']}min, phone {d['phone']}min, "
             f"productivity {d['score']}%" for n, d in data["people"].items()]
    prompt = (f"You are a friendly office manager. Write a clear, encouraging daily summary in simple English "
              f"for {data['date']}. {len(data['people'])} people were seen; total presence {total_present} minutes. "
              "Per-person data:\n" + "\n".join(lines) +
              "\nWrite 4-5 short sentences: (1) the day overall, (2) who was most productive, "
              "(3) gently flag anyone with high phone use, (4) one short friendly tip. "
              "Use only the data given; do not invent anything. No markdown headings.")
    try:
        text = _ollama(prompt)
        if text:
            return jsonify({"ok": True, "text": text, "model": _llm_model})
    except Exception as e:
        log.debug(f"ollama unavailable, using plain summary: {e}")
    return jsonify({"ok": True, "text": _plain_summary(data) + "\n(simple summary - Ollama band hai)"})


def cloud_pusher():
    """If AICAM_CLOUD_URL + AICAM_CLOUD_TOKEN are set, send this office's live
    totals + today's productivity to the central HQ server every 30 seconds."""
    url = os.environ.get("AICAM_CLOUD_URL", "").strip()
    token = os.environ.get("AICAM_CLOUD_TOKEN", "").strip()
    if not url or not token:
        return
    import urllib.request
    import json as _json
    endpoint = url.rstrip("/") + "/api/ingest"
    log.info(f"cloud push ON -> {endpoint}")
    while True:
        try:
            with _lock:
                persons = sum(c["persons"] for c in cams if c["enabled"])
                phones = sum(c["phones"] for c in cams if c["enabled"])
            today = {}
            try:
                d = _today_data()
                if d:
                    today = d
            except Exception:
                pass
            body = _json.dumps({"persons": persons, "phones": phones, "today": today}).encode()
            req = urllib.request.Request(endpoint, data=body,
                                         headers={"Content-Type": "application/json", "X-Token": token})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as e:
            log.debug(f"cloud push skipped: {e}")
        time.sleep(30)


LOGIN = """<!doctype html><html><head><meta charset="utf-8"><title>Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#0f1623;font-family:Arial}
.box{background:#172033;padding:28px;border-radius:14px;border:1px solid #2a3550;width:300px}
h1{color:#e8edf5;font-size:18px;margin:0 0 16px} input{width:100%;padding:11px;border-radius:8px;border:1px solid #2a3550;background:#0f1623;color:#fff;font-size:15px;box-sizing:border-box}
button{margin-top:12px;width:100%;padding:11px;border:0;border-radius:8px;background:#2f5597;color:#fff;font-size:15px;font-weight:bold;cursor:pointer}
.err{color:#ff9b9b;font-size:13px;margin-top:10px}</style></head>
<body><form class="box" method="POST" action="/login">
<h1>WorkLens AI</h1><p style="color:#9db4e0;font-size:12px;margin:-8px 0 14px">Smart attendance &amp; productivity</p>
{% if multi %}<input name="username" placeholder="Username (jaise admin)" value="admin" autofocus style="margin-bottom:10px">{% endif %}
<input type="password" name="password" placeholder="Password" {% if not multi %}autofocus{% endif %}>
<button type="submit">Enter</button>
<div class="err">{{err}}</div>
</form></body></html>"""


HTML = """<!doctype html><html><head><meta charset="utf-8"><title>WorkLens AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box} body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#0f1623;color:#e8edf5}
header{background:#1f3864;padding:14px 20px;font-size:20px;font-weight:bold;display:flex;justify-content:space-between;align-items:center}
header a{color:#9db4e0;font-size:13px;text-decoration:none}
#alert{display:none;background:#a31313;color:#fff;padding:12px 20px;font-weight:bold}
.wrap{display:flex;gap:16px;padding:16px;flex-wrap:wrap}
.feeds{flex:2;min-width:380px;display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:10px}
.feeds figure{margin:0;background:#000;border-radius:12px;overflow:hidden}
.feeds img{width:100%;display:block} .feeds figcaption{padding:6px 10px;font-size:13px;color:#9db4e0}
.side{flex:1;min-width:300px;display:flex;flex-direction:column;gap:14px}
.card{background:#172033;border:1px solid #2a3550;border-radius:12px;padding:14px}
.card h2{margin:0 0 10px;font-size:15px;color:#9db4e0;font-weight:600}
input{width:100%;padding:10px;border-radius:8px;border:1px solid #2a3550;background:#0f1623;color:#fff;font-size:15px}
button{margin-top:10px;width:100%;padding:11px;border:0;border-radius:8px;background:#2f5597;color:#fff;font-size:15px;font-weight:bold;cursor:pointer}
#msg{margin-top:10px;font-size:13px;color:#9db4e0;min-height:18px}
ul{list-style:none;margin:0;padding:0} li{padding:8px 6px;border-bottom:1px solid #222d44;display:flex;justify-content:space-between;align-items:center}
.muted{color:#6b7a99} .row{display:flex;gap:14px} .stat{flex:1;background:#0f1623;border-radius:8px;padding:10px;text-align:center}
.stat b{display:block;font-size:22px} .tag{font-size:12px;padding:2px 9px;border-radius:10px}
.working{background:#1c4023;color:#9ff0ad} .phone{background:#4a1414;color:#ff9b9b}
.idle{background:#3a3a3a;color:#cfcfcf} .walking{background:#4a3a12;color:#ffd98a}
</style></head><body>
<header><span>WorkLens <span style="color:#5da0ff">AI</span> <small style="font-weight:400;font-size:12px;color:#9db4e0;margin-left:6px">smart attendance &amp; productivity</small></span><span><span id="who" style="color:#9db4e0;font-size:13px;margin-right:14px"></span><a href="/logout">logout</a></span></header>
<div id="alert"></div>
<div class="wrap">
  <div class="feeds" id="grid"></div>
  <div class="side">
    <div class="card">
      <h2>Add a face (ek baar - hamesha saved)</h2>
      <input id="name" placeholder="Naam likho, jaise Dikshant" onkeydown="if(event.key==='Enter')addFace()">
      <select id="enrollcam" style="width:100%;margin-top:8px;padding:9px;border-radius:8px;background:#0f1623;color:#fff;border:1px solid #2a3550"></select>
      <button onclick="addFace()">Is camera se face add karo</button>
      <div class="muted" style="font-size:12px;margin-top:6px">Tip: Webcam (laptop) sabse accha hai - saaf, paas se chehra.</div>
      <div id="msg"></div>
    </div>
    <div class="card">
      <h2>Excel report (apne aap save hoti hai)</h2>
      <button onclick="openExcel()">Excel kholo (laptop par)</button>
      <a href="/report" style="text-decoration:none"><button style="margin-top:8px;background:#34507f">Download</button></a>
      <div class="muted" style="font-size:12px;margin-top:6px">Har person ka alag sheet + chart, har din ka data (date, day, time, year). File laptop par auto-save hoti rehti hai.</div>
      <div id="xmsg" style="font-size:12px;color:#9db4e0;margin-top:6px"></div>
    </div>
    <div class="card">
      <h2>AI daily summary</h2>
      <button onclick="genSummary()">Aaj ka summary banao (AI)</button>
      <div id="summary" style="margin-top:10px;font-size:13px;line-height:1.6;color:#cdd8ee;white-space:pre-line"></div>
    </div>
    <div class="card">
      <h2>Cameras - kis par AI chale</h2>
      <div style="display:flex;gap:8px;margin-bottom:8px">
        <button onclick="toggleAll(true)" style="margin:0;flex:1;background:#1c7c34">Sab ON</button>
        <button onclick="toggleAll(false)" style="margin:0;flex:1;background:#444">Sab OFF</button>
      </div>
      <div id="camlist"></div>
      <div class="muted" style="font-size:12px;margin-top:6px">"Sab ON" = poora office ek saath. Jitne zyada ON, utna GPU load (har camera thodi slow ho sakti hai - normal hai).</div>
    </div>
    <div class="card">
      <h2>Office video analyse karo</h2>
      <input type="file" id="vidfile" accept="video/*" style="width:100%;color:#cdd8ee;font-size:13px">
      <button onclick="uploadVideo()" style="margin-top:8px">Video upload + analyse</button>
      <div class="muted" style="font-size:12px;margin-top:6px">Poori recorded video do - live jaisa chala ke sab logon ko detect karega ("Video file" camera me dikhega).</div>
      <div id="vidmsg" style="font-size:12px;color:#9db4e0;margin-top:6px"></div>
    </div>
    <div class="card">
      <h2>Abhi camera ke saamne</h2>
      <div class="row"><div class="stat"><b id="persons">0</b>log</div><div class="stat"><b id="phones">0</b>phone</div></div>
      <ul id="live" style="margin-top:10px"></ul>
      <div id="camstatus" style="color:#ff9b9b;font-size:13px;margin-top:8px"></div>
    </div>
    <div class="card"><h2>Log over time</h2><canvas id="lineChart" height="150"></canvas></div>
    <div class="card"><h2>Activity breakdown</h2><canvas id="pieChart" height="160"></canvas></div>
    <div class="card"><h2>Enrolled log (<span id="encount">0</span>)</h2><ul id="enrolled"></ul>
      <button onclick="clearFaces()" style="margin-top:8px;background:#7a1f1f">Saare faces delete karo</button>
      <div id="clrmsg" style="font-size:12px;color:#9db4e0;margin-top:6px"></div>
    </div>
    <div class="card" id="teamcard" style="display:none">
      <h2>Team / Accounts (logins)</h2>
      <input id="nu_name" placeholder="Naya username">
      <input id="nu_pass" type="password" placeholder="Password (4+ char)" style="margin-top:8px">
      <select id="nu_role" style="width:100%;margin-top:8px;padding:9px;border-radius:8px;background:#0f1623;color:#fff;border:1px solid #2a3550">
        <option value="staff">staff (sirf dekh sakta hai)</option>
        <option value="manager">manager</option>
        <option value="admin">admin (users bana sakta hai)</option>
      </select>
      <button onclick="addUser()">Naya user banao</button>
      <div id="umsg" style="font-size:12px;color:#9db4e0;margin-top:6px"></div>
      <ul id="userlist" style="margin-top:10px"></ul>
      <div class="muted" style="font-size:12px;margin-top:4px">Har banda apne username + password se login karega.</div>
    </div>
  </div>
</div>
<script>
let gridSig="", camSig="", lastAlert=0, line=null, pie=null;
function beep(){try{const a=new (window.AudioContext||window.webkitAudioContext)();const o=a.createOscillator();const g=a.createGain();o.connect(g);g.connect(a.destination);o.type='square';o.frequency.value=880;g.gain.value=0.2;o.start();setTimeout(()=>{o.stop();a.close();},400);}catch(e){}}
function buildGrid(cams){const g=document.getElementById('grid');const on=cams.filter(c=>c.enabled&&c.name.indexOf('Video file')<0);const vid=cams.filter(c=>c.enabled&&c.name.indexOf('Video file')>=0);
  if(!on.length&&!vid.length){g.innerHTML='<div class="muted" style="padding:24px">Koi camera ON nahi. Side me "Cameras" se "Sab ON" ya kisi camera ko ON karo.</div>';return;}
  let html='';
  if(on.length) html+='<figure><img src="/video/all"><figcaption>Live cameras (ek hi stream - fast)</figcaption></figure>';
  vid.forEach(c=>{html+='<figure><img src="/video/'+c.i+'"><figcaption>'+c.name+'</figcaption></figure>';});
  g.innerHTML=html;}
function renderCams(cams){const sig=cams.map(c=>c.name+(c.enabled?'1':'0')+(c.ok?'1':'0')).join('|');if(sig===camSig)return;camSig=sig;const el=document.getElementById('camlist');el.innerHTML='';cams.forEach(c=>{const row=document.createElement('div');row.style='display:flex;justify-content:space-between;align-items:center;padding:6px 2px;border-bottom:1px solid #222d44';const s=document.createElement('span');s.textContent=c.name+(c.enabled&&!c.ok?' (connecting...)':'');const b=document.createElement('button');b.textContent=c.enabled?'ON':'OFF';b.style='width:auto;margin:0;padding:5px 16px;background:'+(c.enabled?'#1c7c34':'#444');b.onclick=()=>toggleCam(c.i,!c.enabled);row.appendChild(s);row.appendChild(b);el.appendChild(row);});}
async function toggleCam(i,on){const el=document.getElementById('camlist');try{await fetch('/set_camera',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({i:i,on:on})});camSig='';tick();}catch(e){}}
async function toggleAll(on){try{await fetch('/set_all_cameras',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({on:on})});camSig='';gridSig='';tick();}catch(e){}}
function initCharts(){
  line=new Chart(document.getElementById('lineChart'),{type:'line',data:{labels:[],datasets:[{label:'People',data:[],borderColor:'#5da0ff',backgroundColor:'rgba(93,160,255,.2)',tension:.3,fill:true}]},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#6b7a99',maxTicksLimit:6}},y:{ticks:{color:'#6b7a99'},beginAtZero:true,precision:0}}}});
  pie=new Chart(document.getElementById('pieChart'),{type:'doughnut',data:{labels:['working','walking','idle','phone'],datasets:[{data:[0,0,0,0],backgroundColor:['#3b6d11','#ba7517','#5f5e5a','#a32d2d']}]},options:{plugins:{legend:{labels:{color:'#9db4e0'}}}}});
}
async function tick(){
  try{
    const s=await (await fetch('/state')).json();
    const liveOn=s.cameras.some(c=>c.enabled&&c.name.indexOf('Video file')<0);
    const vidSig=s.cameras.filter(c=>c.enabled&&c.name.indexOf('Video file')>=0).map(c=>c.i).join(',');
    const sig=(liveOn?'L':'')+'|'+vidSig;
    if(sig!==gridSig){gridSig=sig;buildGrid(s.cameras);}
    renderCams(s.cameras);
    const sel=document.getElementById('enrollcam'); const cur=sel.value;
    sel.innerHTML='';
    s.cameras.filter(c=>c.enabled).forEach(c=>{const o=document.createElement('option');o.value=c.i;o.textContent=c.name;sel.appendChild(o);});
    if(!sel.options.length){const o=document.createElement('option');o.value='';o.textContent='(pehle koi camera ON karo)';sel.appendChild(o);}
    else if(cur && [...sel.options].some(o=>o.value===cur)) sel.value=cur;
    else{const w=[...sel.options].find(o=>o.textContent.indexOf('Webcam')>=0); if(w) sel.value=w.value;}
    document.getElementById('persons').textContent=s.persons;
    document.getElementById('phones').textContent=s.phones;
    const live=document.getElementById('live'); live.innerHTML='';
    if(!s.people.length){live.innerHTML='<li class="muted">Koi nahi dikh raha</li>';}
    s.people.forEach(p=>{const li=document.createElement('li');li.innerHTML='<span>'+p.name+'</span><span class="tag '+p.doing+'">'+p.doing+'</span>';live.appendChild(li);});
    const en=document.getElementById('enrolled'); en.innerHTML='';
    s.enrolled.forEach(n=>{const li=document.createElement('li');li.textContent=n;en.appendChild(li);});
    document.getElementById('encount').textContent=s.enrolled.length;
    applyMe(s.me);
    const camok=s.cameras.some(c=>c.ok);
    document.getElementById('camstatus').textContent=camok?'':'Camera shuru ho raha hai... (10 sec baad bhi black ho to doosra camera app band karo)';
    const al=document.getElementById('alert');
    if(s.alert.id>0){al.style.display='block';al.textContent='\\u26A0 '+s.alert.msg+'  ('+s.alert.ts+')';if(s.alert.id!==lastAlert){lastAlert=s.alert.id;beep();}}
    if(line){line.data.labels=s.history.map(h=>h[0]);line.data.datasets[0].data=s.history.map(h=>h[1]);line.update('none');}
    if(pie){pie.data.datasets[0].data=[s.activity.working,s.activity.walking,s.activity.idle,s.activity.phone];pie.update('none');}
  }catch(e){}
}
initCharts(); setInterval(tick,1500); tick();
async function addFace(){
  const name=document.getElementById('name').value.trim(); const msg=document.getElementById('msg');
  if(!name){msg.textContent='Pehle naam likho.';return;}
  const cam=parseInt(document.getElementById('enrollcam').value);
  if(isNaN(cam)){msg.textContent='Pehle koi camera ON karo (Cameras card me).';return;}
  msg.textContent='Capturing... us camera ke saamne saaf chehra dikhao';
  try{const j=await (await fetch('/enroll',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,cam:cam})})).json();
    msg.textContent=j.msg; if(j.ok){document.getElementById('name').value='';tick();}}catch(e){msg.textContent='Error - dobara try karo';}
}
async function genSummary(){
  const el=document.getElementById('summary'); el.textContent='AI soch raha hai... (thoda time lagega)';
  try{
    const r=await fetch('/summary');
    let t; try{ t=(await r.json()).text; }catch(_){ t='Server error '+r.status+' - window band karke run_app.bat dobara chalao (naya code load hoga).'; }
    el.textContent = t || 'Kuch jawab nahi aaya.';
  }catch(e){ el.textContent='App se connect nahi hua - black window chal raha hai? ('+e+')'; }
}
async function openExcel(){
  const m=document.getElementById('xmsg'); m.textContent='Excel khol raha hoon...';
  try{const j=await (await fetch('/open_excel')).json(); m.textContent=j.msg;}catch(e){m.textContent='Error - dobara try karo';}
}
async function clearFaces(){
  if(!confirm('Pakka? Saare enrolled faces delete ho jayenge.')) return;
  const m=document.getElementById('clrmsg'); m.textContent='Delete kar raha hu...';
  try{const j=await (await fetch('/clear_faces',{method:'POST'})).json(); m.textContent=j.msg; tick();}catch(e){m.textContent='Error - dobara try karo';}
}
async function uploadVideo(){
  const f=document.getElementById('vidfile').files[0]; const m=document.getElementById('vidmsg');
  if(!f){m.textContent='Pehle video select karo.';return;}
  m.textContent='Upload ho rahi hai... (badi file me time lagega, ruko)';
  const fd=new FormData(); fd.append('video', f);
  try{const j=await (await fetch('/upload_video',{method:'POST',body:fd})).json(); m.textContent=j.msg; tick();}catch(e){m.textContent='Upload fail - dobara try karo';}
}
let teamShown=false;
function applyMe(me){
  if(!me) return;
  const who=document.getElementById('who');
  who.textContent = me.username ? (me.username+(me.role?' ('+me.role+')':'')+(me.org?' - '+me.org:'')) : '';
  const tc=document.getElementById('teamcard');
  if(me.is_admin){ tc.style.display='block'; if(!teamShown){teamShown=true; loadUsers();} }
  else { tc.style.display='none'; }
}
async function loadUsers(){
  try{const j=await (await fetch('/users')).json(); const ul=document.getElementById('userlist'); ul.innerHTML='';
    if(!j.ok) return;
    j.users.forEach(u=>{const li=document.createElement('li');
      const left=document.createElement('span'); left.textContent=u.username+' - '+u.role+(u.active?'':' (off)');
      const b=document.createElement('button'); b.textContent='remove'; b.style='width:auto;margin:0;padding:4px 12px;background:#7a1f1f';
      b.onclick=()=>delUser(u.id,u.username); li.appendChild(left); li.appendChild(b); ul.appendChild(li);});
  }catch(e){}
}
async function addUser(){
  const n=document.getElementById('nu_name').value.trim(); const p=document.getElementById('nu_pass').value;
  const r=document.getElementById('nu_role').value; const m=document.getElementById('umsg');
  if(!n||!p){m.textContent='Username aur password dono likho.';return;}
  m.textContent='Add kar raha hu...';
  try{const j=await (await fetch('/add_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:n,password:p,role:r})})).json();
    m.textContent=j.msg; if(j.ok){document.getElementById('nu_name').value='';document.getElementById('nu_pass').value='';loadUsers();}}catch(e){m.textContent='Error - dobara try karo';}
}
async function delUser(id,name){
  if(!confirm("'"+name+"' ka login hata du?")) return;
  try{const j=await (await fetch('/delete_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})})).json();
    document.getElementById('umsg').textContent=j.msg; loadUsers();}catch(e){}
}
</script></body></html>"""


def report_saver():
    """Keep an up-to-date Excel saved on disk while the camera runs.
    Sirf tab rebuild karo jab CSV me NAYA data aaya ho (CPU spike nahi)."""
    last_size = -1
    while True:
        try:
            path = S.csv_log or "events_log.csv"
            sz = os.path.getsize(path) if os.path.exists(path) else 0
            if sz > 0 and sz != last_size:
                from export_excel import build_report
                build_report(path, REPORT_PATH)
                last_size = sz
        except Exception as e:
            log.debug(f"auto report save skipped: {e}")
        time.sleep(120)


def _open_browser():
    time.sleep(1.5)
    try:
        import webbrowser
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass


if __name__ == "__main__":
    for i in range(N):
        threading.Thread(target=cam_loop, args=(i,), daemon=True).start()
    threading.Thread(target=_open_browser, daemon=True).start()
    threading.Thread(target=report_saver, daemon=True).start()
    threading.Thread(target=cloud_pusher, daemon=True).start()   # off unless AICAM_CLOUD_URL set
    log.info(f"AI Office app -> http://localhost:8000  | cameras: {N} | password: set via AICAM_PASSWORD")
    log.info("Phone (same Wi-Fi): http://<this-pc-ip>:8000")
    try:
        from waitress import serve
        log.info("serving with waitress (production server - fast + stable)")
        serve(app, host="0.0.0.0", port=8000, threads=24,
              connection_limit=200, channel_timeout=600)
    except ImportError:
        log.info("waitress nahi mila - Flask dev server par chal raha hai")
        app.run(host="0.0.0.0", port=8000, threaded=True)
