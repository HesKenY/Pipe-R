@echo off
rem ===========================================================
rem   PIPE-R DECK LAUNCHER (1920x720 control deck)
rem   Single double-click launcher:
rem     1. Ensures server.js is running on :7777
rem     2. Co-launches Bird's Nest if present
rem     3. Waits for the server to answer
rem     4. Opens the Trainer Deck in a chromeless 1920x720 window
rem   Uses Chrome --app mode so there is no browser chrome.
rem   Falls back to Edge --app if Chrome is not installed.
rem ===========================================================
setlocal EnableDelayedExpansion
title Pipe-R Deck Launcher
color 0B
cd /d "%~dp0"

echo.
echo   ===========================================================
echo                  PIPE-R  DECK  LAUNCHER
echo                  1920 x 720 Control Deck
echo   ===========================================================
echo.

rem -- [1/4] Server ---------------------------------------------
set SERVER_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7777 ^| findstr LISTENING') do set SERVER_PID=%%a

if defined SERVER_PID (
  echo   [1/4] Server already running on :7777 ^(PID !SERVER_PID!^)
) else (
  echo   [1/4] Starting server.js in background window...
  start "Pipe-R Server :7777" cmd /k "cd /d %~dp0 && node server.js"
)

rem -- [2/4] Wait for :7777 -------------------------------------
echo   [2/4] Waiting for :7777 to come up...
set READY=0
for /L %%i in (1,1,15) do (
  if !READY!==0 (
    netstat -ano | findstr :7777 | findstr LISTENING > nul
    if not errorlevel 1 set READY=1
    if !READY!==0 timeout /t 1 /nobreak > nul
  )
)

if !READY!==0 (
  echo        WARNING: server did not come up within 15s.
  echo        Check the server window for errors, then retry.
  echo.
  pause
  exit /b 1
)

echo        Server is live.

rem -- [3/4] Bird's Nest ----------------------------------------
if exist "nest\nest.js" (
  rem Only co-launch if Nest is not already running
  tasklist /FI "WINDOWTITLE eq Bird's Nest*" 2>nul | find /I "cmd.exe" > nul
  if errorlevel 1 (
    echo   [3/4] Co-launching Bird's Nest...
    start "Bird's Nest" cmd /k "cd /d %~dp0nest && node nest.js"
  ) else (
    echo   [3/4] Bird's Nest already running.
  )
) else (
  echo   [3/4] Nest not found - skipping.
)

rem -- [4/4] Chromeless Trainer Deck window ---------------------
set URL=http://localhost:7777/pipe-r.html?deck=1
set CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"
set CHROME_X86="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set EDGE="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

echo   [4/4] Opening 1920x720 control deck...

if exist %CHROME% (
  start "" %CHROME% --app=%URL% --window-size=1920,720 --window-position=0,0 --new-window --disable-features=TranslateUI
  goto :launched
)
if exist %CHROME_X86% (
  start "" %CHROME_X86% --app=%URL% --window-size=1920,720 --window-position=0,0 --new-window --disable-features=TranslateUI
  goto :launched
)
if exist %EDGE% (
  start "" %EDGE% --app=%URL% --window-size=1920,720 --window-position=0,0 --new-window --disable-features=TranslateUI
  goto :launched
)

echo        No Chrome or Edge found - opening in default browser instead.
start "" "%URL%"

:launched
echo.
echo   Deck launched.
echo   Windows open: Piper server, Bird's Nest, 1920x720 Trainer Deck
echo   Remote (phone):  http://localhost:7777/remote.html
echo   Stop server:     STOP.bat
echo.
timeout /t 3 /nobreak > nul
exit /b 0
