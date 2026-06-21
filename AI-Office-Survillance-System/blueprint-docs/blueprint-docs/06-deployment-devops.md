# 06 — Deployment & DevOps

## Topologies
1. **Single-node (MVP / small site):** one host runs `docker compose` with backend,
   Postgres/Timescale, Redis, MinIO, Grafana; edge pipeline runs on the Pi/Jetson and
   pushes events to the backend over TLS.
2. **Hub-and-spoke (multi-site):** many edge nodes (k3s/Balena fleet) → central cluster
   (managed k8s) with HA Postgres, object storage, Grafana, and horizontally-scaled
   FastAPI + worker pods.
3. **Centralized GPU (enterprise/tennis):** cameras → GPU inference server(s) →
   backend; edge does only capture/encode.

## Containers (per project `deploy/`)
- `docker-compose.yml` — backend, db (timescale), redis, minio, grafana, dashboard,
  (optional) edge-simulator.
- `Dockerfile.backend`, `Dockerfile.edge` (Hailo/CUDA base), `Dockerfile.dashboard`.
- `grafana/` provisioning (datasources + dashboards as code).
- `k8s/` Helm values for fleet deployment.

## CI/CD (GitHub Actions)
```
lint (ruff, black, mypy) → test (pytest, vitest) → build images →
scan (Trivy, pip-audit, npm audit) → push to registry → deploy (staging→prod)
```
- Protected `main`, required checks, signed images, SBOM artifact.
- Blue/green or rolling deploys; DB migrations via Alembic in an init job.

## Edge fleet management
- **Balena** or **k3s + Fleet/ArgoCD** for OTA updates to Pi/Jetson devices.
- Devices pull signed container images; health/heartbeat to backend; remote logs.
- Model rollout is a versioned artifact (MLflow/registry) → staged to a canary device
  → fleet.

## Observability
- **Metrics:** Prometheus (FPS, queue depth, inference latency, dropped frames, alert
  rates, API latency). Grafana dashboards provisioned as code.
- **Logs:** Loki + structured JSON logging (`platform.common.logging`).
- **Errors:** Sentry (backend + dashboard).
- **Alerts on the system itself:** camera offline, edge node down, inference stalled,
  DB lag, disk filling.

## Backups & DR
- Postgres: nightly base + WAL archiving (PITR); test restores.
- Object storage: versioning + lifecycle to cold tier; cross-region for enterprise.
- Config/IaC in git; secrets in vault with backup.
- Documented RTO/RPO per tier.

## Runbooks (ship these)
- Camera offline, edge node reboot, model rollback, DB failover, certificate rotation,
  evidence export for an incident, right-to-erasure execution.
