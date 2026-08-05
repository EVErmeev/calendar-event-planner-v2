@echo off
setlocal
chcp 65001 >nul 2>&1

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%" 2>nul
if errorlevel 1 goto :exit_cd

if not exist "logs" mkdir logs 2>nul
set "LOG_FILE=%APP_DIR%\logs\launcher.log"

:: ============================================================
:: Production launcher.
:: Prefers the bundled private runtime (<install>\runtime\python.exe)
:: with all deps installed at build time. NEVER uses py/python from
:: PATH, never creates a .venv, never runs pip on first launch.
:: ============================================================

set "PRIVATE_PYTHON=%APP_DIR%\runtime\python.exe"
set "DEV_PYTHON=%APP_DIR%\.venv\Scripts\python.exe"
set "RUNTIME_PYTHON="

if exist "%PRIVATE_PYTHON%" (
    set "RUNTIME_PYTHON=%PRIVATE_PYTHON%"
    goto :check_deps
)

:: Dev fallback: use an existing .venv if present. Never create it here.
if exist "%DEV_PYTHON%" (
    set "RUNTIME_PYTHON=%DEV_PYTHON%"
    goto :check_deps
)

:: No private runtime and no dev venv -> broken/not-installed product.
echo [ERROR] Bundled runtime not found: "%PRIVATE_PYTHON%"
echo.
echo This looks like an incomplete installation.
echo Please re-run the CalendarEventPlannerSetup installer.
echo.
echo For developers: create .venv and run pip install -e . manually.
pause
exit /b 1

:check_deps
if "%RUNTIME_PYTHON%"=="" goto :exit_no_runtime
"%RUNTIME_PYTHON%" -c "import calendar_planner, keyring, requests_ntlm" >nul 2>&1
if errorlevel 1 goto :exit_no_deps
goto :run_app

:run_app
"%RUNTIME_PYTHON%" -m calendar_planner.app.bootstrap %*
set "EXIT_CODE=%errorlevel%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Program exited with code %EXIT_CODE%.
    echo Details: logs\launcher.log
    pause
)
exit /b %EXIT_CODE%

:exit_no_runtime
echo [ERROR] No Python runtime selected.
pause
exit /b 1

:exit_no_deps
echo [ERROR] Runtime dependencies missing. Run Diagnostics or reinstall.
echo For developers: %RUNTIME_PYTHON% -m pip install -e . -q
pause
exit /b 1

:exit_cd
echo [ERROR] Cannot change to app directory: %APP_DIR%
pause
exit /b 1