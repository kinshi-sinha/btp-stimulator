@echo off
REM IIoT Traffic Simulator - Windows launcher
REM Double-click this file to start the simulator GUI.

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not on PATH.
    echo.
    echo  Please install Python 3.10 or newer from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During install, check the box
    echo  "Add Python to PATH" on the first screen.
    echo.
    pause
    exit /b 1
)

python main.py
if %errorlevel% neq 0 (
    echo.
    echo  The simulator exited with an error. See messages above.
    pause
)
