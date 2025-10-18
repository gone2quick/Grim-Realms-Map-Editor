@echo off
:: === Variables ===
set "scriptName=map_editor.py"
set "launcherName=launch_map_editor.bat"
set "shortcutName=Map Editor.lnk"
set "iconFile=Pogo.ico"
set "folder=%~dp0"

(
echo @echo off
echo cd /d "%folder%"
echo start "" /min python "%folder%%scriptName%"
) > "%folder%%launcherName%"

powershell -Command ^
$WshShell = New-Object -ComObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('%folder%%shortcutName%'); ^
$Shortcut.TargetPath = '%folder%%launcherName%'; ^
$Shortcut.IconLocation = '%folder%%iconFile%'; ^
$Shortcut.Save()

echo Shortcut created: "%folder%%shortcutName%" with icon "%iconFile%"

ping 127.0.0.1 -n 2 >nul
del "%~f0"

