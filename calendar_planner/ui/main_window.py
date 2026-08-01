from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json

from calendar_planner.ui.controllers import StageController
from calendar_planner.session.storage import SessionStorage
from calendar_planner.session.models import RunSession


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Планировщик календарных событий v2")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        self.controller = StageController()
        self.storage = SessionStorage()

        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self._build_top_panel()
        self._build_stage_sidebar()
        self._build_main_area()
        self._build_bottom_panel()

    def _build_top_panel(self) -> None:
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Label(top_frame, text="Источник:").pack(side=tk.LEFT, padx=(0, 5))

        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(top_frame, textvariable=self.source_var, width=60)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(top_frame, text="Выбрать", command=self._select_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Вставить ссылку", command=self._paste_url).pack(side=tk.LEFT, padx=2)

    def _build_stage_sidebar(self) -> None:
        sidebar = ttk.LabelFrame(self.root, text="Этапы", padding=5)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.stage_labels: list[ttk.Label] = []
        self.stage_status_labels: list[ttk.Label] = []
        stage_names = [
            "1. Подключения",
            "2. Поиск встреч",
            "3. Сравнение",
            "4. Участники",
            "5. Дополнительные данные",
            "6. Создание",
        ]

        for i, name in enumerate(stage_names):
            frame = ttk.Frame(sidebar)
            frame.pack(fill=tk.X, pady=2)
            lbl = ttk.Label(frame, text=name, font=("", 9))
            lbl.pack(side=tk.LEFT)
            st_lbl = ttk.Label(frame, text="●", font=("", 8))
            st_lbl.pack(side=tk.RIGHT, padx=(10, 0))
            self.stage_labels.append(lbl)
            self.stage_status_labels.append(st_lbl)

        self._update_stage_indicators()

    def _build_main_area(self) -> None:
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.main_label = ttk.Label(
            self.main_frame,
            text="Welcome to Calendar Event Planner v2",
            font=("", 14),
        )
        self.main_label.pack(pady=20)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.info_text = tk.Text(self.content_frame, height=4, wrap=tk.WORD, font=("Consolas", 9))
        self.info_text.pack(fill=tk.X, pady=5)
        self.info_text.insert(tk.END, (
            "Этот проект - новый самостоятельный календарный планировщик.\n"
            "Он анализирует источник, находит встречи, сравнивает с календарем,\n"
            "определяет участников, собирает дополнительные данные и формирует черновики событий.\n"
            "Dry-run по умолчанию включен. Реальные события не создаются без подтверждения."
        ))

    def _build_bottom_panel(self) -> None:
        bottom = ttk.Frame(self.root, padding=5)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        ttk.Button(bottom, text="← Назад", command=self._prev_stage).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="Далее →", command=self._next_stage).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="Запустить анализ", command=self._run_analysis).pack(side=tk.LEFT, padx=10)
        ttk.Button(bottom, text="Сохранить сессию", command=self._save_session).pack(side=tk.RIGHT, padx=2)
        ttk.Button(bottom, text="Копировать", command=self._copy_results).pack(side=tk.RIGHT, padx=2)

    def _select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл-источник",
            filetypes=[
                ("Все поддерживаемые", "*.xlsx;*.xlsm;*.csv;*.docx;*.pdf;*.txt;*.md;*.html"),
                ("Excel", "*.xlsx;*.xlsm"),
                ("CSV", "*.csv"),
                ("Word", "*.docx"),
                ("PDF", "*.pdf"),
                ("Text/Markdown", "*.txt;*.md"),
            ],
        )
        if path:
            self.source_var.set(path)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Выбран файл: {path}\nГотов к анализу.")

    def _paste_url(self) -> None:
        try:
            text = self.root.clipboard_get()
            if text:
                self.source_var.set(text)
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, f"Вставлена ссылка: {text}\nГотов к анализу.")
        except Exception:
            messagebox.showwarning("Ошибка", "Не удалось вставить из буфера обмена")

    def _run_analysis(self) -> None:
        source = self.source_var.get().strip()
        if not source:
            messagebox.showwarning("Внимание", "Укажите файл или ссылку")
            return

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, f"Анализ источника: {source}\n")
        self.info_text.insert(tk.END, "=" * 60 + "\n")

        try:
            from calendar_planner.domain.models import SourceReference
            from calendar_planner.source.registry import registry
            from calendar_planner.extraction.structured import StructuredExtractor
            from calendar_planner.app.settings import settings

            if source.startswith("http"):
                src_ref = SourceReference(type="url", url=source)
            else:
                src_ref = SourceReference(type="file", path=source)

            extracted = registry.read_source(src_ref)
            self.info_text.insert(tk.END, f"Тип: {src_ref.type}\n")
            self.info_text.insert(tk.END, f"Листов загружено: {list(extracted.sheets.keys())}\n\n")

            extractor = StructuredExtractor(date_policy=settings.MEETING_DATE_POLICY)
            candidates = extractor.extract(extracted)

            self.controller.set_extracted(extracted)
            self.controller.set_candidates(candidates)
            self.controller.set_skipped_rows(extractor.skipped_rows)

            all_candidates = []
            for sheet_name, sheet_cands in candidates.items():
                all_candidates.extend(sheet_cands)

            for c in all_candidates:
                self.info_text.insert(tk.END, (
                    f"[{c.candidate_id}] {c.subject[:60]}\n"
                    f"  Дата: {c.start_date or '—'} | Время: {c.start_time or '—'} | TZ: {c.timezone or '—'}\n"
                ))

            self.info_text.insert(tk.END, f"\nВсего найдено: {len(all_candidates)} кандидатов\n")
            self.info_text.insert(tk.END, f"Пропущено: {len(extractor.skipped_rows)} строк\n")
            for sr in extractor.skipped_rows:
                self.info_text.insert(tk.END, f"  {sr['sheet']} R{sr['row']}: {sr['reason']}\n")

            self.controller.set_stage_success("stage_1")
            self.controller.set_stage_success("stage_2")
            self._update_stage_indicators()

        except Exception as e:
            self.info_text.insert(tk.END, f"\nОШИБКА: {e}\n")
            self.controller.set_stage_error("stage_2", str(e))

    def _save_session(self) -> None:
        try:
            session = self.controller.create_session(self.storage)
            self.info_text.insert(tk.END, f"\nСессия сохранена: {session.session_id}\n")
            self.info_text.insert(tk.END, f"Каталог: runs/{session.session_id}/\n")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить сессию: {e}")

    def _prev_stage(self) -> None:
        self.controller.prev_stage()
        self._update_stage_indicators()

    def _next_stage(self) -> None:
        self.controller.next_stage()
        self._update_stage_indicators()

    def _copy_results(self) -> None:
        text = self.info_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.info_text.insert(tk.END, "\n[Результаты скопированы в буфер обмена]\n")

    def _update_stage_indicators(self) -> None:
        colors = {
            "success": "green",
            "success_with_warnings": "orange",
            "failed": "red",
            "in_progress": "blue",
            "stale": "gray",
            "not_started": "lightgray",
        }
        for i, (lbl, st_lbl) in enumerate(zip(self.stage_labels, self.stage_status_labels)):
            status = self.controller.get_stage_status(i)
            color = colors.get(status, "lightgray")
            st_lbl.config(foreground=color)
            if i == self.controller.current_stage:
                lbl.config(font=("", 9, "bold"))
            else:
                lbl.config(font=("", 9))

    def _on_close(self) -> None:
        if self.controller.has_unsaved_changes():
            result = messagebox.askyesnocancel(
                "Несохранённые изменения",
                "У вас есть несохранённые изменения. Сохранить сессию перед выходом?",
            )
            if result is None:
                return
            if result:
                self._save_session()
        self.root.destroy()