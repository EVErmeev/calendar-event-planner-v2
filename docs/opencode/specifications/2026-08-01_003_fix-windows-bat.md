# ТЗ: исправление Windows BAT и CI-блокеров после commit 0bb4e86

**Ветка:** fix/initial-audit-findings  
**Цель:** BAT → GUI работает, windows-smoke зелёный, coverage gate фиксирован.

## Ключевые требования

1. PYTHONUTF8=1, PYTHONIOENCODING=utf-8 в BAT
2. `configure_console_encoding()` в bootstrap.py
3. Безопасный поиск Python: реальный запуск `python -c "..."`, а не `where`
4. Единый `:fatal` обработчик с `pause` и логированием
5. `--smoke-gui` в bootstrap
6. Coverage gate: `float()` вместо `int()`
7. `logs\launcher.log`
8. Windows CI: --help, --version, --smoke-gui