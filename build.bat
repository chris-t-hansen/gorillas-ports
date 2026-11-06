@echo off
REM Build script for Windows (gorillas.exe)
REM Requires Python 3.10+ and pip

echo === Gorillas Game Build Script (Windows) ===
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check if venv exists, create if not
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

echo Installing/upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install -r requirements.txt

echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building standalone executable...

REM Clean previous builds
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build with PyInstaller
pyinstaller gorillas.spec

echo.
echo === Build Complete! ===
echo.
echo Executable location: dist\gorillas.exe
echo.
echo To test it:
echo   dist\gorillas.exe
echo.
echo To test with CGA mode:
echo   dist\gorillas.exe --cga
echo.
echo To test with scaling:
echo   dist\gorillas.exe --scale 2
echo.
echo File size:
dir dist\gorillas.exe

echo.
echo Note: The executable includes all dependencies and should run on any Windows 10/11 system.
echo No additional installations required!

pause
