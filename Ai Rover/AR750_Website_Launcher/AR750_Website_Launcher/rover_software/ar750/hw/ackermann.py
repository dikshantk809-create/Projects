"""How the AR-750 actually turns, worked out from its own steering linkage.

This machine steers like a car, not like a tank. That one fact changes more of
the software than anything else, so it gets its own file.

The linkage, measured off AR-750_Rover_Complete_Assembly.f3d:

    servo horn  ---drag link--->  steer plate  ---tie rods--->  steering arms
      12 mm                        pivot at                       39.8 mm
      radius                     x=-225, y=0                      on each
                                 pickup 40 mm                     upright
                                 tie rods 64 mm

Wind that through and full servo travel gives about 24.7 degrees at the road
wheels, which on a 540 mm wheelbase is a turning radius of about 1.17 m to the
rear axle centre - call it a 2.8 m circle for the whole machine.

WHAT THAT MEANS, and it matters:

  * It CANNOT turn on the spot. There is no differential steering to fall back
    on: both axles are driven from the same pair of motors through diffs, and
    the wheels themselves have to be pointed.
  * At the end of a crop row it needs either a headland 2.8 m wide, or a three
    point turn. The mission code does the three point turn, because most
    kitchen plots do not have 2.8 m to spare.
  * Driving it with a "left stick / right stick" mental model will not work.
    Throttle is one thing, steering is another.

Every number here is a default taken from the CAD. Measure the real linkage
once it is built and correct them in config.yaml - a linkage is exactly the
sort of thing that ends up 3 mm different from the drawing.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple


class Steering:
    def __init__(self, cfg: dict, rover_cfg: dict):
        s = (cfg or {}).get("linkage", {}) or {}
        self.horn_r = float(s.get("servo_horn_mm", 12.0))
        self.drag_r = float(s.get("plate_pickup_mm", 40.0))
        self.tie_r = float(s.get("plate_tierod_mm", 64.0))
        self.arm = float(s.get("steer_arm_mm", 39.8))
        self.servo_max = float((cfg or {}).get("servo_max_deg", 60.0))

        self.wheelbase = float(rover_cfg.get("wheelbase_mm", 540.0))
        self.track = float(rover_cfg.get("track_mm", 430.0))

        # a measured override beats the linkage maths every time
        self.wheel_max = float((cfg or {}).get("max_wheel_deg", 0) or 0)
        if self.wheel_max <= 0:
            self.wheel_max = self.wheel_angle(self.servo_max) or 24.7

    # ------------------------------------------------------- linkage, in mm
    def wheel_angle(self, servo_deg: float) -> Optional[float]:
        """Road wheel angle for a given servo angle. None if the linkage jams."""
        sign = 1.0 if servo_deg >= 0 else -1.0
        s = self.horn_r * math.sin(math.radians(min(abs(servo_deg), 90.0)))
        if s > self.drag_r:
            return None
        plate = math.asin(s / self.drag_r)
        tie = self.tie_r * math.sin(plate)
        if tie > self.arm:
            return None
        return sign * math.degrees(math.asin(tie / self.arm))

    def servo_for_wheel(self, wheel_deg: float) -> float:
        """The servo angle that gives this wheel angle. Clamped to what it can do."""
        want = max(-self.wheel_max, min(self.wheel_max, wheel_deg))
        lo, hi = 0.0, self.servo_max
        for _ in range(40):                       # the linkage is not linear,
            mid = (lo + hi) / 2                   # so solve it rather than
            w = self.wheel_angle(mid)             # assuming a straight line
            if w is None or w > abs(want):
                hi = mid
            else:
                lo = mid
        return math.copysign((lo + hi) / 2, want)

    # --------------------------------------------------------- what it means
    def turn_radius(self, wheel_deg: float) -> Optional[float]:
        """Radius in mm about the rear axle centre. None when going straight."""
        a = abs(wheel_deg)
        if a < 0.25:
            return None
        return self.wheelbase / math.tan(math.radians(a))

    def turning_circle_mm(self) -> float:
        """Outside diameter of the smallest circle it can drive."""
        r = self.turn_radius(self.wheel_max) or 1e9
        return 2.0 * (r + self.track / 2.0)

    def ackermann(self, wheel_deg: float) -> Tuple[float, float]:
        """Inner and outer wheel angles. They are not the same, which is the
        whole point of a steering linkage: the inner wheel turns more."""
        R = self.turn_radius(wheel_deg)
        if R is None:
            return 0.0, 0.0
        half = self.track / 2.0
        inner = math.degrees(math.atan(self.wheelbase / (R - half)))
        outer = math.degrees(math.atan(self.wheelbase / (R + half)))
        s = 1.0 if wheel_deg >= 0 else -1.0
        return s * inner, s * outer

    def yaw_rate_dps(self, speed_mps: float, wheel_deg: float) -> float:
        """How fast it comes round, at this speed and this steering angle."""
        R = self.turn_radius(wheel_deg)
        if R is None or R <= 0:
            return 0.0
        s = 1.0 if wheel_deg >= 0 else -1.0
        return s * math.degrees(speed_mps / (R / 1000.0))

    def stick_to_wheel(self, steer: float) -> float:
        """-1..1 from a stick or a row follower, to a wheel angle in degrees."""
        steer = max(-1.0, min(1.0, steer))
        return steer * self.wheel_max

    def describe(self) -> Dict[str, float]:
        return {
            "max_wheel_deg": round(self.wheel_max, 1),
            "min_turn_radius_mm": round(self.turn_radius(self.wheel_max) or 0),
            "turning_circle_mm": round(self.turning_circle_mm()),
            "wheelbase_mm": self.wheelbase,
            "track_mm": self.track,
            "can_spin_on_the_spot": False,
        }
