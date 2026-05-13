@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Document Processor Startup

echo =========================================
echo    Document Processor Initialization
echo =========================================
echo.

:: Define target local python directory
set "LOCAL_PYTHON_DIR=%~dp0python_env"
set "PYTHON_EXE=%LOCAL_PYTHON_DIR%\python.exe"
set "PIP_EXE=%LOCAL_PYTHON_DIR%\Scripts\pip.exe"

:: 1. Check if we already have the local python downloaded
if exist "%PYTHON_EXE%" (
    echo [INFO] Local Python 3.12 environment found.
    goto :INSTALL_DEPS
)

:: 2. If no local python, check system python version
echo [INFO] Checking system Python version...
python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" > "%TEMP%\pyver.txt" 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] System Python not found.
    set "SYS_PY_VER=none"
) else (
    set /p SYS_PY_VER=<"%TEMP%\pyver.txt"
)

:: ML libraries currently best support 3.10, 3.11, 3.12.
:: If the user has 3.14 (or none), we download the portable 3.12.
if "%SYS_PY_VER%"=="3.10" goto :USE_SYSTEM
if "%SYS_PY_VER%"=="3.11" goto :USE_SYSTEM
if "%SYS_PY_VER%"=="3.12" goto :USE_SYSTEM

echo [WARNING] System Python is %SYS_PY_VER%.
echo [INFO] PaddleOCR and PyMuPDF require Python 3.10 - 3.12.
echo [INFO] Downloading a portable Python 3.12 environment. This may take a moment...

:: Use Nuget/PowerShell to download a standalone Python zip. We use python-embed and install pip.
mkdir "%LOCAL_PYTHON_DIR%"
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.2/python-3.12.2-embed-amd64.zip' -OutFile 'python-3.12.2-embed.zip'"

echo [INFO] Extracting Python...
powershell -Command "Expand-Archive -Path 'python-3.12.2-embed.zip' -DestinationPath '%LOCAL_PYTHON_DIR%' -Force"
del "python-3.12.2-embed.zip"

:: Enable site-packages in the embedded Python
powershell -Command "(Get-Content '%LOCAL_PYTHON_DIR%\python312._pth') -replace '#import site', 'import site' | Set-Content '%LOCAL_PYTHON_DIR%\python312._pth'"

:: Download get-pip.py
echo [INFO] Installing pip...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%LOCAL_PYTHON_DIR%\get-pip.py'"
"%PYTHON_EXE%" "%LOCAL_PYTHON_DIR%\get-pip.py"
del "%LOCAL_PYTHON_DIR%\get-pip.py"

echo [INFO] Portable Python 3.12 environment created successfully!
goto :INSTALL_DEPS

:USE_SYSTEM
echo [INFO] System Python %SYS_PY_VER% is compatible.
set "PYTHON_EXE=python"
set "PIP_EXE=python -m pip"

:INSTALL_DEPS
echo.
echo [INFO] Checking dependencies...
"%PIP_EXE%" install --upgrade pip

:: Ensure requirements.txt uses stable versions for our known compatible python
"%PIP_EXE%" install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install one or more dependencies.
    echo Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo [INFO] All dependencies are ready. Starting the application...
echo.

:: Start the main application
cd src
start "" "%PYTHON_EXE%" main.py

exit /b 0
