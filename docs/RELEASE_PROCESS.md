# Release process

Описание процесса выпуска. Применимо к `v1.1.0` и далее.

## Предпосылки

- CI/Install CI на ветке зелёные.
- Единая версия (version.py = pyproject = manifest).
- `0 real events` в автоматических тестах.

## Шаги

1. Обновить `calendar_planner/version.py` → целевая версия.
2. Обновить `CHANGELOG.md`.
3. Проверить: `python -m pytest`, `ruff check`, `python scripts/mypy_gate.py`.
4. Собрать portable: `scripts/build_portable.ps1`.
5. Проверить: `scripts/verify_distribution.ps1`.
6. Собрать installer: `scripts/build_installer.ps1` (нужен Inno Setup).
7. `smoke_clean_windows.ps1`.
8. Сформировать `SHA256SUMS.txt`.
9. Создать annotated tag `vX.Y.Z` на `master`.
10. Создать GitHub Release с assets.

## Assets v1.1.0

```text
CalendarEventPlannerSetup-v1.1.0.exe
CalendarEventPlannerSetup-v1.1.0.exe.sha256
CalendarEventPlanner-portable-v1.1.0.zip
CalendarEventPlanner-portable-v1.1.0.zip.sha256
component-manifest.json
SHA256SUMS.txt
```

## Автоматизация

Workflow `.github/workflows/release.yml` выполняет большинство шагов при push
тега `v*`. Release не публикуется при failed smoke.