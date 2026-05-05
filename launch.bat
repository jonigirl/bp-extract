@echo off
REM BP Extract Web Interface Launcher for Windows
REM This batch file launches the app and opens it in your default browser.
REM
REM How Python is located (in order):
REM   1. uv  - if uv is on PATH, runs via "uv run python"
REM   2. .venv / venv - activates a local virtual environment
REM   3. system python / python3 - falls back to whatever is on PATH
REM
REM Dependencies are installed automatically using whichever method is found.

setlocal enabledelayedexpansion

REM --- Determine how to run Python ---

set "PYTHON_CMD="
set "USE_UV=0"

REM Try uv first
uv --version >nul 2>&1
if not errorlevel 1 (
    echo Found uv - using uv run
    set "USE_UV=1"
    goto :deps_check
)

REM Try activating a local venv
if defined VIRTUAL_ENV (
    echo Using existing virtual environment: !VIRTUAL_ENV!
    set "PYTHON_CMD=python"
    goto :deps_check
)
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call .venv\Scripts\activate.bat
    set "PYTHON_CMD=python"
    goto :deps_check
)
if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call venv\Scripts\activate.bat
    set "PYTHON_CMD=python"
    goto :deps_check
)

REM Fall back to system python / python3
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :deps_check
)
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :deps_check
)

echo.
echo Error: Python 3.12+ is required but was not found on PATH.
echo   - Download Python from https://www.python.org/
echo   - Or install uv from https://docs.astral.sh/uv/
echo.
pause
exit /b 1

:deps_check
REM --- Install dependencies if Flask is missing ---

if "!USE_UV!"=="1" (
    uv run python -c "import flask" >nul 2>&1
) else (
    !PYTHON_CMD! -c "import flask" >nul 2>&1
)

if errorlevel 1 (
    echo Flask not found - installing dependencies...
    if "!USE_UV!"=="1" (
        uv sync
    ) else (
        !PYTHON_CMD! -m pip install -r requirements.txt >nul 2>&1
        if errorlevel 1 (
            !PYTHON_CMD! -m pip install flask
        )
    )
    if errorlevel 1 (
        echo.
        echo Error: Failed to install dependencies.
        echo   With uv:  uv sync
        echo   With pip: pip install flask
        echo.
        pause
        exit /b 1
    )
)

REM --- Launch ---

cls
echo.
echo ============================================================
echo  BP Extract - Blueprint Tracker
echo ============================================================
echo.
echo  Starting... browser will open automatically.
echo  Press Ctrl+C in this window to stop.
echo.

if "!USE_UV!"=="1" (
    uv run python launch.py
) else (
    !PYTHON_CMD! launch.py
)

if errorlevel 1 (
    echo.
    echo Error: Application exited unexpectedly.
    echo Make sure you are running this from the BP Extract folder.
    echo.
    pause
)

endlocal
