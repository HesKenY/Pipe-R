@echo off
REM ========================================================
REM KenAI — portable stop shortcut
REM ========================================================
REM Lives in the Codex clone root. Works from anywhere the
REM Codex folder is. Politely hits /api/stop then kills any
REM PID still listening on :7778.
REM ========================================================

call "%~dp0offline_agent\STOP.bat"
