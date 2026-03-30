@echo off
REM BP Extract Web Interface Launcher for Windows
REM This batch file launches the Flask app and opens it in your default browser

setlocal enabledelayedexpansion

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.12+ from https://www.python.org/
    echo.
    pause
    exit /b 1
)

REM Get the directory where this script is located
for /f "delims=" %%a in ('cd') do set "SCRIPT_DIR=%%a"

REM Check if we're in a virtual environment, if not try to activate one
if defined VIRTUAL_ENV (
    echo Using existing virtual environment: !VIRTUAL_ENV!
) else (
    if exist ".venv\Scripts\activate.bat" (
        echo Activating virtual environment...
        call .venv\Scripts\activate.bat
    ) else if exist "venv\Scripts\activate.bat" (
        echo Activating virtual environment...
        call venv\Scripts\activate.bat
    )
)

REM Check if Flask is installed, if not install it
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask not found. Installing dependencies...
    pip install Flask
    if errorlevel 1 (
        echo.
        echo Error: Failed to install Flask
        echo Try running: pip install Flask
        echo.
        pause
        exit /b 1
    )
)

REM Clear screen and show startup message
cls
echo.
echo ============================================================
echo BP Extract - Blueprint Tracker Web Interface
echo ============================================================
echo.
echo Starting Flask application...
echo Opening browser to http://localhost:5000
echo.
echo To stop the application, press Ctrl+C in this window
echo.
timeout /t 2 >nul

REM Start the Flask app and open browser
echo Launching BP Extract...
start http://localhost:5000
python app.py

if errorlevel 1 (
    echo.
    echo Error: Failed to run the application
    echo Make sure you're in the correct directory and app.py exists
    echo.
    pause
)

endlocal
