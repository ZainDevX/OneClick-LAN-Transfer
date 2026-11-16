@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo   OneClick LAN Transfer - Production Build Script
echo =======================================================
echo.

:: 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found in system PATH.
    echo Please install Python 3.10+ from python.org to build the application.
    pause
    exit /b 1
)

echo [INFO] Python detected:
python --version
echo.

:: 2. Install / Verify Dependencies
echo [INFO] Verifying requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies from requirements.txt.
    pause
    exit /b 1
)
echo.

:: 3. Clean previous build artifacts
echo [INFO] Cleaning old build directories...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

:: 4. Run PyInstaller Build
echo [INFO] Building standalone executable with PyInstaller...
pyinstaller -y --clean OneClickLAN.spec
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)
echo.

:: 5. Validate Output
if exist dist\OneClickLAN\OneClickLAN.exe (
    echo =======================================================
    echo   BUILD SUCCESSFUL!
    echo =======================================================
    echo Portable Distribution created at:
    echo   dist\OneClickLAN\OneClickLAN.exe
    echo.
    echo The 'dist\OneClickLAN' folder can be zipped or copied directly
    echo to any Windows 10/11 computer. End users DO NOT need Python!
    echo =======================================================
) else (
    echo [ERROR] OneClickLAN.exe was not found in dist\OneClickLAN.
    pause
    exit /b 1
)

pause
