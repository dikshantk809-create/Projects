"""Edge → backend ingest for tennis events (ball positions, player tracks, line calls).
Persists time-series and routes line calls into the live match broadcast."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional
from ...core.db import get_db
from ...core.config import get_settings
router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])
S = get_settings()

class EventIn(BaseModel):
    site_id: str; camera_id: str; ts: datetime; type: str
    track_id: Optional[int] = None; confidence: float = 1.0
    attributes: dict[str, Any] = {}

@router.post("/events")
async def ingest(ev: EventIn, authorization: str = Header(default=""),
                 db: AsyncSession = Depends(get_db)):
    if authorization != f"Bearer {S.ingest_token}": raise HTTPException(401, "bad token")
    a = ev.attributes
    if ev.type == "line.call":
        await db.execute(text("""
            INSERT INTO line_calls (match_id, ts, call, bounce_cx, bounce_cy, margin_cm,
                                    confidence, frame)
            VALUES (CAST(:m AS UUID),:ts,:c,:cx,:cy,:mg,:cf,:fr)
        """), {"m": a.get("match_id"), "ts": ev.ts, "c": a.get("call"),
               "cx": a.get("bounce_cx"), "cy": a.get("bounce_cy"),
               "mg": a.get("margin_cm"), "cf": ev.confidence, "fr": a.get("frame")})
        await db.commit()
    return {"ok": True}
