"""Patrols: "check the row every morning at seven", without you being there.

A patrol only ever starts when the rover is genuinely ready: parked, no
emergency stop, enough battery, and nothing already running. If any of those is
not true it says why in the log and tries again at the next slot rather than
forcing it.

Spraying during a patrol is off unless you tick it for that patrol, and even
then the pump has to be armed. An unattended rover that can spray on its own is
not something to switch on by accident.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from .state import Mode

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class Patrols:
    def __init__(self, rover):
        self.r = rover
        self.db = rover.db
        self.state = rover.state
        self._run = True
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def stop(self) -> None:
        self._run = False

    # ------------------------------------------------------------------ next
    def next_due(self) -> Optional[dict]:
        soonest, when = None, None
        for p in self.db.patrols():
            if not p.get("enabled"):
                continue
            t = self._next_time(p)
            if t and (when is None or t < when):
                soonest, when = p, t
        if not soonest:
            return None
        out = dict(soonest)
        out["next_run"] = when
        return out

    def _next_time(self, p: dict) -> Optional[float]:
        try:
            hh, mm = [int(x) for x in str(p.get("at", "07:00")).split(":")]
        except ValueError:
            return None
        days = self._days(p)
        now = time.localtime()
        for ahead in range(0, 8):
            day = time.localtime(time.time() + ahead * 86400)
            if days and day.tm_wday not in days:
                continue
            t = time.mktime((day.tm_year, day.tm_mon, day.tm_mday, hh, mm, 0,
                             0, 0, -1))
            if t > time.time() + 30 or (ahead == 0 and t > time.time()):
                return t
        return None

    @staticmethod
    def _days(p: dict):
        raw = str(p.get("days", "") or "").strip()
        if not raw:
            return set(range(7))
        out = set()
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and 0 <= int(part) <= 6:
                out.add(int(part))
        return out or set(range(7))

    # ------------------------------------------------------------------ loop
    def _loop(self) -> None:
        time.sleep(5)
        while self._run:
            try:
                self._check()
            except Exception as e:                        # never kill the thread
                try:
                    self.state.say("patrol timer: %s" % e, "warn")
                except Exception:
                    pass
            time.sleep(20)

    def _check(self) -> None:
        now = time.time()
        lt = time.localtime(now)
        for p in self.db.patrols():
            if not p.get("enabled"):
                continue
            days = self._days(p)
            if lt.tm_wday not in days:
                continue
            try:
                hh, mm = [int(x) for x in str(p.get("at", "07:00")).split(":")]
            except ValueError:
                continue
            due = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, hh, mm, 0,
                               0, 0, -1))
            # fire inside a two minute window, and only once per day
            if not (0 <= now - due <= 120):
                continue
            if now - float(p.get("last_run") or 0) < 3600:
                continue
            self.db.mark_patrol_run(int(p["id"]))
            self._fire(p)

    def _fire(self, p: dict) -> None:
        name = p.get("name") or "patrol"
        why = self._not_ready()
        if why:
            self.state.say("Patrol '%s' skipped: %s" % (name, why), "warn")
            self.state.add_alert("warn", "Patrol '%s' skipped: %s" % (name, why))
            self.db.add_alert("warn", "Patrol '%s' skipped: %s" % (name, why))
            return

        if not p.get("spray"):
            # inspection only unless you asked for spraying on this patrol
            self.r.set_spray_armed(False)
        self.state.say("Patrol '%s' starting" % name)
        self.r.set_mode(Mode.AUTO)
        self.r.mission.start(int(p.get("plants") or 0), kind="patrol")

    def _not_ready(self) -> str:
        st = self.state
        if st.estop:
            return "the emergency stop is on"
        if st.mission.get("running"):
            return "it is already out"
        if st.mode not in (Mode.IDLE, Mode.HOLD):
            return "it is in %s" % st.mode
        if st.rc_live:
            return "the remote is on, so you are driving"
        pct = st.telemetry.battery_pct
        if pct is not None and pct < 40:
            return "the battery is at %.0f%%" % pct
        return ""
