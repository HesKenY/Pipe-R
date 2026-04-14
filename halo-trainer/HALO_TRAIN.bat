@echo off
REM halo-trainer launcher — runs the full drill pass + prints the scoreboard
cd /d "%~dp0"
echo [halo-trainer] running all drills...
node src/runner.js
echo.
echo [halo-trainer] scoreboard:
node src/scoreboard.js
echo.
pause
