@echo off
cd /d "%~dp0"
echo ==========================================
echo   GestureMaster Installer
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.8 or later
    pause
    exit /b 1
)

REM Create assets directory if not exists
if not exist "assets" mkdir assets

REM Create shortcut
echo Creating shortcuts...
cscript //nologo create_shortcut.vbs

echo.
echo ==========================================
echo   Installation Complete!
echo ==========================================
echo.
echo Shortcuts created:
echo   - Desktop: GestureMaster
echo   - Start Menu: GestureMaster
echo.
echo To run the program:
echo   - Double-click the shortcut on desktop
echo   - Or run: start.bat
echo.
pause
