@echo off
REM ═══════════════════════════════════════════════════════
REM HALO HUNT — memory delta scanner for MCC-Win64-Shipping
REM ═══════════════════════════════════════════════════════
REM Implements Cheat Engine's delta-scan workflow in Python.
REM Attaches to MCC, collects every float in plausible health
REM range, then narrows based on "increased/decreased/changed"
REM as Ken plays. Interactive console — read the intro text
REM on launch for commands.
REM
REM Requires ADMINISTRATOR privileges (memory scanning needs
REM PROCESS_VM_READ). If this .bat was launched normally, the
REM UAC prompt will pop up in ~1 second.
REM
REM Workflow:
REM   1. Start Halo, get into a mission with health bar visible
REM   2. Run this .bat (accept UAC prompt)
REM   3. Wait for "first pass done" — usually 30-90 seconds
REM   4. Alt-tab into Halo, TAKE DAMAGE
REM   5. Alt-tab back, type 'd' + Enter (decreased)
REM   6. Repeat a few times until candidates < 100
REM   7. Type 's' to see the remaining candidate addresses
REM   8. Type 'w 9999' to write 9999 to all → god mode
REM   9. Type 'x' to dump results to hunt_results.jsonl
REM   10. Type 'q' to quit
REM ═══════════════════════════════════════════════════════

cd /d "%~dp0..\scripts"

REM Self-elevate to admin if not already. NET SESSION fails
REM for non-admin users, so we use it to detect.
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [halo_hunt] requesting admin privileges for memory scan...
    powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/k cd /d %~dp0..\scripts && python halo_hunt.py'"
    exit
)

title Halo Hunt - MCC memory scanner
python halo_hunt.py
pause
