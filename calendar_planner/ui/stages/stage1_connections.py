from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Stage1ConnectionsFrame(ttk.Frame):
    def __init__(self, parent, container=None, on_check_done=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.container = container
        self._cred_provider = container.credential_provider if container else None
        self._on_check_done = on_check_done
        self._detected_config: dict = {}
        self._last_results: list[dict] = []
        self._ready = False

        import os
        self._saved_endpoint = os.environ.get("EWS_ENDPOINT", "https://mail.1cbit.ru/EWS/Exchange.asmx")
        self._saved_login = os.environ.get("EWS_USERNAME", "")
        if self._cred_provider:
            if self._cred_provider.has_session_credentials():
                self._saved_pass_status = "сохранён в сессии"
            else:
                creds = self._cred_provider.get_credentials()
                if creds.available:
                    self._cred_provider.set_session_credentials(creds.username, creds.password)
                    self._saved_login = creds.username or self._saved_login
                    self._saved_pass_status = "загружен"
                else:
                    # Try .env password as last fallback
                    env_pass = os.environ.get("EWS_PASSWORD", "")
                    if env_pass:
                        self._cred_provider.set_session_credentials(self._saved_login, env_pass)
                        self._saved_pass_status = "загружен из .env"
                    else:
                        self._saved_pass_status = "не задан"
        else:
            self._saved_pass_status = "не задан"
        self._saved_ready = False
        if container:
            # Preserve readiness from previous check
            self._ready = container.check_all_connections().get("ready_for_analysis", False)

        self._build_ui()
        # Restore last results if available
        if self._ready and self._last_results:
            self._display_results(self._last_results, self._ready)

    def _build_ui(self):
        self._outer_canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._outer_canvas.yview)
        self._scrollable = ttk.Frame(self._outer_canvas)
        self._scrollable.bind("<Configure>", lambda e: self._outer_canvas.configure(scrollregion=self._outer_canvas.bbox("all")))
        self._outer_canvas.create_window((0, 0), window=self._scrollable, anchor="nw", tags="inner")
        self._outer_canvas.configure(yscrollcommand=scrollbar.set)
        self._outer_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._outer_canvas.bind("<Configure>", lambda e: self._outer_canvas.itemconfig("inner", width=e.width))

        h = ttk.Frame(self._scrollable)
        h.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(h, text="1. Подключения", font=("", 12, "bold")).pack(anchor=tk.W)

        btn = ttk.Frame(self._scrollable)
        btn.pack(fill=tk.X, pady=5)
        ttk.Button(btn, text="Определить автоматически", command=self._auto_detect).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Проверить подключения", command=self._check_now).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Копировать результат", command=self._copy).pack(side=tk.LEFT, padx=2)

        # Auth
        auth = ttk.LabelFrame(self._scrollable, text="Авторизация почты", padding=5)
        auth.pack(fill=tk.X, pady=5)
        ttk.Label(auth, text="Авторизация почты выполнена установщиком Exchange MCP.\nЛогин и пароль почты в приложении не требуются.", font=("", 8)).pack(anchor=tk.W)

        # MCP config
        mcp_frame = ttk.LabelFrame(self._scrollable, text="Exchange MCP", padding=5)
        mcp_frame.pack(fill=tk.X, pady=5)
        self._transport_var = tk.StringVar(value="auto")
        row = ttk.Frame(mcp_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Тип:", width=15).pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self._transport_var, values=["auto", "exchange-stdio", "http"], state="readonly", width=20).pack(side=tk.LEFT, padx=5)
        row = ttk.Frame(mcp_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Команда:", width=15).pack(side=tk.LEFT)
        self._command_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._command_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        row = ttk.Frame(mcp_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Calendar tool:", width=15).pack(side=tk.LEFT)
        self._find_tool_var = tk.StringVar(value="find_events")
        ttk.Entry(row, textvariable=self._find_tool_var, width=20).pack(side=tk.LEFT, padx=5)
        row = ttk.Frame(mcp_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Create tool:", width=15).pack(side=tk.LEFT)
        self._create_tool_var = tk.StringVar(value="create_event")
        ttk.Entry(row, textvariable=self._create_tool_var, width=20).pack(side=tk.LEFT, padx=5)

        # EWS
        ews_frame = ttk.LabelFrame(self._scrollable, text="Корпоративный каталог сотрудников (EWS)", padding=5)
        ews_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ews_frame, text="Источник: Exchange EWS GAL | ResolveNames | ActiveDirectory", font=("", 8)).pack(anchor=tk.W)
        row = ttk.Frame(ews_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="EWS endpoint:", width=15).pack(side=tk.LEFT)
        self._ews_endpoint_var = tk.StringVar(value=self._saved_endpoint)
        ttk.Entry(row, textvariable=self._ews_endpoint_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        row = ttk.Frame(ews_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Логин:", width=15).pack(side=tk.LEFT)
        self._ews_login_var = tk.StringVar(value=self._saved_login)
        ttk.Entry(row, textvariable=self._ews_login_var, width=25).pack(side=tk.LEFT, padx=5)
        row = ttk.Frame(ews_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Пароль:", width=15).pack(side=tk.LEFT)
        self._ews_pass_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._ews_pass_var, width=25, show="*").pack(side=tk.LEFT, padx=5)
        self._ews_pass_status_var = tk.StringVar(value=self._saved_pass_status)
        ttk.Label(row, textvariable=self._ews_pass_status_var, font=("", 7), foreground="gray").pack(side=tk.LEFT, padx=5)
        row = ttk.Frame(ews_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Тестовое ФИО:", width=15).pack(side=tk.LEFT)
        self._ews_probe_var = tk.StringVar(value="Ермеев Егор")
        ttk.Entry(row, textvariable=self._ews_probe_var, width=25).pack(side=tk.LEFT, padx=5)
        ews_btn = ttk.Frame(ews_frame); ews_btn.pack(fill=tk.X, pady=5)
        ttk.Button(ews_btn, text="Сохранить EWS", command=self._save_ews).pack(side=tk.LEFT, padx=2)
        ttk.Button(ews_btn, text="Проверить каталог", command=self._check_directory).pack(side=tk.LEFT, padx=2)
        ttk.Button(ews_btn, text="Очистить credentials", command=self._clear_ews).pack(side=tk.LEFT, padx=2)

        # Results
        self._results_frame = ttk.LabelFrame(self._scrollable, text="Результаты проверки", padding=5)
        self._results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self._results_text = tk.Text(self._results_frame, height=14, wrap=tk.WORD, font=("Consolas", 9))
        self._results_text.pack(fill=tk.BOTH, expand=True)

        self._status_var = tk.StringVar(value="1. Нажмите «Определить автоматически»\n2. Затем «Проверить подключения»")
        self._status_label = ttk.Label(self._scrollable, textvariable=self._status_var, font=("", 9, "bold"))
        self._status_label.pack(anchor=tk.W, pady=5)

    def _auto_detect(self):
        try:
            from calendar_planner.app.exchange_detector import ExchangeMCPConfigDetector
            config = ExchangeMCPConfigDetector().detect()
            self._detected_config = config
            if config["found"]:
                self._command_var.set(config["command"])
                self._transport_var.set("exchange-stdio")
                self._find_tool_var.set(config["calendar_find_tool"])
                self._create_tool_var.set(config["calendar_create_tool"])
                self._log("Exchange MCP найден.")
                self._status_var.set("Exchange MCP найден. Нажмите «Проверить подключения»")
            else:
                self._log("Exchange MCP не найден.")
                self._status_var.set("MCP не найден. Проверьте установку Exchange MCP.")
        except Exception as e:
            self._log(f"Ошибка: {e}")

    def _save_ews(self):
        endpoint = self._ews_endpoint_var.get().strip()
        login = self._ews_login_var.get().strip()
        password = self._ews_pass_var.get().strip()

        if self.container:
            self.container.configure_ews(endpoint, login, password if password else None)

        if password and self._cred_provider:
            self._cred_provider.set_session_credentials(login, password)
            self._ews_pass_status_var.set("сохранён в сессии")
            self._ews_pass_var.set("")

        # Save to .env with password
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").split("\n")
            updates = {"EWS_ENDPOINT": endpoint, "EWS_USERNAME": login}
            if password:
                updates["EWS_PASSWORD"] = password
            replaced = set()
            out_lines = []
            for line in lines:
                key = line.split("=")[0].strip() if "=" in line else ""
                if key in updates:
                    out_lines.append(f"{key}={updates[key]}")
                    replaced.add(key)
                else:
                    out_lines.append(line)
            for key, val in updates.items():
                if val and key not in replaced:
                    out_lines.append(f"{key}={val}")
            env_file.write_text("\n".join(out_lines), encoding="utf-8")

        self._log(f"EWS saved. Login: {login}.")

    def _clear_ews(self):
        self._ews_login_var.set("")
        self._ews_pass_var.set("")
        self._ews_pass_status_var.set("не задан")
        if self._cred_provider:
            self._cred_provider.clear_session_credentials()
        if self.container:
            self.container.reset_directory_gateway()
        self._log("EWS credentials очищены.")

    def _check_directory(self):
        if self.container is None: return
        ep = self._ews_endpoint_var.get().strip()
        lg = self._ews_login_var.get().strip()
        pw = self._ews_pass_var.get().strip()
        if not pw and self._cred_provider:
            c = self._cred_provider.get_credentials()
            if c.available: pw = c.password
        probe = self._ews_probe_var.get().strip()
        if not ep or not lg or not pw:
            self._log("[FAIL] Directory: не указаны endpoint, логин или пароль."); return

        self.container.configure_ews(ep, lg, pw)
        self._log(f"Поиск: \"{probe}\"...")
        try:
            from calendar_planner.participants.ews_directory_gateway import (
                EWSDirectoryGateway,
            )
            gw = EWSDirectoryGateway(endpoint=ep, username=lg, password=pw)
            r = gw.search(probe)
            self._log(f"  Статус: {r.status}, найдено: {len(r.people)}")
            for p in r.people[:5]:
                me = p.email[:3] + "***" if len(p.email) > 3 else "***"
                self._log(f"  — {p.display_name} ({me})")
            if r.status in ("success", "ambiguous", "not_found"):
                self._log("[OK] Directory: EWS ResolveNames работает.")
            elif r.status == "auth_failed":
                self._log("[FAIL] Directory: ошибка авторизации.")
            else:
                self._log(f"[FAIL] Directory: {r.status}")
        except Exception as e:
            self._log(f"[FAIL] Directory: {e}")

    def _check_now(self):
        if self.container is None:
            self._log("Контейнер не инициализирован."); return
        self._log("Проверка подключений...")

        ep = self._ews_endpoint_var.get().strip()
        lg = self._ews_login_var.get().strip()
        pw = self._ews_pass_var.get().strip()
        if not pw and self._cred_provider:
            c = self._cred_provider.get_credentials()
            if c.available: pw = c.password
        if ep and lg:
            self.container.configure_ews(ep, lg, pw if pw else None)

        result = self.container.check_all_connections()
        ready = result.get("ready_for_analysis", False)
        self._display_results(result.get("results", []), ready)

        if self._on_check_done:
            self._on_check_done(ready)

    def _display_results(self, results, ready):
        self._last_results = results
        self._ready = ready
        for r in results:
            sym = {"success": "OK", "failed": "FAIL", "warning": "WARN"}.get(r.get("status", ""), "?")
            self._log(f"  [{sym}] {r.get('component', '?')}: {r.get('message', '')}")
        s = "ГОТОВ К АНАЛИЗУ" if ready else "НЕ ГОТОВ"
        self._status_var.set(s)
        self._status_label.config(foreground="green" if ready else "red")

    def get_ready(self) -> bool: return self._ready
    def get_results(self) -> list[dict]: return self._last_results

    def _copy(self):
        text = self._results_text.get(1.0, tk.END)
        self.clipboard_clear(); self.clipboard_append(text)

    def _log(self, msg: str):
        self._results_text.insert(tk.END, msg + "\n")
        self._results_text.see(tk.END)
