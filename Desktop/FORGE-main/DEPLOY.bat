@echo off
title ForgeAgent — Deploy Agents
cd /d "%~dp0"

where python >nul 2>nul || ( echo Python not found. & pause & exit /b 1 )
if not exist ".installed" ( pip install -e . >nul 2>nul & echo.>.installed )

tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 ( start "" ollama serve >nul 2>&1 & timeout /t 3 >nul )

echo.
echo   Click the DEPLOY tab, then "EASY DEPLOY" button
echo   to send an AI agent into a project folder.
echo.

python -m forgeagent %*
pause
