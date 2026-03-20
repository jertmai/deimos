@echo off
setlocal
title Deimos - All-in-One Installer
cd /d "%~dp0"

echo [Deimos] Starting setup...
echo.

:: --- 1. CHECK FOR PYTHON ---
echo [Deimos] Checking for Python...
python --version >nul 2>&1
if %errorlevel% equ 0 goto python_installed

echo [Deimos] Python not found. Downloading Python 3.12...
powershell -Command "Write-Host 'Connecting to python.org...'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe' -OutFile 'python_installer.exe'"

if not exist python_installer.exe goto download_error

echo [Deimos] Installing Python (silent mode)...
start /wait python_installer.exe /quiet PrependPath=1
del python_installer.exe
set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python312\;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\"
echo [Deimos] Python installed!

:python_installed
echo [Deimos] Python is ready.

:: --- 2. CHECK FOR GIT ---
echo [Deimos] Checking for Git...
git --version >nul 2>&1
if %errorlevel% equ 0 goto git_installed

echo [Deimos] Git not found. Downloading Git...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe' -OutFile 'git_installer.exe'"

if not exist git_installer.exe goto download_error

echo [Deimos] Installing Git (silent mode)...
start /wait git_installer.exe /VERYSILENT /NORESTART
del git_installer.exe
set "PATH=%PATH%;C:\Program Files\Git\cmd"
echo [Deimos] Git installed!

:git_installed
echo [Deimos] Git is ready.

:: --- 3. CREATE VIRTUAL ENVIRONMENT ---
echo.
echo [Deimos] Building virtual environment...
if not exist venv (
    python -m venv venv
)

:: --- 4. INSTALL LIBRARIES & PYINSTALLER ---
echo [Deimos] Installing project libraries...
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt pyinstaller

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Library installation failed. 
    pause
    exit /b
)

:: --- 5. BUILD THE STANDALONE EXE ---
if exist Deimos.exe goto finish

echo.
echo [Deimos] COMPILING STANDALONE APP...
echo (This will create your "Deimos" engine app. Please wait...)
echo.
venv\Scripts\pyinstaller --onefile --noconsole --icon=Deimos-logo.ico Deimos.py

:: Move the EXE to the root and clean up
if exist dist\Deimos.exe (
    move /y dist\Deimos.exe .
    rd /s /q build
    rd /s /q dist
    del /f /q Deimos.spec
    echo.
    echo [Deimos] SUCCESS! Your "Deimos.exe" app has been created!
) else (
    echo [WARNING] EXE creation failed. You can still use "Run Deimos.bat".
)

:finish
echo.
echo [Deimos] ============================================
echo [Deimos] INSTALLATION COMPLETE!
echo [Deimos] You can now use "Deimos.exe" to start the app!
echo [Deimos] ============================================
echo.
pause
exit /b

:download_error
echo.
echo [ERROR] Failed to download installers. 
pause
exit /b
