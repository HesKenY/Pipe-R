@echo off
rem ===========================================================
rem   NEST LAUNCHER
rem   Double-click to open Bird's Nest - the customer instance
rem   builder. Nest bakes a zip of the CURRENT cherp.live build
rem   branded per customer, with the CHERP commit SHA stamped
rem   into instance.json and the customer README.
rem
rem   Every build pulls fresh from HesKenY/CHERP main via
rem   src/builder/instance-builder.js _fetchLatestCherp().
rem ===========================================================
setlocal EnableDelayedExpansion
title Bird's Nest Launcher
color 0E
cd /d "%~dp0"

set NEST_DIR=nest

echo.
echo   ===========================================================
echo             BIRD'S NEST  -  Customer Instance Builder
echo   ===========================================================
echo.

rem -- [1/3] Verify Nest repo exists ---------------------------
if not exist "%NEST_DIR%\nest.js" (
  echo   [!] Nest not found at %NEST_DIR%
  echo   [!] Cloning HesKenY/CHERP-Nest to top-level nest/ ...
  echo.
  gh repo clone HesKenY/CHERP-Nest nest 2>nul
  if errorlevel 1 (
    echo   [X] Clone failed. Check gh auth / network.
    pause
    exit /b 1
  )
  echo   [OK] Nest cloned.
  echo.
)

rem -- [2/3] Show where builds will land ------------------------
echo   [1/2] Workspace: %CD%\%NEST_DIR%
echo          Builds output to: %CD%\%NEST_DIR%\builds\
echo          Source cache:    %CD%\%NEST_DIR%\source-cache\CHERP
echo.

rem -- [3/3] Launch Nest ----------------------------------------
echo   [2/2] Launching Bird's Nest...
echo.
cd /d "%~dp0%NEST_DIR%"
node nest.js

echo.
echo   ===========================================================
echo   Nest session ended.
echo   ===========================================================
pause
