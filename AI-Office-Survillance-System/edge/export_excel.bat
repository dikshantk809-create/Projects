@echo off
REM ===========================================================================
REM  Export the recorded detection data (events_log.csv) to an Excel workbook
REM  and open it. Run this AFTER you've run run_gpu_demo.bat for a bit.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title AI Office Surveillance - Excel export
set PIP_DEFAULT_TIMEOUT=120
set PIP_RETRIES=10

if not exist ".venv-gpu\Scripts\python.exe" (
    echo Environment not found. Please run run_gpu_demo.bat first.
    pause
    exit /b 1
)
call ".venv-gpu\Scripts\activate.bat"

echo Making sure Excel libraries are installed...
pip install pandas openpyxl

python export_excel.py events_log.csv office_report.xlsx
if exist office_report.xlsx (
    echo Opening office_report.xlsx ...
    start "" office_report.xlsx
)
pause
endlocal
