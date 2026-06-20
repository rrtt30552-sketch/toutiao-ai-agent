@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   打包为 exe
echo ========================================
echo.

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo 安装 PyInstaller...
    python -m pip install pyinstaller
)

echo 打包中...
python -m PyInstaller --noconfirm --onefile --windowed --name "头条AI生成Agent" gui.py

echo.
echo ========================================
echo   完成! exe 在 dist\ 目录
echo   需要把 data\ 和 .env 复制到 exe 同目录
echo ========================================
pause
