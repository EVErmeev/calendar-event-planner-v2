from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calendar_planner.app.credential_provider import CredentialProvider


class Stage1ConnectionsFrame(ttk.Frame):
    def __init__(self, parent, container=None, credential_provider=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.container = container
        self._cred_provider = credential_provider or CredentialProvider()
        self._detected_config: dict = {}
        self._last_results: list[dict] = []
        self._ready = False
        self._build_ui()

    def _build_ui(self):
        h = ttk.Frame(self)
        h.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(h, text="1. Подключения", font=("", 12, "bold")).pack(anchor=tk.W)

        # Buttons row
        btn = ttk.Frame(self)
        btn.pack(fill=tk.X, pady=5)
        ttk.Button(btn, text="Определить автоматически", command=self._auto_detect).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Проверить подключения", command=self._check_now).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Копировать результат", command=self._copy).pack(side=tk.LEFT, padx=2)

        # Auth notice
        auth = ttk.LabelFrame(self, text="Авторизация почты", padding=5)
        auth.pack(fill=tk.X, pady=5)
        ttk.Label(auth, text="Авторизация почты выполнена установщиком Exchange MCP.\nЛогин и пароль почты в приложении не требуются.", font=("", 8)).pack(anchor=tk.W)

        # Exchange MCP config
        mcp_frame = ttk.LabelFrame(self, text="Exchange MCP", padding=5)
        mcp_frame.pack(fill=tk.X, pady=5)

        self._transport_var = tk.StringVar(value="auto")
        row = ttk.Frame(mcp_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Тип:", width=15).pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self._transport_var, values=["auto", "exchange-stdio", "http"], state="readonly", width=20).pack(side=tk.LEFT, padx=5)

        row = ttk.Frame(mcp_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Команда:", width=15).pack(side=tk.LEFT)
        self._command_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._command_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        row = ttk.Frame(mcp_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Calendar tool:", width=15).pack(side=tk.LEFT)
        self._find_tool_var = tk.StringVar(value="find_events")
        ttk.Entry(row, textvariable=self._find_tool_var, width=20).pack(side=tk.LEFT, padx=5)

        row = ttk.Frame(mcp_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Create tool:", width=15).pack(side=tk.LEFT)
        self._create_tool_var = tk.StringVar(value="create_event")
        ttk.Entry(row, textvariable=self._create_tool_var, width=20).pack(side=tk.LEFT, padx=5)

        # EWS Directory block
        ews_frame = ttk.LabelFrame(self, text="Корпоративный каталог сотрудников (EWS)", padding=5)
        ews_frame.pack(fill=tk.X, pady=5)

        src_label = ttk.Label(ews_frame, text="Источник: Exchange EWS GAL | Метод: ResolveNames | SearchScope: ActiveDirectory", font=("", 8))
        src_label.pack(anchor=tk.W)

        row = ttk.Frame(ews_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="EWS endpoint:", width=15).pack(side=tk.LEFT)
        self._ews_endpoint_var = tk.StringVar(value="https://mail.1cbit.ru/EWS/Exchange.asmx")
        ttk.Entry(row, textvariable=self._ews_endpoint_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        row = ttk.Frame(ews_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Логин:", width=15).pack(side=tk.LEFT)
        self._ews_login_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._ews_login_var, width=25).pack(side=tk.LEFT, padx=5)

        row = ttk.Frame(ews_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Пароль:", width=15).pack(side=tk.LEFT)
        self._ews_pass_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._ews_pass_var, width=25, show="*").pack(side=tk.LEFT, padx=5)

        row = ttk.Frame(ews_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Тестовое ФИО:", width=15).pack(side=tk.LEFT)
        self._ews_probe_var = tk.StringVar(value="Ермеев Егор")
        ttk.Entry(row, textvariable=self._ews_probe_var, width=25).pack(side=tk.LEFT, padx=5)

        ews_btn = ttk.Frame(ews_frame)
        ews_btn.pack(fill=tk.X, pady=5)
        ttk.Button(ews_btn, text="Сохранить EWS", command=self._save_ews).pack(side=tk.LEFT, padx=2)
        ttk.Button(ews_btn, text="Проверить каталог", command=self._check_directory).pack(side=tk.LEFT, padx=2)
        ttk.Button(ews_btn, text="Очистить credentials", command=self._clear_ews).pack(side=tk.LEFT, padx=2)

        # Results
        self._results_frame = ttk.LabelFrame(self, text="Результаты проверки", padding=5)
        self._results_frame.pack(fill=tk.X, pady=5)
        self._results_text = tk.Text(self._results_frame, height=12, wrap=tk.WORD, font=("Consolas", 9))
        self._results_text.pack(fill=tk.BOTH, expand=True)

        # Status
        self._status_var = tk.StringVar(value="Нажмите «Проверить подключения»")
        st = ttk.Label(self, textvariable=self._status_var, font=("", 9, "bold"))
        st.pack(anchor=tk.W, pady=5)
        self._status_label = st

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
                self._log("Exchange MCP найден автоматически.")
                self._log(f"  Транспорт: {config['transport']}")
                self._log(f"  Tools: {', '.join(config['tools'][:5])}...")
                self._log(f"  Calendar tool: {config['calendar_find_tool']}")
                self._log(f"  Create tool: {config['calendar_create_tool']}")
                self._log("  Корпоративный каталог: Exchange EWS GAL (ResolveNames)")
                self._log("    search_emails не используется как каталог.")
            else:
                self._log("Exchange MCP не найден автоматически.")
        except Exception as e:
            self._log(f"Ошибка автоопределения: {e}")

    def _save_ews(self):
        endpoint = self._ews_endpoint_var.get().strip()
        login = self._ews_login_var.get().strip()
        password = self._ews_pass_var.get().strip()

        import os
        if endpoint:
            os.environ["EWS_ENDPOINT"] = endpoint
        if login:
            os.environ["EWS_USERNAME"] = login

        if password:
            self._cred_provider.set_session_credentials(login, password)
            self._log(f"EWS credentials сохранены в сессии (логин: {login})")
            self._log("Пароль хранится только в памяти, не в .env.")
        else:
            self._log("EWS endpoint сохранён. Введите пароль для проверки каталога.")

        # Never write password to .env or env vars
        if "EWS_PASSWORD" in os.environ:
            os.environ.pop("EWS_PASSWORD", None)

        from pathlib import Path
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").split("\n")
            updates = {"EWS_ENDPOINT": endpoint, "EWS_USERNAME": login}
            new_lines = []
            seen = set()
            for line in lines:
                key = line.split("=")[0].strip() if "=" in line else ""
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}")
                    seen.add(key)
                    del updates[key]
                elif key == "EWS_PASSWORD":
                    continue  # Never save password
                else:
                    new_lines.append(line)
            for k, v in updates.items():
                if v and k not in seen:
                    new_lines.append(f"{k}={v}")
            env_file.write_text("\n".join(new_lines), encoding="utf-8")
            self._log("EWS endpoint и логин сохранены в .env (пароль не записан).")

    def _check_directory(self):
        endpoint = self._ews_endpoint_var.get().strip()
        login = self._ews_login_var.get().strip()
        password = self._ews_pass_var.get().strip()
        probe_name = self._ews_probe_var.get().strip()

        # Use session credentials if saved
        if not password:
            creds = self._cred_provider.get_credentials()
            if creds.available:
                password = creds.password
                if not login:
                    login = creds.username

        if not endpoint or not login or not password:
            self._log("[FAIL] Directory: не указаны endpoint, логин или пароль.")
            return

        self._log(f"Поиск в каталоге: \"{probe_name}\"...")

        try:
            from calendar_planner.participants.ews_directory_gateway import (
                EWSDirectoryGateway,
            )
            gw = EWSDirectoryGateway(endpoint=endpoint, username=login, password=password)
            result = gw.search(probe_name)

            self._log(f"  Статус: {result.status}")
            self._log(f"  Источник: {result.source}")
            self._log(f"  Найдено: {len(result.people)}")

            for p in result.people[:5]:
                masked_email = p.email[:3] + "***" if len(p.email) > 3 else "***"
                self._log(f"  — {p.display_name}")
                self._log(f"    email: {masked_email}")
                if p.company:
                    self._log(f"    компания: {p.company}")
                if p.department:
                    self._log(f"    подразделение: {p.department}")
                if p.job_title:
                    self._log(f"    должность: {p.job_title}")

            if result.status == "success":
                self._log("[OK] Directory: EWS ResolveNames работает.")
            elif result.status == "ambiguous":
                self._log("[OK] Directory: EWS ResolveNames доступен (несколько вариантов).")
            elif result.status == "not_found":
                self._log("[OK] Directory: EWS ResolveNames доступен (сотрудник не найден).")
            elif result.status == "auth_failed":
                self._log("[FAIL] Directory: ошибка авторизации. Проверьте логин и пароль.")
            elif result.status == "forbidden":
                self._log("[FAIL] Directory: доступ запрещён (403).")
            elif result.status == "timeout":
                self._log("[FAIL] Directory: таймаут запроса.")
            else:
                self._log(f"[FAIL] Directory: {result.error_message or 'неизвестная ошибка'}.")

        except Exception as e:
            self._log(f"[FAIL] Directory: ошибка — {e}")

    def _clear_ews(self):
        self._ews_login_var.set("")
        self._ews_pass_var.set("")
        self._cred_provider.clear_session_credentials()
        self._log("EWS credentials очищены.")

    def _check_now(self):
        if self.container is None:
            self._log("Контейнер не инициализирован.")
            return
        self._log("Проверка подключений...")

        import os

        # Inject session credentials into container before check
        login = self._ews_login_var.get().strip()
        password = self._ews_pass_var.get().strip()
        if not password:
            creds = self._cred_provider.get_credentials()
            if creds.available:
                password = creds.password
        if login and password:
            os.environ["EWS_USERNAME"] = login
            os.environ["EWS_PASSWORD"] = password

        result = self.container.check_all_connections()
        self._last_results = result.get("results", [])
        self._ready = result.get("ready_for_analysis", False)

        for r in self._last_results:
            sym = {"success": "OK", "failed": "FAIL", "warning": "WARN"}.get(r.get("status", ""), "?")
            self._log(f"  [{sym}] {r.get('component', '?')}: {r.get('message', '')}")
            error = r.get("error", "")
            if error:
                self._log(f"       {error}")

        # Clean password from env after check
        if "EWS_PASSWORD" in os.environ:
            os.environ.pop("EWS_PASSWORD", None)

        status = "ГОТОВ К АНАЛИЗУ" if self._ready else "НЕ ГОТОВ"
        color = "green" if self._ready else "red"
        self._status_var.set(status)
        self._status_label.config(foreground=color)

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

    def get_credential_provider(self):
        return self._cred_provider
