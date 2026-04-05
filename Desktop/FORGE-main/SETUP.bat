@echo off
setlocal EnableDelayedExpansion
title ForgeAgent — Setup

echo.
echo   ========================================
echo     ForgeAgent Setup
echo     AI Coding Agent Hub
echo   ========================================
echo.

REM ── Python ──
echo   [1/4] Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo   ERROR: Python not found.
    echo   Download from https://python.org
    echo   Check "Add to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo         %%i

REM ── Ollama ──
echo   [2/4] Ollama...
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo         Not found. Downloading...
    powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe'"
    start /wait "" "%TEMP%\OllamaSetup.exe" /silent
    timeout /t 10 >nul
) else (
    echo         OK
)

REM ── Model ──
echo   [3/4] AI Model...
start "" ollama serve >nul 2>&1
timeout /t 5 >nul
ollama pull qwen2.5-coder:14b
ollama create forgeagent -f Modelfile 2>nul

REM ── Dependencies ──
echo   [4/4] Python packages...
cd /d "%~dp0"
pip install -e . 2>nul || pip install -r requirements.txt
echo.>.installed

echo.
echo   ========================================
echo     Setup complete!
echo.
echo     Double-click START.bat to launch
echo     or START-CLI.bat for text mode
echo   ========================================
echo.
pause
