"""Normalized event schema — the contract between edge pipelines and the backend.

Every product emits the same Event shape, so one ingest endpoint, one DB hypertable
and one alert engine serve all three systems.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    # shared
    DETECTION = "detection"
    INTRUSION = "intrusion"
    SYSTEM = "system"
    # office
    ATTENDANCE_ENTRY = "attendance.entry"
    ATTENDANCE_EXIT = "attendance.exit"
    BEHAVIOR = "behavior"            # working/idle/phone/talking/walking/break
    SAFETY_FIRE = "safety.fire"
    SAFETY_SMOKE = "safety.smoke"
    SAFETY_WEAPON = "safety.weapon"
    SAFETY_VIOLENCE = "safety.violence"
    SAFETY_FALL = "safety.fall"
    # restaurant
    COUNT_IN = "count.in"
    COUNT_OUT = "count.out"
    TABLE_OCCUPIED = "table.occupied"
    TABLE_VACATED = "table.vacated"
    CUSTOMER_BEHAVIOR = "customer.behavior"
    # tennis
    BALL_BOUNCE = "ball.bounce"
    LINE_CALL = "line.call"          # in / out / let
    RALLY = "rally"
    SERVE = "serve"
    POINT = "point"


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float: return self.x + self.w / 2
    @property
    def cy(self) -> float: return self.y + self.h / 2
    @property
    def foot(self) -> tuple[float, float]:
        """Bottom-center point — best proxy for a person's ground position."""
        return (self.x + self.w / 2, self.y + self.h)


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    site_id: str
    camera_id: str
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: EventType
    track_id: Optional[int] = None
    subject_id: Optional[str] = None      # employee id / customer hash / player id
    confidence: float = 1.0
    zone: Optional[str] = None
    bbox: Optional[BBox] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    media_ref: Optional[str] = None       # s3/minio uri of evidence clip


class Debouncer:
    """Suppress repeated events of the same (type, key) within a cooldown window."""
    def __init__(self, cooldown_s: float = 10.0):
        self.cooldown_s = cooldown_s
        self._last: dict[tuple, float] = {}

    def allow(self, key: tuple, now: float) -> bool:
        last = self._last.get(key)
        if last is None or (now - last) >= self.cooldown_s:
            self._last[key] = now
            return True
        return False
