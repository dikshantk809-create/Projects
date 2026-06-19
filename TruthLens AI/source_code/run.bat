@echo off
cd /d "%~dp0"
echo ================================================
echo    TruthLens AI  -  setup and launch
echo ================================================
echo.
set "PY="
python3.12 --version >nul 2>&1 && set "PY=python3.12"
if not defined PY ( py -3 --version >nul 2>&1 && set "PY=py -3" )
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo [ERROR] Python not found. Install Python 3.12 from python.org and tick "Add to PATH".
  pause
  exit /b 1
)
echo Using Python command: %PY%
echo.
echo [1/3] Installing dependencies (first time: 1-3 min)...
%PY% -m pip install -r requirements.txt
echo.
echo [2/3] Training model (first run only, ~10 sec)...
%PY% -m src.train
echo.
echo [3/3] Launching TruthLens AI in your browser...
echo (Keep this window open. Press Ctrl+C to stop the app.)
%PY% -m streamlit run app.py
pause
