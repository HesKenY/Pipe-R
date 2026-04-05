@echo off
title ForgeAgent — AI Coding Agent Hub
color 0B
cd /d "%~dp0"

echo.
echo   ╔══════════════════════════════════════╗
echo   ║       F O R G E   A G E N T        ║
echo   ║     Local AI Coding Agent Hub       ║
echo   ╚══════════════════════════════════════╝
echo.

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo   [ERROR] Python not found.
    echo   Install from https://python.org
    pause & exit /b 1
)

REM Auto-install deps on first run
if not exist ".installed" (
    echo   Installing dependencies...
    pip install -e . >nul 2>nul || pip install -r requirements.txt >nul 2>nul
    echo.>.installed
    echo   Done.
)

REM Start Ollama if not running
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 (
    where ollama >nul 2>nul
    if %errorlevel% equ 0 (
        echo   Starting Ollama...
        start "" ollama serve >nul 2>&1
        timeout /t 3 /nobreak >nul
    )
)

echo   Launching ForgeAgent...
echo.
python -m forgeagent %*
pause
