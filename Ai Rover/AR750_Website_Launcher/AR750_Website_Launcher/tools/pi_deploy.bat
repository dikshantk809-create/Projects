@echo off
rem ===========================================================================
rem  Puts the rover program on the Raspberry Pi and brings it up. One go.
rem
rem  Needs AR-750.bat choice 6 to have worked once first - after that nothing here
rem  asks for a password. Every step is written into tools\last_pi_deploy.txt.
rem
rem    1  checks the laptop can get in with its key
rem    2  makes a clean copy - without the Windows .venv, the caches, or this
rem       laptop's data folder, so the Pi's own records are never overwritten
rem    3  sends it to ~/AR750_Rover on the Pi
rem    4  runs install.sh there (the long step, 5 to 20 minutes)
rem    5  starts the rover and checks it answers on the Pi itself
rem    6  checks the website answers from this laptop, over the wifi
rem    7  remembers the address for AR-750.bat choice 2
rem    8  runs the end-to-end self test on the Pi
rem ===========================================================================
setlocal enabledelayedexpansion
title AR-750 - putting the rover program on the Raspberry Pi
rem  this file lives in tools\ - work from the project folder above it
cd /d "%~dp0.."
set "APP=%CD%\rover_software"
set "LOG=%~dp0last_pi_deploy.txt"
set "STAGE=%TEMP%\AR750_Rover"
set "SSHO=-o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=20"

> "%LOG%" echo AR-750 deploy   %DATE% %TIME%
>> "%LOG%" echo.

echo.
echo   ================================================================
echo      PUTTING THE ROVER PROGRAM ON THE RASPBERRY PI
echo   ================================================================
echo.

rem ----------------------------------------------------------- which Pi
set "PIADDR="
if exist "pi_address.txt" (
  for /f "usebackq tokens=* delims=" %%A in ("pi_address.txt") do (
    set "L=%%A"
    if not "!L!"=="" if not "!L:~0,1!"=="#" set "PIADDR=!L!"
  )
)
if not defined PIADDR (
  echo   No Pi remembered yet. Use AR-750.bat choice 6 first.
  >> "%LOG%" echo RESULT: NO_PI_ADDRESS
  pause
  exit /b 1
)
for /f "tokens=2 delims=@" %%H in ("!PIADDR!") do set "PIHOST=%%H"
echo   Pi: !PIADDR!
>> "%LOG%" echo pi: !PIADDR!
echo.

rem ------------------------------------------------------------ 1. key
echo   [1/8] Checking the laptop can get in on its own ...
>> "%LOG%" echo ===== 1. KEY LOGIN =====
ssh %SSHO% !PIADDR! "echo KEY_OK; tr -d '\0' < /proc/device-tree/model; echo; grep PRETTY_NAME /etc/os-release" >> "%LOG%" 2>&1
findstr /C:"KEY_OK" "%LOG%" >nul
if errorlevel 1 (
  echo         No. Use AR-750.bat choice 6 first, then this again.
  >> "%LOG%" echo RESULT: KEY_LOGIN_FAILED
  pause
  exit /b 1
)
echo         yes

rem ------------------------------------------------------- 2. clean copy
echo   [2/8] Making a clean copy ...
>> "%LOG%" echo.
>> "%LOG%" echo ===== 2. CLEAN COPY =====
if exist "!STAGE!" rmdir /s /q "!STAGE!"
robocopy "!APP!" "!STAGE!" /E /NFL /NDL /NJH /NJS /NP /XD .venv __pycache__ data data_selftest .git /XF _config_sim.yaml _config_selftest.yaml >nul
if errorlevel 8 (
  echo         The copy failed.
  >> "%LOG%" echo RESULT: COPY_FAILED
  pause
  exit /b 1
)
for /f %%C in ('dir /s /b /a-d "%STAGE%" 2^>nul ^| find /c /v ""') do set "NF=%%C"
echo         !NF! files
>> "%LOG%" echo !NF! files staged

rem ------------------------------------------------------------ 3. send
echo   [3/8] Sending it to the Pi ...
>> "%LOG%" echo.
>> "%LOG%" echo ===== 3. SEND =====
rem scp reads a leading "C:" as a hostname, so go into TEMP and send a
rem relative path instead
rem  A weak wifi can drop the copy half way, so it gets three tries.
pushd "%TEMP%"
set /a TRY=0
:sendagain
set /a TRY+=1
scp -q -r %SSHO% AR750_Rover "!PIADDR!:" >> "%LOG%" 2>&1
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" if !TRY! LSS 3 (
  >> "%LOG%" echo send try !TRY! failed, trying again
  echo         the wifi dropped - trying again ...
  timeout /t 5 >nul
  goto sendagain
)
popd
rmdir /s /q "!STAGE!" 2>nul
>> "%LOG%" echo scp exit: !RC!
if not "!RC!"=="0" (
  echo         Sending failed. See tools\last_pi_deploy.txt
  >> "%LOG%" echo RESULT: SEND_FAILED
  pause
  exit /b 1
)
echo         sent to ~/AR750_Rover

rem --------------------------------------------------------- 4. install
echo   [4/8] Installing on the Pi. The long one: 5 to 20 minutes.
echo.
echo   ----------------------------------------------------------------
echo    The Pi will ask for ITS OWN PASSWORD once, near the top - that
echo    is sudo, which Raspberry Pi OS now protects with a password.
echo    Type it and press ENTER. Nothing shows while you type.
echo    Then leave this window alone until it says FINISHED.
echo   ----------------------------------------------------------------
echo.
>> "%LOG%" echo.
>> "%LOG%" echo ===== 4. INSTALL =====
rem  -t gives the Pi a real terminal, so sudo can ask for the password on
rem  this screen. The output goes to the screen AND to a log on the Pi,
rem  which is copied back into tools\last_pi_deploy.txt afterwards.
rem  The sed strips Windows line endings from any .sh a Notepad save added.
rem  The exit at the end hands back install.sh's own result - on its own, a
rem  pipe into tee always reports success, even when the installer stopped.
ssh -t %SSHO% !PIADDR! "find ~/AR750_Rover -name '*.sh' -exec sed -i 's/\r$//' {} + ; cd ~/AR750_Rover && bash install.sh 2>&1 | tee ~/ar750_install.log; exit ${PIPESTATUS[0]}"
set "IRC=!ERRORLEVEL!"
>> "%LOG%" echo install exit: !IRC!
ssh %SSHO% !PIADDR! "cat ~/ar750_install.log" >> "%LOG%" 2>&1
echo.
if "!IRC!"=="0" (
  echo         install finished
) else (
  echo         INSTALL DID NOT FINISH - exit !IRC! - the lines above say where.
  echo         Carrying on with the checks so the log shows what is there.
  >> "%LOG%" echo RESULT: INSTALL_DID_NOT_FINISH
)

rem ------------------------------------------------------- 5. start it
echo   [5/8] Checking the rover came up on the Pi ...
>> "%LOG%" echo.
>> "%LOG%" echo ===== 5. START =====
rem the checks live in scripts/status.sh on the Pi, so nothing here needs
rem quotes inside quotes - cmd does not understand \" and flips on every "
rem  install.sh has already (re)started the service with the sudo it had, so
rem  this step needs no password: give it a moment, then look.
ssh %SSHO% !PIADDR! "sleep 10; bash ~/AR750_Rover/scripts/status.sh; echo ----- last lines from the rover -----; journalctl -u ar750 -n 30 --no-pager 2>&1" >> "%LOG%" 2>&1
findstr /C:"SERVICE=active" "%LOG%" >nul
if errorlevel 1 (echo         the rover service did NOT start - see the log) else (echo         running)

rem ----------------------------------------------- 6. from this laptop
echo   [6/8] Checking the website answers from this laptop ...
>> "%LOG%" echo.
>> "%LOG%" echo ===== 6. FROM THE LAPTOP =====
powershell -NoProfile -Command "try { 'LAPTOP_SEES=' + (Invoke-WebRequest -UseBasicParsing -TimeoutSec 8 'http://!PIHOST!:8080/api/health').Content } catch { 'LAPTOP_SEES=NOTHING  ' + $_.Exception.Message }" >> "%LOG%" 2>&1
findstr /C:"LAPTOP_SEES={" "%LOG%" >nul
if errorlevel 1 (echo         not reachable yet - see the log) else (echo         yes: http://!PIHOST!:8080/)

rem ------------------------------------------------ 7. remember it
> "rover_address.txt" echo # The AR-750's address on your network. AR-750.bat choice 2 opens it.
>> "rover_address.txt" echo # Written by tools\pi_deploy.bat. One line, no http:// in front.
>> "rover_address.txt" echo !PIHOST!:8080
echo   [7/8] Remembered !PIHOST!:8080 for AR-750.bat choice 2

rem ---------------------------------------------------- 8. self test
echo   [8/8] Running the end-to-end self test on the Pi ...
>> "%LOG%" echo.
>> "%LOG%" echo ===== 8. SELF TEST ON THE PI =====
ssh %SSHO% !PIADDR! "bash ~/AR750_Rover/scripts/selftest.sh 2>&1 | tail -70" >> "%LOG%" 2>&1
echo         done

>> "%LOG%" echo.
>> "%LOG%" echo ===== END =====

echo.
echo   ================================================================
echo      FINISHED.  Everything is in  tools\last_pi_deploy.txt
echo.
echo      The rover's website:   http://!PIHOST!:8080/
echo      or AR-750.bat, choice 2.
echo   ================================================================
echo.
timeout /t 30
