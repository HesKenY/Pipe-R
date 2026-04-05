@echo off
title ForgeAgent — AI Coding Agent Hub
cd /d "%~dp0"

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Trying exe...
    if exist dist\ForgeAgent\ForgeAgent.exe (
        cd /d "%~dp0\dist\ForgeAgent"
        start "" ForgeAgent.exe
        exit
    )
    echo ERROR: Install Python from https://python.org
    pause & exit /b 1
)

REM Auto-install deps on first run
if not exist ".installed" (
    echo First run — installing dependencies...
    pip install -e . >nul 2>nul || pip install -r requirements.txt >nul 2>nul
    echo.>.installed
)

REM Start Ollama if not running
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 (
    echo Starting Ollama...
    start "" ollama serve >nul 2>&1
    timeout /t 3 >nul
)

python -m forgeagent %*
pause
