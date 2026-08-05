# Exchange MCP upstream (обслуживание вендорного компонента)

## Что это

Календарное приложение использует встроенный Exchange MCP для чтения/записи
календаря через EWS. Компонент вендорится в `vendor/exchange_mcp/`.

## Upstream

- Источник: внутренний dist-сервер `https://mcp.1bitai.ru/dist` (area
  `exchange`).
- Обёртка: `%LOCALAPPDATA%\exchange-mcp\exchange-mcp.ps1`.
- Модуль: `server/server.py` + `server/pyproject.toml`.

## Встроенное исправление

| Upstream | Bundled |
|---|---|
| `SEND_AND_SAVE_COPY` | `SEND_TO_ALL_AND_SAVE_COPY` |

`SEND_AND_SAVE_COPY` не является допустимым значением для
`CalendarItem.save(send_meeting_invitations=...)`. Допустимые:
`['SendOnlyToAll', 'SendToAllAndSaveCopy', 'SendToNone']`. Поэтому upstream
отклонял событие с участниками. Вендорный bundle несёт исправление заранее.

## Версионирование

- Bundle: `1.0.0-cep.1`.
- Upstream commit pinned: `calendar_planner/app/component_manifest.py`.

## Обновление вендора

1. Взять pinned upstream.
2. Проверить upstream SHA.
3. Применить встроенное исправление (если ещё не применено).
4. Проверить LICENSE и attribution (`vendor/exchange_mcp/README.md`,
   `LICENSE.md`, `THIRD_PARTY_NOTICES.md`).
5. Прогнать `tests/test_bundled_mcp.py`.
6. Обновить VERSION и manifest.

## Лицензия

Upstream — внутренний компонент «Первый Бит». Права на редистрибуцию должны
быть подтверждены владельцем до релиза. См.
`vendor/exchange_mcp/LICENSE.md`.