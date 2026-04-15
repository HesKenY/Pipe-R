@echo off
cd /d "%~dp0..\scripts"
if exist VISION_STOP.flag del VISION_STOP.flag
start "" /B pythonw halo_vision_observe.py --interval 20
echo [vision] observe loop launched
ping -n 2 127.0.0.1 > nul
exit
