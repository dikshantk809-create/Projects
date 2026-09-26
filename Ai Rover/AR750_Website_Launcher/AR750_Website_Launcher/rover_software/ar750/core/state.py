"""One place that holds what the rover is doing right now.

Everything else reads and writes this. It is guarded by a lock because the
control loop, the RC reader, the camera threads and the web server all touch it.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


class Mode:
    IDLE = "IDLE"          # powered, nothing moving
    MANUAL = "MANUAL"      # the 6 channel remote drives it
    AUTO = "AUTO"          # it drives itself down the row
    HOLD = "HOLD"          # auto paused, holding position
    ESTOP = "ESTOP"        # emergency stop, needs a deliberate reset


@dataclass
class Telemetry:
    battery_v: float = 0.0
    battery_pct: float = 0.0
    current_a: float = 0.0
    soil_pct: Optional[float] = None
    tank_pct: float = 100.0
    tank_ml: float = 1750.0
    heading_deg: float = 0.0
    tilt_deg: float = 0.0
    speed_mps: float = 0.0
    distance_m: float = 0.0
    x_m: float = 0.0            # odometry, metres from where it started
    y_m: float = 0.0
    range_front_cm: Optional[float] = None
    turn_radius_mm: Optional[float] = None
    cpu_temp_c: float = 0.0
    uptime_s: float = 0.0
    # True when the distance came from wheel encoders. False means it was
    # worked out from what the motors were told to do, which drifts - the
    # website says so rather than letting you believe a number that is guessed.
    odometry_measured: bool = False
    # False on a real rover with no ADC wired: the battery number is then NOT
    # a measurement, the website says so, and nothing acts on it.
    battery_measured: bool = True
    # "wet" / "dry" from a soil sensor's digital output, when that is all
    # there is (no ADC for a percentage)
    soil_state: Optional[str] = None


@dataclass
class SteerState:
    """This machine steers like a car, so this is what there is to know."""
    wheel_deg: float = 0.0          # road wheel angle, + is left
    servo_deg: float = 0.0          # what the servo was told
    stick: float = 0.0              # -1..1 as asked for
    turn_radius_mm: Optional[float] = None
    centred: bool = True


@dataclass
class ProbeState:
    state: str = "unknown"          # unknown | up | down | moving | jammed
    moving: str = "stopped"
    busy: bool = False
    fitted: bool = False
    last_read_pct: Optional[float] = None
    last_read_at: float = 0.0


@dataclass
class PlantRecord:
    """One plant the rover has looked at."""
    id: int
    time: float
    x_m: float
    y_m: float
    label: str = "unknown"
    confidence: float = 0.0
    healthy: bool = True
    severity: str = "none"          # none | mild | moderate | severe
    treatment: str = ""
    dose_ml: float = 0.0
    action: str = "none"            # none | sprayed | weed_pulled | needs_you
    advice: str = ""
    photo: str = ""
    soil_pct: Optional[float] = None
    sprayed: bool = False
    common_name: str = ""
    plot: str = ""                  # which plant in the field, eg "r1p07"
    db_id: int = 0                  # its row in the history

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RoverState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.started = time.time()

        self.mode: str = Mode.IDLE
        self.estop: bool = False
        self.estop_reason: str = ""
        self.spray_armed: bool = False
        self.auto_spray: bool = False      # let it spray without asking
        self.sim: bool = False             # True = the wheels are not driven
        self.sim_parts: List[str] = []     # parts still pretending, if any

        self.telemetry = Telemetry()
        self.steer = SteerState()
        self.probe = ProbeState()

        # one throttle for both axles: it is four wheel drive, not skid steer
        self.drive_throttle: float = 0.0   # -1..1 commanded
        self.steer_deg: float = 0.0        # road wheel angle
        self.steer_stick: float = 0.0
        self.boom_sections: List[str] = []
        self.pump_on: bool = False
        self.lamps_on: bool = False

        self.rc_live: bool = False
        self.rc_channels: List[float] = [0.0] * 8

        self.mission: Dict[str, Any] = {
            "running": False,
            "step": "idle",
            "plants_done": 0,
            "plants_target": 0,
            "row": 0,
            "sprayed_ml": 0.0,
            "message": "",
        }

        self.plants: List[PlantRecord] = []
        self.alerts: List[Dict[str, Any]] = []
        self.pending: Optional[Dict[str, Any]] = None   # waiting for your yes/no
        self.log: List[Dict[str, Any]] = []
        self._plant_seq = 0

    # ------------------------------------------------------------ helpers
    def lock(self):
        return self._lock

    def set(self, **kw) -> None:
        with self._lock:
            for k, v in kw.items():
                setattr(self, k, v)

    def next_plant_id(self) -> int:
        with self._lock:
            self._plant_seq += 1
            return self._plant_seq

    def add_plant(self, rec: PlantRecord) -> None:
        with self._lock:
            self.plants.append(rec)
            if len(self.plants) > 500:
                self.plants = self.plants[-500:]

    def add_alert(self, level: str, text: str, **extra) -> None:
        with self._lock:
            self.alerts.insert(0, dict(time=time.time(), level=level,
                                       text=text, **extra))
            self.alerts = self.alerts[:60]

    def say(self, text: str, level: str = "info") -> None:
        with self._lock:
            self.log.insert(0, dict(time=time.time(), level=level, text=text))
            self.log = self.log[:300]

    def trip_estop(self, reason: str) -> None:
        with self._lock:
            if not self.estop:
                self.estop = True
                self.estop_reason = reason
                self.mode = Mode.ESTOP
                self.drive_throttle = 0.0
                self.pump_on = False
                self.mission["running"] = False
                self.say("EMERGENCY STOP: " + reason, "error")
                self.add_alert("error", "Emergency stop: " + reason)

    def clear_estop(self) -> None:
        with self._lock:
            self.estop = False
            self.estop_reason = ""
            self.mode = Mode.IDLE
            self.say("Emergency stop cleared, rover is idle", "warn")

    # ------------------------------------------------------- for the website
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            t = self.telemetry
            t.uptime_s = time.time() - self.started
            return {
                "t": time.time(),
                "mode": self.mode,
                "estop": self.estop,
                "estop_reason": self.estop_reason,
                "sim": self.sim,
                "sim_parts": list(self.sim_parts),
                "spray_armed": self.spray_armed,
                "auto_spray": self.auto_spray,
                "pump_on": self.pump_on,
                "lamps_on": self.lamps_on,
                "rc_live": self.rc_live,
                "rc": [round(c, 3) for c in self.rc_channels],
                "drive": {"throttle": round(self.drive_throttle, 3),
                          "steer_deg": round(self.steer_deg, 1),
                          "steer_stick": round(self.steer_stick, 3)},
                "telemetry": asdict(t),
                "steer": asdict(self.steer),
                "probe": asdict(self.probe),
                "boom_sections": list(self.boom_sections),
                "mission": dict(self.mission),
                "pending": self.pending,
                "plants": [p.as_dict() for p in self.plants[-40:]],
                "alerts": self.alerts[:12],
                "log": self.log[:25],
            }
