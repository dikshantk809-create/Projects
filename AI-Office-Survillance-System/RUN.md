# How to run — AI Office Surveillance (standalone)

This folder is fully self-contained (its own `platform/` library + `blueprint-docs/`).
You can run it **independently** of the other two projects.

## Option A — Docker (recommended, one command)
Install Docker Desktop, then from this folder:
```bash
cp .env.example .env        # edit secrets/tokens
docker compose -f deploy/docker-compose.yml up -d --build
```
Windows: just double-click **run.bat** (and **stop.bat** to stop).

Open:
- API + Swagger docs: http://localhost:8001/docs
- Dashboard:          http://localhost:5174
- Grafana:            http://localhost:3001

## Option B — Local dev (no Docker)
Needs Python 3.12 + a PostgreSQL/TimescaleDB you point `*_DATABASE_URL` at.
```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ./platform
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --port 8001 --reload
```

## Edge pipeline (camera) — run on the Pi/Jetson or your PC with a webcam
```bash
pip install -e "./platform[detect,face]" httpx
# point it at the backend, then:
python edge/*_pipeline.py          # uses AICAM_* vars from .env
```

## Running all THREE projects at the same time
Each project uses **different ports** (this one: API 8001, dashboard 5174, grafana 3001,
and its own database port), so you can start all three with `run.bat` / `docker compose up`
in each folder simultaneously without conflicts.
