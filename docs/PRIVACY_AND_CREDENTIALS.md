# Приватность и учётные данные (Privacy & Credentials)

## Хранение пароля

Пароль от EWS хранится **только** в Windows Credential Manager. Он **не**
попадает в:

- `settings.json`;
- `.env`;
- реестр Windows в открытом виде;
- логи;
- диагностический bundle;
- installer answer files.

## Управляемая конфигурация

Пользовательские настройки хранятся в
`%LOCALAPPDATA%\CalendarEventPlanner\config\settings.json`. Пароля там нет —
только безопасные поля (endpoint, username, timezone, MCP tool names).

## Диагностический bundle

`CalendarEventPlanner-Diagnostics-<timestamp>.zip` исключает:

- пароли;
- токены;
- `Authorization` заголовки;
- NTLM blobs;
- cookies;
- полный `.env`;
- содержимое Credential Manager.

## Миграция

При первом запуске новой версии предлагается «Импортировать существующие
настройки». Импортируются только безопасные поля. Пароль не переносится через
чтение/запись файла — используется существующая запись в Credential Manager,
если она доступна.