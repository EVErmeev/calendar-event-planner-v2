# Changelog

Все заметные изменения в `Calendar Event Planner v2`.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
проект следует [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] — 2026-08-04

### Fixed
- Исправлено `send_meeting_invitations` при создании события с участниками:
  `SEND_AND_SAVE_COPY` → `SEND_TO_ALL_AND_SAVE_COPY` (MCP-сервер отклонял
  событие с участниками). Патч зафиксирован в `scripts/exchange_mcp_send_invitations.patch`.
- Единый источник версии: `calendar_planner/version.py` — CLI `--version`,
  метаданные пакета, CHANGELOG и release assets больше не расходятся.

### Added

- Профиль эталонной таблицы `uraldrone_meeting_v1` (схема A:K).
- Длительность события из колонки D.
- Диагностика создания встреч (JSONL + rotating log + санитизация секретов).
- Обработка фактического ответа `create_event` (`created` / `CREATE_REJECTED` /
  `UNKNOWN_RESPONSE`), включая пост-проверку реально созданного события.
- Кнопка «Копировать техническое сообщение» в диалоге диагностики создания.
- Применение Exchange MCP в runtime (bundled/stdio).
- Сохранение EWS-учётных данных через Credential Manager.
- Обязательная зависимость `keyring`.

### Notes

- Полноценный one-click Windows installer и мастер первого запуска появятся в `v1.1.0`.

## [1.0.0] — 2026-08-01

### Added

- Первичный выпуск: анализ таблиц и текстовых источников, разрешение участников,
  формирование и сравнение черновиков событий, dry-run, создание через Exchange MCP.

[1.0.1]: https://github.com/EVErmeev/calendar-event-planner-v2/releases/tag/v1.0.1
[1.0.0]: https://github.com/EVErmeev/calendar-event-planner-v2/releases/tag/v1.0.0