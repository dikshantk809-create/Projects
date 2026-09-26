"""Tilt and heading, from an MPU6050 or a BNO085.

Two things this gives you that nothing else can:

  * a real tilt reading, so "stop if it leans more than 25 degrees" actually
    works. Without it that rule can never fire, and the rover will happily drive
    itself down a bank.
  * a heading that does not drift with the wheels, so it goes down the row
    straight instead of slowly curving.

Wiring: it is I2C, so it shares SDA and SCL with the servo board and the ADC.
MPU6050 sits at 0x68. Mount it flat, with the arrow pointing forwards, and bolt
it to the chassis rather than the body panel - a panel flexes and you will read
the flex.
"""
from __future__ import annotations

import math
import threading
import time
from typing import Optional

try:
    from smbus2 import SMBus                             # type: ignore
except Exception:                                        # pragma: no cover
    try:
        from smbus import SMBus                          # type: ignore
    except Exception:
        SMBus = None

PWR_MGMT_1 = 0x6B
ACCEL_XOUT = 0x3B
GYRO_ZOUT = 0x47


def _s16(hi: int, lo: int) -> int:
    v = (hi << 8) | lo
    return v - 65536 if v > 32767 else v


class IMU:
    def __init__(self, cfg: dict, sim: bool = False):
        c = (cfg or {}).get("imu", {}) or {}
        self.enabled = bool(c.get("enabled"))
        self.addr = int(c.get("i2c_addr", 0x68))
        self.bus_no = int(c.get("bus", 1))
        self.sim = sim or SMBus is None or not self.enabled
        self.reason = ("switched off in the config" if not self.enabled
                       else "no I2C library" if SMBus is None else "")

        self.tilt_deg = 0.0          # how far off level, either way
        self.roll_deg = 0.0
        self.pitch_deg = 0.0
        self.heading_deg = 0.0       # integrated from the z gyro, relative
        self.turn_rate_dps = 0.0

        self._bus = None
        self._zero_gyro = 0.0
        self._t = time.time()
        self._lock = threading.Lock()

        if not self.sim:                                  # pragma: no cover
            try:
                self._bus = SMBus(self.bus_no)
                self._bus.write_byte_data(self.addr, PWR_MGMT_1, 0)
                time.sleep(0.1)
                self._calibrate()
            except Exception as e:
                self.sim = True
                self.reason = str(e)

    @property
    def live(self) -> bool:
        return not self.sim

    def _calibrate(self, samples: int = 80) -> None:      # pragma: no cover
        """Sit still for a moment and learn what 'not turning' reads as."""
        total = 0.0
        for _ in range(samples):
            d = self._bus.read_i2c_block_data(self.addr, GYRO_ZOUT, 2)
            total += _s16(d[0], d[1]) / 131.0
            time.sleep(0.004)
        self._zero_gyro = total / samples

    def read(self) -> Optional[dict]:
        if self.sim:
            return None
        try:                                              # pragma: no cover
            d = self._bus.read_i2c_block_data(self.addr, ACCEL_XOUT, 6)
            ax = _s16(d[0], d[1]) / 16384.0
            ay = _s16(d[2], d[3]) / 16384.0
            az = _s16(d[4], d[5]) / 16384.0
            g = self._bus.read_i2c_block_data(self.addr, GYRO_ZOUT, 2)
            gz = _s16(g[0], g[1]) / 131.0 - self._zero_gyro
        except Exception:
            return None

        now = time.time()
        with self._lock:
            dt = max(1e-3, min(0.5, now - self._t))
            self._t = now
        self.pitch_deg = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
        self.roll_deg = math.degrees(math.atan2(ay, az if az else 1e-6))
        self.tilt_deg = max(abs(self.pitch_deg), abs(self.roll_deg))
        self.turn_rate_dps = gz
        self.heading_deg = (self.heading_deg + gz * dt) % 360.0
        return {"tilt_deg": round(self.tilt_deg, 1),
                "pitch_deg": round(self.pitch_deg, 1),
                "roll_deg": round(self.roll_deg, 1),
                "heading_deg": round(self.heading_deg, 1),
                "turn_rate_dps": round(gz, 1)}

    def zero_heading(self) -> None:
        self.heading_deg = 0.0

    def close(self) -> None:
        if self._bus:                                     # pragma: no cover
            try:
                self._bus.close()
            except Exception:
                pass
