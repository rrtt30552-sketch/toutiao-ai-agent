@echo off
chcp 65001 >nul 2>&1
set "SCRIPT_DIR=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\cs.vbs"
echo sLinkFile = "%DESKTOP%\头条AI生成Agent.lnk" >> "%TEMP%\cs.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\cs.vbs"
echo oLink.TargetPath = "pythonw" >> "%TEMP%\cs.vbs"
echo oLink.Arguments = """%SCRIPT_DIR%gui.py""" >> "%TEMP%\cs.vbs"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%TEMP%\cs.vbs"
echo oLink.Description = "今日头条AI内容生成Agent V8.2" >> "%TEMP%\cs.vbs"
echo oLink.Save >> "%TEMP%\cs.vbs"

cscript //nologo "%TEMP%\cs.vbs"
del "%TEMP%\cs.vbs"

echo.
echo ✅ 桌面快捷方式已创建
pause
