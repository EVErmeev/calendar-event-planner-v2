from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from calendar_planner.ui.keyboard_shortcuts import bind_shortcuts_recursive


class Stage1ConnectionsFrame(ttk.Frame):
    def __init__(self, parent, container=None, on_check_done=None, on_setting_changed=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.container = container
        self._cred_provider = container.credential_provider if container else None
        self._on_check_done = on_check_done
        self._on_setting_changed = on_setting_changed
        self._detected_config: dict = {}
        self._last_results: list[dict] = []
        self._ready = False
        self._password_masked = False

        import os
        self._saved_endpoint = os.environ.get("EWS_ENDPOINT", "https://mail.1cbit.ru/EWS/Exchange.asmx")
        self._saved_login = os.environ.get("EWS_USERNAME", "")
        self._cred_available = False
        if self._cred_provider:
            if self._cred_provider.has_session_credentials():
                self._saved_pass_status = "сохранён в сессии"
                self._cred_available = True
            else:
                creds = self._cred_provider.load_persistent(self._saved_login)
                if creds.available:
                    self._saved_pass_status = "загружен из Windows Credential Manager"
                    self._cred_available = True
                else:
                    self._saved_pass_status = "не задан"
        else:
            self._saved_pass_status = "не задан"
        self._saved_ready = False
        if container:
            # Preserve readiness from previous check
            self._ready = container.check_all_connections().get("ready_for_analysis", False)

        self._build_ui()
        if self._cred_available:
            self._apply_password_mask()
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
        ttk.Button(btn, text="Применить и подключить Exchange MCP", command=self._apply_mcp).pack(side=tk.LEFT, padx=2)
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
        self._ews_pass_entry = ttk.Entry(row, textvariable=self._ews_pass_var, width=25, show="*")
        self._ews_pass_entry.pack(side=tk.LEFT, padx=5)
        self._change_pass_btn = ttk.Button(row, text="Изменить", command=self._on_change_password)
        self._ews_pass_status_var = tk.StringVar(value=self._saved_pass_status)
        ttk.Label(row, textvariable=self._ews_pass_status_var, font=("", 7), foreground="gray").pack(side=tk.LEFT, padx=5)
        row = ttk.Frame(ews_frame); row.pack(fill=tk.X, pady=2)
        self._ews_remember_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Запомнить пароль на этом компьютере", variable=self._ews_remember_var).pack(side=tk.LEFT)
        row = ttk.Frame(ews_frame); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Тестовое ФИО:", width=15).pack(side=tk.LEFT)
        self._ews_probe_var = tk.StringVar(value="Ермеев Егор")
        ttk.Entry(row, textvariable=self._ews_probe_var, width=25).pack(side=tk.LEFT, padx=5)
        ews_btn = ttk.Frame(ews_frame); ews_btn.pack(fill=tk.X, pady=5)
        ttk.Button(ews_btn, text="Сохранить EWS", command=self._save_ews).pack(side=tk.LEFT, padx=2)
        ttk.Button(ews_btn, text="Проверить каталог", command=self._check_directory).pack(side=tk.LEFT, padx=2)
        ttk.Button(ews_btn, text="Очистить credentials", command=self._clear_ews).pack(side=tk.LEFT, padx=2)

        # Default timezone
        tz_frame = ttk.LabelFrame(self._scrollable, text="Часовой пояс по умолчанию", padding=5)
        tz_frame.pack(fill=tk.X, pady=5)
        tz_row = ttk.Frame(tz_frame)
        tz_row.pack(fill=tk.X, pady=2)
        ttk.Label(tz_row, text="Часовой пояс:", width=15).pack(side=tk.LEFT)
        tz_values = ["Asia/Yekaterinburg", "Europe/Moscow", "Europe/Riga", "UTC", "Другой"]
        current_tz = os.environ.get("DEFAULT_TIMEZONE", "Asia/Yekaterinburg")
        self._tz_var = tk.StringVar(value=current_tz if current_tz in tz_values else "Другой")
        self._tz_combo = ttk.Combobox(tz_row, textvariable=self._tz_var, values=tz_values, state="readonly", width=30)
        self._tz_combo.pack(side=tk.LEFT, padx=5)
        self._tz_combo.bind("<<ComboboxSelected>>", self._on_timezone_changed)
        self._custom_tz_var = tk.StringVar()
        self._custom_tz_entry = ttk.Entry(tz_row, textvariable=self._custom_tz_var, width=30)
        if self._tz_var.get() == "Другой":
            self._custom_tz_entry.pack(side=tk.LEFT, padx=5)
        else:
            self._custom_tz_entry.pack_forget()

        # Calendar missing timezone fallback
        cal_tz_row = ttk.Frame(tz_frame)
        cal_tz_row.pack(fill=tk.X, pady=2)
        ttk.Label(cal_tz_row, text="Календарь без tz:", width=15).pack(side=tk.LEFT)
        cal_tz_values = ["UTC", "Asia/Yekaterinburg", "Europe/Moscow", "Europe/Riga", "Другой"]
        current_cal_tz = os.environ.get("CALENDAR_MISSING_TIMEZONE", "UTC")
        self._cal_tz_var = tk.StringVar(value=current_cal_tz if current_cal_tz in cal_tz_values else "Другой")
        self._cal_tz_combo = ttk.Combobox(cal_tz_row, textvariable=self._cal_tz_var, values=cal_tz_values, state="readonly", width=30)
        self._cal_tz_combo.pack(side=tk.LEFT, padx=5)
        self._cal_tz_combo.bind("<<ComboboxSelected>>", self._on_calendar_tz_changed)
        self._custom_cal_tz_var = tk.StringVar()
        self._custom_cal_tz_entry = ttk.Entry(cal_tz_row, textvariable=self._custom_cal_tz_var, width=30)
        if self._cal_tz_var.get() == "Другой":
            self._custom_cal_tz_entry.pack(side=tk.LEFT, padx=5)
        else:
            self._custom_cal_tz_entry.pack_forget()

        # Results
        self._results_frame = ttk.LabelFrame(self._scrollable, text="Результаты проверки", padding=5)
        self._results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self._results_text = tk.Text(self._results_frame, height=14, wrap=tk.WORD, font=("Consolas", 9))
        self._results_text.pack(fill=tk.BOTH, expand=True)

        self._status_var = tk.StringVar(value="1. Нажмите «Определить автоматически»\n2. Затем «Проверить подключения»")
        self._status_label = ttk.Label(self._scrollable, textvariable=self._status_var, font=("", 9, "bold"))
        self._status_label.pack(anchor=tk.W, pady=5)

        bind_shortcuts_recursive(self._scrollable)

    def _apply_password_mask(self):
        self._ews_pass_var.set("••••••••")
        self._ews_pass_entry.configure(state="readonly")
        self._password_masked = True
        self._change_pass_btn.pack(side=tk.LEFT, padx=5)
        self._ews_remember_var.set(True)

    def _on_change_password(self):
        self._ews_pass_entry.configure(state="normal")
        self._ews_pass_var.set("")
        self._password_masked = False
        self._change_pass_btn.pack_forget()
        self._ews_pass_status_var.set("введите новый пароль")

    def _auto_detect(self):
        if self.container and self.container._mcp_transport and self.container._mcp_transport.is_connected():
            transport = self.container._mcp_transport
            tool_names = transport.list_tools()
            has_find = "find_events" in tool_names
            has_create = "create_event" in tool_names
            if has_find and has_create:
                cmd = getattr(transport, "command", "")
                self._command_var.set(cmd)
                self._transport_var.set("exchange-stdio")
                self._find_tool_var.set("find_events")
                self._create_tool_var.set("create_event")
                self._log(f"Exchange MCP найден. Источник: активное подключение. Транспорт: local stdio. Tools: {len(tool_names)}.")
                self._status_var.set("Exchange MCP найден. Нажмите «Применить и подключить Exchange MCP»")
                return

        try:
            from calendar_planner.app.exchange_detector import ExchangeMCPConfigDetector
            config = ExchangeMCPConfigDetector().detect()
            self._detected_config = config
            if config["found"]:
                self._command_var.set(config["command"])
                self._transport_var.set("exchange-stdio")
                self._find_tool_var.set(config["calendar_find_tool"])
                self._create_tool_var.set(config["calendar_create_tool"])
                self._log("Exchange MCP найден. Применяю и подключаю...")
                self._apply_mcp()
            else:
                self._log("Exchange MCP не найден.")
                self._status_var.set("MCP не найден. Проверьте установку Exchange MCP.")
        except Exception as e:
            self._log(f"Ошибка: {e}")

    def _apply_mcp(self):
        if self.container is None:
            self._log("Контейнер не инициализирован."); return
        command = self._command_var.get().strip()
        find_tool = self._find_tool_var.get().strip() or "find_events"
        create_tool = self._create_tool_var.get().strip() or "create_event"
        if not command:
            self._log("[FAIL] Команда MCP пуста. Нажмите «Определить автоматически»."); return
        self._log("Применяю и подключаю Exchange MCP...")
        res = self.container.configure_mcp_stdio(command, find_tool, create_tool, persist=True)
        if res.get("connected"):
            self._log(
                f"Exchange MCP найден и подключён.\n"
                f"Transport: {res.get('transport')}\n"
                f"Tools: {res.get('tools_count')}\n"
                f"{res.get('find_tool_name', 'find_events')}: {'available' if res.get('find_events') else 'missing'}\n"
                f"{res.get('create_tool_name', 'create_event')}: {'available' if res.get('create_event') else 'missing'}"
            )
            self._status_var.set("Exchange MCP найден и подключён. Нажмите «Проверить подключения»")
            if self._on_check_done:
                self._on_check_done(True)
        else:
            self._log(f"[FAIL] MCP не подключён: {res.get('message')}")
            self._status_var.set("MCP не удалось подключить")
        self._transport_var.set("exchange-stdio")

    def _save_ews(self):
        endpoint = self._ews_endpoint_var.get().strip()
        login = self._ews_login_var.get().strip()
        password = self._ews_pass_var.get().strip()
        if password == "••••••••":
            password = ""

        from calendar_planner.app.credential_provider import ews_save_decision
        from calendar_planner.app.env_config import EnvConfigWriter

        # Persist endpoint/login (never password) in the actual .env.
        env_writer = EnvConfigWriter.default()
        env_writer.set({"EWS_ENDPOINT": endpoint, "EWS_USERNAME": login})

        if not login:
            self._log("[FAIL] EWS: не указан логин.")
            return
        if not password:
            # Mask still active => credentials already present; just reconfigure gateway.
            if self._password_masked:
                if self.container:
                    self.container.configure_ews(endpoint, login, None)
                self._log(f"EWS настроен. Логин: {login}. Пароль не изменён.")
                return
            self._log("[FAIL] EWS: не указан пароль.")
            return

        remember = self._ews_remember_var.get()

        if self.container:
            self.container.configure_ews(endpoint, login, password)
        if self._cred_provider:
            self._cred_provider.set_session_credentials(login, password)

        save_result = None
        if remember and self._cred_provider:
            save_result = self._cred_provider.save_persistent(login, password)

        decision = ews_save_decision(remember, save_result)

        # Apply UI outcome.
        self._ews_remember_var.set(bool(decision.get("checkbox")))
        if decision.get("apply_mask"):
            self._ews_pass_var.set("••••••••")
            self._ews_pass_entry.configure(state="readonly")
            self._password_masked = True
            self._change_pass_btn.pack(side=tk.LEFT, padx=5)
        else:
            # Failure: keep the typed password, no mask, allow retry.
            self._ews_pass_entry.configure(state="normal")
            self._password_masked = False
            self._change_pass_btn.pack_forget()
        self._ews_pass_status_var.set(decision.get("status", ""))

        if decision.get("success"):
            if remember:
                self._log(f"EWS сохранён в Windows Credential Manager. Логин: {login}. (read-after-write OK)")
            else:
                self._log("Пароль сохранён только до закрытия приложения (session-only).")
        else:
            self._log(f"EWS: ошибка сохранения ({decision.get('error_code')}). Введённый пароль не очищен — повторите.")

    def _clear_ews(self):
        login = self._ews_login_var.get().strip()
        self._ews_login_var.set("")
        self._ews_pass_var.set("")
        self._ews_pass_status_var.set("не задан")
        self._password_masked = False
        self._ews_pass_entry.configure(state="normal")
        self._change_pass_btn.pack_forget()
        if self._cred_provider:
            self._cred_provider.clear_session_credentials()
            if login:
                self._cred_provider.delete_persistent(login)
        if self.container:
            self.container.reset_directory_gateway()
        self._log("EWS credentials очищены.")

    def _on_timezone_changed(self, event=None):
        selected = self._tz_var.get()
        if selected == "Другой":
            self._custom_tz_entry.pack(side=tk.LEFT, padx=5)
            tz_value = self._custom_tz_var.get().strip()
            if not tz_value:
                return
        else:
            self._custom_tz_entry.pack_forget()
            tz_value = selected
        os.environ["DEFAULT_TIMEZONE"] = tz_value
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").split("\n")
            out_lines = []
            replaced = False
            for line in lines:
                key = line.split("=")[0].strip() if "=" in line else ""
                if key == "DEFAULT_TIMEZONE":
                    out_lines.append(f"DEFAULT_TIMEZONE={tz_value}")
                    replaced = True
                else:
                    out_lines.append(line)
            if not replaced:
                out_lines.append(f"DEFAULT_TIMEZONE={tz_value}")
            env_file.write_text("\n".join(out_lines), encoding="utf-8")
        else:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"DEFAULT_TIMEZONE={tz_value}\n")
        self._log(f"Часовой пояс по умолчанию: {tz_value}")

    def _on_calendar_tz_changed(self, event=None):
        selected = self._cal_tz_var.get()
        if selected == "Другой":
            self._custom_cal_tz_entry.pack(side=tk.LEFT, padx=5)
            tz_value = self._custom_cal_tz_var.get().strip()
            if not tz_value:
                return
        else:
            self._custom_cal_tz_entry.pack_forget()
            tz_value = selected
        os.environ["CALENDAR_MISSING_TIMEZONE"] = tz_value
        from calendar_planner.app.settings import settings
        settings.CALENDAR_MISSING_TIMEZONE = tz_value
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").split("\n")
            out_lines = []
            replaced = False
            for line in lines:
                key = line.split("=")[0].strip() if "=" in line else ""
                if key == "CALENDAR_MISSING_TIMEZONE":
                    out_lines.append(f"CALENDAR_MISSING_TIMEZONE={tz_value}")
                    replaced = True
                else:
                    out_lines.append(line)
            if not replaced:
                out_lines.append(f"CALENDAR_MISSING_TIMEZONE={tz_value}")
            env_file.write_text("\n".join(out_lines), encoding="utf-8")
        else:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"CALENDAR_MISSING_TIMEZONE={tz_value}\n")
        self._log(f"Часовой пояс для событий без tz: {tz_value}")
        if self._on_setting_changed:
            self._on_setting_changed()

        # Numeric duration unit
        dur_frame = ttk.LabelFrame(self._scrollable, text="Единица числовой длительности", padding=5)
        dur_frame.pack(fill=tk.X, pady=5)
        dur_row = ttk.Frame(dur_frame)
        dur_row.pack(fill=tk.X, pady=2)
        ttk.Label(dur_row, text="Единица:", width=15).pack(side=tk.LEFT)
        dur_values = ["Часы", "Минуты", "Авто"]
        dur_internal = {"Часы": "hours", "Минуты": "minutes", "Авто": "auto"}
        current_dur = os.environ.get("DURATION_NUMERIC_UNIT", "auto")
        current_dur_display = "Авто"
        for display, internal in dur_internal.items():
            if internal == current_dur:
                current_dur_display = display
                break
        self._dur_var = tk.StringVar(value=current_dur_display)
        self._dur_combo = ttk.Combobox(dur_row, textvariable=self._dur_var, values=dur_values, state="readonly", width=30)
        self._dur_combo.pack(side=tk.LEFT, padx=5)
        self._dur_combo.bind("<<ComboboxSelected>>", self._on_duration_unit_changed)

    def _on_duration_unit_changed(self, event=None):
        dur_internal = {"Часы": "hours", "Минуты": "minutes", "Авто": "auto"}
        value = dur_internal.get(self._dur_var.get(), "auto")
        os.environ["DURATION_NUMERIC_UNIT"] = value
        from calendar_planner.app.settings import settings
        settings.DURATION_NUMERIC_UNIT = value
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").split("\n")
            out_lines = []
            replaced = False
            for line in lines:
                key = line.split("=")[0].strip() if "=" in line else ""
                if key == "DURATION_NUMERIC_UNIT":
                    out_lines.append(f"DURATION_NUMERIC_UNIT={value}")
                    replaced = True
                else:
                    out_lines.append(line)
            if not replaced:
                out_lines.append(f"DURATION_NUMERIC_UNIT={value}")
            env_file.write_text("\n".join(out_lines), encoding="utf-8")
        else:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"DURATION_NUMERIC_UNIT={value}\n")
        self._log(f"Единица числовой длительности: {self._dur_var.get()}")

    def _check_directory(self):
        if self.container is None: return
        ep = self._ews_endpoint_var.get().strip()
        lg = self._ews_login_var.get().strip()
        pw = self._ews_pass_var.get().strip()
        if pw == "••••••••":
            pw = ""
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
        if pw == "••••••••":
            pw = ""
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
