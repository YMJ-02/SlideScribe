@echo off
setlocal enabledelayedexpansion

cd /d %~dp0..

echo.
echo ==========================================================
echo   SlideScribe  -  Windows build
echo ==========================================================
echo.

REM ── 1) Check PyInstaller ───────────────────────────────────
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller. Aborting.
        exit /b 1
    )
)

REM ── 2) Clean previous build ────────────────────────────────
if exist dist\SlideScribe (
    echo Cleaning dist\SlideScribe\ ...
    rmdir /s /q dist\SlideScribe
)
if exist build\__pycache__  rmdir /s /q build\__pycache__

REM ── 3) Run PyInstaller ─────────────────────────────────────
echo.
echo Running PyInstaller (this takes a few minutes)...
echo.
pyinstaller build\slidescribe.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo PyInstaller build FAILED.
    exit /b 1
)

REM ── 4) Done message ────────────────────────────────────────
echo.
echo ==========================================================
echo   Build succeeded.
echo ==========================================================
echo   Bundle :  dist\SlideScribe\SlideScribe.exe
echo.
echo   To build the installer (.exe setup):
echo     1. Install Inno Setup 6:  https://jrsoftware.org/isdl.php
echo     2. Run:   iscc build\installer.iss
echo     3. Find:  dist\installer\SlideScribe-Setup-*.exe
echo ==========================================================
echo.

endlocal
