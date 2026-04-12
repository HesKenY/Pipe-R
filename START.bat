@echo off
rem ═══════════════════════════════════════════════════════════
rem  PIPE-R START — restart server + launch hub, from project root
rem  Double-click this to stop any :7777 node, launch server.js in
rem  a new window, then drop into hub.js in this window.
rem ═══════════════════════════════════════════════════════════
title Pipe-R Start
color 0B

echo.
echo ============================================
echo             PIPE-R  —  START
echo ============================================
echo.

cd /d "%~dp0"

rem ── [1/4] Kill any node currently listening on :7777 ──────────
echo [1/4] Checking for running server on :7777...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7777 ^| findstr LISTENING') do (
  echo        Found PID %%a on :7777 — stopping
  taskkill /PID %%a /F > nul 2>&1
)
timeout /t 1 /nobreak > nul

rem ── [2/4] Launch server.js in its own window ─────────────────
echo [2/4] Launching server.js in a new window...
start "Pipe-R Server :7777" cmd /k "cd /d %~dp0 && node server.js"
timeout /t 2 /nobreak > nul

rem ── [3/4] Verify server is alive ─────────────────────────────
echo [3/4] Verifying server came up...
netstat -ano | findstr :7777 > nul
if errorlevel 1 (
  echo        WARNING: nothing listening on :7777 yet. Give it a moment.
) else (
  echo        Server listening on :7777.
)

rem ── [4/4] Drop into hub.js in this window ────────────────────
echo.
echo [4/4] Opening hub.js here...
echo.
timeout /t 1 /nobreak > nul
node hub.js
