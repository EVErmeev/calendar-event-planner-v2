# Разработка (Developer Setup)

Этот документ для разработчиков. Пользовательская инструкция — в
`INSTALL_WINDOWS.md`.

## Требования

- Python 3.11+;
- Git;
- (опционально) OpenCode и skills — см. `DEVELOPER_OPENCODE_SETUP.md`.

## Локальный checkout

```bash
git clone https://github.com/EVErmeev/calendar-event-planner-v2.git
cd calendar-event-planner-v2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Конфигурация для разработки

```bash
copy .env.example .env
```

`.env` используется только при `APP_ENV=development`. В production используется
`settings.json` (см. `docs/PRIVACY_AND_CREDENTIALS.md`).

## Запуск

```bash
run_calendar_planner.bat
```

## Тесты / lint

```bash
python -m pytest
ruff check calendar_planner/ tests/ scripts/
python scripts/mypy_gate.py
```

## Build

```bash
powershell -ExecutionPolicy Bypass -File scripts/build_portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify_distribution.ps1 -ZipPath dist\CalendarEventPlanner-portable-v1.1.0.zip
```