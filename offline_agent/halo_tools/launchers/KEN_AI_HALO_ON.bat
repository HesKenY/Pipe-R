@echo off
REM Portable — resolves the Pipe-R halo controller relative to
REM this launcher's location inside the Codex clone.
set "SCRIPT=%~dp0..\..\..\agent_mode\halo\ken_ai_halo_control.py"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%SCRIPT%" --start-stack
  exit /b %ERRORLEVEL%
)

py -3 "%SCRIPT%" --start-stack
