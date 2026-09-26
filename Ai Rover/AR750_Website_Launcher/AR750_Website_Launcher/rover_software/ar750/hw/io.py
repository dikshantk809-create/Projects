"""The small stuff: pump, valves, lamps, ADC, battery, soil probe, front range.

Everything degrades to simulation if the board is not there, so the rest of the
software behaves the same on a laptop as it does on the rover.
"""
from __future__ import annotations

import math
import random
import threading
import time
from typing import Optional

try:
    import pigpio                                    # type: ignore
except Exception:                                    # pragma: no cover
    pigpio = None

try:
    import board                                     # type: ignore
    import busio                                     # type: ignore
    import adafruit_ads1x15.ads1115 as ADS           # type: ignore
    from adafruit_ads1x15.analog_in import AnalogIn  # type: ignore
except Exception:                                    # pragma: no cover
    ADS = AnalogIn = board = busio = None


class Outputs:
    """Pump, the two spray valves, and the lamps."""

    def __init__(self, spray_cfg: dict, lamp_cfg: dict, sim: bool = False):
        self.sim = sim or pigpio is None
        self.cfg = spray_cfg
        self.pins = {
            "pump": spray_cfg.get("pump_pin"),
            "front": spray_cfg.get("front_valve_pin"),
            "rear": spray_cfg.get("rear_valve_pin"),
            "lamp_front": lamp_cfg.get("front_pin"),
            "lamp_rear": lamp_cfg.get("rear_pin"),
        }
        self.state = {k: False for k in self.pins}
        self._pi = None
        if not self.sim:                             # pragma: no cover
            self._pi = pigpio.pi()
            if not self._pi.connected:
                self._pi = None
                self.sim = True
            else:
                for p in self.pins.values():
                    if p is not None:
                        self._pi.set_mode(p, pigpio.OUTPUT)
                        self._pi.write(p, 0)

    def set(self, what: str, on: bool) -> None:
        if what not in self.pins:
            return
        self.state[what] = bool(on)
        if self._pi is not None and self.pins[what] is not None:  # pragma: no cover
            self._pi.write(self.pins[what], 1 if on else 0)

    def all_off(self) -> None:
        for k in list(self.pins):
            self.set(k, False)

    def close(self) -> None:
        self.all_off()
        if self._pi is not None:                     # pragma: no cover
            self._pi.stop()


class Sprayer:
    """Meters a dose in millilitres by running the pump for a measured time."""

    def __init__(self, outputs: Outputs, cfg: dict, state):
        self.out = outputs
        self.cfg = cfg
        self.state = state
        self.tank_ml = float(cfg.get("tank_litres", 1.75)) * 1000.0
        self.used_ml = 0.0
        self._lock = threading.Lock()

    def remaining_ml(self) -> float:
        return max(0.0, self.tank_ml - self.used_ml)

    def can_spray(self, ml: float) -> tuple[bool, str]:
        if self.state.estop:
            return False, "emergency stop is on"
        if ml <= 0:
            return False, "dose is zero"
        if self.cfg.get("require_arm_switch", True) and not self.state.spray_armed:
            return False, "spray is not armed"
        if ml > float(self.cfg.get("max_ml_per_plant", 25)):
            return False, "dose above the per plant limit"
        if self.used_ml + ml > float(self.cfg.get("max_ml_per_session", 1200)):
            return False, "session dose limit reached"
        if ml > self.remaining_ml():
            return False, "tank is empty"
        return True, ""

    def spray(self, ml: float, nozzle: str = "front") -> tuple[bool, str]:
        ok, why = self.can_spray(ml)
        if not ok:
            return False, why
        rate = max(0.1, float(self.cfg.get("ml_per_second", 12.0)))
        secs = ml / rate
        with self._lock:
            self.out.set(nozzle, True)
            self.out.set("pump", True)
            self.state.set(pump_on=True)
            t0 = time.time()
            while time.time() - t0 < secs:
                if self.state.estop:
                    break
                time.sleep(0.02)
            self.out.set("pump", False)
            self.out.set(nozzle, False)
            self.state.set(pump_on=False)
            done = min(ml, (time.time() - t0) * rate)
            self.used_ml += done
        self.state.telemetry.tank_ml = self.remaining_ml()
        self.state.telemetry.tank_pct = 100.0 * self.remaining_ml() / self.tank_ml
        return True, "%.1f ml" % done


class Analog:
    """ADS1115: soil probe, tank level, battery volts."""

    def __init__(self, cfg: dict, sim: bool = False):
        self.cfg = cfg
        self.adc_cfg = cfg.get("adc", {})
        self.soil_cfg = cfg.get("soil", {})
        self.sim = sim or ADS is None
        self._ads = None
        self._chan = {}
        if not self.sim:                             # pragma: no cover
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self._ads = ADS.ADS1115(i2c, address=int(self.adc_cfg.get("i2c_addr", 0x48)))
                for name, key in (("soil", "soil_channel"), ("tank", "tank_channel"),
                                  ("batt", "battery_channel"),
                                  ("current", "current_channel")):
                    ch = self.adc_cfg.get(key)
                    if ch is not None:
                        self._chan[name] = AnalogIn(self._ads, ch)
            except Exception:
                self.sim = True
                self._ads = None

    def _raw(self, name: str) -> Optional[int]:
        if self._ads is None or name not in self._chan:
            return None
        try:                                         # pragma: no cover
            return int(self._chan[name].value)
        except Exception:
            return None

    def soil_percent(self) -> Optional[float]:
        raw = self._raw("soil")
        if raw is None:
            return None
        dry = float(self.soil_cfg.get("dry_counts", 26000))
        wet = float(self.soil_cfg.get("wet_counts", 11000))
        if dry == wet:
            return None
        pct = 100.0 * (dry - raw) / (dry - wet)
        return max(0.0, min(100.0, pct))

    def battery_volts(self) -> Optional[float]:
        if self._ads is None:
            return None
        try:                                         # pragma: no cover
            v = float(self._chan["batt"].voltage)
            return v * float(self.adc_cfg.get("battery_divider", 6.0))
        except Exception:
            return None

    def tank_percent(self) -> Optional[float]:
        raw = self._raw("tank")
        if raw is None:
            return None
        return max(0.0, min(100.0, raw / 26000.0 * 100.0))

    def current_amps(self) -> Optional[float]:
        """Motor current, if you fitted an ACS712 on the spare ADC channel.

        Worth fitting: a jammed wheel or a seized gearbox shows up here as a
        hard pull seconds before the driver board gets hot enough to fail.
        """
        if self._ads is None or "current" not in self._chan:
            return None
        try:                                         # pragma: no cover
            v = float(self._chan["current"].voltage)
            zero = float(self.cfg.get("current", {}).get("zero_volts", 2.5))
            mv_per_a = float(self.cfg.get("current", {}).get("mv_per_amp", 66.0))
            return (v - zero) * 1000.0 / max(1.0, mv_per_a)
        except Exception:
            return None


class SimSensors:
    """Believable numbers so the dashboard has something to show on a laptop."""

    def __init__(self, cfg: dict):
        self.t0 = time.time()
        self.cfg = cfg or {}
        self.soil = 46.0
        # follow whatever pack the config says, or the simulator trips the
        # low battery cut-out the moment you change the cell count
        try:
            b = self.cfg["safety"]["battery"]
            self.cells = int(b.get("cells", 6))
            self.chem = str(b.get("chemistry", "lead")).strip().lower()
        except Exception:
            self.cells, self.chem = 6, "lead"

    def battery_volts(self) -> float:
        """A pack sagging slowly from full, for whatever chemistry you fitted."""
        full, empty = CHEM.get(self.chem, CHEM["lead"])["span"]
        mins = (time.time() - self.t0) / 60.0
        fall = (full - empty) / 90.0          # flat in about an hour and a half
        per_cell = max(empty, full - fall * mins + random.uniform(-0.004, 0.004))
        return per_cell * self.cells

    def soil_percent(self) -> float:
        self.soil += random.uniform(-0.6, 0.6)
        self.soil = max(12.0, min(88.0, self.soil))
        return self.soil

    def tank_percent(self) -> float:
        return 100.0

    def range_cm(self) -> float:
        return 120.0 + 40.0 * math.sin((time.time() - self.t0) / 7.0)


# Volts per CELL. Three chemistries, because they are nothing like each other
# and guessing one from the other gives you a meter that lies all day.
#
#   lead     a 12 V sealed lead acid brick is 6 cells: 12.7 V full, 11.7 flat
#   lifepo4  a "12 V" LiFePO4 pack is 4 cells: 14.6 V charged, 12.8 nominal
#   lipo     a 4S hobby pack is 4 cells: 16.8 V charged, 13.6 flat
CHEM = {
    "lead": {"span": (2.12, 1.95),
             "table": [(2.12, 100), (2.10, 90), (2.08, 80), (2.06, 70),
                       (2.04, 60), (2.03, 50), (2.01, 40), (1.99, 30),
                       (1.97, 20), (1.95, 10), (1.90, 0)]},
    "lifepo4": {"span": (3.45, 2.90),
                "table": [(3.45, 100), (3.35, 90), (3.32, 80), (3.30, 70),
                          (3.28, 60), (3.26, 50), (3.25, 40), (3.22, 30),
                          (3.20, 20), (3.13, 10), (2.90, 0)]},
    "lipo": {"span": (4.15, 3.45),
             "table": [(4.20, 100), (4.10, 90), (4.00, 80), (3.92, 70),
                       (3.85, 60), (3.79, 50), (3.75, 40), (3.70, 30),
                       (3.65, 20), (3.55, 10), (3.40, 0)]},
}


def battery_percent(v: float, cells: int = 6, chemistry: str = "lead") -> float:
    """State of charge from resting voltage, for the pack you actually fitted."""
    per = v / max(1, cells)
    table = CHEM.get(str(chemistry).strip().lower(), CHEM["lead"])["table"]
    if per >= table[0][0]:
        return 100.0
    for i in range(len(table) - 1):
        hi, hip = table[i]
        lo, lop = table[i + 1]
        if lo <= per <= hi:
            f = (per - lo) / (hi - lo)
            return lop + f * (hip - lop)
    return 0.0


class SoilSwitch:
    """The DO pin of the common soil moisture module (the one with a blue
    LM393 comparator board and a two-pronged fork).

    Without an ADC this is all a Pi can read from it: wet or dry, at the
    point set by the little screw pot on the board. Power the board from
    3.3 V, not 5 V, so DO never puts 5 V on a Pi pin. DO goes LOW when the
    fork is wet (its second LED lights).
    """

    def __init__(self, cfg: dict, sim: bool = False):
        self.pin = cfg.get("digital_pin")
        self.wet_level = int(cfg.get("wet_level", 0))
        self.sim = sim or pigpio is None or self.pin is None
        self._pi = None
        if not self.sim:                             # pragma: no cover
            try:
                self._pi = pigpio.pi()
                if not self._pi.connected:
                    raise RuntimeError("pigpiod is not running")
                self._pi.set_mode(int(self.pin), pigpio.INPUT)
                self._pi.set_pull_up_down(int(self.pin), pigpio.PUD_UP)
            except Exception:
                self.sim = True
                self._pi = None

    @property
    def live(self) -> bool:
        return not self.sim

    def read(self) -> Optional[str]:
        if self._pi is None:
            return None
        try:                                         # pragma: no cover
            return "wet" if self._pi.read(int(self.pin)) == self.wet_level else "dry"
        except Exception:
            return None

    def close(self) -> None:
        if self._pi is not None:                     # pragma: no cover
            try:
                self._pi.stop()
            except Exception:
                pass

