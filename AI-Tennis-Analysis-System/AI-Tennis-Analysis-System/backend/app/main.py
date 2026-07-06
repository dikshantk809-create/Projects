from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import get_settings
from .api.routes import match, ingest
S = get_settings()
app = FastAPI(title=S.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=S.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(match.router)
app.include_router(ingest.router)
@app.get("/health")
async def health(): return {"status": "ok", "service": S.app_name}
