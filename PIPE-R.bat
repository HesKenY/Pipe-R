@echo off
rem ===========================================================
rem   PIPE-R COMMAND CENTER v5 (unified workbench)
rem   Double-click to launch the full stack:
rem     1. Ensures server.js is running on :7777
rem     2. Co-launches Bird's Nest terminal in its own window
rem     3. Opens pipe-r.html (P0K3M0N Trainer Deck) in browser
rem   Piper and Nest run together. Nest is the customer-instance
rem   builder; Piper is the command center that drives it.
rem   Terminal fallbacks: START.bat / STOP.bat / NEST.bat alone.
rem ===========================================================
setlocal EnableDelayedExpansion
title Pipe-R Command Center v5
color 0B
cd /d "%~dp0"

echo.
echo   ===========================================================
echo               PIPE-R  COMMAND  CENTER  v5
echo                 P0K3M0N Trainer Deck
echo   ===========================================================
echo.

rem -- [1/3] Check if server is already on :7777 ---------------
set SERVER_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7777 ^| findstr LISTENING') do set SERVER_PID=%%a

if defined SERVER_PID (
  echo   [1/3] Server already running on :7777 ^(PID !SERVER_PID!^)
) else (
  echo   [1/3] Starting server.js in background window...
  start "Pipe-R Server :7777" cmd /k "cd /d %~dp0 && node server.js"
)

rem -- [2/3] Wait for :7777 to answer --------------------------
echo   [2/3] Waiting for :7777 to come up...
set READY=0
for /L %%i in (1,1,10) do (
  if !READY!==0 (
    netstat -ano | findstr :7777 | findstr LISTENING > nul
    if not errorlevel 1 set READY=1
    if !READY!==0 timeout /t 1 /nobreak > nul
  )
)

if !READY!==0 (
  echo        WARNING: server did not come up within 10s.
  echo        Check the server window for errors, then retry.
  echo.
  pause
  exit /b 1
)

echo        Server is live.

rem -- [3/4] Co-launch Bird's Nest in its own window -----------
if exist "workspace\CHERP-Nest\nest.js" (
  echo   [3/4] Co-launching Bird's Nest...
  start "Bird's Nest" cmd /k "cd /d %~dp0workspace\CHERP-Nest && node nest.js"
) else (
  echo   [3/4] Nest not found at workspace\CHERP-Nest - skipping.
  echo          Run NEST.bat to clone it.
)

rem -- [4/4] Open the web dashboard ----------------------------
echo   [4/4] Opening Trainer Deck in your browser...
start "" "http://localhost:7777/pipe-r.html"

echo.
echo   Command Center launched.
echo   Windows now open: Piper server, Bird's Nest, Trainer Deck
echo   Remote dashboard ^(phone^):  http://localhost:7777/remote.html
echo   Hub terminal fallback:     node hub.js
echo.

rem Small pause so the user sees the status before the window closes.
timeout /t 3 /nobreak > nul
exit /b 0
