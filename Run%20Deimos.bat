@echo off
title Deimos - Running
cd /d "%~dp0"

if not exist venv (
    echo [Deimos] venv folder not found. Running setup...
    call Setup.bat
)

if not exist venv\Scripts\python.exe (
    echo [ERROR] Virtual environment is broken. Please run Setup.bat again!
    pause
    exit /b
)

echo [Deimos] Starting Engine...
venv\Scripts\python Deimos.py

if %errorlevel% neq 0 (
    echo.
    echo [CRASH] Deimos closed with an error code.
)

echo.
pause
