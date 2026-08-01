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

        renderer = DescriptionRenderer()

        for candidate_id, items in sorted(self.enrichment.items()):
            candidate = self.candidates_by_id.get(candidate_id)
            subject = candidate.subject if candidate else candidate_id
            rendered = renderer.render(items, subject)
            self._build_candidate_card(scrollable, candidate_id, subject, items, rendered)

    def _build_candidate_card(
        self, parent: ttk.Frame, candidate_id: str, subject: str,
        items: list[DescriptionItem], rendered_text: str,
    ) -> None:
        card = ttk.LabelFrame(parent, text=f"Кандидат: {candidate_id} — {subject[:50]}", padding=8)
        card.pack(fill=tk.X, pady=5, padx=5)

        agenda_items = [i for i in items if i.item_type == DescriptionItemType.AGENDA and i.included]
        link_items = [i for i in items if i.item_type in (DescriptionItemType.LINK, DescriptionItemType.ONLINE_MEETING_URL) and i.included]
        material_items = [i for i in items if i.item_type in (DescriptionItemType.MATERIAL, DescriptionItemType.DOCUMENT) and i.included]
        location_items = [i for i in items if i.item_type == DescriptionItemType.LOCATION and i.included]

        if agenda_items:
            lbl = ttk.LabelFrame(card, text="Повестка", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in agenda_items:
                ttk.Label(lbl, text=item.value[:200], wraplength=700, anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W, pady=1)

        if link_items:
            lbl = ttk.LabelFrame(card, text="Ссылки", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in link_items:
                ttk.Label(lbl, text=f"{item.title}: {item.value}", wraplength=700, anchor=tk.W).pack(anchor=tk.W, pady=1)

        if material_items:
            lbl = ttk.LabelFrame(card, text="Материалы", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in material_items:
                ttk.Label(lbl, text=f"{item.title}: {item.value[:200]}", wraplength=700, anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W, pady=1)

        if location_items:
            lbl = ttk.LabelFrame(card, text="Место", padding=5)
            lbl.pack(fill=tk.X, pady=2)
            for item in location_items:
                ttk.Label(lbl, text=item.value, wraplength=700, anchor=tk.W).pack(anchor=tk.W, pady=1)

        if rendered_text and not any([agenda_items, link_items, material_items, location_items]):
            preview_frame = ttk.LabelFrame(card, text="Предпросмотр описания", padding=5)
            preview_frame.pack(fill=tk.X, pady=2)
            text_widget = tk.Text(preview_frame, height=6, wrap=tk.WORD, font=("Consolas", 8))
            text_widget.insert(tk.END, rendered_text[:500])
            text_widget.configure(state=tk.DISABLED)
            text_widget.pack(fill=tk.X)

        if not items:
            ttk.Label(card, text="Нет дополнительных данных", font=("", 8, "italic")).pack(anchor=tk.W)

    def refresh(self, enrichment: dict[str, list[DescriptionItem]], candidates_by_id: dict) -> None:
        self.enrichment = enrichment
        self.candidates_by_id = candidates_by_id
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()