@echo off
title Deimos - Running Engine
cd /d "%~dp0"

:: 1. Check if both the venv AND the "requests" library exist
if not exist venv\Scripts\python.exe goto run_setup
venv\Scripts\python -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [Deimos] Environment is missing core libraries (like "requests")...
    goto run_setup
)

:: 2. Launch normally if everything is found
echo [Deimos] Starting...
venv\Scripts\python Deimos.py
goto end

:run_setup
echo [Deimos] Setup needed or incomplete. Initializing...
echo.
call Setup.bat

if exist venv\Scripts\python.exe (
    venv\Scripts\python Deimos.py
)

:end
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Deimos failed to start.
    echo Please run Setup.bat manually to fix the installation!
)

pause
