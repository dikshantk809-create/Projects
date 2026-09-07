@echo off
title AutoCare Pro - Smart Vehicle Maintenance System (SVMS)
cd /d "%~dp0" 2>nul
color 0C
cls
echo.
echo    ================================================================
echo       A U T O C A R E   P R O
echo       Smart Vehicle Maintenance System  //  SVMS
echo    ================================================================
echo.

REM =====================================================================
REM  GUARD: the most common mistake is running this file straight out of
REM  the ZIP. Windows then copies ONLY this .bat into a temp folder, so
REM  server.js / index.html are nowhere to be found. Detect that and say
REM  so in plain English instead of letting Node print a stack trace.
REM =====================================================================
echo %~dp0 | find /i ".zip" >nul
if %errorlevel%==0 goto notextracted
if not exist "%~dp0server.js"  goto notextracted
if not exist "%~dp0index.html" goto notextracted

REM =====================================================================
REM  MENU
REM =====================================================================
echo    How do you want to run it?
echo.
echo       [1]  On this computer          - opens in your browser,
echo                                        plus a Wi-Fi address for
echo                                        your phone            (default)
echo.
echo       [2]  Public link               - same thing, plus a free
echo                                        https link anyone can open
echo                                        from anywhere
echo.
echo       [3]  Single file only          - no server, just open
echo                                        AutoCare-Pro.html
echo.

where choice >nul 2>nul
if %errorlevel%==0 (
    choice /c 123 /n /t 10 /d 1 /m "    Press 1, 2 or 3  (starts with 1 in 10s): "
    set "PICK=%errorlevel%"
) else (
    set "PICK=1"
    set /p "PICK=    Press 1, 2 or 3 then Enter [1]: "
)

echo.
if "%PICK%"=="3" goto singlefile
if "%PICK%"=="2" goto publiclink
goto localonly

REM =====================================================================
:localonly
echo    Starting the local server...
echo    (Keep this window open while you use the app.)
echo.

where node >nul 2>nul
if %errorlevel%==0 (
    echo    Runtime found: Node.js
    node "%~dp0server.js"
    goto stopped
)
where py >nul 2>nul
if %errorlevel%==0 (
    echo    Runtime found: Python ^(py launcher^)
    py -3 "%~dp0server.py"
    goto stopped
)
where python >nul 2>nul
if %errorlevel%==0 (
    echo    Runtime found: Python
    python "%~dp0server.py"
    goto stopped
)

echo    Neither Node.js nor Python was found on this PC.
echo    Falling back to the single-file build.
echo.
goto singlefile

REM =====================================================================
:publiclink
where node >nul 2>nul
if not %errorlevel%==0 (
    echo    The public link needs Node.js.
    echo    Install it from https://nodejs.org, or press 1 next time to
    echo    run locally, or 3 to open the single file.
    echo.
    pause
    goto :eof
)

echo    Starting the server and opening a public link...
echo.
echo    The code stays on THIS computer. The tunnel only forwards
echo    traffic to it, so the link works while this window is open.
echo    First run downloads cloudflared once ^(~40 MB, no account^).
echo.
node "%~dp0share.js"
goto stopped

REM =====================================================================
:singlefile
if not exist "%~dp0AutoCare-Pro.html" (
    echo    AutoCare-Pro.html is missing from this folder.
    echo.
    pause
    goto :eof
)
echo    Opening the single-file build. Everything works from there -
echo    all screens, all algorithms, all charts, saved data - except
echo    the PWA install prompt and the offline service worker, which
echo    browsers only allow over http.
echo.
start "" "%~dp0AutoCare-Pro.html"
echo    Done. You can close this window.
echo.
pause
goto :eof

REM =====================================================================
:notextracted
echo    THE ZIP HAS NOT BEEN EXTRACTED YET.
echo.
echo    You are running this file from inside the compressed folder, so
echo    Windows copied only this .bat to a temporary location and left
echo    server.js and index.html behind.
echo.
echo    Fix it in three steps:
echo.
echo       1. Close this window.
echo       2. Right-click AutoCarePro.zip  ^>  "Extract All..."  ^>  Extract
echo       3. Open the extracted AutoCarePro folder and double-click
echo          Run-AutoCare-Pro.bat again.
echo.
echo    (In a real folder the address bar shows a normal path such as
echo     C:\Users\HP\Downloads\AutoCarePro - not one containing ".zip".)
echo.
if exist "%~dp0AutoCare-Pro.html" (
    echo    Opening the single-file build so you can look around meanwhile...
    start "" "%~dp0AutoCare-Pro.html"
    echo.
)
pause
goto :eof

REM =====================================================================
:stopped
echo.
echo    Stopped. You can close this window.
echo.
pause
