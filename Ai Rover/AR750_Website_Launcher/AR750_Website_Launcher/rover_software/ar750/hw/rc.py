"""Your 6 channel remote, read by the Pi.

Three ways in, pick one in config.yaml:

  sbus  - one wire from the receiver's SBUS pad to the Pi RX through an
          inverter, 100000 baud 8E2. This is the tidiest and what most
          6 channel sets can do today.
  ppm   - one wire carrying all channels, read with pigpio callbacks.
  pwm   - six separate servo wires, one per channel.

Every channel comes out as -1.0 .. 1.0, with 0 in the middle. If the receiver
goes quiet, `live` goes false and the safety layer stops the rover.
"""
from __future__ import annotations

import threading
import time
from typing import List, Optional

try:
    import serial                                    # type: ignore
except Exception:                                    # pragma: no cover
    serial = None

try:
    import pigpio                                    # type: ignore
except Exception:                                    # pragma: no cover
    pigpio = None

N = 8


class RCReceiver:
    def __init__(self, cfg: dict, sim: bool = False):
        self.cfg = cfg
        self.map = cfg.get("map", {})
        self.deadband = float(cfg.get("deadband", 0.05))
        self.proto = cfg.get("protocol", "sim")
        self.enabled = bool(cfg.get("enabled", True))
        self.sim = sim or self.proto == "sim" or not self.enabled

        self.raw_us: List[int] = [1500] * N
        self.values: List[float] = [0.0] * N
        self.last_frame = 0.0
        self._lock = threading.Lock()
        self._run = True
        self._ser = None
        self._pi = None
        self._ppm_last = 0
        self._ppm_idx = 0

        if not self.sim:                             # pragma: no cover
            try:
                if self.proto == "sbus":
                    self._ser = serial.Serial(cfg.get("sbus_port", "/dev/serial0"),
                                              baudrate=100000, bytesize=serial.EIGHTBITS,
                                              parity=serial.PARITY_EVEN,
                                              stopbits=serial.STOPBITS_TWO, timeout=0.02)
                elif self.proto in ("ppm", "pwm"):
                    self._pi = pigpio.pi()
                    if not self._pi.connected:
                        raise RuntimeError("pigpio not running")
                    if self.proto == "ppm":
                        pin = int(cfg.get("ppm_pin", 7))
                        self._pi.set_mode(pin, pigpio.INPUT)
                        self._pi.callback(pin, pigpio.RISING_EDGE, self._on_ppm)
                    else:
                        self._pwm_start = {}
                        for i, pin in enumerate(cfg.get("pwm_pins", [])[:N]):
                            self._pi.set_mode(pin, pigpio.INPUT)
                            self._pi.callback(pin, pigpio.EITHER_EDGE,
                                              self._make_pwm_cb(i))
            except Exception:
                self.sim = True
                self._ser = None
                self._pi = None

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ api
    @property
    def live(self) -> bool:
        if self.sim:
            return False
        return (time.time() - self.last_frame) < float(
            self.cfg.get("failsafe_hold_s", 0.5))

    def channel(self, name: str) -> float:
        idx = self.map.get(name)
        if idx is None:
            return 0.0
        with self._lock:
            return self.values[idx] if idx < len(self.values) else 0.0

    def switch3(self, name: str) -> int:
        """A 3 position switch as -1, 0 or +1."""
        v = self.channel(name)
        if v < -0.4:
            return -1
        if v > 0.4:
            return 1
        return 0

    def switch2(self, name: str) -> bool:
        return self.channel(name) > 0.3

    def snapshot(self) -> List[float]:
        with self._lock:
            return list(self.values)

    def close(self) -> None:
        self._run = False
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        if self._ser is not None:                    # pragma: no cover
            try:
                self._ser.close()
            except Exception:
                pass
        if self._pi is not None:                     # pragma: no cover
            self._pi.stop()

    # -------------------------------------------------------------- inside
    def _loop(self) -> None:
        while self._run:
            if self.sim:
                time.sleep(0.05)
                continue
            if self.proto == "sbus":                 # pragma: no cover
                self._read_sbus()
            else:
                self._publish()
                time.sleep(0.02)

    def _publish(self) -> None:
        with self._lock:
            self.values = [self._norm(us) for us in self.raw_us]

    def _norm(self, us: int) -> float:
        v = (us - 1500) / 500.0
        v = max(-1.0, min(1.0, v))
        return 0.0 if abs(v) < self.deadband else v

    # ---- SBUS
    def _read_sbus(self) -> None:                    # pragma: no cover
        try:
            data = self._ser.read(75)
        except Exception:
            time.sleep(0.05)
            return
        if not data:
            return
        i = data.find(b"\x0f")
        while i >= 0 and i + 25 <= len(data):
            frame = data[i:i + 25]
            if frame[24] in (0x00, 0x04, 0x14, 0x24, 0x34):
                self._decode_sbus(frame)
                self.last_frame = time.time()
            i = data.find(b"\x0f", i + 25)

    def _decode_sbus(self, f: bytes) -> None:        # pragma: no cover
        ch = [0] * 16
        ch[0] = ((f[1] | f[2] << 8) & 0x07FF)
        ch[1] = ((f[2] >> 3 | f[3] << 5) & 0x07FF)
        ch[2] = ((f[3] >> 6 | f[4] << 2 | f[5] << 10) & 0x07FF)
        ch[3] = ((f[5] >> 1 | f[6] << 7) & 0x07FF)
        ch[4] = ((f[6] >> 4 | f[7] << 4) & 0x07FF)
        ch[5] = ((f[7] >> 7 | f[8] << 1 | f[9] << 9) & 0x07FF)
        ch[6] = ((f[9] >> 2 | f[10] << 6) & 0x07FF)
        ch[7] = ((f[10] >> 5 | f[11] << 3) & 0x07FF)
        # SBUS 172..1811 maps onto 1000..2000 us
        with self._lock:
            self.raw_us = [int(1000 + (c - 172) * (1000.0 / 1639.0)) for c in ch[:N]]
            self.values = [self._norm(us) for us in self.raw_us]

    # ---- PPM
    def _on_ppm(self, gpio, level, tick):            # pragma: no cover
        gap = pigpio.tickDiff(self._ppm_last, tick)
        self._ppm_last = tick
        if gap > 3000:
            self._ppm_idx = 0
            self.last_frame = time.time()
            return
        if self._ppm_idx < N:
            with self._lock:
                self.raw_us[self._ppm_idx] = int(gap)
            self._ppm_idx += 1

    # ---- separate PWM wires
    def _make_pwm_cb(self, idx: int):                # pragma: no cover
        def cb(gpio, level, tick):
            if level == 1:
                self._pwm_start[idx] = tick
            elif level == 0 and idx in self._pwm_start:
                w = pigpio.tickDiff(self._pwm_start[idx], tick)
                if 800 < w < 2200:
                    with self._lock:
                        self.raw_us[idx] = int(w)
                    self.last_frame = time.time()
        return cb
