@echo off
rem ===========================================================
rem   PIPE-R LAUNCHER - menu driven control panel
rem   Double-click from C:\Users\Ken\Desktop\Claude
rem   Paired with START.bat / STOP.bat (quick one-shots)
rem ===========================================================
setlocal EnableDelayedExpansion
title Pipe-R Launcher
color 0B
cd /d "%~dp0"

:MENU
cls
echo.
echo   ===========================================================
echo                    PIPE-R  LAUNCHER  v4.0
echo   ===========================================================
echo.

rem -- Status probe ------------------------------------------
set SERVER=OFFLINE
set SERVER_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7777 ^| findstr LISTENING') do (
  set SERVER=ONLINE
  set SERVER_PID=%%a
)

set OLLAMA=OFFLINE
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | findstr /I "ollama.exe" > nul
if !errorlevel!==0 set OLLAMA=ONLINE

set BRANCH=unknown
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%b

set CHANGES=0
for /f %%c in ('git status --short 2^>nul ^| find /c /v ""') do set CHANGES=%%c

echo   --- Status ------------------------------------------------
echo.
if "!SERVER!"=="ONLINE" (
  echo      Server :7777     ONLINE    PID !SERVER_PID!
) else (
  echo      Server :7777     offline
)
if "!OLLAMA!"=="ONLINE" (
  echo      Ollama           ONLINE
) else (
  echo      Ollama           offline
)
echo      Git branch       !BRANCH!  ^(!CHANGES! changed^)
echo.
echo   --- Actions -----------------------------------------------
echo.
echo      [1]  Start Session       kill :7777, launch server+hub
echo      [2]  Stop Server         kill whatever owns :7777
echo      [3]  Launch Hub Only     assumes server already up
echo      [4]  Launch Server Only  background window, no hub
echo      [5]  Open Dashboard      pipe-r.html in browser
echo      [6]  Open Remote         remote.html in browser
echo      [7]  Git Status + Log    one-screen repo check
echo      [8]  View Session Log    .claude\SESSION_LOG.md
echo      [0]  Exit
echo.
echo   -----------------------------------------------------------

set /p CHOICE=  Select:

if "%CHOICE%"=="1" goto START_SESSION
if "%CHOICE%"=="2" goto STOP_SERVER
if "%CHOICE%"=="3" goto LAUNCH_HUB
if "%CHOICE%"=="4" goto LAUNCH_SERVER
if "%CHOICE%"=="5" goto OPEN_DASHBOARD
if "%CHOICE%"=="6" goto OPEN_REMOTE
if "%CHOICE%"=="7" goto GIT_STATUS
if "%CHOICE%"=="8" goto VIEW_LOG
if "%CHOICE%"=="0" goto EXIT
goto MENU

:START_SESSION
echo.
echo   [1/3] Stopping any existing server on :7777...
if defined SERVER_PID taskkill /PID !SERVER_PID! /F > nul 2>&1
timeout /t 1 /nobreak > nul
echo   [2/3] Launching server.js in new window...
start "Pipe-R Server :7777" cmd /k "cd /d %~dp0 && node server.js"
timeout /t 2 /nobreak > nul
echo   [3/3] Opening hub.js here...
echo.
node hub.js
goto MENU

:STOP_SERVER
echo.
if "!SERVER!"=="OFFLINE" (
  echo   Nothing on :7777. Already stopped.
) else (
  echo   Stopping server PID !SERVER_PID!...
  taskkill /PID !SERVER_PID! /F > nul 2>&1
  echo   Server stopped.
)
timeout /t 2 /nobreak > nul
goto MENU

:LAUNCH_HUB
echo.
if "!SERVER!"=="OFFLINE" (
  echo   WARNING: server is offline. Hub will have no agent mode state.
  echo   Press [1] from the menu instead to start the full session.
  timeout /t 3 /nobreak > nul
  goto MENU
)
echo   Launching hub.js...
echo.
node hub.js
goto MENU

:LAUNCH_SERVER
echo.
if "!SERVER!"=="ONLINE" (
  echo   Server already on :7777 as PID !SERVER_PID!. No action.
) else (
  echo   Launching server.js in new window...
  start "Pipe-R Server :7777" cmd /k "cd /d %~dp0 && node server.js"
)
timeout /t 2 /nobreak > nul
goto MENU

:OPEN_DASHBOARD
echo.
if "!SERVER!"=="OFFLINE" (
  echo   Server offline - starting it first...
  start "Pipe-R Server :7777" cmd /k "cd /d %~dp0 && node server.js"
  timeout /t 3 /nobreak > nul
)
echo   Opening dashboard in browser...
start "" "http://localhost:7777/pipe-r.html"
timeout /t 1 /nobreak > nul
goto MENU

:OPEN_REMOTE
echo.
if "!SERVER!"=="OFFLINE" (
  echo   Server offline - starting it first...
  start "Pipe-R Server :7777" cmd /k "cd /d %~dp0 && node server.js"
  timeout /t 3 /nobreak > nul
)
echo   Opening remote in browser...
start "" "http://localhost:7777/remote.html"
timeout /t 1 /nobreak > nul
goto MENU

:GIT_STATUS
echo.
echo   --- git status -------------------------------------------
git status --short
echo.
echo   --- git log (last 8) -------------------------------------
git log --oneline -8
echo.
echo   --- remotes ----------------------------------------------
git remote -v
echo.
pause
goto MENU

:VIEW_LOG
echo.
if exist ".claude\SESSION_LOG.md" (
  start "" notepad ".claude\SESSION_LOG.md"
) else (
  echo   No session log found at .claude\SESSION_LOG.md
  timeout /t 2 /nobreak > nul
)
goto MENU

:EXIT
echo.
echo   Goodbye.
timeout /t 1 /nobreak > nul
exit /b 0
