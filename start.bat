@echo off
chcp 65001 >nul
title Document Processor Startup

echo =========================================
echo    Document Processor Initialization
echo =========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.12 and add it to your system PATH.
    pause
    exit /b 1
)

echo [INFO] Python found. Checking dependencies...
echo.

:: Install or update dependencies from requirements.txt
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install one or more dependencies.
    echo Please check your internet connection or Python environment.
    pause
    exit /b 1
)

echo.
echo [INFO] All dependencies are ready. Starting the application...
echo.

:: Start the main application
cd src
start "" pythonw main.py

exit /b 0
