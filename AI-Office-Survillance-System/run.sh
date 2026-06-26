#!/usr/bin/env bash
# Run AI Office Surveillance independently (Docker required)
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build
echo "AI Office Surveillance → API http://localhost:8001/docs | Dashboard http://localhost:5174 | Grafana http://localhost:3001"
