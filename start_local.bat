@echo off
setlocal
cd /d "%~dp0"

set "PY=%LOCALAPPDATA%\Programs\Python\bili-venv\Scripts\python.exe"
if exist "%CD%\backend\.venv\Scripts\python.exe" set "PY=%CD%\backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

set "PYTHONUTF8=1"
set "FFMPEG_BIN_PATH=%CD%\tools\ffmpeg\bin"
set "BACKEND_PORT=8484"
set "BACKEND_HOST=127.0.0.1"
set "VITE_BACKEND_ORIGIN=http://127.0.0.1:8484"
set "VITE_FRONTEND_PORT=3017"

echo Starting Shike ...
start "Shike Backend :8484" /D "%CD%\backend" cmd /k "%PY% main.py"
start "Shike UI :3017" /D "%CD%\BillNote_frontend_vue" cmd /k "npm run dev"

timeout /t 8 /nobreak >nul
start "" "http://localhost:3017"
endlocal
