# OpenCode workspace

Этот каталог — единый источник технических заданий, результатов аудитов и повторных валидаций проекта `calendar-event-planner-v2`.

## Обязательный порядок работы OpenCode

Перед любыми изменениями:

1. Открыть `docs/opencode/manifest.json`.
2. Открыть документ из поля `active_task`.
3. Открыть документ из поля `latest_audit`.
4. Проверить текущий commit и `git status`.
5. Выполнять работу по активному ТЗ и незакрытым замечаниям последнего аудита.
6. Не считать наличие класса, файла, кнопки или unit-теста доказательством готовности.
7. Подтверждать результат фактическими тестами, CI, coverage, run-артефактами и end-to-end dry-run.
8. Не создавать реальные календарные события во время разработки и валидации.

## Структура

```text
docs/opencode/
├── README.md
├── manifest.json
├── CURRENT_TASK.md
├── audits/
├── specifications/
├── validations/
└── templates/
```

## Именование

```text
specifications/YYYY-MM-DD_NNN_<name>.md
audits/YYYY-MM-DD_<commit-short>_<name>.md
validations/YYYY-MM-DD_<commit-short>_<name>.md
```

## Статусы

```text
draft
active
implemented
superseded
validated
rejected
```

## Доказательства выполнения

Принимаются только:

- код в проверяемом commit;
- прошедшие тесты;
- GitHub Actions status checks;
- coverage критичных модулей;
- contract tests интеграций;
- end-to-end dry-run;
- run-артефакты;
- воспроизводимый контрольный сценарий.

README, комментарии разработчика и наличие неподключённых классов доказательствами не являются.
