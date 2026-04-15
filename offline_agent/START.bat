@echo off
REM ========================================================
REM Ken AI offline — start the FastAPI server + chrome app
REM ========================================================
REM Double-click or fire from a desktop shortcut. Launches
REM main.py in a background console, waits for 127.0.0.1:7778
REM to bind, then opens Chrome in --app mode pointing at it.
REM
REM Ollama MUST already be running — we check for :11434 and
REM warn if it's not responding but don't auto-start it (Ken
REM usually has it running on login via the tray).
REM ========================================================

setlocal enableextensions enabledelayedexpansion

cd /d "%~dp0"

title Ken AI offline — launcher

echo.
echo ============================================================
echo   Ken AI offline v0.1.0-skeleton
echo   http://127.0.0.1:7778
echo ============================================================
echo.

REM ── Check python is on PATH ─────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [fail] python not found on PATH.
    echo        install python 3.11+ from python.org and try again.
    pause
    exit /b 1
)

REM ── Check ollama is responding on 11434 ─────────────────
echo [check] ollama on :11434 ...
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:11434/api/tags > "%TEMP%\olcheck.txt" 2>nul
set /p olcode=<"%TEMP%\olcheck.txt"
del "%TEMP%\olcheck.txt" >nul 2>&1
if "%olcode%"=="200" (
    echo        ok
) else (
    echo [warn] ollama not responding on :11434.
    echo        start it with `ollama serve` in another terminal,
    echo        or leave it running in the system tray.
    echo        continuing anyway — /api/status will show ollama: false
    echo.
)

REM ── Check port 7778 is free ─────────────────────────────
netstat -ano | findstr ":7778 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [warn] something is already listening on :7778.
    echo        if that's a stale Ken AI server, run STOP.bat first.
    echo.
    echo        opening browser to the existing server...
    goto open_browser
)

REM ── Install missing deps quietly (fast no-op if installed) ──
echo [deps ] pip install -q -r requirements.txt ...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [fail] pip install failed. check requirements.txt.
    pause
    exit /b 1
)

REM ── Launch main.py in a new console ─────────────────────
echo [boot ] starting main.py ...
start "Ken AI offline — server" /MIN cmd /c "python main.py"

REM ── Wait for port 7778 to bind (up to 12 seconds) ───────
set /a tries=0
:wait_loop
set /a tries+=1
ping -n 2 127.0.0.1 >nul
netstat -ano | findstr ":7778 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 goto ready
if %tries% lss 6 goto wait_loop

echo [fail] server did not bind :7778 within 12s.
echo        check the "Ken AI offline — server" window for errors.
pause
exit /b 1

:ready
echo [ok   ] server up on http://127.0.0.1:7778
echo.

:open_browser
REM ── Open Chrome in app mode if available, fallback to default ──
set "CHROME="
for %%P in (
    "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) do (
    if exist %%~P set "CHROME=%%~P"
)

if defined CHROME (
    echo [ui   ] opening chrome --app at 1400x900
    start "" "%CHROME%" --app=http://127.0.0.1:7778 --window-size=1400,900 --window-position=200,100
) else (
    echo [ui   ] chrome not found, using default browser
    start "" http://127.0.0.1:7778
)

echo.
echo ============================================================
echo   ready. leave the server window running in the background.
echo   run STOP.bat when you're done.
echo ============================================================
echo.

REM portable pause — ping -n works under cmd.exe and git bash
ping -n 4 127.0.0.1 >nul
exit /b 0
