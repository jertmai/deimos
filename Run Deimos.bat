@echo off
title Deimos - Running
cd /d "%~dp0"

:: 1. If venv environment exists, just RUN immediately
if exist venv\Scripts\python.exe (
    echo [Deimos] Environment found. Starting Engine...
    venv\Scripts\python Deimos.py
    goto end
)

:: 2. If it DOESN'T exist, run the setup once
echo [Deimos] Setup needed. Initializing...
call Setup.bat

:: 3. Try to launch after setup
if exist venv\Scripts\python.exe (
    echo [Deimos] Setup finished. Starting...
    venv\Scripts\python Deimos.py
) else (
    echo.
    echo [ERROR] Setup failed to create the environment.
    echo Please follow the instructions above or run Setup.bat manually.
    pause
)

:end
if %errorlevel% neq 0 (
    echo.
    echo [CRASH] Deimos closed with an error code: %errorlevel%
    pause
)
