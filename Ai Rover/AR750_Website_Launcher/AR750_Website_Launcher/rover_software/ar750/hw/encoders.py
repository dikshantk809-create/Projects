"""Wheel encoders. Fit these and the rover finally knows where it actually is.

Without them the distance on the dashboard is worked out from what the motors
were *told* to do, which is a guess that drifts - a wheel spinning in mud reads
the same as a wheel gripping. With them, "go 350 mm to the next plant" becomes
true, slip is detectable, and the two wheels can be made to turn at the same
speed instead of merely being given the same power.

Wiring (config: drive.encoder), quadrature A and B per motor:

    left  A -> GPIO 23      right A -> GPIO 25
    left  B -> GPIO 24      right B -> GPIO 26

ticks_per_rev is counts at the WHEEL, so motor PPR x gearbox ratio x 4 for a
quadrature edge count. Measure it rather than trusting the listing: jack the
wheel up, mark it, turn it ten times by hand, divide.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

try:
    import pigpio                                        # type: ignore
except Exception:                                        # pragma: no cover
    pigpio = None


class _Wheel:
    """One quadrature channel, counted in the pigpio callback thread."""

    def __init__(self, pi, pin_a: int, pin_b: int):
        self.pi = pi
        self.a, self.b = pin_a, pin_b
        self.ticks = 0
        self._lev_a = 0
        self._lev_b = 0
        self._last = 0
        for p in (pin_a, pin_b):
            pi.set_mode(p, pigpio.INPUT)
            pi.set_pull_up_down(p, pigpio.PUD_UP)
        self._cb = [pi.callback(pin_a, pigpio.EITHER_EDGE, self._edge),
                    pi.callback(pin_b, pigpio.EITHER_EDGE, self._edge)]

    def _edge(self, gpio, level, tick):
        if gpio == self.a:
            self._lev_a = level
        else:
            self._lev_b = level
        # standard 2 bit gray code state machine
        state = (self._lev_a << 1) | self._lev_b
        delta = {0b00: {0b01: 1, 0b10: -1}, 0b01: {0b11: 1, 0b00: -1},
                 0b11: {0b10: 1, 0b01: -1}, 0b10: {0b00: 1, 0b11: -1}}
        self.ticks += delta.get(self._last, {}).get(state, 0)
        self._last = state

    def cancel(self):
        for c in self._cb:
            try:
                c.cancel()
            except Exception:
                pass


class Encoders:
    """Two wheels. Gives you distance in metres and speed in m/s, measured."""

    def __init__(self, drive_cfg: dict, rover_cfg: dict, sim: bool = False):
        cfg = (drive_cfg or {}).get("encoder", {}) or {}
        self.cfg = cfg
        self.enabled = bool(cfg.get("enabled"))
        self.ticks_per_rev = float(cfg.get("ticks_per_rev", 1560) or 1560)
        circ_mm = 3.14159265 * float(rover_cfg.get("wheel_dia_mm", 200))
        self.m_per_tick = (circ_mm / 1000.0) / max(1.0, self.ticks_per_rev)

        self.sim = sim or pigpio is None or not self.enabled
        self.reason = ("switched off in the config" if not self.enabled
                       else "pigpio is not running" if pigpio is None else "")
        self._pi = None
        self._l = self._r = None
        self._lock = threading.Lock()
        self._prev = (0, 0, time.time())
        self.left_mps = 0.0
        self.right_mps = 0.0
        self.left_m = 0.0
        self.right_m = 0.0

        if not self.sim:                                  # pragma: no cover
            try:
                self._pi = pigpio.pi()
                if not self._pi.connected:
                    raise RuntimeError("pigpiod is not running")
                self._l = _Wheel(self._pi, int(cfg["left_a"]), int(cfg["left_b"]))
                self._r = _Wheel(self._pi, int(cfg["right_a"]), int(cfg["right_b"]))
            except Exception as e:
                self.sim = True
                self.reason = str(e)

    @property
    def live(self) -> bool:
        return not self.sim

    def read(self) -> Optional[dict]:
        """Distance and speed since the last call. None if there are none fitted."""
        if self.sim:
            return None
        now = time.time()
        with self._lock:
            lt, rt = self._l.ticks, self._r.ticks
            plt, prt, pt = self._prev
            dt = max(1e-3, now - pt)
            self._prev = (lt, rt, now)
        dl = (lt - plt) * self.m_per_tick
        dr = (rt - prt) * self.m_per_tick
        self.left_mps = dl / dt
        self.right_mps = dr / dt
        self.left_m += dl
        self.right_m += dr
        return {"left_m": dl, "right_m": dr,
                "left_mps": self.left_mps, "right_mps": self.right_mps,
                "dt": dt}

    def slipping(self, commanded_l: float, commanded_r: float,
                 max_mps: float, tol: float = 0.45) -> bool:
        """A wheel told to turn that is not turning, or the other way round."""
        if self.sim:
            return False
        for cmd, got in ((commanded_l, self.left_mps), (commanded_r, self.right_mps)):
            want = abs(cmd) * max_mps
            if want > 0.02 and abs(got) < want * tol:
                return True
        return False

    def close(self) -> None:
        for w in (self._l, self._r):
            if w:
                w.cancel()
        if self._pi:                                      # pragma: no cover
            try:
                self._pi.stop()
            except Exception:
                pass
