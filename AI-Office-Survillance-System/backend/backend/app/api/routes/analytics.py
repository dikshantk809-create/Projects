"""Attendance + productivity read APIs for the dashboard."""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.db import get_db
from ...core.security import require_role

router = APIRouter(prefix="/api/v1", tags=["analytics"])

@router.get("/attendance")
async def attendance(work_date: date | None = None, db: AsyncSession = Depends(get_db),
                     _u=Depends(require_role("hr", "security"))):
    rows = (await db.execute(text("""
        SELECT a.employee_id, e.full_name, a.entry_time, a.exit_time,
               a.work_seconds, a.status
        FROM attendance a JOIN employees e ON e.id=a.employee_id
        WHERE a.work_date = COALESCE(:d, CURRENT_DATE)
        ORDER BY a.entry_time NULLS LAST
    """), {"d": work_date})).mappings().all()
    return {"date": str(work_date or date.today()), "rows": [dict(r) for r in rows]}

@router.get("/productivity/daily")
async def productivity_daily(work_date: date | None = None,
                             db: AsyncSession = Depends(get_db),
                             _u=Depends(require_role("hr"))):
    rows = (await db.execute(text("""
        SELECT p.employee_id, e.full_name, p.working_sec, p.idle_sec, p.phone_sec,
               p.meeting_sec, p.productivity_score
        FROM productivity_daily p JOIN employees e ON e.id=p.employee_id
        WHERE p.work_date = COALESCE(:d, CURRENT_DATE)
        ORDER BY p.productivity_score DESC
    """), {"d": work_date})).mappings().all()
    return {"ranking": [dict(r) for r in rows]}

@router.get("/security/incidents")
async def incidents(status: str | None = None, db: AsyncSession = Depends(get_db),
                    _u=Depends(require_role("security"))):
    rows = (await db.execute(text("""
        SELECT id, ts, camera_id, kind, severity, status, confidence
        FROM security_incidents
        WHERE (:s IS NULL OR status = :s)
        ORDER BY ts DESC LIMIT 200
    """), {"s": status})).mappings().all()
    return {"incidents": [dict(r) for r in rows]}
