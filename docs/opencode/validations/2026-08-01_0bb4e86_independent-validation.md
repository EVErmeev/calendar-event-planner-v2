# Независимая валидация commit 0bb4e86 — Windows BAT и CI

**Репозиторий:** `EVErmeev/calendar-event-planner-v2`  
**Pull Request:** `#1 Implement initial audit fixes`  
**Проверенный code commit:** `0bb4e86d1f3ad1384a5ca89ca3770a4c0bdb2913`  
**Дата проверки:** 01.08.2026

## Вердикт

```text
REQUEST_CHANGES
PR не готов к слиянию
```

BAT-файл не работает. Windows smoke job падает с `UnicodeEncodeError`. Coverage gate сломан.

# P0 дефекты

1. UnicodeEncodeError в --help из-за отсутствия PYTHONUTF8=1
2. Небезопасный поиск Python через where + %errorlevel% внутри блоков
3. Окно закрывается при ошибке
4. Нет --smoke-gui режима
5. Coverage gate: int() на float line-rate

# Вердикт: REQUEST_CHANGES