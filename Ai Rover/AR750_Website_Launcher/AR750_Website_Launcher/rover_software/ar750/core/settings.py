"""Settings you change from the website, not by editing files.

config.yaml holds the defaults - pins, wiring, calibration, the things you set
once when you build the rover. Everything you might want to change while you are
standing in the garden lives here instead, gets saved to data/settings.json, and
takes effect immediately.

The hard limits at the bottom of this file are the exception. Those are in the
code on purpose: no page, no password and no saved file can raise them.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Limits the website can never exceed, whatever anyone types into it.
# If you really need to change one, you have to edit this file and restart,
# which is exactly the amount of friction a limit like this should have.
# ---------------------------------------------------------------------------
HARD = {
    "boom.max_l_per_ha":        600.0,   # litres per hectare, ever
    "boom.max_ml_per_session":  6000.0,  # ml in one outing
    "drive.max_speed_mps":      1.20,    # m/s. It is a 120 kg machine in a
                                         # vegetable bed, not a go kart.
    "ai.auto_spray_confidence": 0.70,    # it may never spray below this
}

# What the website is allowed to edit: key -> (type, low, high)
EDITABLE: Dict[str, tuple] = {
    # driving
    "drive.max_speed_mps":       ("float", 0.02, HARD["drive.max_speed_mps"]),
    "drive.speed_limit":         ("float", 0.10, 1.0),
    "drive.reverse_on_low_batt": ("bool",  None, None),

    # spraying
    "boom.target_l_per_ha":      ("float", 20.0, 600.0),
    "boom.max_l_per_ha":         ("float", 20.0, HARD["boom.max_l_per_ha"]),
    "boom.pwm_hz":               ("float", 2.0, 50.0),
    "boom.min_duty":             ("float", 0.05, 0.9),
    "boom.max_ml_per_session":   ("float", 50.0, HARD["boom.max_ml_per_session"]),
    "boom.ml_per_min_per_nozzle": ("float", 20.0, 3000.0),
    "boom.tank_litres":          ("float", 0.5, 50.0),
    "boom.band_seconds":         ("float", 0.2, 10.0),
    "boom.require_arm_switch":   ("bool",  None, None),

    # the soil probe
    "probe.every_n_plants":      ("int",   0, 200),
    "probe.settle_s":            ("float", 0.2, 30.0),
    "probe.timeout_s":           ("float", 5.0, 120.0),

    # deciding
    "ai.min_confidence":         ("float", 0.30, 0.99),
    "ai.auto_spray_confidence":  ("float", HARD["ai.auto_spray_confidence"], 0.99),
    "ai.inspect_seconds":        ("float", 0.5, 20.0),
    "ai.plant_spacing_mm":       ("int",   50, 3000),
    "ai.row_length_m":           ("float", 1.0, 500.0),
    "ai.rows":                   ("int",   1, 40),
    "ai.row_gap_mm":             ("int",   200, 5000),

    # looking after itself
    "safety.battery.warn_v":     ("float", 6.0, 25.0),
    "safety.battery.stop_v":     ("float", 6.0, 25.0),
    "safety.return_home_pct":    ("int",   0, 90),
    "safety.tilt_stop_deg":      ("float", 5.0, 60.0),

    # recording
    "record.enabled":            ("bool",  None, None),
    "record.every_seconds":      ("float", 0.5, 60.0),
    "record.keep_days":          ("int",   1, 365),

    # telling you about it
    "notify.on_problem":         ("bool",  None, None),
    "notify.on_finish":          ("bool",  None, None),
    "notify.on_low_battery":     ("bool",  None, None),
    "notify.on_estop":           ("bool",  None, None),
    "notify.telegram_token":     ("str",   None, None),
    "notify.telegram_chat_id":   ("str",   None, None),
}

# a few settings are called one thing on the page and another in config.yaml
ALIASES = {
    "drive.max_speed_mps": "rover.max_speed_mps",
}

DEFAULTS: Dict[str, Any] = {
    "drive.speed_limit": 0.6,
    "drive.reverse_on_low_batt": True,
    "safety.return_home_pct": 25,
    "record.enabled": True,
    "record.every_seconds": 2.0,
    "record.keep_days": 30,
    "notify.on_problem": True,
    "notify.on_finish": True,
    "notify.on_low_battery": True,
    "notify.on_estop": True,
    "notify.telegram_token": "",
    "notify.telegram_chat_id": "",
}


def _dig(d: dict, path: str, default=None):
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _plant(d: dict, path: str, value) -> None:
    parts = path.split(".")
    cur = d
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


class Settings:
    """config.yaml underneath, your saved changes on top."""

    def __init__(self, cfg: dict, path: str):
        self.cfg = cfg
        self.path = path
        self._lock = threading.RLock()
        self._over: Dict[str, Any] = {}
        self._watchers = []
        self.load()

    # ------------------------------------------------------------------ read
    def get(self, key: str, default=None):
        with self._lock:
            if key in self._over:
                return self._over[key]
        v = _dig(self.cfg, key, None)
        if v is not None:
            return v
        if key in ALIASES:
            v = _dig(self.cfg, ALIASES[key], None)
            if v is not None:
                return v
        if key in DEFAULTS:
            return DEFAULTS[key]
        return default

    def all(self) -> Dict[str, Any]:
        """Every editable setting, with its limits, for the settings page."""
        out = {}
        for key, (kind, lo, hi) in EDITABLE.items():
            out[key] = {"value": self.get(key), "type": kind,
                        "min": lo, "max": hi,
                        "hard_max": HARD.get(key)}
        return out

    # ----------------------------------------------------------------- write
    def set_many(self, changes: Dict[str, Any]) -> Dict[str, str]:
        """Returns {key: why it was refused} for anything not applied."""
        bad: Dict[str, str] = {}
        good: Dict[str, Any] = {}

        for key, raw in changes.items():
            if key not in EDITABLE:
                bad[key] = "not a setting you can change from here"
                continue
            kind, lo, hi = EDITABLE[key]
            try:
                if kind == "bool":
                    val: Any = bool(raw)
                elif kind == "int":
                    val = int(raw)
                elif kind == "float":
                    val = float(raw)
                else:
                    val = str(raw)[:300]
            except (TypeError, ValueError):
                bad[key] = "that is not a %s" % kind
                continue
            if lo is not None and val < lo:
                bad[key] = "the lowest allowed is %s" % lo
                continue
            if hi is not None and val > hi:
                bad[key] = "the highest allowed is %s" % hi
                continue
            good[key] = val

        # the two battery thresholds have to stay in the right order
        stop = good.get("safety.battery.stop_v", self.get("safety.battery.stop_v"))
        warn = good.get("safety.battery.warn_v", self.get("safety.battery.warn_v"))
        if stop is not None and warn is not None and float(stop) >= float(warn):
            for k in ("safety.battery.stop_v", "safety.battery.warn_v"):
                good.pop(k, None)
                bad[k] = "the stop voltage must be below the warning voltage"

        if good:
            with self._lock:
                self._over.update(good)
                self._save()
            for fn in list(self._watchers):
                try:
                    fn(good)
                except Exception:
                    pass
        return bad

    def on_change(self, fn) -> None:
        self._watchers.append(fn)

    # ------------------------------------------------------------------ disk
    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                with self._lock:
                    self._over = {k: v for k, v in data.items() if k in EDITABLE}
        except (OSError, ValueError):
            pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._over, f, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    # ------------------------------------------------- push back into config
    def apply_to_config(self) -> None:
        """Copy the live values into the config dict the hardware reads."""
        with self._lock:
            items = dict(self._over)
        for key, val in items.items():
            _plant(self.cfg, key, val)
        # a couple of names differ between the page and the config file
        _plant(self.cfg, "rover.max_speed_mps",
               float(self.get("drive.max_speed_mps",
                              _dig(self.cfg, "rover.max_speed_mps", 0.12))))
