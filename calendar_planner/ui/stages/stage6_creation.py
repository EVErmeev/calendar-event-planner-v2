from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calendar_planner.domain.models import FinalEventDraft
from calendar_planner.ui.event_editor import EventEditorFrame


class Stage6CreationFrame(ttk.Frame):
    def __init__(self, parent, drafts: list[FinalEventDraft], on_recheck=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.drafts = drafts
        self.on_recheck = on_recheck
        self._editor_frame: EventEditorFrame | None = None
        self._draft_vars: dict[str, tk.BooleanVar] = {}
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
        self._build_ui()