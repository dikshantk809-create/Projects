@echo off
REM ===========================================================================
REM  Enroll faces with names. Run this FIRST (before run_faces_demo.bat).
REM  Look at the webcam, type each person's name. Re-run any time to add more.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title AI Office Surveillance - enroll faces
set PIP_DEFAULT_TIMEOUT=120
set PIP_RETRIES=10

if not exist ".venv-gpu\Scripts\python.exe" (
    echo Environment not found. Please run run_gpu_demo.bat once first.
    pause
    exit /b 1
)
call ".venv-gpu\Scripts\activate.bat"

echo Installing face-recognition libraries (first time downloads a model ~300MB)...
pip install insightface onnxruntime
REM insightface can pull a no-window OpenCV; reinstall the GUI build so the preview shows
pip uninstall -y opencv-python-headless >nul 2>nul
pip install opencv-python

set AICAM_SOURCE=0
set AICAM_FACE_DB=faces.pkl
python enroll_face.py
pause
endlocal
