@echo off
echo ========================================
echo   Building exe
echo ========================================
echo.

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

echo Building...
python -m PyInstaller --noconfirm --onefile --windowed --name "ToutiaoAI" gui.py

echo.
echo ========================================
echo   Done! exe is in dist\ folder
echo   Copy data\ and .env to the same folder as exe
echo ========================================
pause
