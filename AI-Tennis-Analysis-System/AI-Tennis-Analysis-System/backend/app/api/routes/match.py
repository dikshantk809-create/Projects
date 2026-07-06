"""Match lifecycle + live scoring + line calls. Scoring state is held in memory per
match for low-latency live updates and periodically persisted (see workers)."""
from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from ...services.scoring import TennisMatch
from ...core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["match"])
S = get_settings()
MATCHES: dict[str, TennisMatch] = {}          # match_id -> scoring FSM
WATCHERS: dict[str, set] = {}                 # match_id -> websockets

class NewMatch(BaseModel):
    match_id: str; best_of: int = 3
class PointIn(BaseModel):
    winner: str                               # 'a' | 'b'
    reason: str = "winner"

@router.post("/matches")
async def create_match(m: NewMatch):
    MATCHES[m.match_id] = TennisMatch(best_of=m.best_of)
    return {"match_id": m.match_id, "score": MATCHES[m.match_id].summary()}

@router.get("/matches/{mid}/score")
async def score(mid: str):
    if mid not in MATCHES: raise HTTPException(404, "no such match")
    return MATCHES[mid].summary()

@router.post("/matches/{mid}/point")
async def add_point(mid: str, pt: PointIn):
    if mid not in MATCHES: raise HTTPException(404, "no such match")
    summary = MATCHES[mid].point(pt.winner)
    await _broadcast(mid, {"type": "score", **summary, "reason": pt.reason})
    return summary

class CallIn(BaseModel):
    call: str; margin_cm: float; confidence: float; close: bool = False
@router.post("/matches/{mid}/call")
async def line_call(mid: str, c: CallIn, authorization: str = Header(default="")):
    if authorization != f"Bearer {S.ingest_token}": raise HTTPException(401, "bad token")
    await _broadcast(mid, {"type": "call", **c.model_dump()})
    return {"ok": True}

async def _broadcast(mid: str, msg: dict):
    for ws in list(WATCHERS.get(mid, set())):
        try: await ws.send_json(msg)
        except Exception: WATCHERS[mid].discard(ws)

@router.websocket("/ws/match/{mid}")
async def ws_match(ws: WebSocket, mid: str):
    await ws.accept(); WATCHERS.setdefault(mid, set()).add(ws)
    if mid in MATCHES: await ws.send_json({"type": "score", **MATCHES[mid].summary()})
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: WATCHERS[mid].discard(ws)
