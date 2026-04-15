@echo off
REM Stop the ken aimbot by dropping the stop flag in the scripts dir.
REM The running python process checks every 100ms and exits cleanly.

cd /d "%~dp0..\scripts"
type nul > AIMBOT_STOP.flag
echo [ken_aimbot] stop flag dropped. the aimbot will exit within ~100ms.
ping -n 2 127.0.0.1 > nul
