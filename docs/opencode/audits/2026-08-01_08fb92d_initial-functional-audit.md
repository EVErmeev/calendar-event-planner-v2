# Аудит репозитория `calendar-event-planner-v2`

**Репозиторий:** `EVErmeev/calendar-event-planner-v2`  
**Проверенный commit:** `08fb92dfeb8b038cbce07f34eeaf82e6e98ca97c`  
**Дата аудита:** 01.08.2026  
**Формат проверки:** статический аудит исходного кода, тестов, конфигурации и GitHub CI/status checks.

## 1. Итоговый вердикт

Репозиторий **не готов к функциональной приёмке и реальной работе с календарём**.

Текущая версия представляет собой архитектурный каркас и набор частично реализованных доменных компонентов. Некоторые изолированные функции — нормализация времени, извлечение строк таблицы, формирование payload и отдельные редакторы — написаны, однако единый пользовательский сценарий этапов 1–6 отсутствует.

Главные блокирующие проблемы:

1. В штатном приложении отсутствует реальное MCP-подключение.
2. Главное окно фактически выполняет только чтение источника и структурированное извлечение.
3. Этапы сравнения, участников, дополнительных данных и создания не подключены к GUI.
4. Часовой пояс `ЕКБ` из колонки согласованного времени не сохраняется из-за незавершённого метода.
5. CLI сравнивает с пустым fixture-календарём, а команда создания только печатает сообщение об успехе.
6. Конструктор события существует как отдельный класс, но не используется главным окном.
7. В конструкторе есть ошибки, блокирующие нормальное редактирование и добавление участников.
8. Полная сессия не сохраняется.
9. GitHub Actions и status checks отсутствуют.
10. Критичные UI и CLI исключены из coverage.

---

# 2. Что реализовано положительно

## 2.1. Доменная модель

Созданы отдельные модели:

- `MeetingCandidate`;
- `CalendarEvent`;
- `CalendarMatch`;
- `CandidateParticipants`;
- `DescriptionItem`;
- `FinalEventDraft`;
- `DraftField`;
- `RunSession`.

Это правильное направление: бизнес-данные не хранятся исключительно в виджетах GUI.

## 2.2. Разделение модулей

Проект разделён на:

- source adapters;
- extraction;
- calendar;
- participants;
- enrichment;
- drafts;
- session;
- UI;
- CLI.

Архитектурная структура в целом соответствует целевому ТЗ.

## 2.3. Базовая нормализация времени

Есть поддержка:

- `Z`;
- ISO offset;
- IANA timezone;
- части Windows timezone;
- преобразования в UTC;
- `Asia/Yekaterinburg`.

Изолированный `CalendarMatcher` сравнивает `utc_datetime`, что является правильным принципом.

## 2.4. Политика `AGREED_ONLY`

`StructuredExtractor` действительно не использует плановые дату и время, если выбран `AGREED_ONLY`.

## 2.5. Подтверждение продолжительности

В модели предусмотрены:

```text
duration_minutes
duration_confirmed
```

Исходный кандидат без продолжительности не считается готовым.

## 2.6. Dry-run

`EventCreator` и fixture gateway поддерживают `dry_run`.

---

# 3. Критические дефекты P0

## P0-01. Реальный MCP transport отсутствует

### Файлы

```text
calendar_planner/app/bootstrap.py
calendar_planner/calendar/mcp_gateway.py
calendar_planner/participants/directory_gateway.py
```

### Проблема

`MCPCalendarGateway` работает только если в конструктор передана готовая Python-функция:

```python
MCPCalendarGateway(mcp_call_function=...)
```

Штатный bootstrap:

- не создаёт MCP client;
- не подключается к `MCP_SERVER_URL`;
- не получает tools;
- не внедряет функцию вызова;
- не создаёт calendar gateway;
- не создаёт directory gateway.

Настройки `MCP_SERVER_URL` и tool names сами по себе не используются для установления соединения.

### Последствие

В реальном приложении нельзя:

- прочитать календарь;
- найти сотрудников;
- создать событие.

### Исправление

Реализовать отдельный MCP client/transport:

```text
MCPClient
MCPConnectionManager
MCPToolRegistry
```

Bootstrap должен собирать зависимости и передавать реальные gateways в orchestrator/UI.

---

## P0-02. Этап 1 не проверяет подключения

### Файл

```text
calendar_planner/ui/main_window.py
```

### Проблема

После анализа источника выполняется:

```python
set_stage_success("stage_1")
set_stage_success("stage_2")
```

При этом:

- MCP не проверяется;
- календарь не читается;
- каталог сотрудников не проверяется;
- права создания не проверяются.

CLI `check-connections` также только печатает значения настроек.

### Последствие

Пользователь получает ложный успешный статус подключения.

### Исправление

Этап 1 должен выполнять реальные calls:

```text
MCP initialize/list tools
calendar find events
directory test search
calendar create permission check without real creation
```

---

## P0-03. Главное окно не реализует мастер из шести этапов

### Файл

```text
calendar_planner/ui/main_window.py
```

### Проблема

Главное окно содержит:

- поле источника;
- текстовую область;
- список названий этапов;
- кнопки «Назад/Далее»;
- кнопку анализа.

Кнопки «Назад/Далее» изменяют только `current_stage` и выделение подписи. Содержимое рабочей области не меняется.

Отсутствуют реальные экраны:

- сравнения с календарём;
- участников;
- дополнительных данных;
- списка черновиков;
- конструктора;
- создания.

### Последствие

Пользовательский сценарий заканчивается после этапа 2.

### Исправление

Создать отдельные stage frames и orchestrator:

```text
ConnectionsFrame
ExtractionFrame
CalendarComparisonFrame
ParticipantsFrame
EnrichmentFrame
FinalDraftsFrame
```

---

## P0-04. Timezone `ЕКБ` из согласованной колонки фактически теряется

### Файлы

```text
calendar_planner/source/schema_detector.py
calendar_planner/extraction/structured.py
```

### Проблема

Метод:

```python
TableSchemaDetector._update_timezone_for_col()
```

содержит только:

```python
pass
```

При обнаружении timezone в заголовке колонки согласованного времени код вызывает этот пустой метод.

Дополнительно `header_timezone` устанавливается только в ветке согласованной даты, но в целевом шаблоне `ЕКБ` находится в заголовке времени.

### Последствие

Для фактического шаблона кандидат может получить:

```text
timezone = None
```

`CalendarMatcher.match()` при отсутствии timezone возвращает `None`, поэтому сравнение не выполняется.

### Исправление

Хранить timezone отдельно для каждой временной колонки:

```python
column_timezones: dict[int, str]
```

Для `agreed_time_col` присваивать timezone из её заголовка.

---

## P0-05. CLI сравнения всегда использует пустой fixture-календарь

### Файл

```text
calendar_planner/cli/__init__.py
```

### Проблема

`cmd_compare` создаёт:

```python
FixtureCalendarGateway()
```

без fixture path.

Получается:

```text
0 событий календаря
```

Все кандидаты будут новыми.

### Исправление

В штатном режиме использовать `MCPCalendarGateway`.

Fixture разрешить только с явным ключом:

```text
--fixture-calendar=<path>
```

---

## P0-06. CLI создания не создаёт событие

### Файл

```text
calendar_planner/cli/__init__.py
```

### Проблема

Команда `create`:

- не загружает сессию;
- не ищет draft;
- не валидирует draft;
- не проверяет stale match;
- не формирует payload;
- не вызывает gateway.

Она только печатает:

```text
Событие создано
```

### Последствие

Ложный положительный результат.

### Исправление

Команда должна использовать общий application service:

```text
CreateEventUseCase
```

и возвращать фактический ID/URL или dry-run payload.

---

## P0-07. Запуск CLI из README не работает

### Файлы

```text
README.md
calendar_planner/cli/
```

### Проблема

README предлагает:

```bash
python -m calendar_planner.cli
```

Но в пакете отсутствует:

```text
calendar_planner/cli/__main__.py
```

Для запуска package через `python -m` нужен `__main__.py`.

### Исправление

Добавить:

```python
from . import main

if __name__ == "__main__":
    main()
```

---

## P0-08. Конструктор события не подключён к приложению

### Файлы

```text
calendar_planner/ui/event_editor.py
calendar_planner/ui/main_window.py
```

### Проблема

`EventEditorFrame` определён, но нигде не создаётся и не встраивается в главное окно.

### Последствие

Пользователь не может открыть и редактировать событие.

### Исправление

Подключить editor к этапу 6 и обеспечить выбор draft по стабильному `draft_id`.

---

## P0-09. Редактирование текста фактически останавливается после первого изменения

### Файл

```text
calendar_planner/drafts/editor.py
```

### Проблема

Метод `_update_field` содержит:

```python
if field.modified_by_user:
    return
```

После первого `KeyRelease` поле получает `modified_by_user=True`. Все последующие символы игнорируются моделью.

### Последствие

GUI показывает новый текст в `StringVar`, но `FinalEventDraft` сохраняет только первое изменение.

### Исправление

Не блокировать дальнейшее редактирование пользователем. Блокировка нужна только для автоматического перезаписывания ручных данных.

---

## P0-10. Добавление участника из конструктора падает на Enum

### Файлы

```text
calendar_planner/ui/event_editor.py
calendar_planner/domain/enums.py
```

### Проблема

Combobox возвращает:

```text
performer
customer
```

а Enum ожидает:

```text
PERFORMER
CUSTOMER
```

Аналогично роль возвращается:

```text
required
optional
```

при значениях Enum:

```text
REQUIRED
OPTIONAL
```

Вызовы:

```python
ParticipantSide(side_var.get())
ParticipantRole(role_var.get())
```

завершаются `ValueError`.

### Исправление

Использовать Enum напрямую или явную карту UI → domain.

---

## P0-11. «Проверить дубль» может ложно отметить проверку успешной

### Файл

```text
calendar_planner/ui/event_editor.py
```

### Проблема

Метод `_recheck_duplicate` сначала выполняет:

```python
match_status = "checked"
```

и только затем необязательно вызывает callback.

Если callback отсутствует или не выполнил календарный запрос, статус всё равно становится проверенным.

### Исправление

Статус `checked` присваивается только после успешного реального сравнения и сохранения результата.

---

## P0-12. Небезопасный путь создания

### Файлы

```text
calendar_planner/calendar/creator.py
calendar_planner/domain/validation.py
```

### Проблема

`EventCreator.create_one()` проверяет только payload.

Он не проверяет:

- `duration_confirmed`;
- `draft.is_ready`;
- `match_status`;
- актуальность hash;
- наличие DUPLICATE;
- повторную проверку календаря;
- идемпотентность.

### Последствие

Вызов `create_one()` может создать событие из stale draft, если payload синтаксически валиден.

### Исправление

Перед payload validation выполнять обязательную domain validation:

```python
validate_draft_ready(draft)
validate_match_freshness(draft)
validate_not_duplicate(draft)
validate_idempotency(draft)
```

---

# 4. Высокие дефекты P1

## P1-01. Контактный индекс неверно определяет ФИО

### Файл

```text
calendar_planner/participants/contact_index.py
```

### Проблема

Для строки контактов используется:

```python
full_name = row[0]
```

В целевом листе `row[0]` — номер строки, например `1`, а ФИО находится в следующей колонке.

При этом surname может определиться правильно, но resolver использует:

```python
c.full_name or name
```

и получает `1` как ФИО.

### Исправление

Сначала определить схему контактного листа по заголовкам:

```text
ФИО
E-mail
Телефон
Организация
```

---

## P1-02. Нечёткое сопоставление Заказчика не используется

### Файлы

```text
calendar_planner/participants/contact_index.py
calendar_planner/participants/resolver.py
```

### Проблема

Функция `fuzzy_match_surname()` существует, но `ParticipantResolver` вызывает только:

```python
contact_index.find_by_name(name)
```

Поэтому:

```text
Исламгиев
```

не будет автоматически сопоставлен с:

```text
Исламгалиев Дмитрий Фанисович
```

### Исправление

Добавить второй проход fuzzy matching с контролем порога и уникальности.

---

## P1-03. При нескольких сотрудниках выбирается не лучший, а первый

### Файл

```text
calendar_planner/participants/matcher.py
```

### Проблема

Вычисляется `best`, но затем выполняется:

```python
emp = results[0] if isinstance(results[0], dict) else best
```

Так как результат обычно является dict, всегда выбирается первый элемент.

Дополнительно неоднозначный результат автоматически разрешается, хотя по ТЗ требуется выбор пользователя.

### Исправление

Не разрешать автоматически несколько вариантов. Возвращать `UnresolvedParticipant` с кандидатами.

---

## P1-04. Домен Исполнителя жёстко задан

### Файл

```text
calendar_planner/participants/resolver.py
```

### Проблема

Используется:

```text
1bit.ru
```

Значение не загружается из settings и может не соответствовать реальному каталогу.

### Исправление

Добавить:

```env
PERFORMER_EMAIL_DOMAINS=
```

с поддержкой нескольких доменов.

---

## P1-05. Enrichment может добавлять нерелевантные строки как ссылки

### Файл

```text
calendar_planner/enrichment/extractor.py
```

### Проблема

Поиск по другим листам:

- сравнивает общий фрагмент темы;
- при совпадении добавляет всю строку;
- присваивает ей тип `LINK`, даже если URL отсутствует.

Для темы с префиксом:

```text
Демонстрация процессов: ...
```

сравниваться может общий текст `демонстрация процессов`, что создаёт ложные связи.

### Исправление

Использовать отдельную модель релевантности и определять фактический тип элемента.

---

## P1-06. Этап 5 отсутствует в пользовательском потоке

Классы enrichment существуют, но главное окно их не вызывает и не отображает.

---

## P1-07. Функции восстановления в редакторе не реализованы

### Файл

```text
calendar_planner/ui/event_editor.py
```

Проблемы:

```python
_on_description_changed(): pass
_restore_description(): pass
_restore_attendees(): только перечитывает текущий список
```

Автоматический вариант не восстанавливается.

---

## P1-08. Произвольную длительность фактически нельзя ввести

`duration_var` существует, но отдельного Entry/Spinbox для ввода пользовательского значения нет. Кнопка «Другая» читает текущее значение, которое по умолчанию равно `60`.

---

## P1-09. Поля места и ссылки отсутствуют в конструкторе

Модель содержит `location` и `online_meeting_url`, но editor не предоставляет редактируемых полей.

---

## P1-10. Изменение роли участника не делает match stale

Состав и роли участников входят в финальное событие. После изменения роли необходимо обновлять hash и помечать match устаревшим.

---

## P1-11. Дубли участников не контролируются

Можно повторно добавить один email в required/optional.

---

## P1-12. Сессия сохраняется частично

### Файл

```text
calendar_planner/ui/controllers.py
```

`create_session()` сохраняет:

- источник;
- кандидатов;
- skipped rows;
- statuses.

Не сохраняются:

- raw calendar events;
- normalized calendar events;
- matches;
- participants;
- enrichment;
- drafts;
- user selection;
- creation results;
- draft change log.

`load_session()` также только загружает manifest и не восстанавливает controller state.

---

## P1-13. `CalendarMatch.to_dict()` падает для NEW

### Файл

```text
calendar_planner/domain/models.py
```

Для `NEW` matcher создаёт:

```python
calendar_event=None
```

Но `to_dict()` без проверки вызывает:

```python
self.calendar_event.to_dict()
```

Это приведёт к `AttributeError` при сохранении нового события.

---

## P1-14. Weighted score реализован некорректно

### Файл

```text
calendar_planner/calendar/matcher.py
```

Проблемы:

- за дату начисляется полный балл просто при наличии дат, без проверки равенства;
- вес времени добавляется, но балл за совпадение времени не начисляется;
- вес участников объявлен, но не используется;
- метод не участвует в основном match flow.

---

## P1-15. Реальный формат MCP-ответа не нормализован контрактно

Gateway ожидает, что результат `mcp_call` будет непосредственно `list`.

Не поддержаны распространённые оболочки:

```text
{"events": [...]}
{"result": [...]}
MCP content blocks
JSON string inside content
pagination
```

---

# 5. Средние дефекты P2

## P2-01. StructuredExtractor всегда используется даже для неструктурированных файлов

### Файл

```text
calendar_planner/ui/main_window.py
```

TXT, DOCX и PDF загружаются, но UI всегда вызывает `StructuredExtractor`.

`UnstructuredExtractor` в пользовательском потоке не используется.

---

## P2-02. Доказательства содержат пустые координаты

### Файл

```text
calendar_planner/extraction/structured.py
```

Метод:

```python
_col_str_from_row()
```

возвращает пустую строку.

Evidence не содержит реальную колонку.

---

## P2-03. Workbook timezone определяется неверным свойством

### Файл

```text
calendar_planner/source/adapters/file_adapters.py
```

В metadata записывается:

```python
wb.properties.excelBaseDate
```

Это не timezone книги.

---

## P2-04. Google API settings не используются

В settings присутствуют:

```text
GOOGLE_API_KEY
GOOGLE_SERVICE_ACCOUNT_FILE
```

Но Google Sheets adapter использует только публичный export URL.

Приватные документы не поддерживаются.

---

## P2-05. Confluence и SharePoint адаптеры не имеют аутентификации

Они выполняют обычный HTTP GET. Для защищённых страниц, скорее всего, будет прочитана страница входа.

---

## P2-06. CSV не определяет кодировку и разделитель

Поддерживается только UTF-8 и стандартный `csv.reader`.

---

## P2-07. PDF не поддерживает OCR

Сканированные PDF не будут прочитаны.

---

## P2-08. `compute_end_datetime()` не использует timezone-aware datetime

Расчёт окончания выполняется на naive datetime. Для регионов с DST это может дать неверный результат.

---

## P2-09. All-day payload некорректен

Creator формирует одинаковую дату начала и окончания. Для большинства календарных API end у all-day события является исключающей датой следующего дня.

Одновременно `validate_payload()` требует `dateTime`, поэтому all-day payload будет признан невалидным.

---

# 6. Тесты и CI

## 6.1. GitHub CI отсутствует

Для commit:

```text
08fb92dfeb8b038cbce07f34eeaf82e6e98ca97c
```

нет:

- workflow runs;
- status checks;
- подтверждённого результата pytest;
- опубликованного coverage.

## 6.2. Coverage исключает критичные области

Из coverage исключены:

```text
calendar_planner/ui/*
calendar_planner/cli/*
calendar_planner/app/bootstrap.py
```

Именно в этих областях находятся наиболее критичные дефекты.

## 6.3. Тесты преимущественно изолированные

Сильные стороны:

- есть timezone unit tests;
- есть draft tests;
- есть structured extraction tests;
- есть fixture gateway tests.

Недостаёт:

- реального MCP contract test;
- bootstrap wiring test;
- GUI orchestration test;
- CLI entrypoint test;
- end-to-end теста этапов 1–6;
- теста целевого Google Sheets;
- полного session roundtrip;
- проверки создания после real duplicate recheck;
- теста enum mapping в editor;
- теста многократного редактирования поля;
- теста fuzzy customer resolution внутри resolver;
- теста сохранения NEW match;
- теста команды `create`.

## 6.4. Тесты не должны считать fixture интеграцией

`FixtureCalendarGateway` и `FixtureDirectoryGateway` полезны для unit-тестов, но не подтверждают реальную работу MCP.

---

# 7. Матрица соответствия этапов

| Этап | Статус | Комментарий |
|---|---|---|
| 1. Подключения | Не реализован | Настройки выводятся, реальные подключения не проверяются |
| 2. Поиск встреч | Частично | Structured extraction есть, timezone ЕКБ сломан, unstructured не подключён |
| 3. Сравнение | Частично как библиотека | Matcher есть, runtime и UI отсутствуют |
| 4. Участники | Частично | Fixture и contact index есть, реальные gateway и fuzzy flow не завершены |
| 5. Дополнительные данные | Частично как библиотека | UI и orchestration отсутствуют, релевантность слабая |
| 6. Конструктор | Частично и не подключён | Есть отдельный frame с критичными ошибками |
| 6. Создание | Не реализовано end-to-end | Runtime gateway отсутствует, CLI имитирует успех |
| Сессии | Частично | Полное состояние не сохраняется |
| Тесты | Частично | Unit-тесты есть, CI/E2E отсутствуют |

---

# 8. Рекомендуемый порядок исправления

## Итерация 1 — приложение и интеграции

1. Создать application orchestrator.
2. Реализовать dependency injection/bootstrap.
3. Реализовать MCP transport.
4. Подключить реальные calendar и directory gateways.
5. Реализовать настоящий этап 1.
6. Добавить GitHub Actions.

## Итерация 2 — корректное извлечение

1. Исправить timezone column mapping.
2. Добавить выбор structured/unstructured extractor.
3. Исправить evidence coordinates.
4. Добавить целевой XLSX/Google Sheets fixture.
5. Проверить 8 согласованных встреч.

## Итерация 3 — календарь

1. Реализовать contract normalization MCP.
2. Сохранять raw и normalized events.
3. Исправить `CalendarMatch` optional event.
4. Реализовать hard rules и weighted score.
5. Добавить idempotency.
6. Проверить ожидаемый результат дублей.

## Итерация 4 — участники

1. Детектировать схему контактного листа.
2. Исправить full_name.
3. Подключить fuzzy matching.
4. Не выбирать неоднозначного сотрудника автоматически.
5. Сделать домены настраиваемыми.

## Итерация 5 — GUI этапов 3–6

1. Создать отдельные stage frames.
2. Подключить EventEditorFrame.
3. Исправить многократное редактирование.
4. Исправить enum mapping.
5. Реализовать restore.
6. Добавить location, URL и custom duration.
7. Реализовать выбор строк.

## Итерация 6 — безопасное создание

1. Общая domain validation.
2. Fresh duplicate check.
3. Реальный create gateway.
4. Сохранение ID и URL.
5. Dry-run acceptance test.
6. Full session restore.

---

# 9. Минимальные критерии повторной приёмки

Перед повторной валидацией должны быть представлены:

1. GitHub Actions workflow.
2. Зелёный pytest.
3. Coverage по UI controllers, CLI и bootstrap.
4. MCP contract tests.
5. End-to-end dry-run.
6. Контрольный файл с целевой структурой.
7. Фактический результат:
   - 8 согласованных встреч;
   - корректный `Asia/Yekaterinburg`;
   - реальные события календаря;
   - найденные дубли;
   - участники по каждой встрече;
   - редактируемый constructor;
   - подтверждённая длительность;
   - корректный start/end payload.
8. Подтверждение отсутствия реальных созданных событий при тестировании.

---

# 10. Заключение

Репозиторий содержит полезную основу и показывает правильное направление по структуре модулей и доменным моделям. Однако заявленный в README функционал существенно шире фактически доступного пользовательского сценария.

Текущую версию следует классифицировать как:

```text
архитектурный прототип / каркас
```

а не как готовый функционал автоматического формирования календарных событий.
