@echo off
REM ========================================================
REM KenAI keylog — background pythonw loop
REM ========================================================
cd /d "%~dp0..\scripts"
if exist KEYLOG_STOP.flag del KEYLOG_STOP.flag
start "" /B pythonw halo_keylog.py
echo [keylog] launched
ping -n 2 127.0.0.1 > nul
exit
