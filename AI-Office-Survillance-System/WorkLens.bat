@echo off
title WorkLens Command Center (REAL AI backend) - keep this window OPEN
cd /d "%~dp0"
if not exist .env copy .env.example .env >nul 2>&1
set "PYEXE="
where py     >nul 2>&1 && set "PYEXE=py"
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE ( echo Python 3.11+ chahiye - python.org se install karo, phir dobara chalao. & pause & exit /b )
echo ================================================================
echo   First run: dependencies install ho rahi hain (ultralytics/insightface -
echo   thoda time + internet lagega). Baad me turant chalega.
echo ================================================================
"%PYEXE%" -m pip install --disable-pip-version-check -q -e "./platform[detect,face]" flask supervision
echo.
echo Starting WorkLens (real detection). Browser khud khulega: http://localhost:8000
echo Login passcode (default): office123     (ya AICAM_PASSWORD .env me)
cd edge
"%PYEXE%" app.py
echo.
echo Server band ho gaya. Koi bhi key dabao.
pause >nul
