@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

set "PYTHON_CMD="

where python >nul 2>nul
if %errorlevel%==0 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    where py >nul 2>nul
    if %errorlevel%==0 set "PYTHON_CMD=py"
)

if not defined PYTHON_CMD (
    echo [ОШИБКА] Python не найден.
    echo Установите Python 3.11 или новее: https://www.python.org/downloads/
    echo При установке включите "Add Python to PATH".
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if %PY_MAJOR% LSS 3 (
    echo [ОШИБКА] Требуется Python 3.11+, найден Python %PY_VER%.
    echo Обновите Python: https://www.python.org/downloads/
    pause
    exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 11 (
    echo [ОШИБКА] Требуется Python 3.11+, найден Python %PY_VER%.
    echo Обновите Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Создание виртуального окружения .venv ...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение.
        pause
        exit /b 1
    )

    call ".venv\Scripts\activate.bat"
    echo [INFO] Установка зависимостей...
    python -m pip install --upgrade pip -q
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось обновить pip.
        pause
        exit /b 1
    )

    pip install -e . -q
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить приложение.
        pause
        exit /b 1
    )
    echo [INFO] Установка завершена.
) else (
    call ".venv\Scripts\activate.bat"
)

calendar-planner %*
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ОШИБКА] Программа завершилась с кодом %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
