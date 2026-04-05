@echo off
title ForgeAgent — CLI Mode
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist dist\ForgeAgent\ForgeAgent.exe (
        cd /d "%~dp0\dist\ForgeAgent"
        ForgeAgent.exe --cli
        pause & exit
    )
    echo ERROR: Install Python from https://python.org
    pause & exit /b 1
)

if not exist ".installed" (
    pip install -e . >nul 2>nul || pip install -r requirements.txt >nul 2>nul
    echo.>.installed
)

tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 (
    start "" ollama serve >nul 2>&1
    timeout /t 3 >nul
)

python -m forgeagent --cli %*
pause
