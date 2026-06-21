# 04 — Software Stack

| Layer | Technology | Version (2026) | Why |
|-------|-----------|----------------|-----|
| Language (AI/edge/backend) | Python | 3.11 / 3.12 | ecosystem, OpenCV/Ultralytics |
| Detection | Ultralytics YOLO | YOLO11 default, YOLO26 upgrade | SOTA, multi-task, edge export |
| Tracking | ByteTrack / BoT-SORT | via Ultralytics + supervision | real-time stable IDs |
| Face | InsightFace (ArcFace buffalo_l) | ONNXRuntime | 99.8% LFW, production-proven |
| CV utils | OpenCV, supervision, NumPy | 4.x / latest | decode, draw, zones, line-cross |
| Pose/actions | YOLO11-pose + temporal head | | behavior/productivity classes |
| Edge accel | Hailo (HailoRT/SDK), TensorRT, ONNXRuntime | | Pi/Jetson/GPU backends |
| Backend API | FastAPI + Uvicorn/Gunicorn | latest | async, OpenAPI, WS |
| Validation | Pydantic v2 | | typed schemas |
| ORM/migrations | SQLAlchemy 2 + Alembic | | |
| DB (OLTP+TS) | PostgreSQL 16 + TimescaleDB | | relational + hypertables |
| Cache/stream | Redis 7 (+ Streams) / MQTT | | edge→cloud bus, cache |
| Object storage | MinIO (S3-compatible) / AWS S3 | | clips, faces, evidence |
| Background jobs | Celery / RQ / arq | | reports, exports, retraining |
| Dashboard | React 18 + Vite + TypeScript + Tailwind | | mobile-responsive SPA |
| Charts | Recharts (+ Grafana embeds) | | |
| Live video | WebRTC (go2rtc/mediamtx) or HLS | | low-latency feed |
| Analytics/BI | Grafana | | ops + business dashboards |
| Notifications | Firebase Cloud Messaging, Twilio (SMS+WhatsApp), SMTP | | multi-channel |
| AuthN/Z | OAuth2 + JWT, RBAC, optional Keycloak | | |
| Observability | Prometheus + Grafana + Loki + Sentry | | metrics/logs/errors |
| Containerization | Docker + Docker Compose | | |
| Orchestration | k3s / Kubernetes + Balena (edge fleet) | | multi-site |
| CI/CD | GitHub Actions (lint, test, build, scan, deploy) | | |
| IaC | Docker Compose → Terraform/Helm | | |
| ML tracking | MLflow + DVC (data/version) | | training pipeline |

## Environments
- **dev:** docker-compose, seeded data, hot reload.
- **staging:** mirrors prod, synthetic + sampled real streams.
- **prod:** hardened, TLS everywhere, secrets in vault, backups + monitoring.
