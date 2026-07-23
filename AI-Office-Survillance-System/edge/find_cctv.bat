@echo off
REM Find your CCTV / DVR on the local network (prints its IP + ready RTSP link).
cd /d "%~dp0"
title Find CCTV on network
if exist ".venv-gpu\Scripts\python.exe" (
    ".venv-gpu\Scripts\python.exe" find_cctv.py
) else (
    python find_cctv.py
)
echo.
pause
