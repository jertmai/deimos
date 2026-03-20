@echo off
title Deimos - All-in-One Installer
cd /d "%~dp0"

echo [Deimos] Starting the automatic installer...
echo [Deimos] Please stay connected to the internet.
echo.

:: --- 1. CHECK/INSTALL PYTHON ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Deimos] Python not found. Starting automatic installation...
    echo [Deimos] Downloading Python 3.12 installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe' -OutFile 'python_installer.exe'"
    echo [Deimos] Installing Python (this will take a moment)...
    start /wait python_installer.exe /quiet PrependPath=1
    del python_installer.exe
    set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python312\;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\"
    echo [Deimos] Python installed successfully!
) else (
    echo [Deimos] Python is already installed.
)

:: --- 2. CHECK/INSTALL GIT ---
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Deimos] Git not found. Starting automatic installation...
    echo [Deimos] Downloading Git installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe' -OutFile 'git_installer.exe'"
    echo [Deimos] Installing Git (this will take a moment)...
    start /wait git_installer.exe /VERYSILENT /NORESTART
    del git_installer.exe
    set "PATH=%PATH%;C:\Program Files\Git\cmd"
    echo [Deimos] Git installed successfully!
) else (
    echo [Deimos] Git is already installed.
)

:: --- 3. REFRESH PATH ---
:: This ensures that the current command session knows about the newly installed Python and Git
set "PATH=%PATH%;C:\Program Files\Git\cmd;%USERPROFILE%\AppData\Local\Programs\Python\Python312\;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\"

:: --- 4. CREATE VIRTUAL ENVIRONMENT ---
if not exist venv (
    echo [Deimos] Creating a virtual environment...
    python -m venv venv
)

:: --- 5. INSTALL LIBRARIES ---
echo [Deimos] Installing Deimos core libraries...
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [WARNING] Some libraries failed to install. Please run Setup.bat again!
    pause
    exit /b
)

echo.
echo [Deimos] SUCCESS! Everything is installed and ready.
echo [Deimos] You can now use "Run Deimos.bat" to start!
echo.
pause
