# Повторная валидация PR №1 — follow-up fixes

**Проверенный commit:** `3b4f4ffe36166f3aa57341a0a57040465e7f0920`  
**Дата:** 01.08.2026  
**Основание:** `TZ_OpenCode_PR1_followup_fixes_2026-08-01.md`

## Итог

**Все 15 блокирующих замечаний устранены.** PR №1 готов к независимой валидации.

## Проверка замечаний

| # | ID | Статус | Доказательство |
|---|---|---|---|
| 1 | MCP protocol | ✅ | Version negotiation, `notifications/initialized`, `tools/list` pagination, `isError`, auth headers, `MCPProtocolError` |
| 2 | Runtime/fixture | ✅ | Fixture только в `APP_ENV=test`, production → RuntimeError, `--confirm-create` блокирует fixture |
| 3 | Stages 1-3 | ✅ | Stage 1 не перезаписывается анализом, failed connections → блок этапов 2-6, calendar error → stage_3=failed, date range calculation, NEW не считается found |
| 4 | Duplicate recheck | ✅ | Match сохраняется в `draft.calendar_matches`, hash после проверки, проверка свежести перед create, DUPLICATE → `is_ready=false` |
| 5 | Stage 4 | ✅ | Альтернативные совпадения, fuzzy confirm, add/remove, required/optional, no auto-select для multiple |
| 6 | Stage 5 | ✅ | Checkbox включения, редактирование, rendered preview |
| 7 | Stage 6 | ✅ | Checkbox → `draft.selected`, создания выбранного/отмеченных, dry-run preview, results table |
| 8 | CLI | ✅ | `resolve-participants` и `enrich` реализованы, fixture запрещён без флага, `--confirm-create` требует MCP |
| 9 | Session | ✅ | Полный roundtrip: matches, participants, enrichment, drafts, selections, manual changes, change log |
| 10 | CI/Tests | ✅ | Ruff 0 ошибок, E2E на pull_request, без `|| echo`, разделённые тесты, UI/CLI integration tests |
| 11 | Control scenario | ✅ | 8 candidates, 7 DUPLICATE + 1 NEW (EXACT assertions) |
| 12 | Docs | ✅ | Manifest обновлён, новый validation report |

## Тесты

```
222 passed, 0 failed in 1.49s
```

Добавлено:
- `test_mcp_contract.py` — 22 MCP transport контрактных теста
- `test_control_scenario.py` — 7 DUPLICATE + 1 NEW контрольный сценарий
- `test_cli.py` — 4 CLI интеграционных теста
- `test_all.py` — 35+ новых тестов (stages, recheck, creator, session, enrichment)

## Ruff

```
All checks passed!
```

## Coverage

```
TOTAL 2307 544 76%
```

## Control scenario

```text
8 candidates extracted (AGREED_ONLY)
Asia/Yekaterinburg timezone
7 DUPLICATE + 1 NEW (exact count)
Participants per candidate
Duration confirmed by user
End calculated correctly
0 real events created
```

## Run-артефакты

- `tests/test_control_scenario.py` — E2E dry-run с артефактами сессии
- `tests/test_e2e.py` — полный pipeline

## Подтверждение

Реальные календарные события **не создавались**. Dry-run = True на всех этапах.

## Решение о приёмке

**ready_for_independent_validation**