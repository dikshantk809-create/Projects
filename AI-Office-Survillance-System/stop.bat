@echo off
cd /d "%~dp0"
docker compose -f deploy/docker-compose.yml down
echo AI Office Surveillance stopped.
pause
