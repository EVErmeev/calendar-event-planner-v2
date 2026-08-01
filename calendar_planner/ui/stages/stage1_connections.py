from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Stage1ConnectionsFrame(ttk.Frame):
    def __init__(self, parent, container=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.container = container
        self._detected_config: dict = {}
        self._last_results: list[dict] = []
        self._ready = False
        self._build_ui()

    def _build_ui(self):
        h = ttk.Frame(self)
        h.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(h, text="1. Подключения", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(h, text="Настройка и проверка Exchange MCP подключения", font=("", 8)).pack(anchor=tk.W)

        # Buttons row
        btn = ttk.Frame(self)
        btn.pack(fill=tk.X, pady=5)
        ttk.Button(btn, text="Определить автоматически", command=self._auto_detect).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Проверить подключения", command=self._check_now).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Сохранить настройки", command=self._save_settings).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Копировать результат", command=self._copy).pack(side=tk.LEFT, padx=2)

        # Auth notice
        auth = ttk.LabelFrame(self, text="Авторизация", padding=5)
        auth.pack(fill=tk.X, pady=5)
        ttk.Label(auth, text="Авторизация почты выполняется установщиком Exchange MCP.\nПриложение использует уже настроенное локальное MCP-подключение.\nЛогин и пароль в приложении не требуются.", font=("", 8)).pack(anchor=tk.W)

        # Detected config
        self._config_frame = ttk.LabelFrame(self, text="Настройки подключения", padding=5)
        self._config_frame.pack(fill=tk.X, pady=5)

        self._transport_var = tk.StringVar(value="auto")
        row = ttk.Frame(self._config_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Тип:", width=15).pack(side=tk.LEFT)
        cb = ttk.Combobox(row, textvariable=self._transport_var, values=["auto", "exchange-stdio", "http"], state="readonly", width=20)
        cb.pack(side=tk.LEFT, padx=5)

        row = ttk.Frame(self._config_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Команда:", width=15).pack(side=tk.LEFT)
        self._command_var = tk.StringVar()
        self._command_entry = ttk.Entry(row, textvariable=self._command_var, width=60)
        self._command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        row = ttk.Frame(self._config_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Календарь:", width=15).pack(side=tk.LEFT)
        self._find_tool_var = tk.StringVar(value="find_events")
        ttk.Entry(row, textvariable=self._find_tool_var, width=20).pack(side=tk.LEFT, padx=5)

        row = ttk.Frame(self._config_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Создание:", width=15).pack(side=tk.LEFT)
        self._create_tool_var = tk.StringVar(value="create_event")
        ttk.Entry(row, textvariable=self._create_tool_var, width=20).pack(side=tk.LEFT, padx=5)

        row = ttk.Frame(self._config_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Контакты:", width=15).pack(side=tk.LEFT)
        self._dir_tool_var = tk.StringVar(value="search_emails")
        ttk.Entry(row, textvariable=self._dir_tool_var, width=20).pack(side=tk.LEFT, padx=5)

        # Results
        self._results_frame = ttk.LabelFrame(self, text="Результаты проверки", padding=5)
        self._results_frame.pack(fill=tk.X, pady=5)
        self._results_text = tk.Text(self._results_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self._results_text.pack(fill=tk.BOTH, expand=True)

        # Status
        self._status_var = tk.StringVar(value="Нажмите «Проверить подключения»")
        st = ttk.Label(self, textvariable=self._status_var, font=("", 9), foreground="gray")
        st.pack(anchor=tk.W, pady=5)

    def _auto_detect(self):
        try:
            from calendar_planner.app.exchange_detector import ExchangeMCPConfigDetector
            detector = ExchangeMCPConfigDetector()
            config = detector.detect()
            self._detected_config = config
            if config["found"]:
                self._command_var.set(config["command"])
                self._transport_var.set("exchange-stdio")
                self._find_tool_var.set(config["calendar_find_tool"])
                self._create_tool_var.set(config["calendar_create_tool"])
                self._dir_tool_var.set(config["directory_search_tool"])
                self._log("Exchange MCP найден автоматически.")
                self._log(f"Транспорт: {config['transport']}")
                self._log(f"Tools: {', '.join(config['tools'][:5])}...")
            else:
                self._log("Exchange MCP не найден автоматически.")
                self._log("Установите Exchange MCP командой в терминале OpenCode.")
        except Exception as e:
            self._log(f"Ошибка автоопределения: {e}")

    def _check_now(self):
        if self.container is None:
            self._log("Контейнер не инициализирован.")
            return
        self._log("Проверка подключений...")
        result = self.container.check_all_connections()
        self._last_results = result.get("results", [])
        self._ready = result.get("ready_for_analysis", False)
        for r in self._last_results:
            sym = {"success": "OK", "failed": "FAIL", "warning": "WARN"}.get(r.get("status", ""), "?")
            self._log(f"  [{sym}] {r.get('component', '?')}: {r.get('message', '')}")
        status = "ГОТОВ К АНАЛИЗУ" if self._ready else "НЕ ГОТОВ"
        color = "green" if self._ready else "red"
        self._status_var.set(status)
        for child in self._results_frame.winfo_children():
            if isinstance(child, ttk.Label) and str(child.cget("text")).startswith("ГОТОВ"):
                child.config(foreground=color)

    def _save_settings(self):
        import os
        cmd = self._command_var.get().strip()
        if cmd:
            os.environ["MCP_STDIO_COMMAND"] = cmd
            os.environ["MCP_SERVER_URL"] = ""
        os.environ["MCP_CALENDAR_FIND_TOOL"] = self._find_tool_var.get().strip()
        os.environ["MCP_CALENDAR_CREATE_TOOL"] = self._create_tool_var.get().strip()
        os.environ["MCP_DIRECTORY_SEARCH_TOOL"] = self._dir_tool_var.get().strip()

        env_path = "D:/OpenCode/calendar-event-planner-v2/.env" if hasattr(self, '__module__') else ".env"
        from pathlib import Path
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        lines = []
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").split("\n")
        updated = {"MCP_STDIO_COMMAND": cmd, "MCP_CALENDAR_FIND_TOOL": self._find_tool_var.get().strip(),
                    "MCP_CALENDAR_CREATE_TOOL": self._create_tool_var.get().strip(),
                    "MCP_DIRECTORY_SEARCH_TOOL": self._dir_tool_var.get().strip()}
        new_lines = []
        for line in lines:
            key = line.split("=")[0].strip() if "=" in line else ""
            if key in updated:
                new_lines.append(f"{key}={updated[key]}")
                del updated[key]
            else:
                new_lines.append(line)
        for k, v in updated.items():
            if v:
                new_lines.append(f"{k}={v}")
        env_file.write_text("\n".join(new_lines), encoding="utf-8")
        self._log("Настройки сохранены в .env")

    def _copy(self):
        text = self._results_text.get(1.0, tk.END)
        self.clipboard_clear()
        self.clipboard_append(text)

    def _log(self, msg: str):
        self._results_text.insert(tk.END, msg + "\n")
        self._results_text.see(tk.END)

    def get_ready(self) -> bool:
        return self._ready

    def get_results(self) -> list[dict]:
        return self._last_results
