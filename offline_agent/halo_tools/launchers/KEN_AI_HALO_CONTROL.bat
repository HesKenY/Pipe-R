@echo off
REM Portable — relative to the Codex clone.
set "SCRIPT=%~dp0..\..\..\agent_mode\halo\ken_ai_halo_control.py"

where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "" pythonw "%SCRIPT%"
  exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "" python "%SCRIPT%"
  exit /b 0
)

start "" py -3 "%SCRIPT%"
