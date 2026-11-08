@echo off
chcp 65001 >nul
set "ROOT=%~dp0"
"%ROOT%backend\.venv\Scripts\python.exe" "%ROOT%_once.py" meeting_parse.py %*
pause >nul
