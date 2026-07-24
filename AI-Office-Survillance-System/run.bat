@echo off
REM Run AI Office Surveillance independently (Docker Desktop required)
cd /d "%~dp0"
if not exist .env copy .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build
echo.
echo  AI Office Surveillance is starting...
echo   API docs : http://localhost:8001/docs
echo   Dashboard: http://localhost:5174
echo   Grafana  : http://localhost:3001
pause
