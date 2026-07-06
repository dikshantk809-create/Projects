@echo off
cd /d "%~dp0"
docker compose -f deploy/docker-compose.yml down
echo AI Tennis Analysis stopped.
pause
