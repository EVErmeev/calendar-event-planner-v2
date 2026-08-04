# Legacy mypy errors — controlled baseline

Документ фиксирует состояние типизации на момент релиза `v1.0.1`.

## Решение

Для `v1.0.1` принят управляемый baseline: существующие (legacy) ошибки mypy не
исправляются в рамках release-коммита (они вне объёма релиза и несут лишний
риск). Вместо этого:

- новые и изменённые в PR файлы проверяются mypy жёстко (0 ошибок);
- legacy-модули имеют временный per-module baseline только по конкретным кодам
  ошибок, присутствовавшим на момент фиксации;
- глобальное `ignore_errors = true` НЕ используется;
- CI mypy-гейт падает, если число baseline-ошибок выросло или появилась новая
  ошибка в новом/изменённом файле.

## Baseline (зафиксирован)

- Дата фиксации: 2026-08-04
- Baseline commit SHA (функциональный): `68c8f32eac596be29ac31bf2a8bb37f8ec08b521`
- Всего ошибок: **69**
- Файлов: **16**

### Файлы с legacy-ошибками (baseline)

| Модуль | Кол-во ошибок |
|---|---|
| `ui/stages/stage4_participants.py` | 13 |
| `ui/stages/stage5_enrichment.py` | 11 |
| `ui/stages/stage6_creation.py` | 6 |
| `source/adapters/file_adapters.py` | 6 |
| `cli/__init__.py` | 4 |
| `extraction/structured.py` | 5 |
| `app/stdio_mcp_transport.py` | 3 |
| `app/mcp_transport.py` | 4 |
| `extraction/audit.py` | 3 |
| `ui/stages/stage3_comparison.py` | 2 |
| `ui/main_window.py` | 4 |
| `calendar/creator.py` | 1 |
| `source/registry.py` | 1 |
| `calendar/mcp_gateway.py` | 1 |
| `domain/validation.py` | 1 |
| `ui/event_editor.py` | 1 |

### Коды ошибок в baseline

`misc`, `arg-type`, `union-attr`, `assignment`, `index`, `attr-defined`,
`valid-type`, `call-overload`, `operator`, `var-annotated`, `dict-item`.

## Механизм контроля (mypy.ini)

Legacy-модули перечислены в `mypy.ini` через `disable_error_code` по конкретным
кодам. Новые/изменённые файлы НЕ должны попадать в этот список — их проверка
строгая.

## Гейт в CI

CI-гейт:
1. `mypy --config-file mypy.ini calendar_planner/` — baseline-модули
   приглушены по кодам, остальное проверяется строго.
2. Отдельная команда жёстко проверяет release/новые файлы (0 ошибок).

Любое появление новой ошибки в новом/изменённом файле или рост baseline —
красный прогон.

## Что НЕ относится к baseline

`calendar_planner/version.py`, `calendar_planner/__init__.py`,
`calendar_planner/app/bootstrap.py`, `tests/` — проверяются строго (0 ошибок).

## Задача на устранение

Отдельная задача «Устранение legacy mypy errors»: исправить 69 ошибок в 16
модулях выше, затем удалить их из `mypy.ini`. Не выполнять в release-коммите
`v1.0.1`.