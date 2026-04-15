@echo off
cd /d "%~dp0..\scripts"
type nul > KEYLOG_STOP.flag
echo [keylog] stop flag dropped
ping -n 2 127.0.0.1 > nul
exit
