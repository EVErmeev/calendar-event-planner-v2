from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calendar_planner.domain.models import CandidateParticipants, ResolvedParticipant, UnresolvedParticipant


class Stage4ParticipantsFrame(ttk.Frame):
    def __init__(self, parent, participants: list[CandidateParticipants], **kwargs):
        super().__init__(parent, **kwargs)
        self.participants = participants
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Этап 4 — Определение участников", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Сопоставление имён из источника с контактами", font=("", 8)).pack(anchor=tk.W)

        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scrollable = ttk.Frame(canvas)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = canvas

        for cp in self.participants:
            self._build_candidate_block(scrollable, cp)

    def _build_candidate_block(self, parent: ttk.Frame, cp: CandidateParticipants) -> None:
        block = ttk.LabelFrame(parent, text=f"Кандидат: {cp.candidate_id}", padding=5)
        block.pack(fill=tk.X, pady=5, padx=5)

        columns = ("side", "source_name", "found_name", "email", "status")
        tree = ttk.Treeview(block, columns=columns, show="headings", height=3)
        tree.heading("side", text="Сторона")
        tree.heading("source_name", text="Имя в источнике")
        tree.heading("found_name", text="Найденное имя")
        tree.heading("email", text="Email")
        tree.heading("status", text="Статус")
        tree.column("side", width=80)
        tree.column("source_name", width=150)
        tree.column("found_name", width=150)
        tree.column("email", width=180)
        tree.column("status", width=100)
        tree.pack(fill=tk.X, pady=2)

        for p in cp.performer:
            tree.insert("", tk.END, values=(
                "Исполнитель",
                p.source_name,
                p.full_name,
                p.email or "Email не найден",
                "Найден" if p.email else "Без email",
            ))

        for p in cp.customer:
            tree.insert("", tk.END, values=(
                "Заказчик",
                p.source_name,
                p.full_name,
                p.email or "Email не найден",
                "Найден" if p.email else "Без email",
            ))

        for u in cp.unresolved:
            tree.insert("", tk.END, values=(
                "—",
                u.source_name,
                "Не найден",
                "—",
                u.reason[:40],
            ))

    def refresh(self, participants: list[CandidateParticipants]) -> None:
        self.participants = participants
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()