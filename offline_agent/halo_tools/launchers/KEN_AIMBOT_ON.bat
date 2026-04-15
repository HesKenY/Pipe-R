@echo off
REM ========================================================
REM KEN AIMBOT — background launcher (no visible console)
REM ========================================================
REM Uses pythonw.exe so no cmd window sticks around stealing
REM focus from Halo. Output lands in aimbot.log.jsonl next to
REM the python script. Window closes immediately after launch.
REM
REM Stop:  KEN_AIMBOT_OFF.bat
REM Stats: KEN_AIMBOT_STATS.bat
REM Pause: F10 in-game
REM ========================================================

cd /d "%~dp0..\scripts"
if exist AIMBOT_STOP.flag del AIMBOT_STOP.flag

start "" /B pythonw ken_aimbot.py
echo [ken_aimbot] launched — Halo stays focused, logging to aimbot.log.jsonl
ping -n 2 127.0.0.1 > nul
exit
