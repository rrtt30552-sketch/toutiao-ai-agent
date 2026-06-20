@echo off
set "SCRIPT_DIR=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\cs.vbs"
echo sLinkFile = "%DESKTOP%\ToutiaoAI.lnk" >> "%TEMP%\cs.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\cs.vbs"
echo oLink.TargetPath = "pythonw" >> "%TEMP%\cs.vbs"
echo oLink.Arguments = """"%SCRIPT_DIR%gui.py"""" >> "%TEMP%\cs.vbs"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%TEMP%\cs.vbs"
echo oLink.Description = "Toutiao AI Agent V8.2" >> "%TEMP%\cs.vbs"
echo oLink.Save >> "%TEMP%\cs.vbs"

cscript //nologo "%TEMP%\cs.vbs"
del "%TEMP%\cs.vbs"

echo.
echo Shortcut created on Desktop: ToutiaoAI.lnk
pause
