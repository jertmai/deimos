@echo off
setlocal
title Deimos - Automatic Setup
cd /d "%~dp0"

echo [Deimos] Starting setup...
echo.

:: --- 1. CHECK/INSTALL PYTHON ---
python --version >nul 2>&1
if %errorlevel% equ 0 goto python_installed

echo [Deimos] Python not found. Starting auto-install...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe' -OutFile 'python_installer.exe'"
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

echo [Deimos] Git not found. Starting auto-install...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe' -OutFile 'git_installer.exe'"
start /wait git_installer.exe /VERYSILENT /NORESTART
del git_installer.exe
set "PATH=%PATH%;C:\Program Files\Git\cmd"
echo [Deimos] Git installed!

:git_installed
echo [Deimos] Git is ready.

:: --- 3. CREATE VIRTUAL ENVIRONMENT ---
echo.
echo [Deimos] Building environment...
if not exist venv (
    python -m venv venv
)

:: --- 4. INSTALL LIBRARIES ---
echo [Deimos] Installing project libraries...
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Library installation failed. 
    pause
    exit /b
)

:: --- 5. CREATE THE "CLEAN" DEIMOS APP ICON ---
echo [Deimos] Creating your "Deimos App" icon (Direct Launch)...
set "ShortcutPath=%~dp0\Deimos.lnk"
set "PythonPath=%~dp0\venv\Scripts\pythonw.exe"
set "ScriptPath=%~dp0\Deimos.py"
set "IconPath=%~dp0\Deimos-logo.ico"
set "WorkingDir=%~dp0"

:: This creates a shortcut that runs the GUI directly with ZERO terminal window
powershell -ExecutionPolicy Bypass -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%ShortcutPath%'); $Shortcut.TargetPath = '%PythonPath%'; $Shortcut.Arguments = '\"%ScriptPath%\"'; $Shortcut.IconLocation = '%IconPath%'; $Shortcut.WorkingDirectory = '%WorkingDir%'; $Shortcut.Save()"

echo.
echo [Deimos] SUCCESS! Deimos is fully installed and your App Launcher is ready.
echo [Deimos] You can now double-click the "Deimos" icon to start the GUI directly.
echo.
pause
exit /b
