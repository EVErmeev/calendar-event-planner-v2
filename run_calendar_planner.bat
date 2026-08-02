@echo off
setlocal
chcp 65001 >nul 2>&1

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot change to app directory: %APP_DIR%
    pause
    exit /b 1
)

if not exist "logs" mkdir logs 2>nul

set "LOG_FILE=%APP_DIR%\logs\launcher.log"
( echo %date% %time% Launcher started ) >> "%LOG_FILE%"
( echo %date% %time% App dir: %APP_DIR% ) >> "%LOG_FILE%"

set "VENV_PYTHON=%APP_DIR%\.venv\Scripts\python.exe"

:: ============================================================
:: Find working Python 3.11+
:: ============================================================
set "PYTHON_CMD="

:: Try py -3.11
py -3.11 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    goto :found_python
)

:: Try py
py -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :found_python
)

:: Try python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :found_python
)

echo [ERROR] Python 3.11 or newer not found.
echo Install Python 3.11+: https://www.python.org/downloads/
echo Enable "Add Python to PATH" during installation.
( echo %date% %time% FATAL: Python not found ) >> "%LOG_FILE%"
pause
exit /b 1

:found_python
( echo %date% %time% Python: %PYTHON_CMD% ) >> "%LOG_FILE%"

:: ============================================================
:: Setup venv if missing
:: ============================================================
if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment .venv ...
    ( echo %date% %time% Creating .venv ) >> "%LOG_FILE%"
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        ( echo %date% %time% FATAL: venv creation failed ) >> "%LOG_FILE%"
        pause
        exit /b 1
    )
    ( echo %date% %time% Created .venv ) >> "%LOG_FILE%"

    echo Installing application ...
    "%VENV_PYTHON%" -m pip install --upgrade pip -q --disable-pip-version-check
    if errorlevel 1 (
        echo [ERROR] Failed to upgrade pip.
        ( echo %date% %time% FATAL: pip upgrade failed ) >> "%LOG_FILE%"
        pause
        exit /b 1
    )

    "%VENV_PYTHON%" -m pip install -e . -q
    if errorlevel 1 (
        echo [ERROR] Failed to install application.
        echo Check logs\launcher.log
        ( echo %date% %time% FATAL: pip install failed ) >> "%LOG_FILE%"
        pause
        exit /b 1
    )
    ( echo %date% %time% Package installed ) >> "%LOG_FILE%"
    echo Installation complete.
) else (
    :: Verify venv Python works
    "%VENV_PYTHON%" -c "import sys; sys.exit(0)" >nul 2>&1
    if errorlevel 1 (
        echo Virtual environment damaged, recreating...
        rmdir /s /q ".venv" 2>nul
        %PYTHON_CMD% -m venv .venv
        if errorlevel 1 (
            echo [ERROR] Failed to recreate virtual environment.
            pause
            exit /b 1
        )
        "%VENV_PYTHON%" -m pip install -e . -q
        if errorlevel 1 (
            echo [ERROR] Failed to reinstall application.
            pause
            exit /b 1
        )
    )

    :: Verify package installed
    "%VENV_PYTHON%" -c "import calendar_planner" >nul 2>&1
    if errorlevel 1 (
        echo Updating package...
        "%VENV_PYTHON%" -m pip install -e . -q
        if errorlevel 1 goto :fatal
    )
)

:: ============================================================
:: Run application
:: ============================================================
( echo %date% %time% Running: %VENV_PYTHON% -m calendar_planner.app.bootstrap %* ) >> "%LOG_FILE%"

"%VENV_PYTHON%" -m calendar_planner.app.bootstrap %*
set "EXIT_CODE=%errorlevel%"

( echo %date% %time% Exit code: %EXIT_CODE% ) >> "%LOG_FILE%"

if %EXIT_CODE% neq 0 (
    echo.
    echo [ERROR] Program exited with code %EXIT_CODE%.
    echo Details: logs\launcher.log
    pause
)

exit /b %EXIT_CODE%

:fatal
echo [ERROR] Fatal error occurred.
echo Details: logs\launcher.log
( echo %date% %time% FATAL: unrecoverable error ) >> "%LOG_FILE%"
pause
exit /b 1