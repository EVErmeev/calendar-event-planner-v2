from __future__ import annotations

import tkinter as tk
from tkinter import ttk

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
        self._build_ui()

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

        if not items:
            ttk.Label(card, text="Нет дополнительных данных", font=("", 8, "italic")).pack(anchor=tk.W)
            return

        agenda_items = [i for i in items if i.item_type == DescriptionItemType.AGENDA]
        link_items = [i for i in items if i.item_type in (DescriptionItemType.LINK, DescriptionItemType.ONLINE_MEETING_URL)]
        material_items = [i for i in items if i.item_type in (DescriptionItemType.MATERIAL, DescriptionItemType.DOCUMENT)]
        location_items = [i for i in items if i.item_type == DescriptionItemType.LOCATION]
        other_items = [
            i for i in items
            if i.item_type not in (
                DescriptionItemType.AGENDA,
                DescriptionItemType.LINK,
                DescriptionItemType.ONLINE_MEETING_URL,
                DescriptionItemType.MATERIAL,
                DescriptionItemType.DOCUMENT,
                DescriptionItemType.LOCATION,
            )
        ]

        def make_toggle(item: DescriptionItem, preview_key: str):
            var = tk.BooleanVar(value=item.included)
            self._item_vars[item.item_id] = var
            var.trace_add(
                "write",
                lambda *a, it=item, v=var, pk=preview_key: self._on_item_toggle(it, v.get(), pk),
            )
            return var

        if agenda_items:
            lbl = ttk.LabelFrame(card, text="Повестка", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in agenda_items:
                row = ttk.Frame(lbl)
                row.pack(fill=tk.X, pady=1)
                var = make_toggle(item, candidate_id)
                ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
                ttk.Label(row, text=item.value[:200], wraplength=650, anchor=tk.W, justify=tk.LEFT).pack(side=tk.LEFT, padx=(5, 0))

        if link_items:
            lbl = ttk.LabelFrame(card, text="Ссылки", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in link_items:
                row = ttk.Frame(lbl)
                row.pack(fill=tk.X, pady=1)
                var = make_toggle(item, candidate_id)
                ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
                ttk.Label(row, text=f"{item.title}: {item.value}", wraplength=650, anchor=tk.W).pack(side=tk.LEFT, padx=(5, 0))

        if material_items:
            lbl = ttk.LabelFrame(card, text="Материалы", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in material_items:
                row = ttk.Frame(lbl)
                row.pack(fill=tk.X, pady=1)
                var = make_toggle(item, candidate_id)
                ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
                ttk.Label(row, text=f"{item.title}: {item.value[:200]}", wraplength=650, anchor=tk.W, justify=tk.LEFT).pack(side=tk.LEFT, padx=(5, 0))

        if location_items:
            lbl = ttk.LabelFrame(card, text="Место", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in location_items:
                row = ttk.Frame(lbl)
                row.pack(fill=tk.X, pady=1)
                var = make_toggle(item, candidate_id)
                ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
                ttk.Label(row, text=item.value, wraplength=650, anchor=tk.W).pack(side=tk.LEFT, padx=(5, 0))

        if other_items:
            lbl = ttk.LabelFrame(card, text="Прочее", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in other_items:
                row = ttk.Frame(lbl)
                row.pack(fill=tk.X, pady=1)
                var = make_toggle(item, candidate_id)
                ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
                ttk.Label(row, text=f"{item.title}: {item.value[:200]}", wraplength=650, anchor=tk.W, justify=tk.LEFT).pack(side=tk.LEFT, padx=(5, 0))

        preview_frame = ttk.LabelFrame(card, text="Предпросмотр описания", padding=5)
        preview_frame.pack(fill=tk.X, pady=(5, 0))
        text_widget = tk.Text(preview_frame, height=4, wrap=tk.WORD, font=("Consolas", 8))
        text_widget.insert(tk.END, self._renderer.render(items, subject)[:500])
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.X)
        self._preview_widgets[candidate_id] = text_widget

    def _on_item_toggle(self, item: DescriptionItem, checked: bool, preview_key: str) -> None:
        item.included = checked
        self._refresh_preview(preview_key)

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
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()