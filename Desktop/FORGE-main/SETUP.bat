@echo off
title ForgeAgent — First Time Setup
color 0B
cd /d "%~dp0"

echo.
echo   ╔══════════════════════════════════════╗
echo   ║     F O R G E   A G E N T          ║
echo   ║     First Time Setup                ║
echo   ╚══════════════════════════════════════╝
echo.

REM ── Python ──
echo   [1/4] Checking Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo   ERROR: Python not found.
    echo   Download from https://python.org
    echo   Check "Add to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo         %%i

REM ── Ollama ──
echo   [2/4] Checking Ollama...
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo         Not found. Download from https://ollama.com/download
    echo         Install it, then run this setup again.
    pause & exit /b 1
) else (
    echo         OK
)

REM ── Dependencies ──
echo   [3/4] Installing Python packages...
pip install -e . 2>nul || pip install -r requirements.txt
echo.>.installed

REM ── Ollama Model ──
echo   [4/4] Pulling base model (this may take a few minutes)...
start "" ollama serve >nul 2>&1
timeout /t 5 /nobreak >nul
ollama pull qwen2.5-coder:14b

echo.
echo   ╔══════════════════════════════════════╗
echo   ║     Setup complete!                 ║
echo   ║     Double-click START.bat          ║
echo   ╚══════════════════════════════════════╝
echo.
pause
