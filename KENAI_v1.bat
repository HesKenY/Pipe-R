@echo off
setlocal

REM ============================================================
REM kenai:v1 - interactive chat with the in-repo offline build
REM ============================================================

set "ROOT=%~dp0"
set "MODEL=kenai:v1"
set "MODELFILE=%ROOT%offline_agent\brain\training\modelfiles\kenai-v1.Modelfile"

title kenai:v1 - interactive
echo.
echo ============================================================
echo   kenai:v1 - interactive chat
echo   type / for slash commands, /bye to exit
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
