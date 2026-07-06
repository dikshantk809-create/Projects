# Project 3 — AI Tennis Analysis System

AI referee + match/player analytics for tennis: ball/player/court tracking, automated
IN/OUT line-calling, live scoring, rally/serve/shot stats, player movement analytics,
and spectator + coach dashboards.

> **Accuracy reality (read this):** broadcast Hawk-Eye uses **10+ calibrated cameras at
> ≥120 fps** and achieves ~few-mm accuracy. A single 30–50 fps camera gives **indicative**
> calls only. This system targets **club/academy grade**: ~85–92% line-call agreement
> with 1 good camera, rising toward 95%+ with **2+ synchronized ≥120 fps cameras +
> calibration**. See [`docs/16-accuracy-and-roadmap.md`](docs/16-accuracy-and-roadmap.md).

---

## 1. System Architecture
Capture (high-FPS camera) → ball tracker (TrackNetV4 heatmap) + player tracker
(YOLO11+ByteTrack) + court detector (lines→homography) → bounce detection → project
bounce to court plane → IN/OUT call → scoring FSM → events → backend → dashboards.
Tennis needs more compute per frame than the other two systems → **Jetson Orin or GPU**
recommended (see hardware). [`blueprint-docs/01-system-architecture.md`](blueprint-docs/01-system-architecture.md).

## 2. Hardware List
Tier B/C: NVIDIA Jetson Orin Nano/NX **or** RTX GPU box; **≥1 (ideally 2+) global-shutter
≥120 fps cameras**, fast lens, sturdy elevated mount, calibration target. A single Pi 5 +
Hailo can run player/court analytics but **not** reliable high-speed ball calls.
[`blueprint-docs/02-hardware-guide.md`](blueprint-docs/02-hardware-guide.md).

## 3. Software Stack
Python, PyTorch (TrackNetV4), Ultralytics YOLO11 (players), OpenCV (court lines,
homography), FastAPI, PostgreSQL16+TimescaleDB, React + Tailwind + Recharts, Grafana,
Docker. [`blueprint-docs/04-tech-stack.md`](blueprint-docs/04-tech-stack.md).

## 4. Database Design
[`db/schema.sql`](db/schema.sql): `matches`, `players`, `sets`, `games`, `points`,
`rallies`, `shots`, `ball_positions` (Timescale), `player_tracks` (Timescale),
`line_calls`, `serves`, `highlights`.

## 5. Folder Structure
Same layout: `backend/`, `edge/`, `ml/`, `dashboard/`, `db/`, `deploy/`, `tests/`.
Core logic: `edge/tennis_pipeline.py`, `backend/app/services/scoring.py`,
`backend/app/services/court.py`.

## 6. API Design
[`docs/06-api-design.md`](docs/06-api-design.md): `POST /matches`, `POST /ingest/events`,
`GET /matches/{id}/score` (live), `/matches/{id}/stats`, `/players/{id}/analytics`,
`/matches/{id}/calls`, `/matches/{id}/highlights`, `WS /ws/match/{id}` (live score + ball).

## 7. Dashboard Design
[`docs/07-dashboard-design.md`](docs/07-dashboard-design.md): **Spectator** (live score,
ball-tracking viz, stats, instant replay), **Coach** (strengths/weaknesses, shot
distribution, court heatmaps, tactical suggestions). Mobile-responsive.

## 8. AI Models Used
TrackNetV4 (ball heatmap tracking), YOLO11 + ByteTrack (players), classical+learned court
line detection → homography, bounce detector (trajectory inflection), serve-speed
estimation from ball displacement + calibration. [`blueprint-docs/07-ai-models-overview.md`](blueprint-docs/07-ai-models-overview.md).

## 9. Training Pipeline
[`docs/09-training-pipeline.md`](docs/09-training-pipeline.md): train/fine-tune TrackNet
on labeled tennis rallies (heatmap targets), YOLO player detection (pretrained ok),
court keypoint model; evaluate ball-tracking precision + bounce-localization error.

## 10. Deployment Guide
[`docs/10-deployment.md`](docs/10-deployment.md): GPU/Jetson inference node + backend +
dashboard via docker-compose; camera calibration step before first match.

## 11. Cost Estimation
Tier B ≈ $1.5k–3k; Tier C (true high-accuracy, multi-cam ≥120 fps) ≈ $10k–30k.
[`blueprint-docs/03-cost-estimation.md`](blueprint-docs/03-cost-estimation.md).

## 12. Security Design
No biometrics (sports analytics). JWT + RBAC (admin/coach/player/spectator), TLS,
match-data access control, signed replay/highlight URLs. [`blueprint-docs/05-security-and-compliance.md`](blueprint-docs/05-security-and-compliance.md).

## 13. Source Code
Edge: [`edge/tennis_pipeline.py`](edge/tennis_pipeline.py). Scoring FSM:
[`backend/app/services/scoring.py`](backend/app/services/scoring.py). Court/IN-OUT:
[`backend/app/services/court.py`](backend/app/services/court.py).

## 14. Raspberry Pi Setup
[`docs/14-raspberry-pi-setup.md`](docs/14-raspberry-pi-setup.md): Pi handles player/court
analytics + dashboard client; ball calls need Jetson/GPU. Includes camera calibration.

## 15. Step-by-Step Implementation Plan
[`docs/15-implementation-plan.md`](docs/15-implementation-plan.md): MVP (player tracking +
manual-assisted scoring) → Beta (ball tracking + auto IN/OUT + live score) → Production
(multi-cam calibration, highlights, coach analytics, accuracy validation).

## 16. Future Enhancements
Multi-camera triangulation for 3D ball + 95%+ calls, serve/stroke biomechanics, auto
highlight reels with commentary, broadcast overlay graphics, doubles support, wearable
fusion, opponent scouting reports. [`docs/16-accuracy-and-roadmap.md`](docs/16-accuracy-and-roadmap.md).

### Quick start
```bash
cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build
# API http://localhost:8003/docs   Dashboard http://localhost:5176
```
