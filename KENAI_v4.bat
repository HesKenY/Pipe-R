@echo off
setlocal

REM ============================================================
REM kenai:v4-offline-developer - local developer seed model
REM ============================================================

set "ROOT=%~dp0"
set "MODEL=kenai:v4-offline-developer"
set "MODELFILE=%ROOT%offline_agent\brain\training\modelfiles\kenai-v4-offline-developer.Modelfile"

title kenai:v4-offline-developer - interactive
echo.
echo ============================================================
echo   kenai:v4-offline-developer - interactive chat
echo ============================================================
echo.

if not exist "%MODELFILE%" (
  echo [kenai] modelfile missing:
  echo [kenai] %MODELFILE%
  exit /b 1
)

ollama show %MODEL% >nul 2>&1
if errorlevel 1 (
  echo [kenai] creating %MODEL% from:
  echo [kenai] %MODELFILE%
  ollama create %MODEL% -f "%MODELFILE%"
  if errorlevel 1 exit /b 1
)

ollama run %MODEL%
