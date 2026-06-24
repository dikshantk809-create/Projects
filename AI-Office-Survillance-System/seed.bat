@echo off
REM Seed demo data into the running PostgreSQL/TimescaleDB container.
cd /d "%~dp0"
echo Seeding demo data into deploy-db-1 ...
docker exec -i -e PGPASSWORD=office deploy-db-1 psql -U office -d office < "%~dp0db\seed.sql"
echo.
echo Done. Now reload the dashboard: http://localhost:5174
pause
