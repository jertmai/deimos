@echo off
setlocal EnableDelayedExpansion
title Deimos - All-in-One Installer
cd /d "%~dp0"

echo [Deimos] Starting the automatic installer...
echo [Deimos] Please stay connected to the internet.
echo.

:: --- 1. CHECK FOR PYTHON ---
echo [Deimos] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Deimos] Python not found. Starting automatic installation...
    echo.
    powershell -Command "Write-Host 'Downloading Python...'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe' -OutFile 'python_installer.exe'"
    
    if exist python_installer.exe (
        echo [Deimos] Installing Python (this will take a moment)...
        start /wait python_installer.exe /quiet PrependPath=1 Include_test=0
        del python_installer.exe
        set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python312\;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\;C:\Program Files\Python312\;C:\Program Files\Python312\Scripts\"
        echo [Deimos] Python setup completed.
    ) else (
        echo [ERROR] Failed to download Python installer!
        pause
        exit /b
    )
) else (
    echo [Deimos] Python is already installed.
)

:: --- 2. CHECK FOR GIT ---
echo [Deimos] Checking for Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Deimos] Git not found. Starting automatic installation...
    echo.
    powershell -Command "Write-Host 'Downloading Git...'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe' -OutFile 'git_installer.exe'"
    
    if exist git_installer.exe (
        echo [Deimos] Installing Git (this will take a moment)...
        start /wait git_installer.exe /VERYSILENT /NORESTART
        del git_installer.exe
        set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files (x86)\Git\cmd"
        echo [Deimos] Git setup completed.
    ) else (
        echo [ERROR] Failed to download Git installer!
        pause
        exit /b
    )
) else (
    echo [Deimos] Git is already installed.
)

:: --- 3. CREATE VIRTUAL ENVIRONMENT ---
echo.
echo [Deimos] Preparing virtual environment...
python -m venv venv >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] venv could not be created directly. Trying alternative...
    python -m venv venv
)

:: --- 4. INSTALL LIBRARIES ---
echo [Deimos] Installing Deimos core libraries...
echo (This step might take a few minutes as it pulls from GitHub)
echo.
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Libraries failed to install. 
    echo Please make sure you are online and run Setup.bat again!
    pause
    exit /b
)

echo.
echo [Deimos] SUCCESS! Everything is installed and ready.
echo [Deimos] You can now share this folder with your friend!
echo [Deimos] They just need to double-click "Run Deimos.bat" to start.
echo.
pause
