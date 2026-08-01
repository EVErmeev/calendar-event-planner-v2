from __future__ import annotations

import sys
import os
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

    from calendar_planner.app.settings import settings
    from calendar_planner.app.container import AppContainer

    container = AppContainer(settings)

    if settings.MCP_ENABLED:
        container.init_mcp()

    if "--cli" in sys.argv:
        from calendar_planner.cli import main as cli_main
        cli_main()
        return

    from calendar_planner.ui.main_window import MainWindow

    root = tk.Tk()
    app = MainWindow(root, container=container)
    root.mainloop()


if __name__ == "__main__":
    main()