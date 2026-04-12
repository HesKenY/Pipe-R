@echo off
rem ═══════════════════════════════════════════════════════════
rem  PIPE-R STOP — kill any node listening on :7777
rem  Double-click this to stop the Pipe-R server cleanly.
rem  Does NOT touch other node processes on the box.
rem ═══════════════════════════════════════════════════════════
title Pipe-R Stop
color 0C

echo.
echo ============================================
echo              PIPE-R  —  STOP
echo ============================================
echo.

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7777 ^| findstr LISTENING') do (
  echo  Found server PID %%a on :7777 — stopping
  taskkill /PID %%a /F > nul 2>&1
  set FOUND=1
)

if %FOUND%==0 (
  echo  Nothing listening on :7777. Already stopped.
) else (
  echo  Server stopped.
)

echo.
echo  Session closed.
timeout /t 2 /nobreak > nul
