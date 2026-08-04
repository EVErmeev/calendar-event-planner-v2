@echo off
setlocal
chcp 65001 >nul 2>&1
set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%" 2>nul
call run_calendar_planner.bat --diagnostics
exit /b %errorlevel%