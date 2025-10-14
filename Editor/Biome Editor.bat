@echo off
cd /d "%~dp0"
start "" /min python map_editor.py
timeout /t 1 >nul
powershell -command "
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {
    [DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport(\"user32.dll\")] public static extern IntPtr FindWindowEx(IntPtr parent, IntPtr child, string className, string windowTitle);
    [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
'@;
$hwnd = [Win]::FindWindow('TkTopLevel', $null)
if ($hwnd -eq [IntPtr]::Zero) { $hwnd = [Win]::FindWindow('Python', $null) }
if ($hwnd -ne [IntPtr]::Zero) {
    [Win]::ShowWindow($hwnd, 3)
    [Win]::SetForegroundWindow($hwnd)
}
"
