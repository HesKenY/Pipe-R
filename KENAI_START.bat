@echo off
REM ========================================================
REM KenAI — portable start shortcut
REM ========================================================
REM Lives in the Codex clone root. Works from anywhere the
REM Codex folder is — no hardcoded paths to C: drive or
REM this-machine-specific usernames.
REM
REM Double-click to launch offline_agent/main.py, wait for
REM :7778 to bind, then open Chrome --app pointing at it.
REM ========================================================

call "%~dp0offline_agent\START.bat"
