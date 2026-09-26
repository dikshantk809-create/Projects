"""The soil probe: a lead screw that drives a spike into the ground.

From the model:

    ProbeMotor          on top, z 351..391
    LeadScrew           z 140..345
    ProbeCarriage       rides the screw
    ProbeRod            hangs off the carriage
    ProbeSensor         the moisture spike at the bottom, z 125..185
    LimitSw_Up          z 340
    LimitSw_Down        z 150
    travel between them 190 mm

With the carriage at the top the spike sits 125 mm above the ground. Run it all
the way down and the spike goes about 65 mm INTO the soil, which is where a
moisture reading means something - a reading taken in the air tells you the air
is dry.

This is not a servo. It is a motor that runs until a switch says stop, which
means two things the code has to respect:

  * it must never be driven past a limit switch, because the only thing after
    the switch is the end of the screw
  * if a switch never closes, something is jammed. It gives up after a timeout
    and says so, rather than sitting there stalling the motor
"""
from __future__ import annotations

import threading
import time
from typing import Optional

try:
    import pigpio                                        # type: ignore
except Exception:                                        # pragma: no cover
    pigpio = None

UP, DOWN, STOPPED = "up", "down", "stopped"


class SoilProbe:
    def __init__(self, cfg: dict, sim: bool = False):
        c = (cfg or {}).get("probe", {}) or {}
        self.cfg = c
        self.enabled = bool(c.get("enabled", True))
        self.sim = sim or pigpio is None or not self.enabled
        self.reason = ("switched off in the config" if not self.enabled
                       else "pigpio is not installed" if pigpio is None else "")

        self.pin_up = int(c.get("motor_up_pin", 23))
        self.pin_down = int(c.get("motor_down_pin", 24))
        self.sw_up = int(c.get("limit_up_pin", 25))
        self.sw_down = int(c.get("limit_down_pin", 26))
        self.travel_mm = float(c.get("travel_mm", 190.0))
        self.timeout = float(c.get("timeout_s", 25.0))
        self.settle = float(c.get("settle_s", 2.0))

        self.state = "unknown"        # unknown | up | down | moving | jammed
        self.moving = STOPPED
        self._pi = None
        self._lock = threading.Lock()
        self._busy = False

        if not self.sim:                                 # pragma: no cover
            try:
                self._pi = pigpio.pi()
                if not self._pi.connected:
                    raise RuntimeError("pigpiod is not running")
                for p in (self.pin_up, self.pin_down):
                    self._pi.set_mode(p, pigpio.OUTPUT)
                    self._pi.write(p, 0)
                for p in (self.sw_up, self.sw_down):
                    self._pi.set_mode(p, pigpio.INPUT)
                    self._pi.set_pull_up_down(p, pigpio.PUD_UP)
            except Exception as e:
                self.sim = True
                self.reason = str(e)
                self._pi = None

    @property
    def live(self) -> bool:
        return not self.sim

    @property
    def busy(self) -> bool:
        return self._busy

    # ----------------------------------------------------------- the switches
    def at_top(self) -> bool:
        if self.sim:
            return self.state == "up"
        return self._pi.read(self.sw_up) == 0            # pragma: no cover

    def at_bottom(self) -> bool:
        if self.sim:
            return self.state == "down"
        return self._pi.read(self.sw_down) == 0          # pragma: no cover

    # --------------------------------------------------------------- driving
    def _run(self, direction: str) -> None:
        if self.sim:
            self.moving = direction
            return
        up = direction == UP                             # pragma: no cover
        self._pi.write(self.pin_up, 1 if up else 0)
        self._pi.write(self.pin_down, 0 if up else 1)
        self.moving = direction

    def _halt(self) -> None:
        if not self.sim:                                 # pragma: no cover
            self._pi.write(self.pin_up, 0)
            self._pi.write(self.pin_down, 0)
        self.moving = STOPPED

    def _go(self, direction: str, stop_when) -> tuple:
        with self._lock:
            self._busy = True
            self.state = "moving"
            t0 = time.time()
            try:
                self._run(direction)
                while not stop_when():
                    if time.time() - t0 > self.timeout:
                        self._halt()
                        self.state = "jammed"
                        return False, ("the probe did not reach its %s stop in "
                                       "%.0f s - something is jammed" %
                                       (direction, self.timeout))
                    time.sleep(0.02)
                    if self.sim and time.time() - t0 > 1.4:
                        break                     # the simulator just takes a moment
                self._halt()
                self.state = direction
                return True, "probe is %s" % direction
            finally:
                self._halt()
                self._busy = False

    def retract(self) -> tuple:
        """All the way up, out of the ground. Always safe to call."""
        return self._go(UP, self.at_top)

    def deploy(self) -> tuple:
        """All the way down, into the soil."""
        return self._go(DOWN, self.at_bottom)

    def home(self) -> tuple:
        """Where is it? Nobody knows at power-on, so drive it up and find out."""
        return self.retract()

    def read_soil(self, analog) -> tuple:
        """Put it in, wait for the reading to settle, read, take it out again.

        The reading is taken with the spike IN the soil and the value is
        returned with the probe already retracted, so the rover is never left
        driving off with a spike in the ground.
        """
        ok, msg = self.deploy()
        if not ok:
            self.retract()
            return None, msg
        time.sleep(self.settle)
        val = analog() if callable(analog) else None
        ok2, msg2 = self.retract()
        if not ok2:
            return val, "read %s, but then: %s" % (val, msg2)
        return val, "soil read with the probe in the ground"

    def snapshot(self) -> dict:
        return {"state": self.state, "moving": self.moving,
                "busy": self._busy, "fitted": self.live,
                "travel_mm": self.travel_mm}

    def close(self) -> None:
        try:
            self._halt()
        except Exception:
            pass
        if self._pi:                                     # pragma: no cover
            try:
                self._pi.stop()
            except Exception:
                pass
