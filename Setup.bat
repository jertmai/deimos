@echo off
title Deimos - Automatic Setup
cd /d "%~dp0"

echo [Deimos] Initializing setup...
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo.
    echo 1. Download Python from: https://www.python.org/downloads/
    echo 2. When installing, ENTIRELY CRITICAL: Check the box "Add Python to PATH".
    echo.
    pause
    exit /b
)

:: 2. Check for Git (Highly critical for GitHub-linked dependencies)
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed. 
    echo Some of Deimos's core libraries need to be pulled from GitHub.
    echo.
    echo Download Git from: https://git-scm.com/download/win
    echo.
    pause
    exit /b
)

:: 3. Create Virtual Environment
if not exist venv (
    echo [Deimos] Creating a virtual environment...
    python -m venv venv
)

:: 4. Install Requirements
echo [Deimos] Installing/Updating required libraries...
echo (This may take a minute depending on your internet speed)
echo.
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Something went wrong during installation.
    echo Try running Setup.bat again, or check your internet connection.
    pause
    exit /b
)

echo.
echo [Deimos] SUCCESS! Everything is installed.
echo You can now use "Run Deimos.bat" to start the tool.
echo.
pause
