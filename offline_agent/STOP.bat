@echo off
REM ========================================================
REM Ken AI offline — stop the server
REM ========================================================
REM First tries the graceful /api/stop endpoint, then falls
REM back to killing whichever python.exe is listening on :7778.
REM ========================================================

setlocal enableextensions

title KenAI — stop

echo.
echo [stop ] asking /api/stop politely...
curl -s -o nul -X POST http://127.0.0.1:7778/api/stop 2>nul

REM ── Find the PID listening on 7778 and kill it ─────────
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":7778 " ^| findstr "LISTENING"') do (
    echo [kill ] terminating pid %%P
    taskkill /PID %%P /F >nul 2>&1
)

REM ── Confirm the port is free ────────────────────────────
ping -n 2 127.0.0.1 >nul
netstat -ano | findstr ":7778 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [ok   ] port 7778 is free
) else (
    echo [warn ] something is still listening on 7778.
    echo         check tasklist for stray python.exe.
)

echo.
ping -n 3 127.0.0.1 >nul
exit /b 0
