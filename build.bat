@echo off
python -m PyInstaller --noconfirm --onefile --windowed --name PomodoroTimer main.py
echo.
echo Done. Exe is in dist\PomodoroTimer.exe
pause
