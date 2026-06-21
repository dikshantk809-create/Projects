"""FastAPI application factory for AI Office Surveillance."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .core.config import get_settings
from .api.routes import ingest, analytics

S = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: warm caches / connect redis pubsub here
    yield
    # shutdown

app = FastAPI(title=S.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=S.cors_origins,
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
app.include_router(ingest.router)
app.include_router(analytics.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": S.app_name}

# --- live updates: WebSocket hub (events/alerts pushed to dashboard) ---
class Hub:
    def __init__(self): self.clients: set[WebSocket] = set()
    async def join(self, ws): await ws.accept(); self.clients.add(ws)
    def leave(self, ws): self.clients.discard(ws)
    async def broadcast(self, msg: dict):
        for ws in list(self.clients):
            try: await ws.send_json(msg)
            except Exception: self.leave(ws)

hub = Hub()

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await hub.join(ws)
    try:
        while True:
            await ws.receive_text()   # keepalive / client pings
    except WebSocketDisconnect:
        hub.leave(ws)
