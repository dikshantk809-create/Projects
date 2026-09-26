@echo off
rem ===========================================================================
rem  AR-750  -  the only file you need to double click.
rem
rem  A double click starts everything: it finds the rover on the wifi, opens
rem  it on this laptop, and puts up a QR code so the phone can open it too -
rem  live camera and driving on both at once. Everything else (the pretend
rem  rover, sending new code to the Pi, the self test) is on the menu, one
rem  key away.
rem ===========================================================================
setlocal enabledelayedexpansion
title AR-750
cd /d "%~dp0"
color 0A

set "PORT=8080"
set "APP=%~dp0rover_software"
set "VENV=%APP%\.venv"
set "VPY=%VENV%\Scripts\python.exe"

rem ------------------------------------------------------------------ python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"

rem ------------------------------------------------------------------ start
rem  Double click = start everything. tools\start_rover.ps1 does the work:
rem  it only asks the rover's website whether it is alive, it logs in to
rem  nothing. Exit 0 = open on the laptop and the phone, 1 = not found.
:start
cls
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_rover.ps1" -Root "%~dp0."
if errorlevel 1 goto notfound
echo.
echo   ---------------------------------------------------------------
echo      M   the menu      Q   close this window (the rover keeps running)
echo   ---------------------------------------------------------------
choice /c MQ /n /m "   M or Q: "
if errorlevel 2 exit /b 0
goto menu

:notfound
echo.
echo   ---------------------------------------------------------------
echo      R   try again
echo      P   open the pretend rover on this laptop instead
echo      M   the menu
echo      Q   quit
echo   ---------------------------------------------------------------
choice /c RPMQ /n /m "   R, P, M or Q: "
if errorlevel 4 exit /b 0
if errorlevel 3 goto menu
if errorlevel 2 goto open
goto start

:menu
cls
call :status
echo.
echo   ===============================================================
echo      A R - 7 5 0     C O N S O L E
echo   ===============================================================
echo.
echo      Python        !S_PY!
echo      Set up        !S_VENV!
echo      Console       !S_RUN!
echo.
echo   ---------------------------------------------------------------
echo.
echo      S    Start the rover on this laptop and the phone
echo           what a double click does
echo.
echo      1    Open the console on this computer
echo           the whole website with a pretend rover
echo.
echo      2    Connect to the real rover
echo           for when the machine is built and switched on
echo.
echo      3    Just look at the design
echo           one saved page, no Python, no rover, nothing live
echo.
echo      4    Check everything is working
echo           runs every page and every button against a throwaway copy
echo.
echo      5    Send the code to the Raspberry Pi
echo           copies it, installs it, starts it, checks it - one go
echo.
echo      6    Link this laptop to the Raspberry Pi
echo           once, the first time - or after a new SD card
echo.
echo      7    Stop the console
echo.
echo      8    Quit
echo.
echo   ---------------------------------------------------------------
echo.
set "CHOICE="
set /p "CHOICE=   Type a number and press ENTER:  "

if /i "!CHOICE!"=="S" goto start
if "!CHOICE!"=="1" goto open
if "!CHOICE!"=="2" goto connect
if "!CHOICE!"=="3" goto preview
if "!CHOICE!"=="4" goto check
if "!CHOICE!"=="5" goto sendpi
if "!CHOICE!"=="6" goto linkpi
if "!CHOICE!"=="7" goto stopit
if "!CHOICE!"=="8" exit /b 0
if "!CHOICE!"=="" goto menu
echo.
echo   There is no choice !CHOICE!. Try S or 1 to 8.
timeout /t 2 >nul
goto menu


rem ===========================================================================
rem  1 - run the console here, with the simulator
rem ===========================================================================
:open
cls
echo.
echo   OPENING THE CONSOLE
echo   ===================
echo.

if "!S_RUN!"=="running" (
  echo   It is already running. Opening it in your browser.
  start "" "http://localhost:%PORT%/"
  echo.
  pause
  goto menu
)

if not defined PY (
  echo   Python is not installed on this computer, so the live console
  echo   cannot run. Opening the offline preview instead.
  echo.
  echo   To get the real thing: install Python from
  echo       https://www.python.org/downloads/
  echo   and tick "Add python.exe to PATH" on the FIRST screen of the
  echo   installer. Then run this file again.
  echo.
  start "" "website_preview.html"
  pause
  goto menu
)

if not exist "!VPY!" (
  echo   First time only: setting this up. It downloads about 60 MB and
  echo   takes a few minutes. It never does this again.
  echo.
  !PY! -m venv "!VENV!"
  if errorlevel 1 goto setupfailed
  "!VPY!" -m pip install --upgrade pip --quiet --disable-pip-version-check
  "!VPY!" -m pip install --quiet --disable-pip-version-check pyyaml numpy fastapi "uvicorn[standard]"
  if errorlevel 1 goto setupfailed
  echo   Set up. From now on it opens straight away.
  echo.
)

echo   Starting the console on port %PORT% ...
start "AR-750 website" /D "!APP!" /min "!VPY!" -m ar750.main --sim --port %PORT%

"!VPY!" "%~dp0tools\wait_for_port.py" %PORT%
if errorlevel 1 (
  echo.
  echo   Choice 7 on the menu stops anything half-started.
  pause
  goto menu
)

start "" "http://localhost:%PORT%/"

echo.
echo   The console is open in your browser.
echo.
echo   Sign in the first time with       admin  /  agrirover
echo   It makes you change both straight away. After that the username
echo   and password you set live on the website - you never edit any code.
echo.
echo   Leave the small black window alone while you use it.
echo   When you have finished, come back here and choose 7.
echo.
pause
goto menu

:setupfailed
echo.
echo   The setup did not finish. The usual reasons are no internet
echo   connection, or a company firewall blocking pip.
echo.
echo   You can still look at the design: choice 3 on the menu.
echo.
pause
goto menu


rem ===========================================================================
rem  2 - point the browser at the real machine
rem ===========================================================================
:connect
cls
echo.
echo   CONNECT TO THE REAL AR-750
echo   ==========================
echo.
echo   The rover prints its address on the screen when it starts up.
echo   It looks like   192.168.1.42:8080   or   ar750.local:8080
echo.

set "ADDR="
if exist "rover_address.txt" (
  for /f "usebackq tokens=* delims=" %%A in ("rover_address.txt") do (
    set "LINE=%%A"
    if not "!LINE!"=="" if not "!LINE:~0,1!"=="#" set "ADDR=!LINE!"
  )
)

if defined ADDR (
  echo   Saved address:  !ADDR!
  echo.
  set "CHANGE="
  set /p "CHANGE=   Press ENTER to use it, or type a new one: "
  if not "!CHANGE!"=="" set "ADDR=!CHANGE!"
) else (
  set /p "ADDR=   Type the rover's address: "
)

if "!ADDR!"=="" (
  echo.
  echo   Nothing typed.
  timeout /t 2 >nul
  goto menu
)

rem strip a pasted http:// if there is one
set "ADDR=!ADDR:http://=!"
set "ADDR=!ADDR:https://=!"

> "rover_address.txt" echo # The AR-750's address on your network. AR-750.bat writes this
>> "rover_address.txt" echo # file for you. You can edit it by hand: one line, no http:// .
>> "rover_address.txt" echo !ADDR!

echo.
echo   Opening  http://!ADDR!/
start "" "http://!ADDR!/"
echo.
echo   If the browser says it cannot reach it:
echo     - the rover and this computer must be on the same wifi
echo     - the rover must be switched on and finished starting up
echo     - try the plain IP address instead of ar750.local
echo.
echo   To reach it from outside the house, read
echo   rover_software\docs\REMOTE_ACCESS.md - use Tailscale, and do not
echo   open a port on your router.
echo.
pause
goto menu


rem ===========================================================================
rem  3 - the saved picture of the console
rem ===========================================================================
:preview
cls
echo.
echo   THE OFFLINE PREVIEW
echo   ===================
echo.
echo   Opening the saved page. Every screen is there, but nothing is
echo   live and nothing is saved. It needs no Python and no rover.
echo.
start "" "website_preview.html"
timeout /t 3 >nul
goto menu


rem ===========================================================================
rem  4 - prove it still works
rem
rem  On a throwaway copy: its own port, its own empty data folder, its own
rem  login. Nothing you have set up is read or written, and the copy is shut
rem  down and deleted before this comes back to the menu.
rem ===========================================================================
:check
cls
echo.
echo   CHECKING EVERYTHING
echo   ===================
echo.

if not defined PY (
  echo   This needs Python. Choice 1 explains how to get it.
  echo.
  pause
  goto menu
)
if not exist "!VPY!" (
  echo   Not set up yet. Pick 1 once first, then come back.
  echo.
  pause
  goto menu
)

set "TPORT=8091"
set "TESTS=!APP!\tests"

echo   Making a throwaway copy on port !TPORT! ...
"!VPY!" "!TESTS!\console_selftest_config.py"
if errorlevel 1 goto checkfailed
echo.

start "AR-750 self test server" /D "!APP!" /min "!VPY!" -m ar750.main --config "!APP!\ar750\_config_selftest.yaml" --port !TPORT!
"!VPY!" "%~dp0tools\wait_for_port.py" !TPORT!
if errorlevel 1 goto checkstop
echo.

"!VPY!" "!TESTS!\console_selftest.py" !TPORT!

:checkstop
echo.
echo   Cleaning up the throwaway copy ...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*_config_selftest*' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }"
if exist "!APP!\data_selftest" rmdir /s /q "!APP!\data_selftest"
if exist "!APP!\ar750\_config_selftest.yaml" del /q "!APP!\ar750\_config_selftest.yaml"
echo   Gone. Your own data folder was never touched.
echo.
echo   The report is saved at
echo      rover_software\tests\last_selftest_report.txt
echo.
pause
goto menu

:checkfailed
echo.
echo   The check could not start.
echo.
pause
goto menu


rem ===========================================================================
rem  5 - put the program on the rover's own computer
rem
rem  There is no separate "Pi version": rover_software IS the Pi program.
rem  tools\pi_deploy.bat copies it across as ~/AR750_Rover (leaving out the
rem  Windows virtual environment, the caches and this laptop's data, so the
rem  Pi's own records are never overwritten), runs install.sh there, starts
rem  it, and checks it from the Pi and from this laptop. The Pi asks for its
rem  own password once, for the install.
rem ===========================================================================
:sendpi
cls
call "%~dp0tools\pi_deploy.bat"
cd /d "%~dp0"
goto menu


rem ===========================================================================
rem  6 - let this laptop log in to the Pi with a key, so choice 5 needs no
rem      password to connect. Needed once, and again after a new SD card.
rem ===========================================================================
:linkpi
cls
call "%~dp0tools\pi_login_once.bat"
cd /d "%~dp0"
goto menu


rem ===========================================================================
rem  7 - shut the console down
rem ===========================================================================
:stopit
cls
echo.
echo   STOPPING THE CONSOLE
echo   ====================
echo.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ar750.main*' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }"
echo   Stopped.
timeout /t 2 >nul
goto menu


rem ===========================================================================
rem  what the menu prints at the top
rem ===========================================================================
:status
if defined PY (set "S_PY=found") else (set "S_PY=NOT INSTALLED - choice 3 still works")
if exist "!VPY!" (set "S_VENV=done") else (set "S_VENV=not yet - choice 1 does it")
set "S_RUN=stopped"
netstat -an | findstr /C:":%PORT%" | findstr /I "LISTENING" >nul 2>&1 && set "S_RUN=running  -  http://localhost:%PORT%/"
goto :eof
