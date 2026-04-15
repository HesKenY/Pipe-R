@echo off
setlocal enableextensions
REM ========================================================
REM HALO VISION HUNT - vision-assisted memory scanner
REM
REM Uses llama3.2-vision to read Halo's HUD, then scans MCC
REM process memory for the matching values.
REM
REM Usage:
REM   HALO_VISION_HUNT.bat
REM   HALO_VISION_HUNT.bat restart
REM
REM Behavior:
REM - self-elevates to admin when needed
REM - prevents duplicate launches by default
REM - restart mode kills the old hunt and relaunches cleanly
REM - console closes automatically when python exits
REM ========================================================

set "MODE=%~1"

if /i "%MODE%"=="__elevated" (
    shift
    set "MODE=%~1"
)

cd /d "%~dp0..\scripts"

if /i not "%MODE%"=="restart" (
    set "RUNNING_PID="
    for /f "tokens=2" %%P in ('tasklist /v /fi "IMAGENAME eq cmd.exe" ^| findstr /i /c:"halo_vision_hunt.py" /c:"Halo Vision Hunt"') do (
        set "RUNNING_PID=%%P"
        goto :running_found
    )
    :running_found
    if defined RUNNING_PID (
        echo [vh] already running on pid %RUNNING_PID%
        echo [vh] use HALO_VISION_HUNT.bat restart to relaunch cleanly
        exit /b 0
    )
)

net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [vh] requesting admin privileges...
    powershell -NoProfile -Command "Start-Process -FilePath $env:ComSpec -Verb RunAs -ArgumentList '/c ""%~f0"" __elevated %MODE%'"
    exit /b
)

if /i "%MODE%"=="restart" (
    echo [vh] stopping existing vision hunt instances...
    for /f "tokens=2" %%P in ('tasklist /v /fi "IMAGENAME eq cmd.exe" ^| findstr /i /c:"halo_vision_hunt.py" /c:"Halo Vision Hunt"') do (
        taskkill /PID %%P /T /F >nul 2>&1
    )
    timeout /t 1 >nul
)

title Halo Vision Hunt
python halo_vision_hunt.py
exit /b %ERRORLEVEL%
