# Runtime validation — Exchange MCP integration

**Проверенный code commit:** `b3c8cd7066b527bf165dea82bd4e978687a79f51` (code) + stdio transport fix  
**Дата:** 01.08.2026

## Exchange MCP

| Параметр | Значение |
|---|---|
| Имя | `exchange` |
| Статус | `connected` |
| Транспорт | local stdio (PowerShell) |
| Executable | `powershell -NoProfile -ExecutionPolicy Bypass -File .../exchange-mcp.ps1` |
| Tools | 13 (`find_events`, `create_event`, `find_emails`, `search_emails`, ...) |

## Tool mapping

| Приложение | Exchange MCP | Совместимость |
|---|---|---|
| `MCP_CALENDAR_FIND_TOOL` | `find_events` | ✅ (с параметрами `days_back`/`days_ahead`) |
| `MCP_CALENDAR_CREATE_TOOL` | `create_event` | ✅ |
| `MCP_DIRECTORY_SEARCH_TOOL` | `search_emails` | ✅ (ограничено) |

## Реализовано

1. `StdioMCPTransport` — stdio JSON-RPC транспорт для локальных MCP серверов
2. Поддержка `MCP_STDIO_COMMAND` в `AppContainer`
3. Парсер текстовых ответов Exchange MCP в `_parse_text_response`
4. Преобразование `start`/`end` → `days_back`/`days_ahead` в `find_events`

## Результаты проверок

| Проверка | Результат |
|---|---|
| `opencode mcp list` | exchange: connected (stdio) |
| MCP подключение | success, 13 tools |
| Календарь чтение | 13 событий найдено |
| Поиск сотрудников | работает |
| Dry-run | payload корректен |
| 7 DUPLICATE / 1 NEW | ✅ |
| Реальных событий | 0 создано |

## Изменения кода

- `calendar_planner/app/stdio_mcp_transport.py` — новый файл
- `calendar_planner/app/container.py` — поддержка stdio
- `calendar_planner/app/settings.py` — `MCP_STDIO_COMMAND`
- `calendar_planner/calendar/mcp_gateway.py` — текст-парсер, days_back/ahead
- `.env.example` — `MCP_STDIO_COMMAND`

## Статус

`ready_for_final_metadata`