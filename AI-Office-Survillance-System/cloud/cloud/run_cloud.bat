@echo off
REM ===========================================================================
REM  WorkLens AI - CENTRAL CLOUD (HQ) ko chalao.
REM  Saare offices ek hi screen par. Pehle apne laptop par test karo,
REM  phir kisi always-on server par deploy karo (CLOUD-SETUP-HINGLISH.md dekho).
REM ===========================================================================
setlocal
cd /d "%~dp0"
title WorkLens AI - HQ (cloud)

REM ---- HQ login password - APNA password daalo (admin123 mat rehne dena) ----
set WL_ADMIN_PASSWORD=admin123
set WL_ORG=My Company
set WL_PORT=8080

REM edge ka environment reuse karo (usme flask already hota hai); warna system python
if exist "..\edge\.venv-gpu\Scripts\python.exe" (
    set "PY=..\edge\.venv-gpu\Scripts\python.exe"
) else (
    set "PY=python"
)
"%PY%" -m pip install flask >nul 2>nul

echo.
echo HQ start ho raha hai -> http://localhost:%WL_PORT%
echo Login:  username = admin   password = %WL_ADMIN_PASSWORD%
echo.
echo  1) Login karo
echo  2) "Naya office add karo" - office ka naam daalo, TOKEN milega
echo  3) Wo token us office ke edge\run_app.bat me AICAM_CLOUD_TOKEN me daalo
echo  4) Us office ka run_app.bat chalao - thodi der me yahan live dikhega
echo.
echo Is black window ko khula rakho.
"%PY%" server.py
pause
endlocal
