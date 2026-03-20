@echo off
title Deimos - Automatic Setup
cd /d "%~dp0"

echo [Deimos] Initializing setup...
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from python.org and try again.
    pause
    exit /b
)

:: 2. Check for Git (needed for some dependencies)
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Git was not found. Some features might not install correctly.
    echo It is recommended to install Git from git-scm.com.
)

:: 3. Create Virtual Environment (Optional but cleaner)
if not exist venv (
    echo [Deimos] Creating a virtual environment...
    python -m venv venv
)

:: 4. Install Requirements
echo [Deimos] Installing required libraries...
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

echo.
echo [Deimos] SUCCESS! Everything is installed.
echo You can now use "Run Deimos.bat" to start the tool.
echo.
pause
