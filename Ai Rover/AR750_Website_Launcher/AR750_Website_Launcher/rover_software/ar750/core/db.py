"""The rover's memory: every plant, every outing, every reading, kept.

One SQLite file at data/ar750.db. No server, no setup, and you can copy it
onto a USB stick and open it on any computer.

The point of keeping it is the history. A plant is not just "sick today" - it is
"the third plant in row 2, which had early blight three weeks ago, was sprayed,
and has looked fine since". The website is built on top of these tables.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started REAL NOT NULL,
  ended REAL,
  kind TEXT DEFAULT 'manual',        -- manual | patrol
  plants_checked INTEGER DEFAULT 0,
  problems INTEGER DEFAULT 0,
  sprayed_ml REAL DEFAULT 0,
  distance_m REAL DEFAULT 0,
  note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS plants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id INTEGER,
  plot TEXT,                         -- "r1p07": which plant in the field
  ts REAL NOT NULL,
  x REAL, y REAL,
  label TEXT, common_name TEXT,
  confidence REAL,
  healthy INTEGER,
  severity TEXT,
  treatment TEXT,
  advice TEXT,
  action TEXT,
  dose_ml REAL DEFAULT 0,
  sprayed INTEGER DEFAULT 0,
  soil_pct REAL,
  photo TEXT
);
CREATE INDEX IF NOT EXISTS plants_plot ON plants(plot);
CREATE INDEX IF NOT EXISTS plants_ts ON plants(ts);
CREATE INDEX IF NOT EXISTS plants_mission ON plants(mission_id);

CREATE TABLE IF NOT EXISTS samples (
  ts REAL NOT NULL,
  battery_v REAL, battery_pct REAL, soil_pct REAL, tank_pct REAL,
  speed_mps REAL, distance_m REAL, cpu_temp_c REAL, current_a REAL
);
CREATE INDEX IF NOT EXISTS samples_ts ON samples(ts);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  level TEXT, text TEXT, plant_id INTEGER, seen INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS alerts_ts ON alerts(ts);

CREATE TABLE IF NOT EXISTS recordings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id INTEGER,
  path TEXT, kind TEXT, started REAL, ended REAL, frames INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS patrols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT, days TEXT, at TEXT,     -- days "0,1,2"  at "07:00"
  plants INTEGER DEFAULT 0,
  spray INTEGER DEFAULT 0,
  enabled INTEGER DEFAULT 1,
  last_run REAL DEFAULT 0
);
"""


class DB:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._lock = threading.RLock()
        self._c = sqlite3.connect(path, check_same_thread=False)
        self._c.row_factory = sqlite3.Row
        with self._lock:
            self._c.executescript(SCHEMA)
            self._c.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._c.commit()
                self._c.close()
            except Exception:
                pass

    # ------------------------------------------------------------- plumbing
    def q(self, sql: str, args=()) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._c.execute(sql, args)
            return [dict(r) for r in cur.fetchall()]

    def one(self, sql: str, args=()) -> Optional[Dict[str, Any]]:
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def run(self, sql: str, args=()) -> int:
        with self._lock:
            cur = self._c.execute(sql, args)
            self._c.commit()
            return int(cur.lastrowid or 0)

    # -------------------------------------------------------------- missions
    def start_mission(self, kind: str = "manual") -> int:
        return self.run("INSERT INTO missions (started, kind) VALUES (?,?)",
                        (time.time(), kind))

    def end_mission(self, mid: int, **kw) -> None:
        if not mid:
            return
        fields = ["ended=?"]
        args: List[Any] = [time.time()]
        for k in ("plants_checked", "problems", "sprayed_ml", "distance_m", "note"):
            if k in kw:
                fields.append("%s=?" % k)
                args.append(kw[k])
        args.append(mid)
        self.run("UPDATE missions SET %s WHERE id=?" % ",".join(fields), args)

    def missions(self, limit: int = 40) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM missions ORDER BY started DESC LIMIT ?",
                      (limit,))

    # ---------------------------------------------------------------- plants
    def add_plant(self, rec: Dict[str, Any], mission_id: int, plot: str) -> int:
        return self.run(
            """INSERT INTO plants (mission_id, plot, ts, x, y, label, common_name,
               confidence, healthy, severity, treatment, advice, action, dose_ml,
               sprayed, soil_pct, photo)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mission_id, plot, rec.get("time", time.time()),
             rec.get("x_m"), rec.get("y_m"), rec.get("label"),
             rec.get("common_name", ""), rec.get("confidence"),
             1 if rec.get("healthy") else 0, rec.get("severity"),
             rec.get("treatment"), rec.get("advice"), rec.get("action"),
             rec.get("dose_ml", 0), 1 if rec.get("sprayed") else 0,
             rec.get("soil_pct"), rec.get("photo")))

    def update_plant(self, row_id: int, **kw) -> None:
        if not row_id or not kw:
            return
        cols = ", ".join("%s=?" % k for k in kw)
        self.run("UPDATE plants SET %s WHERE id=?" % cols,
                 list(kw.values()) + [row_id])

    def plant_history(self, plot: str, limit: int = 60) -> List[Dict[str, Any]]:
        return self.q("SELECT * FROM plants WHERE plot=? ORDER BY ts DESC LIMIT ?",
                      (plot, limit))

    def field(self) -> List[Dict[str, Any]]:
        """The latest look at every plant in the field, for the map."""
        return self.q("""
            SELECT p.* FROM plants p
            JOIN (SELECT plot, MAX(ts) AS t FROM plants GROUP BY plot) last
              ON p.plot = last.plot AND p.ts = last.t
            ORDER BY p.plot""")

    def plant_counts(self, plot: str) -> Dict[str, Any]:
        r = self.one("""SELECT COUNT(*) n, SUM(1-healthy) ill, SUM(sprayed) sp,
                        SUM(dose_ml) ml, MIN(ts) first, MAX(ts) last
                        FROM plants WHERE plot=?""", (plot,))
        return r or {}

    # ----------------------------------------------------------- the numbers
    def sample(self, t) -> None:
        self.run("""INSERT INTO samples (ts, battery_v, battery_pct, soil_pct,
                    tank_pct, speed_mps, distance_m, cpu_temp_c, current_a)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                 (time.time(), t.battery_v, t.battery_pct, t.soil_pct,
                  t.tank_pct, t.speed_mps, t.distance_m, t.cpu_temp_c,
                  t.current_a))

    def samples_since(self, seconds: float, step: int = 1) -> List[Dict[str, Any]]:
        rows = self.q("SELECT * FROM samples WHERE ts > ? ORDER BY ts",
                      (time.time() - seconds,))
        return rows[::max(1, step)]

    def days(self, n: int = 14) -> List[Dict[str, Any]]:
        """Plants checked and problems found, per day, for the chart."""
        return self.q("""
            SELECT date(ts,'unixepoch','localtime') AS day,
                   COUNT(*) AS checked,
                   SUM(1-healthy) AS problems,
                   SUM(sprayed) AS sprayed,
                   SUM(dose_ml) AS ml
            FROM plants WHERE ts > ?
            GROUP BY day ORDER BY day""",
            (time.time() - n * 86400,))

    def problem_tally(self, n_days: int = 30) -> List[Dict[str, Any]]:
        return self.q("""
            SELECT label, common_name, COUNT(*) AS n
            FROM plants WHERE healthy=0 AND ts > ?
            GROUP BY label ORDER BY n DESC LIMIT 12""",
            (time.time() - n_days * 86400,))

    # ---------------------------------------------------------------- alerts
    def add_alert(self, level: str, text: str, plant_id=None) -> int:
        return self.run(
            "INSERT INTO alerts (ts, level, text, plant_id) VALUES (?,?,?,?)",
            (time.time(), level, text, plant_id))

    def alerts(self, limit: int = 60, unseen_only: bool = False):
        sql = "SELECT * FROM alerts %s ORDER BY ts DESC LIMIT ?" % (
            "WHERE seen=0" if unseen_only else "")
        return self.q(sql, (limit,))

    def mark_alerts_seen(self) -> None:
        self.run("UPDATE alerts SET seen=1 WHERE seen=0")

    # ------------------------------------------------------------ recordings
    def add_recording(self, mission_id: int, path: str, kind: str,
                      started: float, ended: float, frames: int) -> int:
        return self.run("""INSERT INTO recordings
                        (mission_id, path, kind, started, ended, frames)
                        VALUES (?,?,?,?,?,?)""",
                        (mission_id, path, kind, started, ended, frames))

    def recordings(self, limit: int = 40):
        return self.q("SELECT * FROM recordings ORDER BY started DESC LIMIT ?",
                      (limit,))

    # --------------------------------------------------------------- patrols
    def patrols(self):
        return self.q("SELECT * FROM patrols ORDER BY at")

    def save_patrol(self, p: Dict[str, Any]) -> int:
        if p.get("id"):
            self.run("""UPDATE patrols SET name=?, days=?, at=?, plants=?,
                        spray=?, enabled=? WHERE id=?""",
                     (p.get("name", ""), p.get("days", ""), p.get("at", "07:00"),
                      int(p.get("plants", 0)), 1 if p.get("spray") else 0,
                      1 if p.get("enabled", True) else 0, int(p["id"])))
            return int(p["id"])
        return self.run("""INSERT INTO patrols (name, days, at, plants, spray,
                        enabled) VALUES (?,?,?,?,?,?)""",
                        (p.get("name", ""), p.get("days", ""),
                         p.get("at", "07:00"), int(p.get("plants", 0)),
                         1 if p.get("spray") else 0,
                         1 if p.get("enabled", True) else 0))

    def delete_patrol(self, pid: int) -> None:
        self.run("DELETE FROM patrols WHERE id=?", (pid,))

    def mark_patrol_run(self, pid: int) -> None:
        self.run("UPDATE patrols SET last_run=? WHERE id=?", (time.time(), pid))

    # ------------------------------------------------------------ tidying up
    def prune(self, keep_days: int = 30) -> None:
        cut = time.time() - keep_days * 86400
        self.run("DELETE FROM samples WHERE ts < ?", (cut,))
        self.run("DELETE FROM alerts WHERE ts < ? AND seen=1", (cut,))
