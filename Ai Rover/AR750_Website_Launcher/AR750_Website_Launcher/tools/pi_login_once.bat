@echo off
rem ===========================================================================
rem  The ONE time anybody types the Raspberry Pi's password.
rem
rem  It puts this laptop's public key on the Pi, so that from now on the laptop
rem  can log in with the key instead. Then it checks the key works and writes
rem  down what kind of Pi this is, for the install that comes next.
rem
rem  The password goes straight from your keyboard to the Pi. It is not saved
rem  anywhere, not in any file, not on this laptop.
rem ===========================================================================
setlocal enabledelayedexpansion
title AR-750 - let this laptop into the Raspberry Pi
cd /d "%~dp0.."
set "PIIP=192.168.0.120"
set "KEY=%USERPROFILE%\.ssh\id_ed25519"
set "OUT=%~dp0last_pi_login.txt"

> "%OUT%" echo started %DATE% %TIME%

echo.
echo   ================================================================
echo      LET THIS LAPTOP INTO THE RASPBERRY PI
echo   ================================================================
echo.
echo   Looking for the Pi on the wifi ...

rem  The Pi's address can change when the router hands them out again, so
rem  find it rather than trust the last one - before anyone types a password
rem  at the wrong machine.
set "FOUND="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0locate_pi.ps1" -Last "%PIIP%"`) do set "FOUND=%%I"
if not defined FOUND (
  echo.
  echo   Could not find the Pi on this wifi.
  echo   Is it switched on, has it had two minutes, and is it on the same wifi?
  echo.
  >> "%OUT%" echo RESULT: PI_NOT_FOUND
  pause
  exit /b 1
)
set "PIIP=!FOUND!"
>> "%OUT%" echo pi ip: !PIIP!

echo   Found your Pi at   !PIIP!
echo.
echo   This is the ONLY time you type the Pi's password. After this the
echo   laptop has its own key on the Pi, and nobody types it again.
echo.
echo   The username is the one chosen when the SD card was flashed.
echo   If you never chose one, it is probably just:   pi
echo.
set "PIUSER="
set /p "PIUSER=   Pi username, then ENTER:  "
if "!PIUSER!"=="" set "PIUSER=pi"
>> "%OUT%" echo user: !PIUSER!


rem  If the SD card has been flashed again since this laptop last spoke to the
rem  Pi, the Pi has a brand new host key and ssh refuses - loudly, before it
rem  even asks for a password. Forget the old key for this address; the new
rem  one is recorded on first contact.
ssh-keygen -R !PIIP! >nul 2>&1

rem  If this laptop's key was pasted into Raspberry Pi Imager when the card
rem  was flashed, no password is needed at all. Try that first.
echo.
echo   Checking whether the Pi already knows this laptop ...
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 !PIUSER!@!PIIP! "echo LOGIN_WITH_KEY_OK" >> "%OUT%" 2>&1
findstr /C:"LOGIN_WITH_KEY_OK" "%OUT%" >nul
if not errorlevel 1 (
  echo   It does - no password needed.
  >> "%OUT%" echo key was already on the Pi
  goto havekey
)
echo   Not yet.

echo.
echo   Now type that user's PASSWORD and press ENTER.
echo   Nothing appears on the screen while you type it - that is normal.
echo.

rem  the key goes in on stdin; the password is read from the keyboard.
rem  sort -u means running this twice does not add the key twice.
type "%KEY%.pub" | ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 !PIUSER!@!PIIP! "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && sort -u -o ~/.ssh/authorized_keys ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo KEY_ADDED"
set "RC=!ERRORLEVEL!"
>> "%OUT%" echo add-key exit: !RC!

if not "!RC!"=="0" (
  echo.
  echo   That did not work. Usually:
  echo     - the username or password was wrong. Try again.
  echo     - the Pi rebooted or lost wifi in the middle.
  echo.
  >> "%OUT%" echo RESULT: KEY_NOT_ADDED
  pause
  exit /b 1
)

echo.
echo   Key added. Checking the laptop can now get in on its own ...
ssh -o BatchMode=yes -o ConnectTimeout=15 !PIUSER!@!PIIP! "echo LOGIN_WITH_KEY_OK" >> "%OUT%" 2>&1
findstr /C:"LOGIN_WITH_KEY_OK" "%OUT%" >nul
if errorlevel 1 (
  echo   The key went on, but logging in with it did not work.
  >> "%OUT%" echo RESULT: KEY_LOGIN_FAILED
  pause
  exit /b 1
)

:havekey
rem  remember the Pi for AR-750.bat choice 5 and everything after this
> "pi_address.txt" echo # The Raspberry Pi, as user@address. Written by AR-750.bat, choice 6.
>> "pi_address.txt" echo !PIUSER!@!PIIP!

echo   It works. Writing down what kind of Pi this is ...
>> "%OUT%" echo RESULT: KEY_LOGIN_OK
>> "%OUT%" echo.
ssh -o BatchMode=yes -o ConnectTimeout=15 !PIUSER!@!PIIP! "echo ===MODEL; tr -d '\0' < /proc/device-tree/model; echo; echo ===HOSTNAME; hostname; echo ===OS; grep -E 'PRETTY_NAME=|VERSION_CODENAME=' /etc/os-release; echo ===ARCH; uname -m; uname -r; echo ===PYTHON; python3 --version; echo ===DISK; df -h / | tail -1; echo ===MEMORY; free -h | head -2; echo ===SUDO; sudo -n true 2>/dev/null && echo SUDO_OK || echo SUDO_NEEDS_PASSWORD; echo ===IP; hostname -I; echo ===INTERNET; ping -c1 -W3 pypi.org >/dev/null 2>&1 && echo INTERNET_OK || echo NO_INTERNET; echo ===PIGPIO; which pigpiod 2>&1; echo ===I2C; ls /dev/i2c* 2>&1; echo ===CAMERA; ls /dev/video0 /dev/media0 2>&1; echo ===UART; ls -l /dev/serial0 2>&1; echo ===ALREADY_HERE; ls -d ~/AR750_Rover 2>&1; systemctl is-enabled ar750 2>&1; echo ===THROTTLED; vcgencmd get_throttled 2>&1; echo ===TEMP; vcgencmd measure_temp 2>&1; echo ===END" >> "%OUT%" 2>&1

echo.
echo   ================================================================
echo      DONE. You will not need the Pi's password again.
echo   ================================================================
echo.
echo   Next: AR-750.bat choice 5 sends the rover program across.
echo.
timeout /t 30
