@echo off
echo ============================================
echo  SlideScribe - Windows Setup
echo ============================================
echo.

echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing CUDA 12 libraries (cuBLAS + cuDNN)...
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
if errorlevel 1 (
    echo WARNING: CUDA library install failed. GPU acceleration may not work.
)

echo.
echo [3/4] Registering CUDA DLL paths to system PATH...
for /f "delims=" %%i in ('python -c "import site; print(site.getsitepackages()[0])"') do set SITE=%%i

set CUBLAS_PATH=%SITE%\nvidia\cublas\bin
set CUDNN_PATH=%SITE%\nvidia\cudnn\bin

if exist "%CUBLAS_PATH%\cublas64_12.dll" (
    setx PATH "%PATH%;%CUBLAS_PATH%;%CUDNN_PATH%"
    echo CUDA paths registered:
    echo   %CUBLAS_PATH%
    echo   %CUDNN_PATH%
) else (
    echo WARNING: cublas64_12.dll not found. CUDA PATH registration skipped.
    echo If you see CUDA errors at runtime, re-run this script or set PATH manually.
)

echo.
echo [4/4] Verifying ffmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo WARNING: ffmpeg not found in PATH.
    echo Please install ffmpeg and add it to PATH:
    echo   winget install ffmpeg
    echo   or download from https://ffmpeg.org/download.html
) else (
    echo ffmpeg OK.
)

echo.
echo ============================================
echo  Setup complete! Run the app with:
echo    python app.py
echo ============================================
pause
