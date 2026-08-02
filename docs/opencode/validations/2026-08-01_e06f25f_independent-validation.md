# Независимая валидация PR №1 — commit e06f25f

**Репозиторий:** `EVErmeev/calendar-event-planner-v2`  
**PR:** `#1 Implement initial audit fixes`  
**Проверенный code commit / текущий head:** `e06f25f0c3ab4b96ebe5c50cbbf0e9f0de63a235`  
**Дата:** 01.08.2026

## Вердикт

```text
REQUEST_CHANGES
PR пока не сливать
```

Большая часть последнего ТЗ выполнена. Подтверждены:

- Xvfb добавлен;
- GUI-тесты Stage 4/5 проходят в test jobs;
- Stage 4 явно принимает настройки;
- из Stage 5 удалены чужие participant-параметры;
- dry-run и real-create разделены в интерфейсе;
- `python-dateutil` исправлен;
- global coverage gate `75%` добавлен;
- MCP initialized notification теперь может прервать connect;
- контрольный сценарий `7 DUPLICATE + 1 NEW` сохранён;
- test jobs Python 3.11, 3.12 и 3.13 успешны;
- E2E Dry-Run успешен.

Однако есть блокирующие проблемы.

# P0

## P0-01. Общий CI красный

Lint job завершился ошибкой:

```text
tests/test_mcp_gateway.py
I001 — import block is unsorted
F401 — pytest imported but unused
```

Отчёт OpenCode «Ruff: All checks passed» не соответствует GitHub Actions.

Исправление:

```bash
ruff check tests/test_mcp_gateway.py --fix
ruff check calendar_planner/ tests/
```

После push все CI jobs должны быть зелёными.

## P0-02. Real create callback падает до создания

В `MainWindow._make_real_create_callback()`:

```python
if isinstance(
    calendar_gw,
    self.container.__class__.__module__.split(".")[0],
):
```

Второй аргумент `isinstance()` является строкой (`"calendar_planner"`), а должен быть типом или tuple типов.

Результат:

```text
TypeError: isinstance() arg 2 must be a type
```

Кнопка реального создания не работает.

Исправление:

```python
from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

if not isinstance(calendar_gw, MCPCalendarGateway):
    ...
```

Дополнительно проверить:

```python
calendar_gw.is_available()
```

Лучше использовать явное свойство gateway kind/capability, а не распознавать module string.

## P0-03. Payload не показывается до реального создания

Текущая последовательность:

```python
result = creator.create_one(draft)
payload = creator.build_payload(draft)
```

Сначала происходит создание, затем строится payload. При этом `payload` далее не используется.

Это не выполняет требование:

```text
показать фактический payload до отправки
```

Исправление:

1. построить payload;
2. проверить payload;
3. показать payload пользователю;
4. получить отдельное подтверждение;
5. только затем вызвать `create_one()`.

## P0-04. Creation results не сохраняются в RunSession

Callback пишет данные в динамическое поле:

```python
controller._creation_results
```

Но `StageController.__init__()` не инициализирует это поле.

`StageController.create_session()` не записывает его в:

```text
session.creation_results_json
creation_results.json
```

`load_session()` его также не восстанавливает.

Заявление «результаты сохраняются в session» не подтверждено.

# P1

## P1-01. Package smoke test маскирует ошибку

CI содержит:

```bash
calendar-planner --help || true
```

Любое падение команды считается успешным.

Исправить на:

```bash
calendar-planner --help
```

Если основной entrypoint открывает GUI, создать отдельный CLI help entrypoint либо проверять импорт/версию без запуска GUI.

## P1-02. Per-module coverage targets не закреплены

CI проверяет только:

```text
TOTAL >= 75%
```

Цели:

```text
mcp_transport >= 80%
mcp_gateway >= 80%
creator >= 90%
```

не являются gates и могут незаметно снизиться.

Добавить отдельную проверку coverage XML/JSON либо специализированный script.

## P1-03. Ruff-ignore скрывает потенциальную ошибку

В `pyproject.toml` добавлен ignore:

```text
F823 — undefined local
```

В real-create callback `messagebox` используется до локального import в ветке `container is None`.

Не следует глобально отключать F823. Перенести import в начало модуля/функции и убрать F823 из ignore.

# Итог

```text
Тестовая матрица: PASS
E2E: PASS
Lint: FAIL
Real create: BROKEN
Session creation results: NOT PERSISTED
Package smoke test: MASKED
```

## Критерии следующей проверки

1. Все CI jobs зелёные.
2. Ruff 0 errors без глобального F823 ignore.
3. Real-create callback не вызывает TypeError.
4. Payload показан до отправки.
5. Creation results сохраняются и восстанавливаются через RunSession.
6. `calendar-planner --help` выполняется без `|| true`.
7. Контрольный сценарий остаётся `7 DUPLICATE + 1 NEW`.
8. В тестах создаётся 0 реальных событий.