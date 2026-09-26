"""The website the rover serves.

Open http://<pi-address>:8080 on a phone or laptop on the same network.
You sign in. The first time it is admin / agrirover and it makes you change it.

  GET  /                 the dashboard          GET  /login       sign in
  GET  /api/state        one snapshot           WS   /ws          live, 5 a second
  GET  /cam/front        live video             GET  /photos/<n>  a plant photo
  GET  /video/<name>     a saved run            POST /api/command everything it does
  GET  /api/field        every plant on the map GET  /api/plant/<plot>  its history
  GET  /api/history      per day, for charts    GET  /api/samples chart lines
  GET  /api/report.csv   the whole log          GET  /api/settings  what you can change
  GET  /api/patrols      the timetable          POST /api/patrols   change it

Everything except /login, /api/login and /api/health needs a signed in session.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import zipfile
import os
import time
from typing import Any, Dict, Optional

from fastapi import (FastAPI, WebSocket, WebSocketDisconnect, HTTPException,
                     Request, Response, Cookie)
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               PlainTextResponse, RedirectResponse,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles

from ..core.auth import Auth
from ..core.schedule import DAY_NAMES

PHOTOSET_NOTE = """%d photos, in folders named after what the rover called them.

This is a training set waiting to be corrected.

1. Open each folder and look at the photos.
2. Anything in the wrong folder, drag into the right one. Everything in
   _not_sorted_yet has never been looked at by a model at all - that is where
   most of them will be until you have trained one.
3. Delete the blurry ones. A blurry photo teaches the model to be confident
   about blur.
4. Aim for at least 100 photos per folder before you train anything, and take
   them across different days and different light. A model trained on one
   sunny afternoon works on one sunny afternoon.
5. Folder names must match the keys in ar750/ai/treatment.py, or the rover
   will not know what to do about what the model finds.

docs/TRAINING_THE_MODEL.md has the rest.
"""

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
COOKIE = "agrirover_session"

# Paths that are already compressed (pictures, video, zip, fonts) or that
# stream for ever (the camera). Gzip on those only costs the Pi CPU, and on a
# stream it holds frames back in its buffer until the picture stops moving.
_NO_GZIP = ("/cam/", "/video/", "/photos/", "/api/photoset", "/static/fonts/")


class _GzipText:
    """Gzip the pages, scripts and JSON - about a quarter of the bytes over
    a slow wifi - and leave everything in _NO_GZIP exactly as it was."""

    def __init__(self, app, minimum_size: int = 1024):
        from starlette.middleware.gzip import GZipMiddleware
        self.app = app
        self.gz = GZipMiddleware(app, minimum_size=minimum_size, compresslevel=6)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not scope.get("path", "").startswith(_NO_GZIP):
            await self.gz(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class _FreshStatic(StaticFiles):
    """The page's scripts and styles, with "check before you reuse this".

    Without it a browser may keep an old app.js for hours after new code
    was sent to the Pi, and the phone shows buttons the rover no longer has
    - or misses new ones. Checking costs one tiny request per file; an
    unchanged file still comes back as a 304 with no body."""

    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        r.headers["Cache-Control"] = "no-cache"
        return r


def build_app(rover) -> FastAPI:
    app = FastAPI(title="AR-750", docs_url=None, redoc_url=None)
    app.add_middleware(_GzipText)
    auth = Auth(os.path.join(rover.data_dir, "users.json"))
    rover.auth = auth

    # ------------------------------------------------------------------ auth
    def who(request: Request) -> Optional[dict]:
        return auth.user_for(request.cookies.get(COOKIE, ""))

    def need(request: Request) -> dict:
        u = who(request)
        if not u:
            raise HTTPException(status_code=401, detail="please sign in")
        return u

    def page(name: str) -> str:
        with open(os.path.join(STATIC, name), encoding="utf-8") as f:
            return f.read()

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        if not who(request):
            return RedirectResponse("/login", status_code=302)
        # always ask again, so a phone never keeps last week's page
        return HTMLResponse(page("index.html"), headers={"Cache-Control": "no-cache"})

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        if who(request):
            return RedirectResponse("/", status_code=302)
        return HTMLResponse(page("login.html"))

    @app.post("/api/login")
    async def do_login(request: Request, body: Dict[str, Any]):
        addr = request.client.host if request.client else "?"
        wait = auth.rate_limited(addr)
        if wait:
            return JSONResponse({"ok": False,
                                 "error": "too many tries, wait %d seconds" % wait},
                                status_code=429)
        token = auth.login(str(body.get("username", "")),
                           str(body.get("password", "")), addr)
        if not token:
            return JSONResponse({"ok": False, "error": "wrong username or password"},
                                status_code=401)
        u = auth.user_for(token) or {}
        r = JSONResponse({"ok": True, "user": u})
        r.set_cookie(COOKIE, token, httponly=True, samesite="lax",
                     max_age=60 * 60 * 24 * 14, path="/")
        return r

    @app.post("/api/logout")
    def do_logout(request: Request):
        auth.logout(request.cookies.get(COOKIE, ""))
        r = JSONResponse({"ok": True})
        r.delete_cookie(COOKIE, path="/")
        return r

    @app.get("/api/me")
    def me(request: Request):
        u = need(request)
        return {"ok": True, "user": u}

    @app.post("/api/account")
    async def account(request: Request, body: Dict[str, Any]):
        u = need(request)
        ok, msg = auth.change(u["name"], str(body.get("old", "")),
                              str(body.get("new", "")),
                              str(body.get("username", "") or u["name"]))
        if not ok:
            return JSONResponse({"ok": False, "error": msg}, status_code=400)
        rover.state.say("Sign in details changed", "warn")
        r = JSONResponse({"ok": True, "message": "Changed. Please sign in again."})
        r.delete_cookie(COOKIE, path="/")
        return r

    # ------------------------------------------------------------- telemetry
    def snap() -> Dict[str, Any]:
        """One picture of the rover for the website.

        The AI flags travel with every update on purpose: the page must never
        be able to show a green "AI ready" light while the model is missing.
        """
        s = rover.state.snapshot()
        s["ai_ready"] = bool(rover.classifier.ready)
        s["ai_reason"] = str(rover.classifier.reason or "")
        s["recording"] = bool(rover.recorder.running)
        s["rec_frames"] = int(rover.recorder.frames)
        s["returning"] = bool(rover._returning)
        s["speed_limit"] = round(rover._speed_limit, 2)
        s["auto_blind_cap"] = round(rover.auto_blind_cap, 2)
        s["steering"] = rover.steering.describe()
        if rover.drive_hw.skid:
            s["steering"]["can_spin_on_the_spot"] = True
        s["drive_hw"] = rover.drive_hw.snapshot()
        s["boom"] = rover.boom.snapshot()
        s["probe_hw"] = rover.probe.snapshot()
        s["servos"] = rover.servos.snapshot()
        s["cam_calibrated"] = bool(
            float(rover.cfg["cameras"]["front"].get("height_mm", 0) or 0) > 0)
        s["fitted"] = {"encoders": rover.enc.live, "imu": rover.imu.live,
                       "range": rover.rangef.live, "camera": not rover.cam_front.sim}
        nxt = None
        try:
            p = rover.patrols.next_due()
            if p:
                nxt = {"name": p.get("name") or "patrol", "at": p["next_run"]}
        except Exception:
            pass
        s["next_patrol"] = nxt
        return s

    @app.get("/api/state")
    def state(request: Request):
        need(request)
        return JSONResponse(snap())

    @app.get("/api/health")
    def health():
        """Deliberately says nothing private - it is for checking it is alive."""
        return {"ok": True, "sim": rover.state.sim, "name": "AR-750"}

    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        if not auth.user_for(sock.cookies.get(COOKIE, "")):
            await sock.close(code=4401)
            return
        await sock.accept()

        # The joystick talks back on the same socket: one small message ten
        # times a second, instead of a whole HTTP request each time. On a
        # weak wifi that is the difference between steering and waiting.
        # Only driving comes this way - everything else is a normal command.
        async def listen():
            while True:
                try:
                    m = json.loads(await sock.receive_text())
                except (WebSocketDisconnect, RuntimeError):
                    return
                except Exception:
                    continue
                if isinstance(m, dict) and m.get("cmd") == "drive":
                    try:
                        rover.web_drive(float(m.get("throttle", 0)),
                                        float(m.get("steer", 0)))
                    except (TypeError, ValueError):
                        pass

        listener = asyncio.ensure_future(listen())
        try:
            while not listener.done():
                await sock.send_text(json.dumps(snap()))
                rover._last_web = time.time()
                await asyncio.sleep(0.2)
        except WebSocketDisconnect:
            return
        except Exception:
            return
        finally:
            listener.cancel()

    # ------------------------------------------------------------------ video
    def mjpeg(cam):
        def gen():
            boundary = b"--frame\r\n"
            # the camera says which format it managed to encode: JPEG with
            # OpenCV, PNG without it
            ctype = ("Content-Type: %s\r\n" % getattr(cam, "mime", "image/jpeg"))
            ctype_b = ctype.encode()
            # The camera still runs at its full rate for row following; only
            # what goes over the wifi is capped. At 15 frames a second this
            # one picture was several Mbit/s, enough to choke a weak home
            # wifi and make every button on the page wait behind it.
            sfps = float((getattr(cam, "cfg", {}) or {}).get("stream_fps", 6))
            period = 1.0 / max(1.0, min(float(cam.fps), sfps))
            dry = 0.0
            last = None
            while True:
                buf = cam.jpeg()
                if buf and buf is not last:
                    # a new frame: send it, all in one piece
                    last = buf
                    dry = 0.0
                    yield (boundary + ctype_b + b"Content-Length: "
                           + str(len(buf)).encode() + b"\r\n\r\n" + buf + b"\r\n")
                else:
                    # Nothing new: sending the same frame again is wasted
                    # wifi. And a camera that has stopped producing frames
                    # used to leave the browser holding a request open for
                    # ever, never firing onerror - ending the response after
                    # a few dry seconds lets the page put up "no picture".
                    dry += period
                    if dry > 5.0:
                        return
                time.sleep(period)
        return StreamingResponse(
            gen(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/cam/front")
    def cam_front(request: Request):
        need(request)
        return mjpeg(rover.cam_front)


    @app.get("/photos/{name}")
    def photo(request: Request, name: str):
        need(request)
        p = os.path.join(rover.photo_dir, os.path.basename(name))
        if not os.path.exists(p):
            raise HTTPException(404, "no such photo")
        return FileResponse(p, media_type="image/jpeg")

    @app.get("/video/{name}")
    def video(request: Request, name: str):
        need(request)
        p = os.path.join(rover.video_dir, os.path.basename(name))
        if not os.path.exists(p):
            raise HTTPException(404, "no such recording")
        return FileResponse(p, media_type="video/mp4", filename=os.path.basename(name))

    if os.path.isdir(STATIC):
        app.mount("/static", _FreshStatic(directory=STATIC), name="static")

    # ---------------------------------------------------------------- commands
    @app.post("/api/command")
    async def command(request: Request, body: Dict[str, Any]):
        need(request)
        cmd = str(body.get("cmd", ""))
        a = body.get("args", {}) or {}
        st = rover.state

        if cmd == "estop":
            rover.estop(a.get("reason", "stop button on the website"))
        elif cmd == "clear_estop":
            rover.clear_estop()
        elif cmd == "mode":
            if not rover.set_mode(str(a.get("mode", "IDLE"))):
                return {"ok": False,
                        "error": getattr(rover, "mode_refusal", "") or "cannot change mode now"}
        elif cmd == "drive":
            rover.web_drive(float(a.get("throttle", 0)), float(a.get("steer", 0)))
        elif cmd == "speed_limit":
            rover.set_speed_limit(float(a.get("value", 1.0)))
        elif cmd == "servo":
            # one joint of the arm, or the camera's pan servo: an angle, or
            # a nudge from wherever it is heading now
            if a.get("deg") is None and a.get("delta") is None:
                return {"ok": False, "error": "say where: deg or delta"}
            ok, msg = rover.move_servo(
                str(a.get("name", "")),
                deg=None if a.get("deg") is None else float(a["deg"]),
                delta=None if a.get("delta") is None else float(a["delta"]))
            if not ok:
                return {"ok": False, "error": msg}
        elif cmd == "servo_pose":
            ok, msg = rover.servo_pose(str(a.get("pose", "")))
            if not ok:
                return {"ok": False, "error": msg}
        elif cmd == "servo_relax":
            rover.servos.relax(a.get("name") or None)
        elif cmd == "servo_pose_save":
            # remember where the arm is now, under a name - it moves nothing
            ok, msg = rover.servos.save_pose(str(a.get("name", "")))
            return {"ok": ok, "message": msg} if ok else {"ok": False, "error": msg}
        elif cmd == "servo_pose_delete":
            ok, msg = rover.servos.delete_pose(str(a.get("name", "")))
            return {"ok": ok, "message": msg} if ok else {"ok": False, "error": msg}
        elif cmd == "probe":
            if a.get("read"):
                return {"ok": True, "soil_pct": rover.probe_soil()}
            ok, msg = (rover.probe.deploy() if a.get("down")
                       else rover.probe.retract())
            return {"ok": ok, "message": msg}
        elif cmd == "steer_centre":
            rover.drive_hw.centre_steering()
        elif cmd == "spray_arm":
            rover.set_spray_armed(bool(a.get("on", False)))
        elif cmd == "auto_spray":
            rover.set_auto_spray(bool(a.get("on", False)))
        elif cmd == "spray_now":
            secs = a.get("seconds")
            ok, msg = rover.spray_sections(
                a.get("sections") or ["centre"],
                float(secs) if secs else None)
            return {"ok": ok, "message": msg}
        elif cmd == "spray_stop":
            ok, msg = rover.spray_stop()
            return {"ok": ok, "message": msg}
        elif cmd == "lamps":
            rover.set_lamps(bool(a.get("on", False)))
        elif cmd == "probe_soil":
            return {"ok": True, "soil_pct": rover.probe_soil()}
        elif cmd == "mission_start":
            # autostart off, or switching to AUTO would open a run of its own
            # and this one would be the second row in the history
            rover.set_mode("AUTO", autostart=False)
            rover.mission.start(int(a.get("plants", 0)))
        elif cmd == "mission_stop":
            rover.mission.stop("stopped from the website")
        elif cmd == "answer":
            rover.mission.answer(bool(a.get("approve", False)))
        elif cmd == "clear_alerts":
            st.set(alerts=[])
            rover.db.mark_alerts_seen()
        elif cmd == "mark_home":
            rover.mark_home()
        elif cmd == "go_home":
            rover.return_home()
        elif cmd == "stop_home":
            rover.stop_returning()
        elif cmd == "record":
            if a.get("on"):
                rover.recorder.start(rover.mission.mission_id)
            else:
                rover.recorder.stop()
        else:
            return {"ok": False, "error": "unknown command: %s" % cmd}
        return {"ok": True}

    # ---------------------------------------------------------------- history
    @app.get("/api/field")
    def field(request: Request):
        need(request)
        rows = rover.db.field()
        for r in rows:
            r["healthy"] = bool(r.get("healthy"))
            r["sprayed"] = bool(r.get("sprayed"))
        return {"ok": True, "plants": rows}

    @app.get("/api/plant/{plot}")
    def plant(request: Request, plot: str):
        need(request)
        rows = rover.db.plant_history(plot)
        if not rows:
            raise HTTPException(404, "no such plant")
        for r in rows:
            r["healthy"] = bool(r.get("healthy"))
            r["sprayed"] = bool(r.get("sprayed"))
        return {"ok": True, "plot": plot, "history": rows,
                "summary": rover.db.plant_counts(plot)}

    @app.get("/api/history")
    def history(request: Request, days: int = 14):
        need(request)
        return {"ok": True, "days": rover.db.days(max(1, min(120, days))),
                "problems": rover.db.problem_tally(max(1, min(365, days * 3)))}

    @app.get("/api/samples")
    def samples(request: Request, hours: float = 6.0):
        need(request)
        rows = rover.db.samples_since(max(0.1, min(720.0, hours)) * 3600)
        # thin it out so a week of readings is still a chart and not 60 000 points
        step = max(1, len(rows) // 400)
        return {"ok": True, "samples": rows[::step]}

    @app.get("/api/missions")
    def missions(request: Request):
        need(request)
        return {"ok": True, "missions": rover.db.missions()}

    @app.get("/api/recordings")
    def recordings(request: Request):
        need(request)
        rows = rover.db.recordings()
        for r in rows:
            p = os.path.join(rover.video_dir, str(r.get("path") or ""))
            r["exists"] = os.path.exists(p)
            r["size_mb"] = round(os.path.getsize(p) / 1e6, 1) if r["exists"] else 0
        return {"ok": True, "recordings": rows}

    @app.get("/api/alerts")
    def alerts(request: Request):
        need(request)
        return {"ok": True, "alerts": rover.db.alerts()}

    # ------------------------------------------------------- the training set
    @app.get("/api/photos")
    def photos(request: Request, limit: int = 500):
        need(request)
        rows = rover.db.q(
            """SELECT photo, label, common_name, plot, ts, confidence, healthy
               FROM plants WHERE photo != '' ORDER BY ts DESC LIMIT ?""",
            (max(1, min(5000, limit)),))
        out = []
        for r in rows:
            if os.path.exists(os.path.join(rover.photo_dir, str(r["photo"]))):
                r["healthy"] = bool(r["healthy"])
                out.append(r)
        return {"ok": True, "photos": out, "total": len(out)}

    @app.get("/api/photoset.zip")
    def photoset(request: Request):
        """Every photo it has taken, in folders named after what it called them.

        This is the shape a classifier wants to be trained on. Go through the
        folders, move the wrong ones into the right folder, and you have a
        training set of YOUR plants under YOUR light - which is the only kind
        worth training on. docs/TRAINING_THE_MODEL.md takes it from there.
        """
        need(request)
        rows = rover.db.q("SELECT photo, label, plot, ts FROM plants "
                          "WHERE photo != '' ORDER BY ts")
        buf = io.BytesIO()
        n = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            for r in rows:
                src = os.path.join(rover.photo_dir, str(r["photo"]))
                if not os.path.exists(src):
                    continue
                label = str(r["label"] or "unknown")
                if label == "not_checked":
                    label = "_not_sorted_yet"
                stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(r["ts"]))
                z.write(src, "%s/%s_%s.jpg" % (label, r["plot"] or "plant", stamp))
                n += 1
            z.writestr("READ_ME_FIRST.txt", PHOTOSET_NOTE % n)
        buf.seek(0)
        name = "agrirover_photos_%s.zip" % time.strftime("%Y%m%d")
        return StreamingResponse(
            buf, media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="%s"' % name})

    # ----------------------------------------------------------------- report
    @app.get("/api/report")
    def report(request: Request):
        need(request)
        rows = []
        for p in rover.state.plants:
            d = p.as_dict()
            d["time_text"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                           time.localtime(p.time))
            rows.append(d)
        return {
            "summary": {
                "plants_checked": len(rows),
                "problems_found": sum(1 for r in rows if not r["healthy"]),
                "plants_sprayed": sum(1 for r in rows if r["sprayed"]),
                "total_ml": round(rover.sprayer.used_ml, 1),
                "distance_m": rover.state.telemetry.distance_m,
            },
            "plants": rows,
        }

    @app.get("/api/report.csv")
    def report_csv(request: Request, days: int = 90):
        need(request)
        rows = rover.db.q(
            "SELECT * FROM plants WHERE ts > ? ORDER BY ts DESC",
            (time.time() - max(1, days) * 86400,))
        buf = io.StringIO()
        cols = ["ts", "when", "plot", "label", "common_name", "confidence",
                "healthy", "severity", "action", "dose_ml", "sprayed",
                "soil_pct", "treatment", "advice", "photo", "x", "y"]
        w = csv.writer(buf)
        w.writerow(["time", "date and time", "plant", "what it found",
                    "name", "how sure", "healthy", "how bad", "what it did",
                    "ml used", "sprayed", "soil %", "treatment",
                    "what you should do", "photo", "x m", "y m"])
        for r in rows:
            r["when"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.localtime(r.get("ts", 0)))
            w.writerow([r.get(c, "") for c in cols])
        name = "agrirover_%s.csv" % time.strftime("%Y%m%d")
        return PlainTextResponse(
            buf.getvalue(), media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="%s"' % name})

    # --------------------------------------------------------------- settings
    @app.get("/api/settings")
    def get_settings(request: Request):
        u = need(request)
        cam = rover.cfg["cameras"]["front"]
        return {"ok": True, "settings": rover.settings.all(), "user": u,
                "fitted": {"encoders": rover.enc.live, "imu": rover.imu.live,
                           "range": rover.rangef.live, "probe": rover.probe.live,
                           "boom": rover.boom.live, "drive": rover.drive_hw.live,
                           "camera_measured": float(cam.get("height_mm", 0) or 0) > 0},
                "why": {"encoders": rover.enc.reason, "imu": rover.imu.reason,
                        "range": rover.rangef.reason,
                        "ai": rover.classifier.reason,
                        "probe": rover.probe.reason,
                        "boom": rover.boom.reason,
                        "drive": rover.drive_hw.reason,
                        "camera_measured":
                            "set height_mm, pitch_deg and vfov_deg for the "
                            "front camera in config.yaml, measured off the "
                            "real rover"},
                "steering": rover.steering.describe()}

    @app.post("/api/settings")
    async def post_settings(request: Request, body: Dict[str, Any]):
        need(request)
        changes = body.get("changes", body) or {}
        changes.pop("password", None)
        bad = rover.settings.set_many(changes)
        return {"ok": not bad, "refused": bad, "settings": rover.settings.all()}

    @app.post("/api/notify/test")
    def notify_test(request: Request):
        need(request)
        ok, msg = rover.notify.test()
        return {"ok": ok, "message": msg}

    # ---------------------------------------------------------------- patrols
    @app.get("/api/patrols")
    def get_patrols(request: Request):
        need(request)
        rows = rover.db.patrols()
        for r in rows:
            r["enabled"] = bool(r.get("enabled"))
            r["spray"] = bool(r.get("spray"))
        nxt = rover.patrols.next_due()
        return {"ok": True, "patrols": rows, "day_names": DAY_NAMES,
                "next": {"name": nxt.get("name"), "at": nxt["next_run"]} if nxt else None}

    @app.post("/api/patrols")
    async def save_patrol(request: Request, body: Dict[str, Any]):
        need(request)
        if body.get("delete"):
            rover.db.delete_patrol(int(body["delete"]))
            return {"ok": True}
        pid = rover.db.save_patrol(body)
        rover.state.say("Timetable changed")
        return {"ok": True, "id": pid}

    return app
