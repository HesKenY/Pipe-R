@echo off
setlocal
title Building ForgeAgent.exe

echo ========================================
echo   Building ForgeAgent.exe
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Checking PyInstaller...
pip show pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo    Installing PyInstaller...
    pip install pyinstaller
)

echo [2/3] Building executable...
pyinstaller ^
    --name ForgeAgent ^
    --onedir ^
    --console ^
    --icon NONE ^
    --add-data "forgeagent;forgeagent" ^
    --add-data ".env.example;." ^
    --add-data "Modelfile;." ^
    --hidden-import forgeagent ^
    --hidden-import forgeagent.__main__ ^
    --hidden-import forgeagent.config ^
    --hidden-import forgeagent.core.query_engine ^
    --hidden-import forgeagent.core.interfaces ^
    --hidden-import forgeagent.providers.ollama.client ^
    --hidden-import forgeagent.providers.ollama.tool_protocol ^
    --hidden-import forgeagent.tools.registry ^
    --hidden-import forgeagent.commands.registry ^
    --hidden-import forgeagent.training.dataset_manager ^
    --hidden-import forgeagent.training.model_builder ^
    --hidden-import forgeagent.training.evaluator ^
    --hidden-import forgeagent.training.web_scraper ^
    --hidden-import forgeagent.deploy.agent_deployer ^
    --hidden-import forgeagent.deploy.instance_manager ^
    --hidden-import forgeagent.deploy.templates ^
    --hidden-import forgeagent.memory.session_store ^
    --hidden-import forgeagent.buddy.buddy ^
    --hidden-import forgeagent.ui.cli ^
    --hidden-import forgeagent.ui.tui ^
    --hidden-import forgeagent.utils.helpers ^
    --hidden-import textual ^
    --hidden-import textual.app ^
    --hidden-import textual.widgets ^
    --hidden-import textual.containers ^
    --hidden-import rich ^
    --hidden-import httpx ^
    --hidden-import click ^
    --hidden-import dotenv ^
    --hidden-import pydantic ^
    --collect-all textual ^
    --collect-all rich ^
    forgeagent/launcher.py

echo.
echo [3/3] Creating launcher shortcuts...

REM Copy Modelfile and .env.example into dist
copy Modelfile dist\ForgeAgent\ >nul 2>nul
copy .env.example dist\ForgeAgent\ >nul 2>nul

REM Create easy launchers inside dist
(
echo @echo off
echo title ForgeAgent
echo cd /d "%%~dp0"
echo tasklist /FI "IMAGENAME eq ollama.exe" 2^>nul ^| find /I "ollama.exe" ^>nul
echo if %%errorlevel%% neq 0 ^(
echo     echo Starting Ollama...
echo     start "" ollama serve ^>nul 2^>^&1
echo     timeout /t 3 ^>nul
echo ^)
echo ForgeAgent.exe
echo pause
) > dist\ForgeAgent\START.bat

(
echo @echo off
echo title ForgeAgent CLI
echo cd /d "%%~dp0"
echo tasklist /FI "IMAGENAME eq ollama.exe" 2^>nul ^| find /I "ollama.exe" ^>nul
echo if %%errorlevel%% neq 0 ^(
echo     start "" ollama serve ^>nul 2^>^&1
echo     timeout /t 3 ^>nul
echo ^)
echo ForgeAgent.exe --cli
echo pause
) > dist\ForgeAgent\START-CLI.bat

echo.
echo ========================================
echo   Build complete!
echo.
echo   Output: dist\ForgeAgent\
echo   Run:    dist\ForgeAgent\START.bat
echo           dist\ForgeAgent\ForgeAgent.exe
echo ========================================
echo.
pause
