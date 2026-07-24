"""Zones (polygons) and tripwires (lines) + point/line tests used for counting,
attendance zones, table occupancy, and court regions."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence

Point = tuple[float, float]


def point_in_polygon(pt: Point, poly: Sequence[Point]) -> bool:
    """Ray-casting point-in-polygon test."""
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def _ccw(a: Point, b: Point, c: Point) -> bool:
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def segment_intersects(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """True if segment p1p2 intersects p3p4 (used for tripwire crossing)."""
    return _ccw(p1, p3, p4) != _ccw(p2, p3, p4) and _ccw(p1, p2, p3) != _ccw(p1, p2, p4)


def side_of_line(pt: Point, a: Point, b: Point) -> float:
    """Signed side of point relative to directed line a->b (>0 left, <0 right)."""
    return (b[0] - a[0]) * (pt[1] - a[1]) - (b[1] - a[1]) * (pt[0] - a[0])


@dataclass
class Zone:
    name: str
    polygon: list[Point]

    def contains(self, pt: Point) -> bool:
        return point_in_polygon(pt, self.polygon)


@dataclass
class Tripwire:
    """A directed line; counts crossings by which side a track moves to."""
    name: str
    a: Point
    b: Point
    _last_side: dict[int, float] = field(default_factory=dict)

    def update(self, track_id: int, pt: Point) -> str | None:
        """Feed a track's latest point. Returns 'in' / 'out' / None on crossing."""
        s = side_of_line(pt, self.a, self.b)
        prev = self._last_side.get(track_id)
        self._last_side[track_id] = s
        if prev is None or prev == 0:
            return None
        if prev < 0 <= s:
            return "in"
        if prev > 0 >= s:
            return "out"
        return None
