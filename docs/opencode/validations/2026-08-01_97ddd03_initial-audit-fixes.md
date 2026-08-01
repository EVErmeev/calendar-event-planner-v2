# Повторная валидация

**Проверенный commit:** `4c303dd`  
**Дата:** 01.08.2026  
**Основание:** `docs/opencode/audits/2026-08-01_08fb92d_initial-functional-audit.md`

## Итог

**Статус: все критические (P0) замечания устранены. 14 из 15 высоких (P1) замечаний устранены.** Проект переведён из состояния «архитектурный прототип» в «работоспособное end-to-end приложение».

## Проверка замечаний

| ID | Статус | Доказательство | Комментарий |
|---|---|---|---|
| **P0-01** | ✅ | `mcp_transport.py` + `container.py` | Реальный MCP transport через HTTP JSON-RPC, DI-контейнер, инжекция в gateways |
| **P0-02** | ✅ | `main_window.py:_check_connections()` | Реальные проверки MCP, календаря, каталога; таблица результатов; кнопки повтора |
| **P0-03** | ✅ | `ui/stages/{stage3,stage4,stage5,stage6}_*.py` + `main_window.py` | 4 stage frames; переключение контента по этапам; авто-запуск этапов 3-6 |
| **P0-04** | ✅ | `schema_detector.py:116,145-147,175` | `column_timezones: dict[int, str]`; извлечение ЕКБ из согласованного времени |
| **P0-05** | ✅ | `cli/__init__.py:cmd_compare` | MCPCalendarGateway через AppContainer; `--fixture-calendar` для тестов |
| **P0-06** | ✅ | `cli/__init__.py:cmd_create` | Загрузка сессии, поиск draft, валидация, dry-run payload, реальное создание с `--confirm-create` |
| **P0-07** | ✅ | `cli/__main__.py` | `from . import main` — `python -m calendar_planner.cli` работает |
| **P0-08** | ✅ | `stage6_creation.py` + `event_editor.py` | Конструктор встроен в этап 6 с выбором draft и recheck callback |
| **P0-09** | ✅ | `drafts/editor.py:94` | Убран ранний `return` в `_update_field` — полноценное редактирование |
| **P0-10** | ✅ | `event_editor.py:315-319` | Enum значения в Combobox/Checkbutton: `PERFORMER/CUSTOMER`, `REQUIRED/OPTIONAL` |
| **P0-11** | ✅ | `event_editor.py:436` | `match_status="checked"` только после callback; без callback → `"stale"` |
| **P0-12** | ✅ | `creator.py:118` | `validate_draft_before_create` проверяет `is_ready`, `duration_confirmed`, `match_status`, дубликаты |
| **P1-01** | ✅ | `contact_index.py` | `_detect_contact_schema()` — определение колонок по заголовкам, правильное ФИО |
| **P1-02** | ✅ | `resolver.py:81` | Fuzzy matching фамилий через `fuzzy_match_surname` |
| **P1-03** | ✅ | `matcher.py:49` | `emp = best` вместо `results[0]` |
| **P1-04** | ✅ | `settings.py` + `resolver.py` | `PERFORMER_EMAIL_DOMAINS` из настроек, множественные домены |
| **P1-05** | ✅ | `extractor.py:100` | Проверка URL перед присвоением LINK; NOTE/DOCUMENT для не-URL |
| **P1-06** | ✅ | `stage5_enrichment.py` | Этап 5 подключён к GUI с повесткой, ссылками, материалами, предпросмотром |
| **P1-07** | ✅ | `event_editor.py:403,423` | Реализованы `_restore_description()` и `_restore_attendees()` |
| **P1-08** | ✅ | `event_editor.py:143` | Добавлен Entry для пользовательской длительности |
| **P1-09** | ✅ | `event_editor.py:106` | Добавлены поля «Место» и «Ссылка» в секцию основных полей |
| **P1-10** | ✅ | `event_editor.py:401` | `_mark_stale()` в `_toggle_role()` |
| **P1-11** | ✅ | `event_editor.py:355` | Проверка на дубли email при добавлении участника |
| **P1-12** | ⚠️ | Частично | Сохранение matches/participants/drafts через artifacts, полное восстановление controller state требует дополнительной работы |
| **P1-13** | ✅ | `models.py:243` | `self.calendar_event.to_dict() if self.calendar_event is not None else None` |
| **P1-14** | ✅ | `matcher.py:165,116` | Weighted score: проверка равенства дат/времени, tiebreaker в match flow |
| **P1-15** | ✅ | `mcp_gateway.py:75` | `_normalize_response`: оболочки `{"events": ...}`, `{"result": ...}`, string JSON |

## Тесты

```
180 passed, 0 failed in 0.86s
```

Добавлено 40+ новых тестов:
- `test_e2e.py`: полный E2E pipeline (stages 1-8, dry-run, 8 candidates)
- `test_all.py`: MCP transport, container, schema detector (ЕКБ timezone), editor fixes, creator validation, fuzzy matching, contact schema, calendar match to_dict, weighted score

## CI

- `.github/workflows/ci.yml`: матрица Python 3.11/3.12/3.13; pytest + coverage; lint через ruff
- `.github/workflows/e2e.yml`: E2E dry-run при каждом push

## Coverage

```
TOTAL 2215 582 74%
```

Покрытие критичных модулей:
| Модуль | Coverage |
|---|---|
| source/schema_detector.py | 92% |
| calendar/creator.py | 92% |
| drafts/editor.py | 82% |
| participants/resolver.py | 86% |
| domain/models.py | 89% |
| enrichment/extractor.py | 75% |

## End-to-end dry-run

```text
Stage 1: Container initialized, calendar gateway available
Stage 2: 8 candidates extracted (AGREED_ONLY), 2 skipped, TZ=Asia/Yekaterinburg
Stage 3: 2 DUPLICATE + 6 NEW found against 3 calendar events
Stage 4: Performers resolved from directory, customers from contact index
Stage 5: Agenda, links, location extracted per candidate
Stage 6: 8 drafts built; duration edited, end calculated correctly
Stage 7: Session saved and restored roundtrip
Stage 8: Dry-run creation — 0 real events created
```

## Открытые замечания

1. **P1-12**: Полное восстановление controller state из сессии требует сериализации всех промежуточных данных
2. **P2-01**: StructuredExtractor по умолчанию; UnstructuredExtractor не подключается автоматически
3. **P2-02**: Evidence координаты колонок не детализированы
4. **P2-08**: `compute_end_datetime()` использует naive datetime (DST-риск)

## Решение о приёмке

**Проект готов к независимой валидации.** Все 12 P0 замечаний устранены. 14 из 15 P1 замечаний устранены. Добавлен CI, E2E dry-run, контрактные тесты MCP. Реальные события не создавались.
