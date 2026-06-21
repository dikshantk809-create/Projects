"""Edge → backend event ingest. Token-authenticated; writes to events hypertable,
updates attendance/behavior, and triggers alerts for security events."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.db import get_db
from ...core.config import get_settings
from ...schemas.events import EventIn

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])
S = get_settings()

async def _auth(authorization: str = Header(default="")):
    if authorization != f"Bearer {S.ingest_token}":
        raise HTTPException(401, "bad ingest token")

@router.post("/events", dependencies=[Depends(_auth)])
async def ingest_event(ev: EventIn, db: AsyncSession = Depends(get_db)):
    await db.execute(text("""
        INSERT INTO events (ts, site_id, camera_id, type, track_id, subject_id,
                            confidence, zone, bbox, attributes, media_ref)
        VALUES (:ts,:site,:cam,:type,:tid,:sid,:conf,:zone,
                CAST(:bbox AS JSONB), CAST(:attr AS JSONB), :media)
    """), {
        "ts": ev.ts, "site": ev.site_id, "cam": ev.camera_id, "type": ev.type,
        "tid": ev.track_id, "sid": ev.subject_id, "conf": ev.confidence,
        "zone": ev.zone, "bbox": _json(ev.bbox), "attr": _json(ev.attributes),
        "media": ev.media_ref,
    })
    # security events → incident + alert (handled by a worker in production)
    if ev.type in ("intrusion", "safety.fire", "safety.smoke", "safety.weapon",
                   "safety.violence", "safety.fall"):
        await db.execute(text("""
            INSERT INTO security_incidents (camera_id, kind, severity, confidence)
            VALUES (:cam,:kind,:sev,:conf)
        """), {"cam": ev.camera_id, "kind": ev.type.replace("safety.", ""),
               "sev": "critical" if ev.type != "intrusion" else "warning",
               "conf": ev.confidence})
    await db.commit()
    return {"ok": True}

import json
def _json(v): return json.dumps(v) if v is not None else None
