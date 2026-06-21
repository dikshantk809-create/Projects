from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel

class EventIn(BaseModel):
    event_id: Optional[str] = None
    site_id: str
    camera_id: str
    ts: datetime
    type: str
    track_id: Optional[int] = None
    subject_id: Optional[str] = None
    confidence: float = 1.0
    zone: Optional[str] = None
    bbox: Optional[dict] = None
    attributes: dict[str, Any] = {}
    media_ref: Optional[str] = None
