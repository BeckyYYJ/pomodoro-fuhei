@echo off
setlocal
cd /d "%~dp0"
set "BUILD_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "BUILD_PYTHON=.venv\Scripts\python.exe"
"%BUILD_PYTHON%" -m PyInstaller --clean --noconfirm PomodoroTimer.spec
if errorlevel 1 (
    echo.
    echo Build failed. Check the error above.
    pause
    exit /b 1
)
echo.
echo Done. Versioned exe is in %CD%\dist
pause
