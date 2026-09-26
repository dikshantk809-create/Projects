"""The spray boom: five nozzles on a 700 mm bar, in three switchable sections.

From the model:

    BoomTube        700 mm across the back of the rover
    5 nozzles       at y = -280, -140, 0, +140, +280   (140 mm apart)
    height          235 mm above the ground
    ChemTank        300 x 200 x 100 mm outside, about 5 litres inside
    Pump            one, feeding the whole boom

This is a boom sprayer, so it does not spray one plant at a time - it lays a
band down as it drives. What it CAN do is choose which part of the band:

    left    nozzles 1 and 2     y -280 and -140
    centre  nozzle 3            y 0
    right   nozzles 4 and 5     y +140 and +280

so a problem on one side of the row gets treated without dosing the other side.
Fitting three valves to do that is worth the afternoon it takes.

HOW MUCH GOES ON, which is the number that matters:

    litres per hectare = 0.6 x (ml per minute per nozzle)
                             / (speed in km/h x nozzle spacing in metres)

Put the AR-750's real numbers in and a problem falls out immediately. It follows
a row at base_speed x max_speed_mps = 0.35 x 0.45 = 0.16 m/s, and with 350
ml/min nozzles 140 mm apart that comes to about 2650 litres per hectare. A
vegetable crop wants somewhere around 200. It would be putting down thirteen
times too much.

You cannot fix that by driving faster: hitting 200 l/ha that way needs about
2 m/s, which is 7.5 km/h down a vegetable bed, and no.

So the boom PULSES. The section valves are switched on and off about ten times
a second, and the fraction of the time they are open sets the dose:

    duty = wanted rate / rate at full flow

That is how every modern precision sprayer does it, the solenoid valves in the
design can already do it, and it means the rate stays right whatever speed the
rover happens to be going. Below about 15% duty the pattern starts to go
stripey, and this says so rather than quietly spraying a bad pattern.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional, Tuple

try:
    import pigpio                                        # type: ignore
except Exception:                                        # pragma: no cover
    pigpio = None

SECTIONS = ("left", "centre", "right")


class Boom:
    def __init__(self, cfg: dict, state, sim: bool = False):
        c = (cfg or {}).get("boom", {}) or {}
        self.cfg = c
        self.state = state
        # a rover built without the boom: its pins stay untouched, so they
        # can carry something else (the arm's servos, on the small build)
        self.enabled = bool(c.get("enabled", True))
        self.sim = sim or pigpio is None or not self.enabled
        self.reason = ("switched off in the config" if not self.enabled
                       else "pigpio is not installed" if pigpio is None else "")
        self._pi = None
        self._lock = threading.Lock()

        self.pump_pin = int(c.get("pump_pin", 16))
        self.section_pins = {
            "left": int(c.get("left_pin", 17)),
            "centre": int(c.get("centre_pin", 27)),
            "right": int(c.get("right_pin", 22)),
        }
        self.nozzle_spacing_m = float(c.get("nozzle_spacing_mm", 140)) / 1000.0
        self.nozzles = int(c.get("nozzles", 5))
        self.ml_per_min_per_nozzle = float(c.get("ml_per_min_per_nozzle", 350.0))
        self.tank_ml = float(c.get("tank_litres", 5.0)) * 1000.0
        self.used_ml = 0.0
        self.max_l_per_ha = float(c.get("max_l_per_ha", 400.0))
        self.target_l_per_ha = float(c.get("target_l_per_ha", 200.0))
        self.pwm_hz = float(c.get("pwm_hz", 10.0))
        self.min_duty = float(c.get("min_duty", 0.15))
        self.duty = 1.0
        self.max_ml_per_session = float(c.get("max_ml_per_session", 4000.0))
        self.require_arm_switch = bool(c.get("require_arm_switch", True))

        self.pump_on = False
        self.open_sections: List[str] = []
        self._t_open = 0.0

        if not self.sim:                                 # pragma: no cover
            try:
                self._pi = pigpio.pi()
                if not self._pi.connected:
                    raise RuntimeError("pigpiod is not running")
                for p in [self.pump_pin] + list(self.section_pins.values()):
                    self._pi.set_mode(p, pigpio.OUTPUT)
                    self._pi.write(p, 0)
            except Exception as e:
                self.sim = True
                self.reason = str(e)
                self._pi = None

    @property
    def live(self) -> bool:
        return not self.sim

    def remaining_ml(self) -> float:
        return max(0.0, self.tank_ml - self.used_ml)

    # ------------------------------------------------------------- the maths
    def rate_l_per_ha(self, speed_mps: float, sections: Optional[List[str]] = None
                      ) -> Optional[float]:
        """What it is actually putting down, at this speed, right now."""
        if speed_mps <= 0.005:
            return None                       # standing still: not a rate at all
        n = self.nozzle_count(sections)
        if not n:
            return None
        kmh = speed_mps * 3.6
        return 600.0 * self.ml_per_min_per_nozzle / (kmh * self.nozzle_spacing_m) / 1000.0

    def speed_for_rate(self, l_per_ha: float) -> Optional[float]:
        """How fast to drive to lay down this many litres per hectare."""
        if l_per_ha <= 0:
            return None
        kmh = 600.0 * self.ml_per_min_per_nozzle / (l_per_ha * 1000.0 * self.nozzle_spacing_m)
        return kmh / 3.6

    def duty_for_rate(self, l_per_ha: float, speed_mps: float
                      ) -> Tuple[Optional[float], str]:
        """What fraction of the time the valves should be open.

        Returns (duty, a note). duty above 1 means even wide open it cannot put
        that much on at this speed - slow down. Below min_duty means the pulses
        get so short the band goes stripey - speed up, or fit smaller nozzles.
        """
        full = self.rate_l_per_ha(speed_mps, self.open_sections or ["centre"])
        if full is None or full <= 0:
            return None, "it is not moving"
        d = l_per_ha / full
        if d > 1.0:
            return 1.0, ("wide open it only manages %.0f l/ha at this speed - "
                         "slow down to get %.0f" % (full, l_per_ha))
        if d < self.min_duty:
            return d, ("only %.0f%% duty: the band will be stripey. Drive "
                       "faster or fit smaller nozzles." % (d * 100))
        return d, ""

    def right_nozzle_ml_min(self, l_per_ha: Optional[float] = None,
                            speed_mps: float = 0.35) -> float:
        """The nozzle you should actually have bought.

        Pulsing covers a mismatch; it does not make a badly sized nozzle right.
        If this comes out a long way under what you fitted, the honest fix is
        smaller nozzles or lower pressure, not a 5% duty cycle.
        """
        want = float(l_per_ha if l_per_ha is not None else self.target_l_per_ha)
        kmh = max(0.01, speed_mps * 3.6)
        return want * 1000.0 * self.nozzle_spacing_m * kmh / 600.0

    def nozzle_count(self, sections: Optional[List[str]] = None) -> int:
        s = sections if sections is not None else self.open_sections
        n = 0
        for name in s:
            n += 1 if name == "centre" else 2
        return n

    def ml_per_second(self, sections: Optional[List[str]] = None) -> float:
        return self.nozzle_count(sections) * self.ml_per_min_per_nozzle / 60.0

    # -------------------------------------------------------------- checking
    def can_spray(self, sections: List[str], speed_mps: float) -> Tuple[bool, str]:
        if self.state.estop:
            return False, "emergency stop is on"
        if self.require_arm_switch and not self.state.spray_armed:
            return False, "the spray is not armed"
        bad = [s for s in sections if s not in SECTIONS]
        if bad:
            return False, "no such boom section: %s" % ", ".join(bad)
        if not sections:
            return False, "no boom section chosen"
        if self.remaining_ml() < 50:
            return False, "the tank is empty"
        if self.used_ml >= self.max_ml_per_session:
            return False, "session limit reached"
        rate = self.rate_l_per_ha(speed_mps, sections)
        if rate is None:
            return False, ("it is not moving - a boom sprayer has to be driving "
                           "or it dumps the whole dose in one spot")
        if self.target_l_per_ha > self.max_l_per_ha:
            return False, ("the target rate %.0f l/ha is above the %.0f limit"
                           % (self.target_l_per_ha, self.max_l_per_ha))
        return True, ""

    # --------------------------------------------------------------- doing it
    def open(self, sections: List[str], speed_mps: float,
             l_per_ha: Optional[float] = None) -> Tuple[bool, str]:
        ok, why = self.can_spray(sections, speed_mps)
        if not ok:
            return False, why
        want = float(l_per_ha if l_per_ha is not None else self.target_l_per_ha)
        with self._lock:
            self.open_sections = list(sections)
            duty, note = self.duty_for_rate(want, speed_mps)
            self.duty = 1.0 if duty is None else max(0.02, min(1.0, duty))
            for name in SECTIONS:
                self._pulse(self.section_pins[name],
                            self.duty if name in sections else 0.0)
            self._write(self.pump_pin, True)
            self.pump_on = True
            self._t_open = time.time()
        self.state.set(pump_on=True)
        msg = ("spraying %s at %.0f l/ha, valves %.0f%% open at %.0f Hz"
               % ("+".join(sections), want, self.duty * 100, self.pwm_hz))
        return True, msg + ((" - " + note) if note else "")

    def close(self) -> Tuple[bool, str]:
        with self._lock:
            used = 0.0
            if self.pump_on:
                # pulsing means only the duty fraction actually came out
                used = (time.time() - self._t_open) * self.ml_per_second() * self.duty
                self.used_ml += used
            self._write(self.pump_pin, False)
            for p in self.section_pins.values():
                self._pulse(p, 0.0)
            self.pump_on = False
            self.open_sections = []
            self.duty = 1.0
        self.state.set(pump_on=False)
        self.state.telemetry.tank_ml = self.remaining_ml()
        self.state.telemetry.tank_pct = round(
            100.0 * self.remaining_ml() / max(1.0, self.tank_ml), 1)
        return True, "%.0f ml used" % used

    def burst(self, sections: List[str], seconds: float, speed_mps: float,
              l_per_ha: Optional[float] = None) -> Tuple[bool, str]:
        """Spray for a fixed time. Used for a band over one plant as it passes."""
        ok, why = self.open(sections, speed_mps, l_per_ha)
        if not ok:
            return False, why
        time.sleep(max(0.05, min(10.0, seconds)))
        return self.close()

    def all_off(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _write(self, pin: int, on: bool) -> None:
        if not self.sim:                                 # pragma: no cover
            self._pi.write(pin, 1 if on else 0)

    def _pulse(self, pin: int, duty: float) -> None:
        """Open a valve `duty` of the time, ten times a second."""
        if self.sim:
            return
        if duty <= 0:                                    # pragma: no cover
            self._pi.set_PWM_dutycycle(pin, 0)
            self._pi.write(pin, 0)
            return
        self._pi.set_PWM_frequency(pin, int(self.pwm_hz))
        self._pi.set_PWM_range(pin, 1000)
        self._pi.set_PWM_dutycycle(pin, int(max(0, min(1000, duty * 1000))))

    def snapshot(self) -> Dict:
        return {"pump_on": self.pump_on, "sections": list(self.open_sections),
                "used_ml": round(self.used_ml, 1),
                "remaining_ml": round(self.remaining_ml(), 1),
                "nozzles": self.nozzles, "fitted": self.live,
                "duty": round(self.duty, 3), "pwm_hz": self.pwm_hz,
                "target_l_per_ha": self.target_l_per_ha}

    def shutdown(self) -> None:
        self.all_off()
        if self._pi:                                     # pragma: no cover
            try:
                self._pi.stop()
            except Exception:
                pass
