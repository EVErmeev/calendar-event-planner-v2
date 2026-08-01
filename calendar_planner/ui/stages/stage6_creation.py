from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calendar_planner.domain.models import FinalEventDraft
from calendar_planner.ui.event_editor import EventEditorFrame


class Stage6CreationFrame(ttk.Frame):
    def __init__(self, parent, drafts: list[FinalEventDraft], on_recheck=None, on_create=None, on_real_create=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.drafts = drafts
        self.on_recheck = on_recheck
        self.on_create = on_create
        self.on_real_create = on_real_create
        self._editor_frame: EventEditorFrame | None = None
        self._draft_vars: dict[str, tk.BooleanVar] = {}
        self._current_draft: FinalEventDraft | None = None
        self._results_table: ttk.Frame | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Этап 6 — Создание событий", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Черновики событий для подтверждения и создания", font=("", 8)).pack(anchor=tk.W)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        canvas = tk.Canvas(left_frame)
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=canvas.yview)
        self._left_scrollable = ttk.Frame(canvas)
        self._left_scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._left_scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_draft_list(self._left_scrollable)

        self._right_frame = ttk.Frame(paned)
        paned.add(self._right_frame, weight=2)

        no_draft_label = ttk.Label(
            self._right_frame,
            text="Выберите черновик из списка слева\nдля просмотра и редактирования",
            font=("", 10, "italic"),
            anchor=tk.CENTER,
            justify=tk.CENTER,
        )
        no_draft_label.pack(expand=True)

        self._build_action_bar()

    def _build_draft_list(self, parent: ttk.Frame) -> None:
        for draft in self.drafts:
            var = tk.BooleanVar(value=draft.selected)
            self._draft_vars[draft.draft_id] = var
            self._add_draft_row(parent, draft, var)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Button(btn_frame, text="Выбрать все", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Снять все", command=self._deselect_all).pack(side=tk.LEFT, padx=2)

    def _add_draft_row(self, parent: ttk.Frame, draft: FinalEventDraft, var: tk.BooleanVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2, padx=5)

        var.trace_add("write", lambda *a, d=draft, v=var: setattr(d, "selected", v.get()))
        cb = ttk.Checkbutton(row, variable=var)
        cb.pack(side=tk.LEFT)

        info_frame = ttk.Frame(row)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        subject = draft.subject.value or "Без темы"
        display = f"[{draft.draft_id}] {subject[:60]}"
        btn = ttk.Button(info_frame, text=display, command=lambda d=draft: self._on_draft_click(d))
        btn.pack(anchor=tk.W)

        date_info = f"{draft.start_date.value or '?'} {draft.start_time.value or ''}"
        ttk.Label(info_frame, text=date_info, font=("", 7)).pack(anchor=tk.W)

        status_text = "Готов" if draft.is_ready else "Не готов"
        status_color = "green" if draft.is_ready else "orange"
        ttk.Label(info_frame, text=status_text, foreground=status_color, font=("", 7)).pack(anchor=tk.W)

    def _on_draft_click(self, draft: FinalEventDraft) -> None:
        self._current_draft = draft
        for widget in self._right_frame.winfo_children():
            widget.destroy()

        self._editor_frame = EventEditorFrame(
            self._right_frame,
            draft,
            on_recheck=self._on_recheck_callback,
        )
        self._editor_frame.pack(fill=tk.BOTH, expand=True)

    def _on_recheck_callback(self, draft: FinalEventDraft) -> None:
        if self.on_recheck:
            self.on_recheck(draft)

    def _select_all(self) -> None:
        for var in self._draft_vars.values():
            var.set(True)
        for d in self.drafts:
            d.selected = True

    def _deselect_all(self) -> None:
        for var in self._draft_vars.values():
            var.set(False)
        for d in self.drafts:
            d.selected = False

    def get_selected_drafts(self) -> list[FinalEventDraft]:
        return [d for d in self.drafts if self._draft_vars.get(d.draft_id, tk.BooleanVar(value=False)).get()]

    def refresh(self, drafts: list[FinalEventDraft], on_recheck=None) -> None:
        self.drafts = drafts
        self.on_recheck = on_recheck or self.on_recheck
        for widget in self.winfo_children():
            widget.destroy()
        self._editor_frame = None
        self._draft_vars = {}
        self._current_draft = None
        self._results_table = None
        self._build_ui()

    def _build_action_bar(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, pady=(10, 0), padx=5)
        ttk.Button(bar, text="Предпросмотр (dry-run)", command=self._create_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Предпросмотр отмеченных", command=self._create_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Создать выбранное", command=self._real_create_selected).pack(side=tk.LEFT, padx=(20, 2))
        ttk.Button(bar, text="Создать отмеченные", command=self._real_create_checked).pack(side=tk.LEFT, padx=2)

    def _create_selected(self) -> None:
        draft = self._current_draft
        if draft is None:
            from tkinter import messagebox
            messagebox.showinfo("Информация", "Сначала выберите черновик для предпросмотра.")
            return
        if self.on_create is not None:
            self.on_create(draft)
        else:
            self._show_dry_run_result(draft.draft_id, draft.subject.value or "Без темы")

    def _create_checked(self) -> None:
        selected = self.get_selected_drafts()
        if not selected:
            from tkinter import messagebox
            messagebox.showinfo("Информация", "Нет отмеченных черновиков.")
            return
        if self.on_create is not None:
            for draft in selected:
                self.on_create(draft)
        else:
            for draft in selected:
                self._show_dry_run_result(draft.draft_id, draft.subject.value or "Без темы")

    def _real_create_selected(self) -> None:
        draft = self._current_draft
        if draft is None:
            from tkinter import messagebox
            messagebox.showinfo("Информация", "Сначала выберите черновик.")
            return
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Подтверждение создания",
            f"Создать реальное календарное событие?\n\n"
            f"Тема: {draft.subject.value}\n"
            f"Дата: {draft.start_date.value} {draft.start_time.value}\n"
            f"Часовой пояс: {draft.timezone.value}\n\n"
            f"Это реальная операция создания события в календаре.",
        ):
            return
        if self.on_real_create is None:
            messagebox.showinfo("Информация", "Создание недоступно — отсутствует подключение к календарю.")
            return
        self.on_real_create(draft)

    def _real_create_checked(self) -> None:
        selected = self.get_selected_drafts()
        if not selected:
            from tkinter import messagebox
            messagebox.showinfo("Информация", "Нет отмеченных черновиков.")
            return
        from tkinter import messagebox
        count = len(selected)
        subjects = "\n".join(f"  - {d.subject.value}" for d in selected)
        if not messagebox.askyesno(
            "Подтверждение создания",
            f"Создать {count} реальных календарных событий?\n\n{subjects}\n\nЭто реальная операция создания событий в календаре.",
        ):
            return
        if self.on_real_create is None:
            messagebox.showinfo("Информация", "Создание недоступно — отсутствует подключение к календарю.")
            return
        for draft in selected:
            self.on_real_create(draft)

    def _show_dry_run_result(self, draft_id: str, subject: str) -> None:
        self._ensure_results_table()
        row = ttk.Frame(self._results_table)
        row.pack(fill=tk.X, pady=1)
        ttk.Label(row, text=draft_id, width=12, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text=subject[:40], width=30, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text="DRY RUN — событие не создано", foreground="gray", width=30, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text="—", width=12, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text="—", width=20, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text="—", width=20, anchor=tk.W).pack(side=tk.LEFT, padx=2)

    def show_creation_result(self, draft_id: str, subject: str, status: str, event_id: str = "", url: str = "", errors: str = "") -> None:
        self._ensure_results_table()
        row = ttk.Frame(self._results_table)
        row.pack(fill=tk.X, pady=1)
        ttk.Label(row, text=draft_id, width=12, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text=subject[:40], width=30, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        status_color = "green" if status == "created" else "red"
        status_text = "Создано" if status == "created" else f"Ошибка: {status}"
        ttk.Label(row, text=status_text, foreground=status_color, width=30, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text=event_id or "—", width=12, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text=url or "—", width=20, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        ttk.Label(row, text=errors or "—", width=20, anchor=tk.W).pack(side=tk.LEFT, padx=2)

    def _ensure_results_table(self) -> None:
        if self._results_table is not None:
            return
        results_frame = ttk.LabelFrame(self, text="Результаты создания", padding=5)
        results_frame.pack(fill=tk.X, pady=(10, 0), padx=5)
        self._results_table = results_frame

        header = ttk.Frame(self._results_table)
        header.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(header, text="Draft ID", width=12, anchor=tk.W, font=("", 8, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="Subject", width=30, anchor=tk.W, font=("", 8, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="Status", width=30, anchor=tk.W, font=("", 8, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="Event ID", width=12, anchor=tk.W, font=("", 8, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="URL", width=20, anchor=tk.W, font=("", 8, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="Errors", width=20, anchor=tk.W, font=("", 8, "bold")).pack(side=tk.LEFT, padx=2)