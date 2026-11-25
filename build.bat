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

:: 5. Validate the onedir folder. The exe alone cannot start.
if not exist dist\OneClickLAN\OneClickLAN.exe (
    echo [ERROR] OneClickLAN.exe was not found in dist\OneClickLAN.
    pause
    exit /b 1
)
dir /b "dist\OneClickLAN\_internal\python3*.dll" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] The Python runtime DLL is missing from dist\OneClickLAN\_internal.
    echo The folder is incomplete. Do not ship the exe by itself.
    pause
    exit /b 1
)
if not exist "dist\OneClickLAN\_internal\vcruntime140.dll" (
    echo [ERROR] vcruntime140.dll is missing from dist\OneClickLAN\_internal.
    echo A new Windows PC would fail to load the Python DLL.
    pause
    exit /b 1
)

:: 6. Zip the whole folder. End users unpack this zip and run the exe inside it.
echo [INFO] Creating dist\OneClickLAN-win64.zip ...
if exist dist\OneClickLAN-win64.zip del /f /q dist\OneClickLAN-win64.zip
tar -a -c -f dist\OneClickLAN-win64.zip -C dist OneClickLAN
if errorlevel 1 (
    echo [ERROR] Failed to create the portable ZIP.
    pause
    exit /b 1
)

echo =======================================================
echo   BUILD SUCCESSFUL!
echo =======================================================
echo Portable folder:
echo   dist\OneClickLAN\
echo Portable ZIP (give this file to end users):
echo   dist\OneClickLAN-win64.zip
echo.
echo Unpack the ZIP and run OneClickLAN\OneClickLAN.exe.
echo The _internal folder must stay next to the exe.
echo End users do not install Python.
echo =======================================================

pause
