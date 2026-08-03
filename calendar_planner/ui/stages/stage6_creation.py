from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calendar_planner.domain.models import FinalEventDraft
from calendar_planner.domain.validation import preflight_validate
from calendar_planner.ui.event_editor import EventEditorFrame

_STATUS_TEXT = {
    "validation_failed": "Валидация не пройдена",
    "transport_failed": "Ошибка транспорта",
    "server_rejected": "Сервер отклонил",
    "unknown_response": "Ответ не распознан",
    "created_unverified": "Создано (не проверено)",
    "created_verified": "Создано и подтверждено",
    "dry_run": "DRY RUN — событие не создано",
    "cancelled": "Отменено пользователем",
}

_STATUS_TAG = {
    "validation_failed": "failed",
    "transport_failed": "failed",
    "server_rejected": "failed",
    "unknown_response": "failed",
    "created_unverified": "created",
    "created_verified": "created",
    "dry_run": "dry_run",
    "cancelled": "dry_run",
}


class Stage6CreationFrame(ttk.Frame):
    def __init__(self, parent, drafts: list[FinalEventDraft], on_recheck=None, on_create=None, on_real_create=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.drafts = drafts
        self.on_recheck = on_recheck
        self.on_create = on_create
        self.on_real_create = on_real_create
        self._editor_frame: EventEditorFrame | None = None
        self._draft_vars: dict[str, tk.BooleanVar] = {}
        self._draft_widgets: dict[str, dict] = {}
        self._current_draft: FinalEventDraft | None = None
        self._results_table: ttk.LabelFrame | None = None
        self._results_tree: ttk.Treeview | None = None
        self._attempts: dict[str, dict] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Этап 6 — Создание событий", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Карточки событий для подтверждения и создания", font=("", 8)).pack(anchor=tk.W)
        ttk.Label(
            header,
            text="Карточка события — это предварительно заполненное событие календаря. На этом этапе оно ещё не создано.",
            font=("", 8, "italic"),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(2, 0))

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
        self._right_frame.pack_propagate(False)
        paned.add(self._right_frame, weight=2)

        no_draft_label = ttk.Label(
            self._right_frame,
            text="Выберите карточку из списка слева\nдля просмотра и редактирования",
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

        if self.drafts:
            self.after(10, lambda: self._on_draft_click(self.drafts[0]))

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
        date_lbl = ttk.Label(info_frame, text=date_info, font=("", 7))
        date_lbl.pack(anchor=tk.W)

        preflight = preflight_validate(draft)
        draft.is_ready = preflight.ready
        if preflight.ready:
            status_lbl = ttk.Label(info_frame, text="Готово", foreground="green", font=("", 7))
            status_lbl.pack(anchor=tk.W)
        else:
            errors_short = ", ".join(e["message_ru"][:40] for e in preflight.blocking_errors[:2])
            status_lbl = ttk.Label(info_frame, text=errors_short or "Не готово", foreground="red", font=("", 7), wraplength=300)
            status_lbl.pack(anchor=tk.W)

        self._draft_widgets[draft.draft_id] = {
            "subject_btn": btn,
            "date_lbl": date_lbl,
            "status_lbl": status_lbl,
        }

    def refresh_card_row(self, draft_or_id: FinalEventDraft | str) -> None:
        if isinstance(draft_or_id, FinalEventDraft):
            draft = draft_or_id
            draft_id = draft.draft_id
        else:
            draft_id = draft_or_id
            draft = next((d for d in self.drafts if d.draft_id == draft_id), None)

        if draft is None or draft_id not in self._draft_widgets:
            return

        w = self._draft_widgets[draft_id]

        subject = draft.subject.value or "Без темы"
        w["subject_btn"].configure(text=f"[{draft_id}] {subject[:60]}")

        date_info = f"{draft.start_date.value or '?'} {draft.start_time.value or ''}"
        w["date_lbl"].configure(text=date_info)

        preflight = preflight_validate(draft)
        draft.is_ready = preflight.ready
        if preflight.ready:
            w["status_lbl"].configure(text="Готово", foreground="green")
        else:
            errors_short = ", ".join(e["message_ru"][:40] for e in preflight.blocking_errors[:2])
            w["status_lbl"].configure(text=errors_short or "Не готово", foreground="red")

    def _on_draft_click(self, draft: FinalEventDraft) -> None:
        self._current_draft = draft
        for widget in self._right_frame.winfo_children():
            widget.destroy()

        self._editor_frame = EventEditorFrame(
            self._right_frame,
            draft,
            on_recheck=self._on_recheck_callback,
            on_draft_updated=self.refresh_card_row,
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
        self._draft_widgets = {}
        self._current_draft = None
        self._results_table = None
        self._results_tree = None
        self._attempts = {}
        self._build_ui()

    def _build_action_bar(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, pady=(10, 0), padx=5)
        ttk.Button(bar, text="Предпросмотр (dry-run)", command=self._create_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Предпросмотр отмеченных", command=self._create_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Создать текущую карточку", command=self._real_create_selected).pack(side=tk.LEFT, padx=(20, 2))
        ttk.Button(bar, text="Создать отмеченные события", command=self._real_create_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Открыть папку логов", command=self._open_logs_folder).pack(side=tk.LEFT, padx=(20, 2))

    def _create_selected(self) -> None:
        draft = self._current_draft
        if draft is None:
            from tkinter import messagebox
            messagebox.showinfo("�?нформация", "Сначала выберите карточку для предпросмотра.")
            return
        if self.on_create is not None:
            self.on_create(draft)
        else:
            self._show_dry_run_result(draft.draft_id, draft.subject.value or "Без темы")

    def _create_checked(self) -> None:
        selected = self.get_selected_drafts()
        if not selected:
            from tkinter import messagebox
            messagebox.showinfo("�?нформация", "Нет отмеченных карточек событий.")
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
            messagebox.showinfo("�?нформация", "Сначала выберите карточку.")
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
            messagebox.showinfo("�?нформация", "Создание недоступно — отсутствует подключение к календарю.")
            return
        self.on_real_create(draft)

    def _real_create_checked(self) -> None:
        selected = self.get_selected_drafts()
        if not selected:
            from tkinter import messagebox
            messagebox.showinfo("�?нформация", "Нет отмеченных карточек событий.")
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
            messagebox.showinfo("�?нформация", "Создание недоступно — отсутствует подключение к календарю.")
            return
        for draft in selected:
            self.on_real_create(draft)

    def _show_dry_run_result(self, draft_id: str, subject: str) -> None:
        self._ensure_results_table()
        self._results_tree.insert("", tk.END, values=(
            draft_id,
            subject[:60],
            "DRY RUN — событие не создано",
            "—",
        ))

    def show_creation_result(self, draft_id: str, subject: str, status: str, event_id: str = "", url: str = "", errors: str = "") -> None:
        self._ensure_results_table()
        if status == "created":
            status_text = "Создано" + (f" (ID: {event_id})" if event_id else "")
            tag = "created"
        elif status == "dry_run":
            status_text = "DRY RUN — payload корректен, событие не создано"
            tag = "dry_run"
        elif status == "invalid":
            status_text = "Ошибка валидации"
            tag = "failed"
        else:
            status_text = f"Ошибка: {status}"
            tag = "failed"
        self._results_tree.insert("", tk.END, values=(
            draft_id,
            subject[:60],
            status_text,
            errors or "—",
        ), tags=(tag,))

    def show_creation_attempt(self, attempt, attempt_id: str | None = None) -> None:
        """Render a CreationAttemptResult into the results table."""
        self._ensure_results_table()
        aid = attempt_id or getattr(attempt, "attempt_id", "")
        if not aid:
            aid = f"att-{len(self._attempts) + 1}"
        self._attempts[aid] = attempt.to_dict() if hasattr(attempt, "to_dict") else dict(attempt)

        status = getattr(attempt, "status", "")
        code = getattr(attempt, "error_code", None)
        event_id = getattr(attempt, "event_id", None) or ""
        subject = getattr(attempt, "subject", "") or "Без темы"

        status_text = _STATUS_TEXT.get(status, status)
        if status in ("created_verified", "created_unverified") and event_id:
            status_text += f" (ID: {event_id})"
        if code:
            status_text += f" [{code}]"

        reason = getattr(attempt, "message", "") or ""
        if not reason and code:
            reason = code

        self._results_tree.insert("", tk.END, values=(
            getattr(attempt, "draft_id", ""),
            subject[:60],
            status_text,
            reason[:200] or "—",
        ), tags=(_STATUS_TAG.get(status, "failed"),))

    def _open_logs_folder(self) -> None:
        import os
        import subprocess
        import sys
        from pathlib import Path

        from calendar_planner.app.settings import settings

        logs_dir = Path(settings.RUNS_DIR).parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(logs_dir))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(logs_dir)])
            else:
                subprocess.Popen(["xdg-open", str(logs_dir)])
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showwarning("Логи", f"Не удалось открыть папку: {exc}\nПапка: {logs_dir}")

    def _ensure_results_table(self) -> None:
        if self._results_table is not None:
            return
        results_frame = ttk.LabelFrame(self, text="Результаты создания", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0), padx=5)
        self._results_table = results_frame

        columns = ("event", "status", "errors")
        self._results_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            height=6,
        )
        self._results_tree.heading("event", text="Черновик")
        self._results_tree.heading("status", text="Статус / Код")
        self._results_tree.heading("errors", text="Причина")
        self._results_tree.column("event", width=250, minwidth=100)
        self._results_tree.column("status", width=220, minwidth=100)
        self._results_tree.column("errors", width=320, minwidth=120)

        self._results_tree.tag_configure("created", foreground="green")
        self._results_tree.tag_configure("dry_run", foreground="blue")
        self._results_tree.tag_configure("failed", foreground="red")

        v_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self._results_tree.yview)
        h_scroll = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self._results_tree.xview)
        self._results_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self._results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self._results_tree.bind("<Double-1>", self._on_result_double_click)

    def _on_result_double_click(self, event) -> None:
        selection = self._results_tree.selection()
        if not selection:
            return
        values = self._results_tree.item(selection[0], "values")
        if not values:
            return
        draft_id = values[0] if values else ""
        attempt = self._attempts.get(draft_id)
        if attempt is None:
            # legacy row without stored attempt
            if len(values) >= 3 and values[2] and values[2] != "—":
                self._show_text_dialog("Детали", values[2])
            return
        self._show_attempt_dialog(attempt)

    def _show_text_dialog(self, title: str, text: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("500x300")
        box = tk.Text(dialog, wrap=tk.WORD, font=("Consolas", 9))
        box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        box.insert(tk.END, text)
        box.config(state=tk.DISABLED)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(text)

        ttk.Button(dialog, text="Копировать", command=copy).pack(pady=(0, 10))

    def _show_attempt_dialog(self, attempt: dict) -> None:
        import json

        dialog = tk.Toplevel(self)
        dialog.title(f"Диагностика создания — {attempt.get('draft_id', '')}")
        dialog.geometry("760x560")

        status = attempt.get("status", "")
        code = attempt.get("error_code") or ""
        reason = attempt.get("message") or "—"
        created_at = attempt.get("created_at") or "—"
        attempt_id = attempt.get("attempt_id") or "—"

        summary = (
            f"Статус: {_STATUS_TEXT.get(status, status)}\n"
            f"Код: {code}\n"
            f"Время: {created_at}\n"
            f"Attempt ID: {attempt_id}\n"
            f"Event ID: {attempt.get('event_id') or '—'}\n"
            f"URL: {attempt.get('url') or '—'}\n\n"
            f"Причина: {reason}\n"
        )

        body = {
            "attempt_id": attempt.get("attempt_id"),
            "draft_id": attempt.get("draft_id"),
            "status": status,
            "error_code": code,
            "message": attempt.get("message"),
            "technical_message": attempt.get("technical_message"),
            "created_at": created_at,
            "event_id": attempt.get("event_id"),
            "url": attempt.get("url"),
            "verification": attempt.get("verification"),
            "payload": attempt.get("payload"),
        }

        box = tk.Text(dialog, wrap=tk.WORD, font=("Consolas", 9))
        box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        box.insert(tk.END, summary + "\n" + "=" * 70 + "\n")
        box.insert(tk.END, json.dumps(body, ensure_ascii=False, indent=2))
        box.config(state=tk.DISABLED)

        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, padx=10, pady=(0, 10))

        def copy_diag():
            self.clipboard_clear()
            self.clipboard_append(json.dumps(body, ensure_ascii=False, indent=2))

        ttk.Button(btns, text="Копировать диагностику", command=copy_diag).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Открыть папку логов", command=self._open_logs_folder).pack(side=tk.LEFT, padx=2)

        if self.on_real_create is not None and status in ("validation_failed", "transport_failed", "server_rejected", "unknown_response"):
            draft = next((d for d in self.drafts if d.draft_id == attempt.get("draft_id")), None)
            if draft is not None:
                ttk.Button(btns, text="Повторить", command=lambda: self.on_real_create(draft)).pack(side=tk.LEFT, padx=2)