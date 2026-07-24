# Project 1 — AI Office Surveillance System

Turn ordinary office CCTV/IP cameras into an AI platform for **attendance,
productivity analytics, and 24/7 security/safety** — running on a Raspberry Pi 5 edge
node and a FastAPI + PostgreSQL + React backend.

> ⚠️ **Legal first:** this system processes employee **biometric data** and monitors
> behavior. Consent, notice, retention limits and a DPIA are mandatory (GDPR/BIPA).
> Prefer **aggregate** productivity analytics over individual scoring. See
> [`blueprint-docs/05-security-and-compliance.md`](blueprint-docs/05-security-and-compliance.md).

---

## 1. System Architecture
Edge-first (see [`blueprint-docs/01-system-architecture.md`](blueprint-docs/01-system-architecture.md)).
Per floor: a Pi 5 + AI HAT+ ingests camera RTSP, runs YOLO11 person/object detection +
ByteTrack + InsightFace recognition + pose-based behavior, applies zone/attendance/
safety rules, records evidence clips locally, and streams compact **events** to the
backend. The FastAPI server persists events to PostgreSQL/TimescaleDB, computes
attendance & productivity, fans out alerts (push/SMS/WhatsApp/email), and serves the
React dashboard + Grafana.

```
Cameras → Pi5+Hailo edge (detect→track→face→pose→rules→evidence) → events →
FastAPI ingest → Postgres/Timescale + MinIO → dashboard / Grafana / alerts
```

## 2. Hardware List
Tier A per floor (Pi 5 8GB + AI HAT+ Hailo-8, Pi Cam 3 and/or 2–4 IP cams, 256GB+
NVMe, UPS, active cooling, PoE switch). Large buildings → Tier B Jetson Orin.
Full bill of materials: [`blueprint-docs/02-hardware-guide.md`](blueprint-docs/02-hardware-guide.md).

## 3. Software Stack
Python 3.12, Ultralytics YOLO11 (→YOLO26), ByteTrack, InsightFace/ArcFace, YOLO11-pose,
OpenCV, FastAPI, PostgreSQL16+TimescaleDB, Redis, MinIO, React+Vite+Tailwind, Recharts,
Grafana, Docker. Details: [`blueprint-docs/04-tech-stack.md`](blueprint-docs/04-tech-stack.md).

## 4. Database Design
See [`db/schema.sql`](db/schema.sql). Core tables: `employees`, `face_embeddings`,
`cameras`, `zones`, `events` (Timescale hypertable), `attendance` (entry/exit/work
hours), `behavior_samples`, `productivity_daily`, `security_incidents`,
`evidence_clips`, `users`/`roles` (RBAC), `audit_log`, `consent`.

## 5. Folder Structure
```
project-1-office-surveillance/
├── backend/app/   FastAPI: api/routes, core(config,security,db), models, schemas,
│                  services(attendance, productivity, security, recognition), workers
├── edge/          office_pipeline.py (main edge loop) + pipelines/
├── ml/            datasets/ training/ export/ (behavior + safety fine-tuning)
├── dashboard/     React (Live, Attendance, Productivity, Security, Admin)
├── db/            schema.sql, migrations (Alembic)
├── deploy/        docker-compose, Dockerfiles, grafana/, k8s/
└── tests/
```

## 6. API Design
REST + WebSocket (full table in [`docs/06-api-design.md`](docs/06-api-design.md)):
- `POST /api/v1/ingest/events` — edge → backend event ingest (token auth)
- `POST /api/v1/employees` / `GET /api/v1/employees` — CRUD + enrollment
- `POST /api/v1/employees/{id}/enroll` — upload face image(s) → embedding
- `GET /api/v1/attendance?date=&employee=` — attendance + work hours
- `GET /api/v1/productivity/daily|weekly|monthly` — scores, ranking, charts data
- `GET /api/v1/security/incidents` · `GET /api/v1/security/{id}/clip`
- `GET /api/v1/cameras` · `GET /api/v1/cameras/{id}/stream` (WebRTC/HLS)
- `WS /ws/live` — live events/alerts; `WS /ws/feed/{camera_id}` — annotations
- `POST /api/v1/subjects/{id}/erase` — right-to-erasure (GDPR)

## 7. Dashboard Design
React + Tailwind, mobile-responsive. Pages: **Live** (multi-camera grid + real-time
alerts), **Attendance** (daily roster, entry/exit, work hours), **Productivity**
(scores, trends, ranking, mobile-usage hours, heatmaps), **Security** (intrusion
timeline, incident clips, visitor history, alarm/light controls), **Admin** (employees,
enrollment, cameras, zones, RBAC, retention/consent). Wireframes:
[`docs/07-dashboard-design.md`](docs/07-dashboard-design.md).

## 8. AI Models Used
YOLO11 (person/phone/bag + fine-tuned fire/smoke/weapon), ByteTrack tracking,
InsightFace ArcFace recognition, YOLO11-pose → behavior classifier (working/idle/
phone/talking/walking/break/meeting) and fall detection, temporal model for violence.
See [`blueprint-docs/07-ai-models-overview.md`](blueprint-docs/07-ai-models-overview.md).

## 9. Training Pipeline
[`ml/`](ml/): collect+label (CVAT/Roboflow) → train YOLO fine-tunes (fire/smoke/weapon,
phone-in-hand) + behavior temporal head on pose sequences → evaluate (PR curves per
class) → export ONNX→HEF(Hailo)/TensorRT → register in MLflow. Commands in
[`docs/09-training-pipeline.md`](docs/09-training-pipeline.md). Pretrained COCO + ArcFace
get you to MVP with no training.

## 10. Deployment Guide
`cp .env.example .env` → `docker compose -f deploy/docker-compose.yml up -d --build`.
Edge: flash Pi OS, install HailoRT + deps, run `edge/office_pipeline.py`. Full guide +
fleet/k3s: [`docs/10-deployment.md`](docs/10-deployment.md) and
[`blueprint-docs/06-deployment-devops.md`](blueprint-docs/06-deployment-devops.md).

## 11. Cost Estimation
Tier A ≈ $400–950 one-time + ~$40–135/mo per floor. See
[`blueprint-docs/03-cost-estimation.md`](blueprint-docs/03-cost-estimation.md).

## 12. Security Design
RBAC (admin/security/hr/viewer), JWT, TLS/mTLS, edge-only raw video, encrypted storage,
audit logging of footage access, retention + auto-deletion, right-to-erasure, evidence
hashing. See [`blueprint-docs/05-security-and-compliance.md`](blueprint-docs/05-security-and-compliance.md).

## 13. Source Code
Edge loop: [`edge/office_pipeline.py`](edge/office_pipeline.py). Backend:
[`backend/app/`](backend/app/). Behavior/productivity logic:
[`backend/app/services/`](backend/app/services/). Built on shared
[`platform/aicam_platform`](platform/aicam_platform).

## 14. Raspberry Pi Setup
[`docs/14-raspberry-pi-setup.md`](docs/14-raspberry-pi-setup.md): Pi OS 64-bit, AI HAT+
firmware + HailoRT, Python env, camera enable, model HEF, systemd service, auto-start.

## 15. Step-by-Step Implementation Plan
[`docs/15-implementation-plan.md`](docs/15-implementation-plan.md): MVP (attendance on
one camera) → Beta (productivity + security + multi-cam + alerts) → Production (fleet,
HA, compliance, accuracy validation).

## 16. Future Enhancements
Multi-site federation, anti-spoofing/liveness, mask/PPE compliance, desk-occupancy &
space optimization, Slack/Teams attendance bot, anomaly detection, on-device LLM
incident summaries, access-control (door) integration.

---
### Quick start
```bash
cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build
# API docs: http://localhost:8001/docs   Dashboard: http://localhost:5174
```
