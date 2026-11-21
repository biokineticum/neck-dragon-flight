@echo off
setlocal EnableDelayedExpansion

echo ====================================================================
echo   FIRST-PERSON DRAGON FLIGHT - WEBCAM HEAD-TRACKING LAUNCHER
echo ====================================================================

rem Determine project root path
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

rem Step 1: Verify Python installation
where python >nul 2>&1
if ERRORLEVEL 1 (
    echo [ERROR] Python was not found in system PATH.
    echo Please install Python 3.11+ and verify 'python' command is accessible.
    pause
    exit /b 1
)

rem Step 2: Verify Python dependencies
python -c "import cv2, mediapipe, numpy" >nul 2>&1
if ERRORLEVEL 1 (
    echo [WARN] Missing Python dependencies. Installing from requirements.txt...
    python -m pip install -r "%PROJECT_DIR%tracker\requirements.txt"
    if ERRORLEVEL 1 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
)

rem Step 3: Discover Godot binary
set "GODOT_EXE="
if defined GODOT_BIN (
    if exist "%GODOT_BIN%" set "GODOT_EXE=%GODOT_BIN%"
)
if not defined GODOT_EXE (
    where godot >nul 2>&1
    if not ERRORLEVEL 1 (
        for /f "delims=" %%i in ('where godot') do (
            if not defined GODOT_EXE set "GODOT_EXE=%%i"
        )
    )
)
if not defined GODOT_EXE (
    if exist "C:\Users\Lenovo\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe" (
        set "GODOT_EXE=C:\Users\Lenovo\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe"
    ) else if exist "C:\Program Files\Godot\Godot_v4.7.2-stable_win64_console.exe" (
        set "GODOT_EXE=C:\Program Files\Godot\Godot_v4.7.2-stable_win64_console.exe"
    ) else if exist "C:\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe" (
        set "GODOT_EXE=C:\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe"
    )
)

if not defined GODOT_EXE (
    echo [ERROR] Godot 4.7.2 executable not found.
    echo Please set GODOT_BIN environment variable or install Godot to C:\Tools\Godot\.
    pause
    exit /b 1
)

echo [INFO] Python: OK
echo [INFO] Godot: "%GODOT_EXE%"
echo [INFO] Starting Python Head Tracker on port 42425...

rem Step 4: Start Python Head Tracker
start "Dragon Head Tracker" cmd /k python tracker\head_tracker.py

rem Step 5: Start Godot Game Engine
echo [INFO] Launching Godot project...
call "%GODOT_EXE%" --path .

if ERRORLEVEL 1 (
    echo [ERROR] Godot exited with an error code.
    pause
)

rem Step 6: Cleanup tracker process upon Godot closing
echo [INFO] Shutting down background head tracker...
taskkill /FI "WINDOWTITLE eq Dragon Head Tracker*" /T /F >nul 2>&1

echo [INFO] Clean exit.
endlocal
