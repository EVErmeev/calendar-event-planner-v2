from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calendar_planner.domain.enums import MatchDecision
from calendar_planner.domain.models import CalendarMatch


class Stage3ComparisonFrame(ttk.Frame):
    def __init__(self, parent, matches: dict[str, CalendarMatch | None], candidates_by_id: dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.matches = matches
        self.candidates_by_id = candidates_by_id
        self._tree: ttk.Treeview | None = None
        self._detail_panel: ttk.Frame | None = None
        self._detail_canvas: tk.Canvas | None = None
        self._summary_label: ttk.Label | None = None
        self._decision_labels = {
            MatchDecision.DUPLICATE: "ДУБЛИКАТ",
            MatchDecision.POSSIBLE_DUPLICATE: "ВОЗМОЖНЫЙ ДУБЛИКАТ",
            MatchDecision.POSSIBLE_RESCHEDULE: "ВОЗМОЖНЫЙ ПЕРЕНОС",
            MatchDecision.NEW: "НОВОЕ СОБЫТИЕ",
            MatchDecision.NORMALIZATION_ERROR: "ОШИБКА НОРМАЛИЗАЦИИ",
        }
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Этап 3 — Сравнение с календарём", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Сопоставление кандидатов с событиями календаря", font=("", 8)).pack(anchor=tk.W)

        self._summary_label = ttk.Label(self, text="", font=("", 9))
        self._summary_label.pack(fill=tk.X, pady=(0, 5))

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        columns = ("candidate", "calendar_event", "time_diff", "subject_sim", "decision")
        tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=12)
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

        tree_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=tree_scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tree.bind("<ButtonRelease-1>", self._on_single_click)
        tree.bind("<Double-1>", self._on_double_click)
        self._tree = tree

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(
            btn_frame, text="Показать объяснение",
            command=self._show_explanation_for_selected,
        ).pack(side=tk.LEFT, padx=(0, 8))

        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        detail_canvas = tk.Canvas(right_frame)
        detail_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=detail_canvas.yview)
        self._detail_panel = ttk.Frame(detail_canvas)
        self._detail_panel.bind(
            "<Configure>", lambda e: detail_canvas.configure(scrollregion=detail_canvas.bbox("all"))
        )
        detail_canvas.create_window((0, 0), window=self._detail_panel, anchor=tk.NW)
        detail_canvas.configure(yscrollcommand=detail_scrollbar.set)
        detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._detail_canvas = detail_canvas

        self._show_detail_placeholder()

        self._populate_rows()

    def _show_detail_placeholder(self) -> None:
        self._clear_detail()
        ttk.Label(
            self._detail_panel,
            text="Выберите строку в таблице\nи нажмите «Показать объяснение»",
            font=("", 10),
            justify=tk.CENTER,
        ).pack(expand=True)

    def _clear_detail(self) -> None:
        for widget in self._detail_panel.winfo_children():
            widget.destroy()

    def _populate_rows(self) -> None:
        tree = self._tree
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

        total = 0
        dupes = 0
        news = 0

        for candidate_id, match in sorted(self.matches.items()):
            candidate = self.candidates_by_id.get(candidate_id)
            subject = candidate.subject[:60] if candidate else candidate_id

            if match is None:
                tree.insert("", tk.END, values=(
                    subject, "Нет данных", "—", "—", "Невозможно сравнить"
                ), tags=("none",))
                total += 1
                continue

            cal_subject = match.calendar_event.subject[:60] if match.calendar_event else "—"

            effective_decision = match.decision
            if match.user_decision == "duplicate":
                effective_decision = MatchDecision.DUPLICATE
            elif match.user_decision == "new":
                effective_decision = MatchDecision.NEW

            if effective_decision == MatchDecision.NEW:
                time_diff = "—"
                cal_subject = "—"
            else:
                time_diff = f"{match.time_diff_minutes} мин" if match.time_diff_minutes is not None else "—"
            subj_sim = f"{match.subject_similarity:.0%}"
            decision_display = self._decision_labels.get(effective_decision, effective_decision.value)
            if match.decision_origin == "manual":
                decision_display += " (вручную)"

            item_id = tree.insert("", tk.END, values=(
                subject, cal_subject, time_diff, subj_sim, decision_display
            ), tags=(candidate_id,))

            total += 1
            if effective_decision in (
                MatchDecision.DUPLICATE,
                MatchDecision.POSSIBLE_DUPLICATE,
                MatchDecision.POSSIBLE_RESCHEDULE,
            ):
                dupes += 1
            elif effective_decision == MatchDecision.NEW:
                news += 1

        self._summary_label.configure(
            text=f"Всего кандидатов: {total}, Дубликаты: {dupes}, Новые: {news}"
        )

    def _on_single_click(self, event: tk.Event) -> None:
        pass

    def _on_double_click(self, event: tk.Event) -> None:
        tree = self._tree
        if tree is None:
            return
        selection = tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = tree.item(item, "tags")
        if not tags:
            return
        candidate_id = tags[0]
        match = self.matches.get(candidate_id)
        if match is None:
            return
        self._show_detail_dialog(candidate_id, match)

    def _show_explanation_for_selected(self) -> None:
        tree = self._tree
        if tree is None:
            return
        selection = tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = tree.item(item, "tags")
        if not tags:
            return
        candidate_id = tags[0]
        match = self.matches.get(candidate_id)
        if match is None:
            return
        self._show_detail_side_panel(candidate_id, match)

    def _show_detail_side_panel(self, candidate_id: str, match: CalendarMatch) -> None:
        self._clear_detail()
        parent = self._detail_panel
        candidate = self.candidates_by_id.get(candidate_id)

        def _section(title):
            frame = ttk.LabelFrame(parent, text=title, padding=8)
            frame.pack(fill=tk.X, pady=(0, 8))
            return frame

        def _row(container, label, value, max_len=None):
            row = ttk.Frame(container)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label + ":", font=("", 9, "bold"), width=16).pack(side=tk.LEFT, anchor=tk.NW)
            display = str(value or "—")
            if max_len and len(display) > max_len:
                display = display[:max_len] + "…"
            ttk.Label(row, text=display, wraplength=350).pack(side=tk.LEFT, anchor=tk.NW, padx=(4, 0))

        cand_section = _section("Кандидат из источника")
        _row(cand_section, "candidate_id", candidate_id)
        _row(cand_section, "Лист / Строка",
             f"{candidate.sheet_name or '—'} / {candidate.row_number or '—'}" if candidate else "—")
        _row(cand_section, "Тема", candidate.subject if candidate else "—", 120)
        _row(cand_section, "Дата / Время",
             f"{candidate.start_date or '—'} {candidate.start_time or '—'}" if candidate else "—")
        _row(cand_section, "Часовой пояс", candidate.timezone if candidate else "—")
        _row(cand_section, "Длительность",
             f"{candidate.duration_minutes} мин" if candidate and candidate.duration_minutes else "—")
        _row(cand_section, "Исполнители",
             ", ".join(candidate.performer_names) if candidate and candidate.performer_names else "—")
        _row(cand_section, "Заказчики",
             ", ".join(candidate.customer_names) if candidate and candidate.customer_names else "—")

        cal_section = _section("Событие календаря")
        cal_event = match.calendar_event
        if cal_event is not None:
            _row(cal_section, "event_id", cal_event.event_id)
            _row(cal_section, "iCal UID", cal_event.ical_uid)
            _row(cal_section, "Тема", cal_event.subject, 120)
            if cal_event.start:
                _row(cal_section, "Начало (raw)",
                     f"{cal_event.start.raw_datetime} ({cal_event.start.raw_timezone or '—'})")
                _row(cal_section, "Начало (UTC)", cal_event.start.utc_datetime.isoformat())
            if cal_event.end:
                _row(cal_section, "Конец (raw)",
                     f"{cal_event.end.raw_datetime} ({cal_event.end.raw_timezone or '—'})")
                _row(cal_section, "Конец (UTC)", cal_event.end.utc_datetime.isoformat())
            _row(cal_section, "Место", cal_event.location)
            _row(cal_section, "Online URL", cal_event.online_url)
            attendees_str = "—"
            if cal_event.attendees:
                attendees_str = ", ".join(
                    a.get("email", a.get("name", "")) for a in cal_event.attendees
                )
            _row(cal_section, "Участники", attendees_str, 120)
        else:
            ttk.Label(cal_section, text="Событие не найдено (НОВОЕ)").pack(anchor=tk.W)
            best_rejected = match.best_rejected
            if best_rejected:
                rejected_section = _section("Ближайшее совпадение не достигло порога")
                _row(rejected_section, "Тема", best_rejected.get("subject", "—"), 120)
                _row(rejected_section, "Разница по времени",
                     f"{best_rejected.get('time_diff_minutes', '—')} мин")
                _row(rejected_section, "Сходство темы",
                     f"{best_rejected.get('subject_similarity', 0.0):.0%}")
                _row(rejected_section, "Причина", best_rejected.get("reasoning", "—"), 120)

        dec_section = _section("Решение")
        _row(dec_section, "Решение",
             self._decision_labels.get(match.decision, match.decision.value))
        _row(dec_section, "Score", f"{match.score:.2f}")
        _row(dec_section, "Сходство темы", f"{match.subject_similarity:.0%}")
        _row(dec_section, "Разница по времени",
             f"{match.time_diff_minutes} мин" if match.time_diff_minutes is not None else "—")
        if match.details:
            _row(dec_section, "Детали", str(match.details), 200)

        user_section = _section("Действие пользователя")
        if match.decision_origin == "manual" and match.user_decision:
            _row(user_section, "Статус",
                 "Подтверждено как ДУБЛИКАТ" if match.user_decision == "duplicate" else "Подтверждено как НОВОЕ")

        btn_frame = ttk.Frame(user_section)
        btn_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Button(
            btn_frame, text="Подтвердить как дубликат",
            command=lambda: self._set_user_decision_side(candidate_id, match, "duplicate"),
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            btn_frame, text="Подтвердить как новое",
            command=lambda: self._set_user_decision_side(candidate_id, match, "new"),
        ).pack(side=tk.LEFT)

        if self._detail_canvas:
            self._detail_canvas.yview_moveto(0)

    def _show_detail_dialog(self, candidate_id: str, match: CalendarMatch) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(f"Детали сравнения — {candidate_id}")
        dialog.geometry("750x600")
        dialog.transient(self)
        dialog.grab_set()

        canvas = tk.Canvas(dialog)
        scrollbar_v = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar_v.set)

        candidate = self.candidates_by_id.get(candidate_id)

        def _section(parent, title):
            frame = ttk.LabelFrame(parent, text=title, padding=8)
            frame.pack(fill=tk.X, pady=(0, 8))
            return frame

        def _row(parent, label, value, max_len=None):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label + ":", font=("", 9, "bold"), width=18).pack(side=tk.LEFT, anchor=tk.NW)
            display = str(value or "—")
            if max_len and len(display) > max_len:
                display = display[:max_len] + "…"
            ttk.Label(row, text=display, wraplength=500).pack(side=tk.LEFT, anchor=tk.NW, padx=(4, 0))

        # --- Candidate section ---
        cand_section = _section(scroll_frame, "Кандидат из источника")
        _row(cand_section, "candidate_id", candidate_id)
        _row(cand_section, "Лист / Строка",
             f"{candidate.sheet_name or '—'} / {candidate.row_number or '—'}" if candidate else "—")
        _row(cand_section, "Тема", candidate.subject if candidate else "—", 120)
        _row(cand_section, "Дата / Время",
             f"{candidate.start_date or '—'} {candidate.start_time or '—'}" if candidate else "—")
        _row(cand_section, "Часовой пояс", candidate.timezone if candidate else "—")
        _row(cand_section, "Длительность",
             f"{candidate.duration_minutes} мин" if candidate and candidate.duration_minutes else "—")
        _row(cand_section, "Исполнители",
             ", ".join(candidate.performer_names) if candidate and candidate.performer_names else "—")
        _row(cand_section, "Заказчики",
             ", ".join(candidate.customer_names) if candidate and candidate.customer_names else "—")

        # --- Calendar event section ---
        cal_section = _section(scroll_frame, "Событие календаря")
        cal_event = match.calendar_event
        if cal_event is not None:
            _row(cal_section, "event_id", cal_event.event_id)
            _row(cal_section, "iCal UID", cal_event.ical_uid)
            _row(cal_section, "Тема", cal_event.subject, 120)
            if cal_event.start:
                _row(cal_section, "Начало (raw)",
                     f"{cal_event.start.raw_datetime} ({cal_event.start.raw_timezone or '—'})")
                _row(cal_section, "Начало (UTC)", cal_event.start.utc_datetime.isoformat())
            if cal_event.end:
                _row(cal_section, "Конец (raw)",
                     f"{cal_event.end.raw_datetime} ({cal_event.end.raw_timezone or '—'})")
                _row(cal_section, "Конец (UTC)", cal_event.end.utc_datetime.isoformat())
            _row(cal_section, "Место", cal_event.location)
            _row(cal_section, "Online URL", cal_event.online_url)
            attendees_str = "—"
            if cal_event.attendees:
                attendees_str = ", ".join(
                    a.get("email", a.get("name", "")) for a in cal_event.attendees
                )
            _row(cal_section, "Участники", attendees_str, 120)
        else:
            ttk.Label(cal_section, text="Событие не найдено (НОВОЕ)").pack(anchor=tk.W)
            best_rejected = match.best_rejected
            if best_rejected:
                rejected_section = _section(scroll_frame, "Ближайшее совпадение не достигло порога")
                _row(rejected_section, "Тема", best_rejected.get("subject", "—"), 120)
                _row(rejected_section, "Разница по времени",
                     f"{best_rejected.get('time_diff_minutes', '—')} мин")
                _row(rejected_section, "Сходство темы",
                     f"{best_rejected.get('subject_similarity', 0.0):.0%}")
                _row(rejected_section, "Причина", best_rejected.get("reasoning", "—"), 120)

        # --- Decision section ---
        dec_section = _section(scroll_frame, "Решение")
        _row(dec_section, "Решение",
             self._decision_labels.get(match.decision, match.decision.value))
        _row(dec_section, "Score", f"{match.score:.2f}")
        _row(dec_section, "Сходство темы", f"{match.subject_similarity:.0%}")
        _row(dec_section, "Разница по времени",
             f"{match.time_diff_minutes} мин" if match.time_diff_minutes is not None else "—")
        if match.details:
            _row(dec_section, "Детали", str(match.details), 200)

        # --- User decision ---
        user_section = _section(scroll_frame, "Действие пользователя")
        if match.decision_origin == "manual" and match.user_decision:
            _row(user_section, "Статус",
                 "Подтверждено как ДУБЛИКАТ" if match.user_decision == "duplicate" else "Подтверждено как НОВОЕ")

        btn_frame = ttk.Frame(user_section)
        btn_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Button(
            btn_frame, text="Подтвердить как дубликат",
            command=lambda: self._set_user_decision(candidate_id, match, "duplicate", dialog),
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            btn_frame, text="Подтвердить как новое",
            command=lambda: self._set_user_decision(candidate_id, match, "new", dialog),
        ).pack(side=tk.LEFT)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)

    def _set_user_decision(
        self,
        candidate_id: str,
        match: CalendarMatch,
        decision: str,
        dialog: tk.Toplevel,
    ) -> None:
        match.user_decision = decision
        match.decision_origin = "manual"
        dialog.destroy()
        self._populate_rows()
        self._show_detail_placeholder()

    def _set_user_decision_side(
        self,
        candidate_id: str,
        match: CalendarMatch,
        decision: str,
    ) -> None:
        match.user_decision = decision
        match.decision_origin = "manual"
        self._populate_rows()
        self._show_detail_side_panel(candidate_id, match)

    def refresh(self, matches: dict[str, CalendarMatch | None], candidates_by_id: dict) -> None:
        self.matches = matches
        self.candidates_by_id = candidates_by_id
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()