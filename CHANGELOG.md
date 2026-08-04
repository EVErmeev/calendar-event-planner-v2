# Changelog

Все заметные изменения в `Calendar Event Planner v2`.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
проект следует [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v1.1.0 (Windows installer)

### Added

- Встроенный (bundled) Exchange MCP в `vendor/exchange_mcp/` со встроенным
  исправлением `SEND_TO_ALL_AND_SAVE_COPY`.
- Управляемая конфигурация `settings.json` (`%LOCALAPPDATA%\CalendarEventPlanner`)
  + миграция из dev `.env`.
- Единый источник версии `calendar_planner/version.py`.
- Component manifest (`component-manifest.json`).
- Логика мастера первого запуска (EWS, Credential Manager, ResolveNames,
  bundled MCP, timezone, итог).
- Диагностика установки и безопасный диагностический bundle (без секретов).
- Foundation обновления/отката (backup/restore).
- Build-скрипты: `build_runtime`, `build_exchange_mcp_bundle`, `build_portable`,
  `build_installer`, `verify_distribution`, `smoke_clean_windows`.
- Windows installer (Inno Setup) — `CalendarEventPlannerSetup-v1.1.0.exe`.
- GitHub Actions: `installer-ci.yml` и `release.yml`.
- Документация пользователя и разработчика.
- `THIRD_PARTY_NOTICES.md` и лицензии вендорного компонента.

### Notes

- Installer v1.1.0 пока не подписан Authenticode (до появления сертификата).
- Права на редистрибуцию вендорного Exchange MCP должны быть подтверждены.

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
[Unreleased]: https://github.com/EVErmeev/calendar-event-planner-v2/compare/v1.0.1...HEAD