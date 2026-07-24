@echo off
REM ==================================================================
REM   WORKLENS AI COMMAND CENTER  -  ONE-CLICK LAUNCHER
REM   Bas is file par DOUBLE-CLICK karo -> poora project chal jayega.
REM   Browser khud khulega:  http://localhost:8000
REM   Login:  admin / office123
REM   Ye black window OPEN rakho - yehi server hai.
REM ==================================================================
setlocal
cd /d "%~dp0"
title WorkLens AI Command Center - is window ko OPEN rakho
set PIP_DEFAULT_TIMEOUT=120
set PIP_RETRIES=10

REM ---------- Python chuno: project ka GPU environment > system Python ----------
set "PYEXE="
if exist "%~dp0edge\.venv-gpu\Scripts\python.exe" set "PYEXE=%~dp0edge\.venv-gpu\Scripts\python.exe"
if not defined PYEXE ( where py     >nul 2>&1 && set "PYEXE=py" )
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
    echo.
    echo   Python nahi mila. https://python.org se Python 3.11+ install karo
    echo   install ke waqt "Add python.exe to PATH" tick karna, phir dobara double-click karo.
    echo.
    pause
    exit /b 1
)

REM ---------- Pehli baar - GPU env na ho to libraries install ----------
if exist "%~dp0edge\.venv-gpu\Scripts\python.exe" goto deps_done
if exist "%~dp0.worklens_deps_ok" goto deps_done
echo ==================================================================
echo   Pehli baar: AI libraries install ho rahi hain
echo   internet chahiye, 5-15 min lag sakte hain. Agli baar turant chalega.
echo ==================================================================
"%PYEXE%" -m pip install --disable-pip-version-check -e "./platform[detect,face]" flask supervision pandas openpyxl
if errorlevel 1 (
    echo.
    echo   Install fail hua - internet check karke dobara chalao.
    pause
    exit /b 1
)
echo ok > "%~dp0.worklens_deps_ok"
:deps_done

REM ---------- aicam_platform hamesha mile - folder kahin bhi move ho ----------
set "PYTHONPATH=%~dp0platform;%PYTHONPATH%"

REM ---------- GPU face-recognition: ek baar onnxruntime-gpu install ----------
if not exist "%~dp0edge\.venv-gpu\Scripts\python.exe" goto gpu_done
if exist "%~dp0.gpu_face_ok" goto gpu_done
echo GPU face-recognition set ho raha hai - ek hi baar, 1-2 min...
"%PYEXE%" -m pip uninstall -y onnxruntime >nul 2>&1
"%PYEXE%" -m pip install --disable-pip-version-check onnxruntime-gpu
if not errorlevel 1 echo ok > "%~dp0.gpu_face_ok"
:gpu_done
REM CUDA/cuDNN DLLs - torch ke saath aati hain - onnxruntime ko dikhein:
set "PATH=%~dp0edge\.venv-gpu\Lib\site-packages\torch\lib;%PATH%"

REM ---------- Production server - waitress - ek baar install ----------
if exist "%~dp0.waitress_ok" goto srv_done
"%PYEXE%" -m pip install --disable-pip-version-check -q waitress
if not errorlevel 1 echo ok > "%~dp0.waitress_ok"
:srv_done

REM ---------- Camera / AI settings - run_app.bat wali hi config ----------
REM  Ghar/office ka CCTV DVR - 8 channels. Password badalna ho to yahi line badlo.
REM  subtype=1 = DVR ka SUB-STREAM (halka, 8 camera ke liye TEZ). HD chahiye to subtype=0.
set "AICAM_DVR=rtsp://admin:dikshant@05@192.168.0.105:554/cam/realmonitor?channel={ch}&subtype=1"
set AICAM_CAM_COUNT=8
REM  DVR nahi chahiye / sirf laptop webcam chahiye to upar wali 2 lines ke aage "REM " laga do.
set AICAM_DEVICE=0
set AICAM_MODEL_PATH=yolo11n.pt
set AICAM_IMGSZ=640
set AICAM_CONF=0.3
set AICAM_FPS_BUDGET=24
set AICAM_FACE_ENABLED=true
set AICAM_FACE_DB=faces.pkl
set AICAM_FACE_THRESHOLD=0.5
set AICAM_CSV_LOG=events_log.csv
REM  Dashboard ka login password - apna rakhna ho to badlo. Login: admin / ye password
set AICAM_PASSWORD=office123
set AICAM_LLM_MODEL=

REM ---------- ADVANCED FEATURES ----------
REM  PHONE ALERTS (Telegram): @BotFather se bot banao - token yahan daalo,
REM  phir bot ko msg bhejo aur api.telegram.org/bot<TOKEN>/getUpdates se chat id lo.
REM  Dono bharte hi unknown-person / after-hours / zone alerts photo ke saath phone par aayenge.
set TELEGRAM_BOT_TOKEN=
set TELEGRAM_CHAT_ID=
REM  OFFICE HOURS - iske BAHAR koi bhi movement = CRITICAL alert + auto recording
set AICAM_OFFICE_HOURS=09:00-21:00
REM  Is time ke baad first-seen hone wala LATE ginega (ATTND page par)
set AICAM_WORK_START=09:30

echo.
echo ==================================================================
echo   WorkLens AI start ho raha hai...
echo   Browser khud khulega:  http://localhost:8000
echo   Login:  admin / office123
echo   Phone se - same WiFi:  http://APNE-PC-KA-IP:8000
echo   Is window ko OPEN rakho. Band karne ke liye ise close karo ya Ctrl+C.
echo ==================================================================
echo.
cd /d "%~dp0edge"
"%PYEXE%" app.py 2> "%~dp0worklens_error.log"
echo.
if exist "%~dp0worklens_error.log" (
    echo ---------------- LOG: worklens_error.log ----------------
    type "%~dp0worklens_error.log"
    echo ----------------------------------------------------------
)
echo   Server band ho gaya. Koi bhi key dabao.
pause >nul
endlocal
