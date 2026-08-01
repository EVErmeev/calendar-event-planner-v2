# ТЗ OpenCode: завершение PR №1 после независимой валидации commit e06f25f

## 1. Общие сведения

**Репозиторий:**

```text
EVErmeev/calendar-event-planner-v2
```

**Рабочая ветка:**

```text
fix/initial-audit-findings
```

**Pull Request:**

```text
https://github.com/EVErmeev/calendar-event-planner-v2/pull/1
```

**Проверенный code commit:**

```text
e06f25f0c3ab4b96ebe5c50cbbf0e9f0de63a235
```

**Основание для работ:**

```text
docs/opencode/validations/2026-08-01_e06f25f_independent-validation.md
```

## 2. Цель работ

Устранить последние блокирующие замечания независимой валидации, обеспечить полностью зелёный CI, исправить реальное создание календарного события, обеспечить сохранение результатов создания в сессию и добавить удобный Windows `.bat`-файл для запуска программы.

После выполнения PR должен быть готов к повторной независимой проверке.

## 3. Правила выполнения

1. Не изменять уже подтверждённый контрольный сценарий:
   - 8 кандидатов;
   - 7 `DUPLICATE`;
   - 1 `NEW`;
   - 7 дублей заблокированы;
   - 1 новая встреча проходит dry-run;
   - 0 реальных событий создаётся в автоматических тестах.
2. Не отключать тесты и не переводить их в `xfail` или `skip` для получения зелёного CI.
3. Не маскировать ошибки конструкциями:
   - `|| true`;
   - `continue-on-error`, кроме необязательной отправки coverage;
   - пустыми `except`;
   - глобальными исключениями Ruff для реально существующих ошибок.
4. Не создавать реальные календарные события в CI и автоматических тестах.
5. Для каждого исправления добавить или актуализировать тест, воспроизводящий соответствующий сценарий.
6. После исправлений обновить validation report, но metadata commit создавать только после независимой проверки нового code commit.

# 4. Обязательные исправления

## 4.1. Исправить Ruff и общий CI

В текущем CI lint job падает в:

```text
tests/test_mcp_gateway.py
```

Ошибки:

```text
I001 — import block is unsorted
F401 — pytest imported but unused
```

Необходимо:

1. Удалить неиспользуемый импорт `pytest`, если он действительно не нужен.
2. Отсортировать imports.
3. Запустить:

```bash
ruff check calendar_planner/ tests/
```

4. Добиться нулевого количества ошибок Ruff.
5. Не добавлять данные ошибки в глобальный ignore.

### Критерий приёмки

```text
Ruff: All checks passed
CI lint job: success
```

## 4.2. Исправить проверку реального MCP gateway

В `_make_real_create_callback()` используется некорректная конструкция:

```python
isinstance(calendar_gw, self.container.__class__.__module__.split(".")[0])
```

Второй аргумент `isinstance()` является строкой, поэтому callback завершается с `TypeError`.

Необходимо:

1. Использовать явный тип gateway:

```python
from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway
```

2. Проверить:

```python
isinstance(calendar_gw, MCPCalendarGateway)
```

3. Дополнительно проверить доступность:

```python
calendar_gw.is_available()
```

4. Для fixture, unavailable или другого gateway реальное создание должно блокироваться с понятным сообщением.
5. Не определять тип gateway через имя модуля, строку или имя класса.

## 4.3. Исправить порядок реального создания события

Сейчас событие создаётся до того, как пользователь видит payload.

Требуемая последовательность:

```text
1. Повторная проверка дубля.
2. Проверка актуальности match hash.
3. build_payload().
4. validate_payload().
5. Показ полного payload пользователю.
6. Отдельное финальное подтверждение.
7. EventCreator(..., dry_run=False).
8. Отображение результата.
9. Сохранение результата в сессию.
```

## 4.4. Сохранять результаты создания в сессию

В `StageController` необходимо явно добавить:

```python
self._creation_results: list[dict] = []
```

Реализовать методы:

```python
add_creation_result(result: dict) -> None
get_creation_results() -> list[dict]
clear_creation_results() -> None
```

Не использовать прямое динамическое присваивание.

## 4.5. Исправить package smoke test

В CI сейчас используется:

```bash
calendar-planner --help || true
```

Это маскирует ошибку.

Необходимо оставить:

```bash
calendar-planner --help
```

без `|| true`.

## 4.6. Убрать глобальное исключение Ruff F823

Из `pyproject.toml` удалить:

```text
F823
```

## 4.7. Закрепить coverage gates

Общий порог:

```text
TOTAL >= 75%
```

Дополнительно закрепить пороги:

```text
calendar_planner/app/mcp_transport.py >= 80%
calendar_planner/calendar/mcp_gateway.py >= 80%
calendar_planner/calendar/creator.py >= 90%
```

# 5. Создание Windows BAT-файла для запуска программы

В корне репозитория создать:

```text
run_calendar_planner.bat
```

BAT-файл должен:
- запускать программу двойным кликом в Windows;
- находить `python` или `py`;
- проверять Python 3.11+;
- создавать `.venv` при первом запуске;
- устанавливать приложение;
- запускать официальный entrypoint;
- передавать аргументы через `%*`;
- показывать понятную ошибку при сбое;
- не содержать токены, пароли и персональные пути.

## 6. Тестирование BAT

В GitHub Actions Windows job добавить:

```yaml
windows-smoke:
  runs-on: windows-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Run BAT help smoke test
      shell: cmd
      run: run_calendar_planner.bat --help
```

BAT при `--help` не должен зависать на GUI и не должен требовать ручного ввода.
