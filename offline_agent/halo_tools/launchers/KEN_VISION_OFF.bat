@echo off
cd /d "%~dp0..\scripts"
type nul > VISION_STOP.flag
echo [vision] stop flag dropped
ping -n 2 127.0.0.1 > nul
exit
