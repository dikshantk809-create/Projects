@echo off
REM Run AI Tennis Analysis independently (Docker Desktop required)
cd /d "%~dp0"
if not exist .env copy .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build
echo.
echo  AI Tennis Analysis is starting...
echo   API docs : http://localhost:8003/docs
echo   Dashboard: http://localhost:5176
echo   Grafana  : http://localhost:3003
pause
