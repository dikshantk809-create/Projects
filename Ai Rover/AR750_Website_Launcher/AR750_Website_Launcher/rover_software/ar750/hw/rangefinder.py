"""Something in front of it. The sensor that stops it hitting your feet.

An HC-SR04 is a rupee-store part and works fine in a garden. Wiring
(config: sensors.range_front):

    VCC  -> 5 V (Pi pin 2 or 4)      GND -> any ground
    TRIG -> GPIO 7 (Pi pin 26)
    ECHO -> GPIO 8 (Pi pin 24) THROUGH A DIVIDER. The echo pin puts out 5 V and the Pi's
            pins are 3.3 V. Two resistors - 1 kOhm from ECHO to the Pi pin,
            2 kOhm from the Pi pin to ground. Skip this and you damage the Pi.

It reads the median of three pings, because a single ultrasonic ping off wet
leaves lies often enough to matter.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

try:
    import pigpio                                        # type: ignore
except Exception:                                        # pragma: no cover
    pigpio = None

SPEED_OF_SOUND = 34300.0          # cm per second


class RangeFinder:
    def __init__(self, cfg: dict, sim: bool = False):
        c = (cfg or {}).get("range_front", {}) or {}
        self.cfg = c
        self.enabled = bool(c.get("enabled"))
        self.trig = int(c.get("trig", 22))
        self.echo = int(c.get("echo", 4))
        self.stop_cm = float(c.get("stop_cm", 35))
        self.sim = sim or pigpio is None or not self.enabled
        self.reason = ("switched off in the config" if not self.enabled
                       else "pigpio is not running" if pigpio is None else "")
        self._pi = None
        self._lock = threading.Lock()
        self.cm: Optional[float] = None

        if not self.sim:                                  # pragma: no cover
            try:
                self._pi = pigpio.pi()
                if not self._pi.connected:
                    raise RuntimeError("pigpiod is not running")
                self._pi.set_mode(self.trig, pigpio.OUTPUT)
                self._pi.set_mode(self.echo, pigpio.INPUT)
                self._pi.write(self.trig, 0)
                time.sleep(0.05)
            except Exception as e:
                self.sim = True
                self.reason = str(e)

    @property
    def live(self) -> bool:
        return not self.sim

    def _ping(self) -> Optional[float]:                   # pragma: no cover
        pi = self._pi
        pi.gpio_trigger(self.trig, 10, 1)
        start = time.time()
        while pi.read(self.echo) == 0:
            if time.time() - start > 0.03:
                return None
        t0 = time.time()
        while pi.read(self.echo) == 1:
            if time.time() - t0 > 0.03:
                return None
        return (time.time() - t0) * SPEED_OF_SOUND / 2.0

    def read(self) -> Optional[float]:
        if self.sim:
            return None
        with self._lock:                                  # pragma: no cover
            hits = [d for d in (self._ping() for _ in range(3)) if d]
            if not hits:
                self.cm = None
                return None
            hits.sort()
            self.cm = round(hits[len(hits) // 2], 1)
            return self.cm

    def blocked(self) -> bool:
        return self.cm is not None and self.cm < self.stop_cm

    def close(self) -> None:
        if self._pi:                                      # pragma: no cover
            try:
                self._pi.stop()
            except Exception:
                pass
