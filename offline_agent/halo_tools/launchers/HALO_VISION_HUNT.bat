@echo off
REM ═══════════════════════════════════════════════════════
REM HALO VISION HUNT — vision-assisted memory scanner
REM ═══════════════════════════════════════════════════════
REM Uses llama3.2-vision to READ Halo's HUD (shield / health)
REM then searches MCC process memory for those exact values.
REM When Ken takes damage, rescan with the new HUD value —
REM narrows candidates in 2-3 rounds instead of 10+.
REM
REM Requires: admin + MCC running + llama3.2-vision installed
REM Workflow: type 'r' → take damage → 'r' → repeat → 'w 9999'
REM ═══════════════════════════════════════════════════════

cd /d "%~dp0..\scripts"
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [vh] requesting admin privileges...
    powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/k cd /d %~dp0..\scripts && python halo_vision_hunt.py'"
    exit
)
title Halo Vision Hunt
python halo_vision_hunt.py
pause
