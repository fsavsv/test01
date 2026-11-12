@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist "%~dp0pc_health_check.ps1" (
    echo [ERROR] pc_health_check.ps1 not found in this folder.
    echo         Keep both files in the same folder and try again.
    echo.
    pause
    exit /b 1
)

echo Starting PC health check, please wait...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc_health_check.ps1"

echo.
echo Check finished. Press any key to close...
pause >nul
