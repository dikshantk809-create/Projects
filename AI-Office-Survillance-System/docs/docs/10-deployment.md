# 10 — Deployment (Office)

## Single-node (server) + edge nodes
```bash
cd project-1-office-surveillance
cp .env.example .env                       # set secrets
docker compose -f deploy/docker-compose.yml up -d --build
# backend  http://localhost:8001/docs   dashboard http://localhost:5174
# grafana  http://localhost:3001         minio http://localhost:9001
```
Edge (per Pi): follow `docs/14-raspberry-pi-setup.md`, point `AICAM_BACKEND_URL` at the
server, run the systemd service.

## Production
- Reverse proxy (Traefik/Nginx) + TLS; backend not exposed directly.
- Managed/HA Postgres+Timescale; object storage with lifecycle; secrets in vault.
- Edge fleet via k3s/Balena; OTA model + app updates.
- Observability: Prometheus + Grafana + Loki + Sentry; alert on camera/edge offline.
- Backups (PITR) + tested restores; retention jobs verified. See `../blueprint-docs/06`.
