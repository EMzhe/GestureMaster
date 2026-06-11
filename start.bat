@echo off
cd /d "%~dp0"
echo ==========================================
echo   GestureMaster - Gesture Control Master
echo ==========================================
echo.
echo Starting...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.8 or later
    pause
    exit /b 1
)

REM Run program
python launch.py
set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% neq 0 (
    echo.
    echo Program exited with error code: %EXIT_CODE%
    echo.
    pause
)
