@echo off
title Deimos - Running Engine
cd /d "%~dp0"

:: Check if setup has been run
if not exist venv (
    echo [Deimos] Setup hasn't been run yet. Starting setup now...
    echo.
    call Setup.bat
)

:: Run Deimos from the virtual environment
echo [Deimos] Starting...
venv\Scripts\python Deimos.py
pause
