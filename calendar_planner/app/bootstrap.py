from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path


def load_env_file() -> None:
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value


def main() -> None:
    load_env_file()

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    if "--help" in sys.argv or "-h" in sys.argv:
        print("Calendar Event Planner v2")
        print()
        print("Usage: calendar-planner [OPTIONS]")
        print()
        print("Опции:")
        print("  --help, -h       Показать эту справку")
        print("  --cli            Запустить CLI-режим")
        print("  --version        Показать версию")
        print()
        print("CLI команды: python -m calendar_planner.cli <command>")
        print("  check-connections")
        print("  analyze --source=<path>")
        print("  compare --session=<id>")
        print("  resolve-participants --session=<id>")
        print("  enrich --session=<id>")
        print("  preview --session=<id>")
        print("  create --session=<id> --draft-id=<id> --confirm-create")
        print()
        print("Запуск в Windows: run_calendar_planner.bat")
        return

    if "--version" in sys.argv:
        print("calendar-event-planner-v2 1.0.0")
        return

    from calendar_planner.app.container import AppContainer
    from calendar_planner.app.settings import settings

    container = AppContainer(settings)

    if settings.MCP_ENABLED:
        container.init_mcp()

    if "--cli" in sys.argv:
        from calendar_planner.cli import main as cli_main
        cli_main()
        return

    from calendar_planner.ui.main_window import MainWindow

    root = tk.Tk()
    _app = MainWindow(root, container=container)
    root.mainloop()


if __name__ == "__main__":
    main()