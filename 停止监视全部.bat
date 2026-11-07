@echo off
chcp 65001 >nul
taskkill /FI "WINDOWTITLE eq SHIKE-VIDEO" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SHIKE-BILI" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SHIKE-MEETING" /T /F >nul 2>&1
echo All watchers stopped. Backend service untouched.
timeout /t 4 >nul
