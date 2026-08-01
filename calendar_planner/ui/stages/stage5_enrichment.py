from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from calendar_planner.domain.models import DescriptionItem, DescriptionItemType
from calendar_planner.enrichment.renderer import DescriptionRenderer


class Stage5EnrichmentFrame(ttk.Frame):
    def __init__(self, parent, enrichment: dict[str, list[DescriptionItem]], candidates_by_id: dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.enrichment = enrichment
        self.candidates_by_id = candidates_by_id
        self._renderer = DescriptionRenderer()
        self._item_vars: dict[str, tk.BooleanVar] = {}
        self._preview_widgets: dict[str, tk.Text] = {}
        self._original_items: dict[str, DescriptionItem] = {}
        self._callbacks: dict[str, list[callable]] = {}
        for cid, items in self.enrichment.items():
            for it in items:
                self._original_items[it.item_id] = DescriptionItem.from_dict(it.to_dict())
        self._build_ui()

    def on(self, event: str, callback: callable) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, **kwargs) -> None:
        for cb in self._callbacks.get(event, []):
            cb(**kwargs)

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Этап 5 — Дополнительные данные", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Повестка, ссылки, материалы и место проведения", font=("", 8)).pack(anchor=tk.W)

        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scrollable = ttk.Frame(canvas)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = canvas

        for candidate_id, items in sorted(self.enrichment.items()):
            candidate = self.candidates_by_id.get(candidate_id)
            subject = candidate.subject if candidate else candidate_id
            self._build_candidate_card(scrollable, candidate_id, subject, items)

    def _build_candidate_card(
        self, parent: ttk.Frame, candidate_id: str, subject: str,
        items: list[DescriptionItem],
    ) -> None:
        card = ttk.LabelFrame(parent, text=f"Кандидат: {candidate_id} — {subject[:50]}", padding=8)
        card.pack(fill=tk.X, pady=5, padx=5)

        add_row = ttk.Frame(card)
        add_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(
            add_row, text="+ Добавить элемент",
            command=lambda cid=candidate_id: self._add_item(cid),
        ).pack(side=tk.LEFT)

        if not items:
            ttk.Label(card, text="Нет дополнительных данных", font=("", 8, "italic")).pack(anchor=tk.W)

        self._store_originals(items)

        type_groups: list[tuple[str, list[DescriptionItem]]] = [
            ("Повестка", [i for i in items if i.item_type == DescriptionItemType.AGENDA]),
            ("Ссылки", [i for i in items if i.item_type in (DescriptionItemType.LINK, DescriptionItemType.ONLINE_MEETING_URL)]),
            ("Материалы", [i for i in items if i.item_type in (DescriptionItemType.MATERIAL, DescriptionItemType.DOCUMENT)]),
            ("Место", [i for i in items if i.item_type == DescriptionItemType.LOCATION]),
            ("Прочее", [
                i for i in items
                if i.item_type not in (
                    DescriptionItemType.AGENDA,
                    DescriptionItemType.LINK,
                    DescriptionItemType.ONLINE_MEETING_URL,
                    DescriptionItemType.MATERIAL,
                    DescriptionItemType.DOCUMENT,
                    DescriptionItemType.LOCATION,
                )
            ]),
        ]

        for group_name, group_items in type_groups:
            if group_items:
                self._build_item_group(card, candidate_id, group_name, group_items)

        preview_frame = ttk.LabelFrame(card, text="Предпросмотр описания", padding=5)
        preview_frame.pack(fill=tk.X, pady=(5, 0))
        text_widget = tk.Text(preview_frame, height=4, wrap=tk.WORD, font=("Consolas", 8))
        text_widget.insert(tk.END, self._renderer.render(items, subject)[:500])
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.X)
        self._preview_widgets[candidate_id] = text_widget

    def _store_originals(self, items: list[DescriptionItem]) -> None:
        for item in items:
            if item.item_id not in self._original_items:
                from dataclasses import replace
                self._original_items[item.item_id] = replace(
                    item,
                    value=item.value,
                    included=item.included,
                )

    def _build_item_group(
        self, parent: ttk.Frame, candidate_id: str,
        group_name: str, items: list[DescriptionItem],
    ) -> None:
        lbl = ttk.LabelFrame(parent, text=group_name, padding=5)
        lbl.pack(fill=tk.X, pady=2)

        for item in items:
            self._build_item_row(lbl, candidate_id, item)

    def _build_item_row(
        self, parent: ttk.Frame, candidate_id: str, item: DescriptionItem,
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=1)

        var = tk.BooleanVar(value=item.included)
        self._item_vars[item.item_id] = var
        var.trace_add(
            "write",
            lambda *a, it=item, v=var, cid=candidate_id: self._on_item_toggle(it, v.get(), cid),
        )
        ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)

        value_var = tk.StringVar(value=item.value)
        value_entry = ttk.Entry(row, textvariable=value_var, width=40)
        value_entry.pack(side=tk.LEFT, padx=(2, 5))
        value_var.trace_add(
            "write",
            lambda *a, it=item, vv=value_var, cid=candidate_id: self._on_value_changed(it, vv.get(), cid),
        )

        meta_text_parts = []
        if item.source_location:
            meta_text_parts.append(f"Источник: {item.source_location}")
        if item.reasoning:
            meta_text_parts.append(f"Обоснование: {item.reasoning}")
        if meta_text_parts:
            meta_label = ttk.Label(row, text=" | ".join(meta_text_parts), foreground="gray", font=("", 7), wraplength=300)
            meta_label.pack(side=tk.LEFT, padx=(5, 5))

        conf_text = f"{item.confidence:.0%}" if item.confidence else ""
        if conf_text:
            ttk.Label(row, text=f"Уверенность: {conf_text}", foreground="gray", font=("", 7)).pack(side=tk.LEFT, padx=(0, 5))

        btn_frame = ttk.Frame(row)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(
            btn_frame, text="Копировать", width=9,
            command=lambda v=item.value: self._copy_to_clipboard(v),
        ).pack(side=tk.LEFT, padx=1)

        ttk.Button(
            btn_frame, text="Изменить", width=8,
            command=lambda it=item, vv=value_var, cid=candidate_id: self._show_edit_dialog(it, vv, cid),
        ).pack(side=tk.LEFT, padx=1)

        ttk.Button(
            btn_frame, text="Вернуть", width=7,
            command=lambda it=item, cid=candidate_id: self._revert_item(it, cid),
        ).pack(side=tk.LEFT, padx=1)

        ttk.Button(
            btn_frame, text="Удалить", width=7,
            command=lambda it=item, cid=candidate_id: self._delete_item(it, cid),
        ).pack(side=tk.LEFT, padx=1)

    def _on_item_toggle(self, item: DescriptionItem, checked: bool, candidate_id: str) -> None:
        item.included = checked
        self._refresh_preview(candidate_id)
        self._emit("item_changed", candidate_id=candidate_id, item_id=item.item_id)

    def _on_value_changed(self, item: DescriptionItem, new_value: str, candidate_id: str) -> None:
        if new_value != item.value:
            item.value = new_value
            item.modified_by_user = True
            self._refresh_preview(candidate_id)
            self._emit("item_changed", candidate_id=candidate_id, item_id=item.item_id)

    def _edit_item_value(self, item: DescriptionItem, value_var: tk.StringVar, candidate_id: str) -> None:
        self._show_edit_dialog(item, value_var, candidate_id)

    def _show_edit_dialog(self, item: DescriptionItem, value_var: tk.StringVar, candidate_id: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(f"Редактировать: {item.title}")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Значение:").pack(padx=10, pady=(10, 0), anchor=tk.W)
        text = tk.Text(dialog, height=5, width=60, wrap=tk.WORD)
        text.insert(tk.END, item.value)
        text.pack(padx=10, pady=5)

        def _save():
            new_value = text.get(1.0, tk.END).strip()
            item.value = new_value
            item.modified_by_user = True
            value_var.set(new_value)
            self._refresh_preview(candidate_id)
            self._emit("item_changed", candidate_id=candidate_id, item_id=item.item_id)
            dialog.destroy()

        ttk.Button(dialog, text="Сохранить", command=_save).pack(pady=(0, 10))

    def _copy_to_clipboard(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def _revert_item(self, item: DescriptionItem, candidate_id: str) -> None:
        original = self._original_items.get(item.item_id)
        if original is None:
            return
        item.value = original.value
        item.included = original.included
        item.modified_by_user = False
        if item.item_id in self._item_vars:
            self._item_vars[item.item_id].set(item.included)
        self._refresh_preview(candidate_id)
        self._emit("item_changed", candidate_id=candidate_id, item_id=item.item_id)

    def _delete_item(self, item: DescriptionItem, candidate_id: str) -> None:
        if candidate_id in self.enrichment and item in self.enrichment[candidate_id]:
            self.enrichment[candidate_id].remove(item)
        self._refresh_preview(candidate_id)
        self._emit("item_changed", candidate_id=candidate_id, item_id=item.item_id)
        self.refresh(self.enrichment, self.candidates_by_id)

    def _add_item(self, candidate_id: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Добавить элемент")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Название:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        title_entry = ttk.Entry(dialog, width=30)
        title_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Тип:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        type_var = tk.StringVar(value="note")
        type_combo = ttk.Combobox(
            dialog, textvariable=type_var,
            values=["agenda", "link", "material", "location", "online_meeting_url", "document", "note"],
            state="readonly", width=27,
        )
        type_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Значение:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        text = tk.Text(dialog, height=4, width=30)
        text.grid(row=2, column=1, padx=5, pady=5)

        def _do_add():
            title = title_entry.get().strip()
            value = text.get(1.0, tk.END).strip()
            if not title or not value:
                messagebox.showwarning("Ошибка", "Заполните название и значение", parent=dialog)
                return

            try:
                item_type = DescriptionItemType(type_var.get())
            except ValueError:
                item_type = DescriptionItemType.NOTE

            import uuid
            new_item = DescriptionItem(
                item_id=f"USR-{uuid.uuid4().hex[:8]}",
                item_type=item_type,
                title=title,
                value=value,
                included=True,
                modified_by_user=True,
                candidate_id=candidate_id,
            )
            self._original_items[new_item.item_id] = DescriptionItem(
                item_id=new_item.item_id,
                item_type=item_type,
                title=title,
                value=value,
            )

            if candidate_id not in self.enrichment:
                self.enrichment[candidate_id] = []
            self.enrichment[candidate_id].append(new_item)

            self._emit("item_changed", candidate_id=candidate_id, item_id=new_item.item_id)
            dialog.destroy()
            self.refresh(self.enrichment, self.candidates_by_id)

        ttk.Button(dialog, text="Добавить", command=_do_add).grid(row=3, column=0, columnspan=2, pady=10)

    def _refresh_preview(self, candidate_id: str) -> None:
        widget = self._preview_widgets.get(candidate_id)
        if widget is None:
            return
        widget.configure(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        items = self.enrichment.get(candidate_id, [])
        candidate = self.candidates_by_id.get(candidate_id)
        subject = candidate.subject if candidate else candidate_id
        widget.insert(tk.END, self._renderer.render(items, subject)[:500])
        widget.configure(state=tk.DISABLED)

    def refresh(self, enrichment: dict[str, list[DescriptionItem]], candidates_by_id: dict) -> None:
        self.enrichment = enrichment
        self.candidates_by_id = candidates_by_id
        self._item_vars = {}
        self._preview_widgets = {}
        self._original_items = {}
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()