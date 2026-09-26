"""Every hobby servo that is not the steering: the robotic arm, and the servo
under the camera that turns it to look left and right.

They hang off a PCA9685 16-channel servo board on the I2C bus (address 0x40)
by default, because after the drive, the boom, the probe and the lights the
Pi has only a handful of GPIO pins left. `driver: gpio` puts them on spare
Pi pins through pigpio instead.

Nothing here ever jumps a joint. Each one is given a target and walked to it
at its own speed, 50 times a second, so a heavy arm moves smoothly and does
not throw itself - or the rover - about.

A hobby servo cannot say where it is. So a joint stays ASLEEP (no pulse at
all) until the first time it is asked to move, and it wakes up believing it
is at its park angle. Leave the arm in its park pose when you switch off and
the first move is smooth; leave it anywhere else and that first move is a
jump. "Relax" puts a joint back to sleep - limp - on purpose.

Without the board it simulates, like every other part: the website shows
the angles moving and nothing is driven.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from smbus2 import SMBus                             # type: ignore
except Exception:                                        # pragma: no cover
    try:
        from smbus import SMBus                          # type: ignore
    except Exception:
        SMBus = None

try:
    import pigpio                                        # type: ignore
except Exception:                                        # pragma: no cover
    pigpio = None


# ------------------------------------------------------------ PCA9685 board
class PCA9685:
    """Just enough of the PCA9685 to hold servos: one frequency, per-channel
    pulse widths. Written against smbus2 directly, so it does not need the
    Adafruit Blinka stack, which is fussy about which Pi and which OS."""

    MODE1, MODE2, PRESCALE, LED0 = 0x00, 0x01, 0xFE, 0x06

    def __init__(self, bus: int = 1, addr: int = 0x40, hz: float = 50.0):
        self.addr = int(addr)
        self.hz = float(hz)
        self.bus = SMBus(int(bus))
        self.bus.read_byte_data(self.addr, self.MODE1)   # raises if not there
        pre = int(round(25_000_000.0 / (4096.0 * self.hz))) - 1
        self.bus.write_byte_data(self.addr, self.MODE1, 0x10)    # sleep
        self.bus.write_byte_data(self.addr, self.PRESCALE, max(3, min(255, pre)))
        self.bus.write_byte_data(self.addr, self.MODE1, 0x20)    # wake, auto-inc
        time.sleep(0.005)
        self.bus.write_byte_data(self.addr, self.MODE1, 0xA0)    # restart
        self.bus.write_byte_data(self.addr, self.MODE2, 0x04)    # totem pole

    def ticks(self, us: float) -> int:
        return max(0, min(4095, int(round(us * self.hz * 4096.0 / 1e6))))

    def pulse(self, ch: int, us: float) -> None:
        t = self.ticks(us)
        self.bus.write_i2c_block_data(self.addr, self.LED0 + 4 * int(ch),
                                      [0, 0, t & 0xFF, (t >> 8) & 0x0F])

    def off(self, ch: int) -> None:
        # the "full off" bit: no pulse at all, so the servo goes limp
        self.bus.write_i2c_block_data(self.addr, self.LED0 + 4 * int(ch),
                                      [0, 0, 0, 0x10])

    def close(self) -> None:
        try:
            self.bus.close()
        except Exception:
            pass


class _GpioServos:
    """The same two calls, on Pi pins, through pigpio."""

    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpiod is not running")

    def pulse(self, pin: int, us: float) -> None:
        self.pi.set_servo_pulsewidth(int(pin), int(max(500, min(2500, us))))

    def off(self, pin: int) -> None:
        self.pi.set_servo_pulsewidth(int(pin), 0)

    def close(self) -> None:
        try:
            self.pi.stop()
        except Exception:
            pass


# --------------------------------------------------------------- one joint
class Joint:
    def __init__(self, c: Dict[str, Any], default_speed: float):
        self.name = str(c["name"])
        self.label = str(c.get("label", self.name))
        self.group = str(c.get("group", "arm"))
        self.channel = c.get("channel", c.get("pin"))
        self.lo = float(c.get("min", 0))
        self.hi = float(c.get("max", 180))
        if self.hi < self.lo:
            self.lo, self.hi = self.hi, self.lo
        self.park = self.clamp(float(c.get("park", (self.lo + self.hi) / 2)))
        self.speed = max(1.0, float(c.get("speed_deg_s", default_speed)))
        self.min_us = float(c.get("min_us", 500))        # pulse at 0 degrees
        self.max_us = float(c.get("max_us", 2500))       # pulse at 180 degrees
        self.reverse = bool(c.get("reverse", False))
        # a gripper can name its open and closed angles
        self.open_deg = c.get("open")
        self.closed_deg = c.get("closed")
        self.deg = self.park          # where it is (as far as we know)
        self.target = self.park
        self.awake = False
        self._sent: Optional[float] = None

    def clamp(self, d: float) -> float:
        return max(self.lo, min(self.hi, float(d)))

    def us(self, deg: float) -> float:
        d = 180.0 - deg if self.reverse else deg
        return self.min_us + (self.max_us - self.min_us) * d / 180.0

    def snapshot(self) -> Dict[str, Any]:
        return {"name": self.name, "label": self.label, "group": self.group,
                "deg": round(self.deg, 1), "target": round(self.target, 1),
                "min": self.lo, "max": self.hi, "park": self.park,
                "awake": self.awake, "moving": abs(self.target - self.deg) > 0.4,
                "open": self.open_deg, "closed": self.closed_deg}


# --------------------------------------------------------------- the lot
class Servos:
    def __init__(self, cfg: Optional[Dict[str, Any]], sim: bool = False,
                 store: Optional[str] = None):
        cfg = cfg or {}
        self.cfg = cfg
        self.store = store             # where poses you teach it are kept
        self.enabled = bool(cfg.get("enabled", True))
        self.driver = str(cfg.get("driver", "pca9685")).strip().lower()
        speed = float(cfg.get("speed_deg_s", 45))
        self.joints: Dict[str, Joint] = {}
        for c in cfg.get("joints", []) or []:
            try:
                j = Joint(c, speed)
                self.joints[j.name] = j
            except Exception:
                continue
        self.poses: Dict[str, Dict[str, float]] = {
            str(k): {str(n): float(v) for n, v in (p or {}).items()}
            for k, p in (cfg.get("poses", {}) or {}).items()}
        self.builtin = set(self.poses)
        self.saved: Dict[str, Dict[str, float]] = {}
        self._load_saved()

        self.sim = sim or not self.enabled or not self.joints
        self.reason = ("switched off in config.yaml" if not self.enabled else
                       "no joints listed in config.yaml" if not self.joints else
                       "simulation" if sim else "")
        self._hw = None
        if not self.sim:                                  # pragma: no cover
            try:
                if self.driver == "gpio":
                    if pigpio is None:
                        raise RuntimeError("pigpio is not installed")
                    self._hw = _GpioServos()
                else:
                    if SMBus is None:
                        raise RuntimeError("smbus2 is not installed")
                    self._hw = PCA9685(int(cfg.get("i2c_bus", 1)),
                                       int(cfg.get("i2c_addr", 0x40)),
                                       float(cfg.get("pwm_hz", 50)))
            except Exception as e:
                self.sim = True
                self._hw = None
                self.reason = ("no servo board answered at 0x%02X on the I2C bus (%s)"
                               % (int(cfg.get("i2c_addr", 0x40)), e)
                               if self.driver != "gpio" else str(e))

        self._lock = threading.Lock()
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ api
    @property
    def live(self) -> bool:
        return not self.sim

    def has(self, name: str) -> bool:
        return name in self.joints

    def set(self, name: str, deg: float) -> Tuple[bool, str]:
        j = self.joints.get(name)
        if j is None:
            return False, "there is no joint called %s" % name
        with self._lock:
            if not j.awake:
                # it has been limp; the best guess is that it is resting at
                # its park angle, so start the walk from there
                j.deg = j.park
                j.awake = True
            j.target = j.clamp(deg)
        return True, ""

    def nudge(self, name: str, delta: float) -> Tuple[bool, str]:
        j = self.joints.get(name)
        if j is None:
            return False, "there is no joint called %s" % name
        base = j.target if j.awake else j.park
        return self.set(name, base + float(delta))

    def pose(self, name: str) -> Tuple[bool, str]:
        p = self.poses.get(name)
        if p is None:
            return False, "there is no pose called %s" % name
        for joint, deg in p.items():
            if joint in self.joints:
                self.set(joint, deg)
        return True, ""

    # ------------------------------------------------ poses you teach it
    # Move the arm where you want it with the sliders, give the position a
    # name, and from then on one tap puts it back there. Kept in data/, so a
    # new install of the code never loses them. The poses in config.yaml
    # cannot be overwritten or deleted from the website.
    def _load_saved(self) -> None:
        if not self.store or not os.path.exists(self.store):
            return
        try:
            with open(self.store, encoding="utf-8") as f:
                raw = json.load(f)
            for k, p in (raw or {}).items():
                name = str(k)
                if name in self.builtin:
                    continue
                self.saved[name] = {str(n): float(v) for n, v in (p or {}).items()}
                self.poses[name] = self.saved[name]
        except Exception:
            pass                       # a damaged file costs the poses, not the rover

    def _write_saved(self) -> None:
        if not self.store:
            return
        tmp = self.store + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.saved, f, indent=1, sort_keys=True)
        os.replace(tmp, self.store)

    def save_pose(self, name: str) -> Tuple[bool, str]:
        name = re.sub(r"\s+", " ", str(name or "")).strip()[:24]
        if not name:
            return False, "Give the pose a name"
        if name in self.builtin:
            return False, "%s is one of the built-in poses - pick another name" % name
        with self._lock:
            pose = {j.name: round(j.target, 1) for j in self.joints.values()
                    if j.group != "camera" and j.awake}
        if not pose:
            return False, "Move the arm first - nothing is holding a position yet"
        self.saved[name] = pose
        self.poses[name] = pose
        try:
            self._write_saved()
        except Exception as e:
            return False, "Could not save it: %s" % e
        return True, "Saved %s" % name

    def delete_pose(self, name: str) -> Tuple[bool, str]:
        if name in self.builtin:
            return False, "The built-in poses live in config.yaml"
        if name not in self.saved:
            return False, "There is no saved pose called %s" % name
        del self.saved[name]
        self.poses.pop(name, None)
        try:
            self._write_saved()
        except Exception as e:
            return False, "Could not save that: %s" % e
        return True, "Deleted %s" % name

    def relax(self, name: Optional[str] = None) -> None:
        """Stop the pulse: the joint goes limp. Mind anything it was holding up."""
        with self._lock:
            for j in self.joints.values():
                if name and j.name != name:
                    continue
                j.awake = False
                j.target = j.deg
                j._sent = None
                if self._hw is not None:                 # pragma: no cover
                    try:
                        self._hw.off(j.channel)
                    except Exception:
                        pass

    def hold(self) -> None:
        """Emergency stop: every joint stops exactly where it is, and holds."""
        with self._lock:
            for j in self.joints.values():
                j.target = j.deg

    def moving(self) -> bool:
        return any(j.awake and abs(j.target - j.deg) > 0.4
                   for j in self.joints.values())

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"live": self.live, "reason": self.reason,
                    "driver": self.driver,
                    "joints": [j.snapshot() for j in self.joints.values()],
                    "poses": list(self.poses.keys()),
                    "saved_poses": sorted(self.saved.keys())}

    def close(self) -> None:
        # Stop walking, but do not go limp: an arm held up by its servos
        # would drop. The PCA9685 keeps the last pulse going on its own.
        self._run = False
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        if self._hw is not None and self.driver == "gpio":   # pragma: no cover
            self._hw.close()

    # --------------------------------------------------------------- inside
    def _loop(self) -> None:
        period = 0.02
        last = time.time()
        while self._run:
            now = time.time()
            dt = min(0.1, now - last)
            last = now
            with self._lock:
                for j in self.joints.values():
                    if not j.awake:
                        continue
                    err = j.target - j.deg
                    step = j.speed * dt
                    if abs(err) <= step:
                        j.deg = j.target
                    else:
                        j.deg += step if err > 0 else -step
                    # only talk to the board when the pulse actually changes
                    if j._sent is None or abs(j.deg - j._sent) >= 0.25:
                        j._sent = j.deg
                        if self._hw is not None:         # pragma: no cover
                            try:
                                self._hw.pulse(j.channel, j.us(j.deg))
                            except Exception as e:
                                self.reason = "servo board stopped answering: %s" % e
            time.sleep(period)
