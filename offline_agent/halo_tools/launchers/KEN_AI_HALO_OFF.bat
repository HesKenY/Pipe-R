@echo off
REM Portable — relative to the Codex clone.
set "SCRIPT=%~dp0..\..\..\agent_mode\halo\ken_ai_halo_control.py"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%SCRIPT%" --stop-stack
  exit /b %ERRORLEVEL%
)

py -3 "%SCRIPT%" --stop-stack
