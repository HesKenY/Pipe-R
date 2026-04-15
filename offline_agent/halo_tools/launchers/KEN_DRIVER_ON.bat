@echo off
cd /d "%~dp0..\scripts"
if exist DRIVER_STOP.flag del DRIVER_STOP.flag
start "" /B pythonw halo_driver.py --tick 800
echo [driver] KenAI gameplay driver launched
ping -n 2 127.0.0.1 > nul
exit
