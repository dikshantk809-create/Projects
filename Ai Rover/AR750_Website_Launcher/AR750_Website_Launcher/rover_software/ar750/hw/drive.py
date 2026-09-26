"""The two drive motors, through their ESCs, and the steering servo.

The AR-750 has one motor at each end, each feeding a differential:

    Motor_F --16T--> 40T --16T--> 38T diff --> front wheels
    Motor_R --16T--> 40T --16T--> 38T diff --> rear wheels

    5.9375 : 1 after whatever gearbox is already on the motor

Both motors do the same thing at the same time - this is four wheel drive, not
skid steer. Turning is the steering servo's job, and nothing else's. If you
ever find yourself writing "left motor faster than right" for this machine,
stop: the diffs will simply let the inside wheels spin and it will go straight
anyway, while the motors fight each other through the ground.

There are two ways to drive those motors, and `drive.driver` in config.yaml
picks which one you built:

  "bts7960"   TWO PINS PER MOTOR, one for each direction, both PWM. This is
              the BTS7960 / IBT-2 board, and it is what the parts list buys:
              6-27 V, 43 A, about Rs 256. Tie R_EN and L_EN high and drive
              RPWM and LPWM. Forward puts PWM on one pin and holds the other
              low; reverse swaps them; both low is coast. Nothing to arm.

  "esc"       ONE PIN PER MOTOR, the same 1-2 ms pulse a servo takes:

                  1000 us  full reverse      (on a reversible ESC)
                  1500 us  stopped
                  2000 us  full forward

              An ESC is NOT an H bridge. Most cheap brushed ESCs also need to
              see neutral for a moment at power-up before they will do
              anything, which this does on startup.

Watch the voltage if you pick "esc": nearly every hobby brushed ESC sold is
built for RC cars and stops at 3S, which is 12.6 V. A 12 V lead acid pack is
13.8 V straight off the charger and LiFePO4 charges to 14.6 V, so both sit
above that. The BTS7960 has no such problem.

  "l298n"     the small red L298N board: the same two-pins-per-motor idea
              as the BTS7960 (IN1/IN2 for one motor, IN3/IN4 for the other),
              so it uses the same code. Leave the ENA and ENB jumpers ON.
              2 A per side: fine for small 12 V geared motors, not for the
              big AR-750 motors.

Either way both motors always get the same value, and a change of direction
passes through zero first - kind to the gearbox on an H bridge, and required
on a brushed ESC.

`drive.layout` says how the machine turns:

  "car"   the AR-750: front and rear axles, a steering servo points the
          wheels. Both motors always get the same value.

  "skid"  a small rover with no steering servo: the LEFT side and the RIGHT
          side are driven separately, and it turns by running one side faster
          than the other - or one forward and one back to spin on the spot.
          On an L298N: OUT1/OUT2 go to the left motors, OUT3/OUT4 to the
          right. Nothing is sent to the steering pin, so it is free for
          something else (the camera's pan servo).
"""
from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

try:
    import pigpio                                        # type: ignore
except Exception:                                        # pragma: no cover
    pigpio = None


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class _Channel:
    """One ESC or servo output on one pin."""

    def __init__(self, pi, pin: int, neutral: int, lo: int, hi: int):
        self.pi = pi
        self.pin = int(pin)
        self.neutral, self.lo, self.hi = int(neutral), int(lo), int(hi)
        self.us = self.neutral
        if pi:                                           # pragma: no cover
            pi.set_mode(self.pin, pigpio.OUTPUT)
            pi.set_servo_pulsewidth(self.pin, self.neutral)

    def write_us(self, us: float) -> None:
        self.us = int(_clamp(us, self.lo, self.hi))
        if self.pi:                                      # pragma: no cover
            self.pi.set_servo_pulsewidth(self.pin, self.us)

    def write_frac(self, f: float) -> None:
        """-1..1 onto the pulse range, with neutral in the middle."""
        f = _clamp(f, -1.0, 1.0)
        span = (self.hi - self.neutral) if f >= 0 else (self.neutral - self.lo)
        self.write_us(self.neutral + f * span)

    def off(self) -> None:
        if self.pi:                                      # pragma: no cover
            self.pi.set_servo_pulsewidth(self.pin, 0)


class _HBridge:
    """One BTS7960 / IBT-2 board: a PWM pin for each direction.

    Wire R_EN and L_EN to 3.3 V and leave them there. Then only RPWM and
    LPWM matter, and exactly one of them is ever driven at a time.
    """

    RANGE = 1000                     # duty is 0..1000 so 0.1% steps

    def __init__(self, pi, fwd_pin: int, rev_pin: int, hz: float = 1000.0,
                 min_duty: float = 0.0):
        self.pi = pi
        self.fwd_pin, self.rev_pin = int(fwd_pin), int(rev_pin)
        self.hz = float(hz)
        self.min_duty = _clamp(float(min_duty), 0.0, 0.9)
        self.duty = 0.0              # -1..1, signed, what it is actually doing
        if pi:                                           # pragma: no cover
            for p in (self.fwd_pin, self.rev_pin):
                pi.set_mode(p, pigpio.OUTPUT)
                pi.set_PWM_frequency(p, int(self.hz))
                pi.set_PWM_range(p, self.RANGE)
                pi.set_PWM_dutycycle(p, 0)

    def write_frac(self, f: float) -> None:
        """-1..1. Below min_duty the motor only buzzes, so scale into it."""
        f = _clamp(f, -1.0, 1.0)
        mag = abs(f)
        if mag < 1e-3:
            mag = 0.0
        elif self.min_duty > 0:
            mag = self.min_duty + mag * (1.0 - self.min_duty)
        self.duty = mag if f >= 0 else -mag
        on, off = ((self.fwd_pin, self.rev_pin) if f >= 0
                   else (self.rev_pin, self.fwd_pin))
        if self.pi:                                      # pragma: no cover
            self.pi.set_PWM_dutycycle(off, 0)
            self.pi.set_PWM_dutycycle(on, int(round(mag * self.RANGE)))

    def off(self) -> None:
        """Both low: the motor coasts. Not a brake."""
        self.duty = 0.0
        if self.pi:                                      # pragma: no cover
            self.pi.set_PWM_dutycycle(self.fwd_pin, 0)
            self.pi.set_PWM_dutycycle(self.rev_pin, 0)


class Drive:
    """Both drive motors together, plus the steering servo."""

    def __init__(self, cfg: dict, rover_cfg: dict, sim: bool = False):
        self.cfg = cfg or {}
        esc = self.cfg.get("esc", {}) or {}
        st = self.cfg.get("steering", {}) or {}
        self.sim = sim or pigpio is None
        self.reason = "pigpio is not installed" if pigpio is None else ""
        self._pi = None
        self._lock = threading.Lock()

        self.ramp = float(self.cfg.get("ramp_per_tick", 0.05))
        self.invert_front = bool(self.cfg.get("invert_front", False))
        self.invert_rear = bool(self.cfg.get("invert_rear", False))
        self.throttle = 0.0                  # what the wheels are being given
        self._want = 0.0
        self.steer_deg = 0.0                 # road wheel angle, not servo angle

        if not self.sim:                                 # pragma: no cover
            try:
                self._pi = pigpio.pi()
                if not self._pi.connected:
                    raise RuntimeError("pigpiod is not running")
            except Exception as e:
                self.sim = True
                self.reason = str(e)
                self._pi = None

        # --- which kind of motor driver did you actually build?
        self.driver = str(self.cfg.get("driver", "esc")).strip().lower()
        if self.driver not in ("esc", "bts7960", "l298n"):
            raise ValueError("drive.driver must be 'l298n', 'bts7960' or 'esc', "
                             "not %r" % self.driver)
        self.layout = str(self.cfg.get("layout", "car")).strip().lower()
        if self.layout not in ("car", "skid"):
            raise ValueError("drive.layout must be 'car' or 'skid', not %r" % self.layout)
        if self.layout == "skid" and self.driver == "esc":
            raise ValueError("drive.layout skid needs an H bridge (l298n or bts7960)")
        self.skid = self.layout == "skid"
        self.hbridge = self.driver in ("bts7960", "l298n")
        # in skid mode "front" is the LEFT side and "rear" the RIGHT side
        self.turn = 0.0                      # -1..1 what the sides are given
        self._want_turn = 0.0
        self.left_out = 0.0                  # what each side is actually doing
        self.right_out = 0.0

        if self.hbridge:
            hb = self.cfg.get("hbridge", {}) or {}
            hz = float(hb.get("pwm_hz", 1000))
            md = float(hb.get("min_duty", 0.0))
            if self.skid:
                self.front = _HBridge(self._pi, hb.get("left_fwd_pin", 12),
                                      hb.get("left_rev_pin", 19), hz, md)
                self.rear = _HBridge(self._pi, hb.get("right_fwd_pin", 13),
                                     hb.get("right_rev_pin", 10), hz, md)
            else:
                self.front = _HBridge(self._pi, hb.get("front_fwd_pin", 12),
                                      hb.get("front_rev_pin", 19), hz, md)
                self.rear = _HBridge(self._pi, hb.get("rear_fwd_pin", 13),
                                     hb.get("rear_rev_pin", 10), hz, md)
        else:
            n, lo, hi = (int(esc.get("neutral_us", 1500)),
                         int(esc.get("min_us", 1000)),
                         int(esc.get("max_us", 2000)))
            self.front = _Channel(self._pi, esc.get("front_pin", 12), n, lo, hi)
            self.rear = _Channel(self._pi, esc.get("rear_pin", 13), n, lo, hi)

        self.servo_centre = int(st.get("centre_us", 1500))
        self.servo_us_per_deg = float(st.get("us_per_deg", 9.0))
        self.servo_trim = float(st.get("trim_us", 0))
        self.servo_reverse = bool(st.get("reverse", False))
        # A skid rover has no steering servo, and its steering pin may be
        # wired to something else entirely - so nothing is ever sent to it.
        self.steer = _Channel(None if self.skid else self._pi, st.get("pin", 18),
                              self.servo_centre, int(st.get("min_us", 900)),
                              int(st.get("max_us", 2100)))
        self.invert_left = bool(self.cfg.get("invert_left", self.invert_front))
        self.invert_right = bool(self.cfg.get("invert_right", self.invert_rear))
        self.turn_gain = float((self.cfg.get("skid", {}) or {}).get("turn_gain", 0.7))

        # ESCs want to see neutral for a moment before they will arm.
        # An H bridge has nothing to arm, so it is ready straight away.
        self.arm_seconds = (0.0 if self.hbridge
                            else float(esc.get("arm_seconds", 2.0)))
        self._armed_at = time.time()
        self._last_sign = 0

    @property
    def live(self) -> bool:
        return not self.sim

    @property
    def armed(self) -> bool:
        return time.time() - self._armed_at > self.arm_seconds

    # ------------------------------------------------------------- throttle
    def set_throttle(self, f: float) -> None:
        """-1..1. Both motors, same value: it is four wheel drive."""
        self._want = _clamp(f, -1.0, 1.0)

    def set_turn(self, f: float) -> None:
        """Skid only: -1..1, positive turns right. Ignored on a car layout."""
        self._want_turn = _clamp(f, -1.0, 1.0) if self.skid else 0.0

    def tick(self) -> None:
        """Call this from the control loop. Ramps, so nothing snatches."""
        with self._lock:
            if not self.armed:
                self._apply(0.0)
                return
            if self.skid:
                self._tick_skid()
                return
            d = self._want - self.throttle
            step = self.ramp
            if abs(d) > step:
                d = step if d > 0 else -step
            new = self.throttle + d

            # going through neutral when reversing, which a brushed ESC needs
            if new * self.throttle < 0:
                new = 0.0
            self._apply(new)

    def _apply(self, f: float) -> None:
        self.throttle = f
        if self.skid:
            self.turn = 0.0
            self._write_sides(f, f)
            return
        self.left_out = self.right_out = f
        self.front.write_frac(-f if self.invert_front else f)
        self.rear.write_frac(-f if self.invert_rear else f)

    # --------------------------------------------------------------- skid
    def _tick_skid(self) -> None:
        """Each side ramps on its own towards throttle +/- turn."""
        t, s = self._want, self._want_turn * self.turn_gain
        left, right = t + s, t - s
        big = max(1.0, abs(left), abs(right))     # keep the turn when flat out
        left, right = left / big, right / big
        step = self.ramp
        def walk(cur, want):
            d = want - cur
            return want if abs(d) <= step else cur + (step if d > 0 else -step)
        nl, nr = walk(self.left_out, left), walk(self.right_out, right)
        self.throttle = (nl + nr) / 2.0
        self.turn = (nl - nr) / 2.0
        self._write_sides(nl, nr)

    def _write_sides(self, left: float, right: float) -> None:
        self.left_out, self.right_out = left, right
        self.front.write_frac(-left if self.invert_left else left)
        self.rear.write_frac(-right if self.invert_right else right)

    def stop(self) -> None:
        with self._lock:
            self._want = 0.0
            self._want_turn = 0.0
            self._apply(0.0)

    # ------------------------------------------------------------- steering
    def set_steer_deg(self, wheel_deg: float, max_deg: float) -> float:
        """Point the wheels. Takes the ROAD WHEEL angle, returns what it used."""
        wheel_deg = _clamp(wheel_deg, -max_deg, max_deg)
        self.steer_deg = wheel_deg
        return wheel_deg

    def write_servo(self, servo_deg: float) -> None:
        """Send a servo angle out. The linkage maths lives in ackermann.py."""
        s = -servo_deg if self.servo_reverse else servo_deg
        self.steer.write_us(self.servo_centre + self.servo_trim
                            + s * self.servo_us_per_deg)

    def centre_steering(self) -> None:
        self.steer_deg = 0.0
        self.write_servo(0.0)

    # ----------------------------------------------------------------- tidy
    def snapshot(self) -> dict:
        s = {"driver": self.driver, "layout": self.layout,
             "throttle": round(self.throttle, 3),
             "steer_deg": round(self.steer_deg, 1),
             "steer_us": self.steer.us, "armed": self.armed}
        if self.skid:
            s["left_duty"] = round(self.front.duty, 3)
            s["right_duty"] = round(self.rear.duty, 3)
        elif self.hbridge:
            s["front_duty"] = round(self.front.duty, 3)
            s["rear_duty"] = round(self.rear.duty, 3)
        else:
            s["front_us"] = self.front.us
            s["rear_us"] = self.rear.us
        return s

    def release(self) -> None:
        self.stop()
        self.centre_steering()
        time.sleep(0.1)
        for ch in (self.front, self.rear, self.steer):
            ch.off()
        if self._pi:                                     # pragma: no cover
            try:
                self._pi.stop()
            except Exception:
                pass
