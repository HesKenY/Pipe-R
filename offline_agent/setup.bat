@echo off
setlocal

echo.
echo ================================================
echo   KenAI Offline Developer Setup - Windows 10/11
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause & exit /b 1
)
echo [OK] Python found
python --version

:: Check pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip not found.
    pause & exit /b 1
)
echo [OK] pip found

:: Check Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Ollama not running on localhost:11434
    echo        Install Ollama from https://ollama.com
    echo        Then run: ollama serve
    echo        And pull a model: ollama pull qwen2.5-coder:14b
) else (
    echo [OK] Ollama is running
)

:: Check ripgrep
rg --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] ripgrep (rg) not found. Search will fall back to grep.
    echo        Install: winget install BurntSushi.ripgrep.MSVC
) else (
    echo [OK] ripgrep found
)

:: Check git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] git not found. Git tools will not work.
    echo        Install: https://git-scm.com/download/win
) else (
    echo [OK] git found
)

:: Install Python deps
echo.
echo Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed.
    pause & exit /b 1
)
echo [OK] Dependencies installed

:: Create __init__ files
echo. > agent_core\__init__.py
echo. > models\__init__.py
echo. > tools\__init__.py

echo.
echo ================================================
echo   Setup complete!
echo.
echo   Run:  python main.py
echo   Open: http://localhost:7778
echo ================================================
echo.
pause
