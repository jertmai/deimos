@echo off
title Deimos - Running Engine
cd /d "%~dp0"

:: Check if setup has been run (look for the activate script)
if not exist venv\Scripts\python.exe (
    echo [Deimos] Setup hasn't been run yet or is incomplete. Starting setup now...
    echo.
    call Setup.bat
)

:: Run Deimos from the virtual environment
echo [Deimos] Starting...
venv\Scripts\python Deimos.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Deimos crashed or failed to start.
    echo Please run Setup.bat again to fix the installation!
)

pause
