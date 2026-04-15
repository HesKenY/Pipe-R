@echo off
cd /d "%~dp0..\scripts"
type nul > DRIVER_STOP.flag
echo [driver] stop flag dropped
ping -n 2 127.0.0.1 > nul
exit
