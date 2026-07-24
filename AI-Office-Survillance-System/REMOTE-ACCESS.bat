@echo off
REM ==================================================================
REM  WORKLENS AI - REMOTE ACCESS (internet se kahin bhi dashboard kholo)
REM  Same WiFi ki zaroorat NAHI - phone ke mobile data se bhi chalega.
REM
REM  STEP 1: pehle START-WORKLENS.bat chalu rakho (band mat karna).
REM  STEP 2: ye file chalao. Jo https://....trycloudflare.com link aaye,
REM          WAHI aapka remote link hai - kahin se bhi kholo, login wahi
REM          admin / office123 wala.
REM  NOTE: har baar naya link banta hai (free version). PERMANENT address
REM        chahiye to TAILSCALE-GUIDE.md padho (project folder me).
REM ==================================================================
setlocal
cd /d "%~dp0"
title WorkLens AI - Remote Access (is window ko khula rakho)

set "CF=%~dp0cloudflared.exe"
set "CF_URL=https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
if exist "%~dp0edge\cloudflared.exe" set "CF=%~dp0edge\cloudflared.exe"

if not exist "%CF%" (
    echo cloudflared pehli baar download ho raha hai - ~20 MB, official Cloudflare...
    powershell -Command "try{ Invoke-WebRequest -Uri '%CF_URL%' -OutFile '%CF%' } catch { exit 1 }"
)
if not exist "%CF%" (
    echo.
    echo Download nahi hua. Internet check karke dobara chalao.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Neeche jo  https://....trycloudflare.com  link aaye,
echo  wahi aapka REMOTE LINK hai - phone/laptop kahin se bhi kholo.
echo  Is window ko khula rakho. Band karoge to link band.
echo ============================================================
echo.
"%CF%" tunnel --url http://localhost:8000
echo.
echo Remote link band ho gaya. Koi bhi key dabao.
pause >nul
endlocal
