# Диагностика и устранение неполадок (Troubleshooting)

## Запуск диагностики

```powershell
.\run_calendar_planner.bat --diagnostics
```

или через меню «Настройки → Диагностика установки».

Диагностика проверяет:

- целостность файлов приложения;
- наличие runtime и запуск Python;
- импорт пакета;
- keyring backend;
- доступ к Credential Manager;
- пользовательский config;
- права на каталог логов;
- наличие встроенного MCP;
- версию MCP и встроенное исправление приглашений;
- инициализацию MCP и `tools/list`;
- `find_events`;
- аутентификацию EWS и ResolveNames;
- согласованность версии релиза.

## Восстановление

Кнопки на экране диагностики:

- «Восстановить Exchange MCP» — берёт файлы из installer cache / подписанного
  release package;
- «Восстановить runtime»;
- «Переустановить runtime dependencies»;
- «Повторно настроить почту»;
- «Сбросить только настройки MCP»;
- «Открыть логи»;
- «Экспортировать диагностику».

## Экспорт диагностики

Создаётся ZIP `CalendarEventPlanner-Diagnostics-<timestamp>.zip`. Включает
версии, manifest, safe settings, результаты подключений, логи. Исключает
пароли, токены, Authorization, NTLM blobs, cookies, полный `.env` и содержимое
Credential Manager.

## Типичные проблемы

### «MCP не подключён»

Проверьте, что в каталоге установки есть `exchange-mcp\server\server.py` и
`exchange-mcp\exchange-mcp.ps1`. Запустите диагностику → «Восстановить
Exchange MCP».

### «Пароль не сохраняется»

Убедитесь, что Windows Credential Manager доступен. Проверьте, что чекбокс
«Запомнить пароль» включён.

### «Создание события отклонено»

Если раньше встречалась ошибка `'send_meeting_invitations' 'SendAndSaveCopy'
must be one of ...` — она исправлена встроенной версией MCP
(`SEND_TO_ALL_AND_SAVE_COPY`). Убедитесь, что используется bundled MCP, а не
старый `%LOCALAPPDATA%\exchange-mcp`.