#!/usr/bin/env bash
# Run AI Tennis Analysis independently (Docker required)
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build
echo "AI Tennis Analysis → API http://localhost:8003/docs | Dashboard http://localhost:5176 | Grafana http://localhost:3003"
