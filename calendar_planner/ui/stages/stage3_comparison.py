from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calendar_planner.domain.models import CalendarMatch
from calendar_planner.domain.enums import MatchDecision


class Stage3ComparisonFrame(ttk.Frame):
    def __init__(self, parent, matches: dict[str, CalendarMatch | None], candidates_by_id: dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.matches = matches
        self.candidates_by_id = candidates_by_id
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Этап 3 — Сравнение с календарём", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Сопоставление кандидатов с событиями календаря", font=("", 8)).pack(anchor=tk.W)

        columns = ("candidate", "calendar_event", "time_diff", "subject_sim", "decision")
        tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        tree.heading("candidate", text="Кандидат")
        tree.heading("calendar_event", text="Событие в календаре")
        tree.heading("time_diff", text="Разница по времени")
        tree.heading("subject_sim", text="Сходство темы")
        tree.heading("decision", text="Решение")
        tree.column("candidate", width=200)
        tree.column("calendar_event", width=200)
        tree.column("time_diff", width=140)
        tree.column("subject_sim", width=100)
        tree.column("decision", width=180)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        decision_labels = {
            MatchDecision.DUPLICATE: "ДУБЛИКАТ",
            MatchDecision.POSSIBLE_DUPLICATE: "ВОЗМОЖНЫЙ ДУБЛИКАТ",
            MatchDecision.POSSIBLE_RESCHEDULE: "ВОЗМОЖНЫЙ ПЕРЕНОС",
            MatchDecision.NEW: "НОВОЕ СОБЫТИЕ",
            MatchDecision.NORMALIZATION_ERROR: "ОШИБКА НОРМАЛИЗАЦИИ",
        }

        for candidate_id, match in sorted(self.matches.items()):
            candidate = self.candidates_by_id.get(candidate_id)
            subject = candidate.subject[:60] if candidate else candidate_id

            if match is None:
                tree.insert("", tk.END, values=(
                    subject, "Нет данных", "—", "—", "Невозможно сравнить"
                ))
                continue

            cal_subject = match.calendar_event.subject[:60] if match.calendar_event else "—"
            time_diff = f"{match.time_diff_minutes} мин" if match.time_diff_minutes is not None else "—"
            subj_sim = f"{match.subject_similarity:.0%}"
            decision = decision_labels.get(match.decision, match.decision.value)

            tree.insert("", tk.END, values=(subject, cal_subject, time_diff, subj_sim, decision))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def refresh(self, matches: dict[str, CalendarMatch | None], candidates_by_id: dict) -> None:
        self.matches = matches
        self.candidates_by_id = candidates_by_id
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()