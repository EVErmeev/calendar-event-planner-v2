# Calendar Event Planner v2

Автоматическое формирование календарных событий по произвольному источнику.

## Возможности

- Анализ структурированных таблиц (Excel, CSV, Google Sheets)
- Анализ неструктурированных документов (TXT, PDF, DOCX, HTML, Word)
- Поиск встреч по согласованным датам (AGREED_ONLY)
- Timezone-aware сравнение с календарём
- Разделение участников на Исполнителя и Заказчика
- Обогащение описания встречи (повестка, ссылки, место)
- Конструктор события с полным редактированием
- Повторная проверка дублей после изменений
- Dry-run по умолчанию

## Установка

```bash
cd D:\OpenCode\calendar-event-planner-v2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Настройка

```bash
cp .env.example .env
# Отредактируйте .env и заполните MCP_SERVER_URL и другие параметры
```

## Запуск

### GUI

```bash
python -m calendar_planner.app.bootstrap
```

### CLI

```bash
python -m calendar_planner.cli check-connections
python -m calendar_planner.cli analyze --source="path/to/file.xlsx"
python -m calendar_planner.cli compare --session="abc123"
python -m calendar_planner.cli preview --session="abc123"
python -m calendar_planner.cli create --session="abc123" --draft-id="DRF-0001" --confirm-create
```

## Запуск тестов

```bash
pytest tests/ -v --cov=calendar_planner --cov-report=term-missing
```

## Архитектура

```
calendar_planner/
├── app/              # Bootstrap и настройки
├── domain/           # Доменные модели, енамы, валидация
├── source/           # Адаптеры источников, registry
│   └── adapters/     # Txt, Csv, Xlsx, Docx, Pdf, Html, Google Sheets, Google Docs
├── extraction/       # Извлечение встреч, нормализация дат, аудит
├── calendar/         # Gateway (MCP/fixture), matcher, creator
├── participants/     # Directory gateway, contact index, matcher, resolver
├── enrichment/       # Extractor, relevance, renderer
├── drafts/           # Builder, editor, validation, hash
├── session/          # Модели сессии, storage
├── ui/               # GUI (main_window, stages, event_editor, controllers)
└── cli/              # CLI команды
```

## Основные принципы

- Бизнес-логика отделена от GUI
- Нет глобальных переменных
- Dry-run по умолчанию
- Timezone-aware все операции со временем
- Idempotent: повторный запуск не создаёт дубли
- AGREED_ONLY: только согласованные даты

## Известные ограничения

1. MCP-подключение требует настроенного сервера
2. Google Sheets API требует API ключ для не-публичных документов
3. Confluence/SharePoint без аутентификации имеют ограниченный доступ
4. Распознавание неструктурированного текста упрощённое — рекомендуется для структурированных таблиц

## Запуск в Windows

Двойной клик по `run_calendar_planner.bat` в корне проекта.

Требования:
- Python 3.11+
- При первом запуске автоматически создаётся `.venv` и устанавливаются зависимости

```bat
run_calendar_planner.bat           # запуск программы
run_calendar_planner.bat --help    # справка
```

Токены и настройки MCP задаются через `.env` или переменные среды, не внутри BAT.
4. Распознавание неструктурированного текста упрощённое — рекомендуется для структурированных таблиц