@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where pwsh >nul 2>nul
if %errorlevel%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local.ps1" %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local.ps1" %*
)

if errorlevel 1 (
    echo.
    echo Startup failed. Check logs\backend.log or logs\frontend.log.
    echo If you need help, copy the messages above.
    pause
)
endlocal
