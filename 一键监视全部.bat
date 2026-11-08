@echo off
chcp 65001 >nul
set "ROOT=%~dp0"
set "PY=%ROOT%backend\.venv\Scripts\python.exe"
"%PY%" "%ROOT%launch_all.py"
echo.
echo Press any key to close this window (watchers keep running).
pause >nul
