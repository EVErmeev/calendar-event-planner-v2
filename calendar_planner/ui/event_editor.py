from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from calendar_planner.domain.models import FinalEventDraft, ResolvedParticipant, ParticipantRole
from calendar_planner.domain.enums import ParticipantSide
from calendar_planner.drafts.editor import DraftEditor
from calendar_planner.drafts.hash import compute_draft_hash


class EventEditorFrame(ttk.Frame):
    def __init__(self, parent, draft: FinalEventDraft, on_recheck=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.draft = draft
        self.editor = DraftEditor()
        self.on_recheck = on_recheck

        self._build_ui()
        self._populate_fields()

    def _build_ui(self) -> None:
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas = canvas

        self._build_header()
        self._build_main_fields()
        self._build_duration_section()
        self._build_attendees_section()
        self._build_description_section()
        self._build_bottom_buttons()

    def _build_header(self) -> None:
        header = ttk.Frame(self.scrollable_frame)
        header.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header,
            text="Конструктор события",
            font=("", 14, "bold"),
        ).pack(anchor=tk.W)

        draft_id_label = ttk.Label(
            header,
            text=f"Draft: {self.draft.draft_id} | Кандидат: {self.draft.candidate_id}",
            font=("", 8),
        )
        draft_id_label.pack(anchor=tk.W)

    def _build_main_fields(self) -> None:
        fields_frame = ttk.LabelFrame(self.scrollable_frame, text="Основные поля", padding=10)
        fields_frame.pack(fill=tk.X, pady=5)

        row_frame = ttk.Frame(fields_frame)
        row_frame.pack(fill=tk.X, pady=5)
        ttk.Label(row_frame, text="Тема:", width=15).pack(side=tk.LEFT)
        self.subject_var = tk.StringVar()
        self.subject_entry = ttk.Entry(row_frame, textvariable=self.subject_var, width=50)
        self.subject_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.subject_entry.bind("<KeyRelease>", lambda e: self._on_field_changed("subject"))

        row_frame = ttk.Frame(fields_frame)
        row_frame.pack(fill=tk.X, pady=5)
        ttk.Label(row_frame, text="Дата:", width=15).pack(side=tk.LEFT)
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(row_frame, textvariable=self.date_var, width=15)
        self.date_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.date_entry.bind("<KeyRelease>", lambda e: self._on_field_changed("date"))

        ttk.Label(row_frame, text="Время начала:", width=15).pack(side=tk.LEFT)
        self.time_var = tk.StringVar()
        self.time_entry = ttk.Entry(row_frame, textvariable=self.time_var, width=10)
        self.time_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.time_entry.bind("<KeyRelease>", lambda e: self._on_field_changed("time"))

        row_frame = ttk.Frame(fields_frame)
        row_frame.pack(fill=tk.X, pady=5)
        ttk.Label(row_frame, text="Час. пояс:", width=15).pack(side=tk.LEFT)
        self.tz_var = tk.StringVar()
        self.tz_entry = ttk.Entry(row_frame, textvariable=self.tz_var, width=25)
        self.tz_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.tz_entry.bind("<KeyRelease>", lambda e: self._on_field_changed("timezone"))

        self.all_day_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row_frame, text="Весь день", variable=self.all_day_var).pack(side=tk.LEFT)

    def _build_duration_section(self) -> None:
        dur_frame = ttk.LabelFrame(self.scrollable_frame, text="Длительность", padding=10)
        dur_frame.pack(fill=tk.X, pady=5)

        self.duration_var = tk.StringVar(value="60")
        self.end_date_var = tk.StringVar()
        self.end_time_var = tk.StringVar()

        preset_frame = ttk.Frame(dur_frame)
        preset_frame.pack(fill=tk.X, pady=5)

        presets = [15, 30, 45, 60, 90, 120]
        for p in presets:
            ttk.Button(
                preset_frame, text=f"{p} мин",
                command=lambda val=p: self._set_duration(val),
                width=8,
            ).pack(side=tk.LEFT, padx=2)

        ttk.Button(preset_frame, text="Другая", command=self._custom_duration, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Label(dur_frame, text=f"Текущая: {self._duration_status()}").pack(anchor=tk.W)

        end_frame = ttk.Frame(dur_frame)
        end_frame.pack(fill=tk.X, pady=5)
        ttk.Label(end_frame, text="Окончание:", width=12).pack(side=tk.LEFT)
        ttk.Label(end_frame, textvariable=self.end_date_var).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(end_frame, textvariable=self.end_time_var).pack(side=tk.LEFT)

    def _build_attendees_section(self) -> None:
        att_frame = ttk.LabelFrame(self.scrollable_frame, text="Участники", padding=10)
        att_frame.pack(fill=tk.X, pady=5)

        self.attendees_tree = ttk.Treeview(
            att_frame,
            columns=("name", "email", "side", "role"),
            show="headings",
            height=5,
        )
        self.attendees_tree.heading("name", text="ФИО")
        self.attendees_tree.heading("email", text="Email")
        self.attendees_tree.heading("side", text="Сторона")
        self.attendees_tree.heading("role", text="Роль")
        self.attendees_tree.column("name", width=200)
        self.attendees_tree.column("email", width=200)
        self.attendees_tree.column("side", width=100)
        self.attendees_tree.column("role", width=80)
        self.attendees_tree.pack(fill=tk.X, pady=5)

        btn_frame = ttk.Frame(att_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Добавить", command=self._add_attendee).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self._remove_attendee).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Обязательный / Необязательный", command=self._toggle_role).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Вернуть авто", command=self._restore_attendees).pack(side=tk.LEFT, padx=2)

    def _build_description_section(self) -> None:
        desc_frame = ttk.LabelFrame(self.scrollable_frame, text="Описание и повестка", padding=10)
        desc_frame.pack(fill=tk.X, pady=5)

        self.description_text = tk.Text(desc_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self.description_text.pack(fill=tk.X, pady=5)
        self.description_text.bind("<KeyRelease>", lambda e: self._on_description_changed())

        btn_frame = ttk.Frame(desc_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Сохранить", command=self._save_description).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Отменить", command=self._cancel_description).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Очистить", command=self._clear_description).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Вернуть авто", command=self._restore_description).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Копировать", command=self._copy_description).pack(side=tk.LEFT, padx=2)

    def _build_bottom_buttons(self) -> None:
        bottom = ttk.Frame(self.scrollable_frame)
        bottom.pack(fill=tk.X, pady=10)

        self.status_label = ttk.Label(bottom, text="", font=("", 9))
        self.status_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            bottom,
            text="Проверить дубль",
            command=self._recheck_duplicate,
        ).pack(side=tk.RIGHT, padx=2)

        ttk.Button(
            bottom,
            text="Сохранить изменения",
            command=self._save_all,
        ).pack(side=tk.RIGHT, padx=2)

    def _populate_fields(self) -> None:
        self.subject_var.set(self.draft.subject.value or "")
        self.date_var.set(self.draft.start_date.value or "")
        self.time_var.set(self.draft.start_time.value or "")
        self.tz_var.set(self.draft.timezone.value or "")

        if self.draft.duration_minutes.value:
            self.duration_var.set(str(self.draft.duration_minutes.value))

        self._update_end_datetime()

        description = self.draft.description.value or ""
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(tk.END, description)
        self._description_saved = description

        self._populate_attendees()
        self._update_ready_status()

    def _populate_attendees(self) -> None:
        for item in self.attendees_tree.get_children():
            self.attendees_tree.delete(item)

        for att in self.draft.required_attendees:
            self.attendees_tree.insert("", tk.END, values=(
                att.full_name,
                att.email or "Email не найден",
                "Исполнитель" if att.side == ParticipantSide.PERFORMER else "Заказчик",
                "Обязательный",
            ))

        for att in self.draft.optional_attendees:
            self.attendees_tree.insert("", tk.END, values=(
                att.full_name,
                att.email or "Email не найден",
                "Исполнитель" if att.side == ParticipantSide.PERFORMER else "Заказчик",
                "Необязательный",
            ))

    def _set_duration(self, minutes: int) -> None:
        self.editor.set_duration(self.draft, minutes)
        self.duration_var.set(str(minutes))
        self._update_end_datetime()
        self._mark_stale()

    def _custom_duration(self) -> None:
        try:
            val = int(self.duration_var.get())
            if val > 0:
                self._set_duration(val)
        except ValueError:
            messagebox.showwarning("Ошибка", "Введите целое число минут")

    def _update_end_datetime(self) -> None:
        end_date, end_time = self.draft.compute_end_datetime()
        if end_date and end_time:
            self.end_date_var.set(f"{end_date}")
            self.end_time_var.set(f"{end_time}")
        else:
            self.end_date_var.set("—")
            self.end_time_var.set("—")

    def _duration_status(self) -> str:
        if self.draft.duration_confirmed:
            return "Подтверждена"
        return "Не подтверждена — выберите длительность"

    def _on_field_changed(self, field: str) -> None:
        if field == "subject":
            self.editor.edit_subject(self.draft, self.subject_var.get())
        elif field == "date":
            self.editor.edit_date(self.draft, self.date_var.get())
        elif field == "time":
            self.editor.edit_time(self.draft, self.time_var.get())
        elif field == "timezone":
            self.editor.edit_timezone(self.draft, self.tz_var.get())
        self._update_end_datetime()
        self._mark_stale()

    def _on_description_changed(self) -> None:
        pass

    def _mark_stale(self) -> None:
        self.status_label.config(
            text=f"Match: STALE — требуется проверка дубля | Готовность: {'Да' if self.draft.is_ready else 'Нет'}",
            foreground="red",
        )

    def _update_ready_status(self) -> None:
        from calendar_planner.domain.validation import validate_draft_ready
        errors = validate_draft_ready(self.draft)
        self.draft.is_ready = len(errors) == 0

        if errors:
            self.status_label.config(
                text=f"Ошибки: {'; '.join(errors[:2])}",
                foreground="red",
            )
        else:
            color = "green" if self.draft.match_status != "stale" else "orange"
            msg = "Готов к созданию" if self.draft.match_status != "stale" else "Готов, но требуется проверка дубля"
            self.status_label.config(text=msg, foreground=color)

    def _add_attendee(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Добавить участника")
        dialog.geometry("400x250")

        ttk.Label(dialog, text="ФИО:").pack(pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=40).pack(pady=5)

        ttk.Label(dialog, text="Email:").pack()
        email_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=email_var, width=40).pack(pady=5)

        ttk.Label(dialog, text="Сторона:").pack()
        side_var = tk.StringVar(value="customer")
        ttk.Combobox(dialog, textvariable=side_var, values=["performer", "customer"], state="readonly").pack(pady=5)

        role_var = tk.StringVar(value="required")
        ttk.Checkbutton(dialog, text="Обязательный", variable=role_var, onvalue="required", offvalue="optional").pack(pady=5)

        def add():
            name = name_var.get().strip()
            email = email_var.get().strip() or None
            if not name:
                messagebox.showwarning("Ошибка", "Введите ФИО")
                return

            participant = ResolvedParticipant(
                full_name=name,
                email=email,
                side=ParticipantSide(side_var.get()),
                role=ParticipantRole(role_var.get()),
                source_name=name,
                match_source="manual",
            )
            self.editor.add_attendee(self.draft, participant, ParticipantRole(role_var.get()))
            self._populate_attendees()
            self._mark_stale()
            dialog.destroy()

        ttk.Button(dialog, text="Добавить", command=add).pack(pady=15)

    def _remove_attendee(self) -> None:
        selection = self.attendees_tree.selection()
        if not selection:
            return
        item = self.attendees_tree.item(selection[0])
        values = item.get("values", [])
        if len(values) >= 2 and values[1] != "Email не найден":
            self.editor.remove_attendee(self.draft, values[1])
            self._populate_attendees()
            self._mark_stale()

    def _toggle_role(self) -> None:
        selection = self.attendees_tree.selection()
        if not selection:
            return
        item = self.attendees_tree.item(selection[0])
        values = item.get("values", [])
        if len(values) >= 2 and values[1] != "Email не найден":
            current_role = values[3]
            new_role = ParticipantRole.OPTIONAL if current_role == "Обязательный" else ParticipantRole.REQUIRED
            self.editor.change_attendee_role(self.draft, values[1], new_role)
            self._populate_attendees()

    def _restore_attendees(self) -> None:
        self._populate_attendees()

    def _save_description(self) -> None:
        text = self.description_text.get(1.0, tk.END).strip()
        self.editor.edit_description(self.draft, text)
        self._description_saved = text
        self._mark_stale()

    def _cancel_description(self) -> None:
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(tk.END, self._description_saved)

    def _clear_description(self) -> None:
        self.description_text.delete(1.0, tk.END)
        self._save_description()

    def _restore_description(self) -> None:
        pass

    def _copy_description(self) -> None:
        text = self.description_text.get(1.0, tk.END).strip()
        self.clipboard_clear()
        self.clipboard_append(text)

    def _recheck_duplicate(self) -> None:
        self.draft.match_input_hash = compute_draft_hash(self.draft)
        self.draft.match_status = "checked"

        if self.on_recheck:
            self.on_recheck(self.draft)

        self.status_label.config(
            text=f"Проверка дубля выполнена (hash: {self.draft.match_input_hash[:16]}...)",
            foreground="blue",
        )
        self._update_ready_status()

    def _save_all(self) -> None:
        self._save_description()
        self.draft.match_status = "stale"
        self.status_label.config(text="Изменения сохранены. Требуется проверка дубля.", foreground="orange")

    def get_draft(self) -> FinalEventDraft:
        return self.draft