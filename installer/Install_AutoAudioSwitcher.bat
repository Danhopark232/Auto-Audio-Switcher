@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_AutoAudioSwitcher.ps1"
set "exit_code=%ERRORLEVEL%"
if not "%exit_code%"=="0" (
    echo.
    echo Install failed. Exit code: %exit_code%
    pause
)
exit /b %exit_code%
