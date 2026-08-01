from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from calendar_planner.domain.models import (
    CandidateParticipants,
    ParticipantRole,
    ParticipantSide,
    ResolvedParticipant,
    UnresolvedParticipant,
)


class Stage4ParticipantsFrame(ttk.Frame):
    def __init__(self, parent, participants: list[CandidateParticipants],
                 performer_domains: list[str] | None = None,
                 fuzzy_threshold: float = 0.85, **kwargs):
        super().__init__(parent, **kwargs)
        self.participants = participants
        self.performer_domains = performer_domains or ["1bit.ru"]
        self.fuzzy_threshold = fuzzy_threshold
        self._callbacks: dict[str, list[callable]] = {}
        self._build_ui()

    def on(self, event: str, callback: callable) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, **kwargs) -> None:
        for cb in self._callbacks.get(event, []):
            cb(**kwargs)

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
        self.scrollable = scrollable

        for cp in self.participants:
            self._build_candidate_block(scrollable, cp)

    def _build_candidate_block(self, parent: ttk.Frame, cp: CandidateParticipants) -> None:
        block = ttk.LabelFrame(parent, text=f"Кандидат: {cp.candidate_id}", padding=5)
        block.pack(fill=tk.X, pady=5, padx=5)

        actions_row = ttk.Frame(block)
        actions_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(
            actions_row, text="+ Добавить участника",
            command=lambda cp=cp, blk=block: self._add_participant(cp, blk),
        ).pack(side=tk.LEFT, padx=(0, 5))

        for p in cp.performer:
            self._build_resolved_row(block, cp, p, ParticipantSide.PERFORMER)

        for p in cp.customer:
            self._build_resolved_row(block, cp, p, ParticipantSide.CUSTOMER)

        for u in cp.unresolved:
            self._build_unresolved_row(block, cp, u)

    def _build_resolved_row(
        self, parent: ttk.Frame, cp: CandidateParticipants,
        p: ResolvedParticipant, side: ParticipantSide,
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)

        side_text = "Исполнитель" if side == ParticipantSide.PERFORMER else "Заказчик"
        ttk.Label(row, text=side_text, width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row, text=p.source_name, width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))

        name_var = tk.StringVar(value=p.full_name)
        ttk.Label(row, textvariable=name_var, width=22, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))

        email_var = tk.StringVar(value=p.email or "")
        email_entry = ttk.Entry(row, textvariable=email_var, width=25)
        email_entry.pack(side=tk.LEFT, padx=(0, 5))
        email_var.trace_add("write", lambda *a, p=p, v=email_var: self._on_email_edited(p, v.get()))

        confidence_text = ""
        if p.is_fuzzy_match and p.fuzzy_score is not None:
            confidence_text = f" {p.fuzzy_score:.0%}"
        elif p.match_source == "fuzzy_match" and p.confidence < 1.0 or p.confidence < 1.0:
            confidence_text = f" {p.confidence:.0%}"

        status_text = p.match_source
        if confidence_text:
            status_text += f", уверенность: {confidence_text}"
        ttk.Label(row, text=status_text[:35], width=35, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))

        role_btn_text = "Обязательный" if p.role == ParticipantRole.REQUIRED else "Опциональный"
        ttk.Button(
            row, text=role_btn_text, width=12,
            command=lambda p=p: self._toggle_role(cp, p),
        ).pack(side=tk.LEFT, padx=(0, 2))

        ttk.Button(
            row, text="Удалить", width=8,
            command=lambda cp=cp, p=p: self._remove_participant(cp, p),
        ).pack(side=tk.LEFT, padx=(0, 2))

        if p.is_fuzzy_match:
            ttk.Button(
                row, text="Отклонить", width=9,
                command=lambda cp=cp, p=p: self._reject_fuzzy_match(cp, p),
            ).pack(side=tk.LEFT)

    def _build_unresolved_row(
        self, parent: ttk.Frame, cp: CandidateParticipants, u: UnresolvedParticipant,
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)

        ttk.Label(row, text="Не разрешён", width=12, anchor=tk.W, foreground="orange").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row, text=u.source_name, width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))

        options = u.possible_matches

        if options:
            choices = [
                f"{m.get('full_name', '?')} ({m.get('email', 'нет email')})"
                for m in options
            ]
            combo_var = tk.StringVar(value=choices[0] if choices else "")
            combo = ttk.Combobox(row, textvariable=combo_var, values=choices, width=35, state="readonly")
            combo.pack(side=tk.LEFT, padx=(0, 5))

            ttk.Button(
                row, text="Выбрать", width=8,
                command=lambda cp=cp, u=u, opts=options, cv=combo_var:
                    self._select_alternative(cp, u, opts, cv),
            ).pack(side=tk.LEFT, padx=(0, 2))
        else:
            ttk.Label(row, text="— Вариантов нет —", width=35, anchor=tk.W, foreground="gray").pack(
                side=tk.LEFT, padx=(0, 5),
            )

        ttk.Label(row, text=u.reason[:30], width=30, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            row, text="Повторить поиск", width=14,
            command=lambda cp=cp, u=u: self._retry_search(cp, u),
        ).pack(side=tk.LEFT, padx=(0, 2))

        ttk.Button(
            row, text="Удалить", width=8,
            command=lambda cp=cp, u=u: self._remove_unresolved(cp, u),
        ).pack(side=tk.LEFT)

    def _select_alternative(
        self, cp: CandidateParticipants, u: UnresolvedParticipant,
        options: list[dict], combo_var: tk.StringVar,
    ) -> None:
        selected_text = combo_var.get()
        if not selected_text:
            return

        for m in options:
            if m.get("full_name", "") in selected_text:
                resolved = ResolvedParticipant(
                    full_name=m.get("full_name", u.source_name),
                    email=m.get("email"),
                    side=u.side,
                    role=ParticipantRole.REQUIRED,
                    source_name=u.source_name,
                    match_source="user_selected",
                    confidence=m.get("score", 0.7),
                    organization=m.get("organization"),
                )
                if u in cp.unresolved:
                    cp.unresolved.remove(u)
                if u.side == ParticipantSide.PERFORMER:
                    cp.performer.append(resolved)
                else:
                    cp.customer.append(resolved)
                break

        self._emit("participant_changed", candidate_id=cp.candidate_id)
        self.refresh(self.participants)

    def _toggle_role(self, cp: CandidateParticipants, p: ResolvedParticipant) -> None:
        if p.role == ParticipantRole.REQUIRED:
            p.role = ParticipantRole.OPTIONAL
        else:
            p.role = ParticipantRole.REQUIRED
        self._emit("participant_changed", candidate_id=cp.candidate_id)
        self.refresh(self.participants)

    def _on_email_edited(self, p: ResolvedParticipant, new_email: str) -> None:
        p.email = new_email if new_email else None

    def _remove_participant(self, cp: CandidateParticipants, p: ResolvedParticipant) -> None:
        if p in cp.performer:
            cp.performer.remove(p)
        if p in cp.customer:
            cp.customer.remove(p)
        self._emit("participant_changed", candidate_id=cp.candidate_id)
        self.refresh(self.participants)

    def _reject_fuzzy_match(self, cp: CandidateParticipants, p: ResolvedParticipant) -> None:
        if p in cp.performer:
            cp.performer.remove(p)
        if p in cp.customer:
            cp.customer.remove(p)
        cp.unresolved.append(UnresolvedParticipant(
            source_name=p.source_name,
            side=p.side,
            reason="Fuzzy-совпадение отклонено пользователем",
            possible_matches=[{
                "full_name": p.full_name,
                "email": p.email,
                "organization": p.organization,
            }],
        ))
        self._emit("participant_changed", candidate_id=cp.candidate_id)
        self.refresh(self.participants)

    def _remove_unresolved(self, cp: CandidateParticipants, u: UnresolvedParticipant) -> None:
        if u in cp.unresolved:
            cp.unresolved.remove(u)
        self._emit("participant_changed", candidate_id=cp.candidate_id)
        self.refresh(self.participants)

    def _retry_search(self, cp: CandidateParticipants, u: UnresolvedParticipant) -> None:
        self._emit("retry_search", candidate_id=cp.candidate_id, source_name=u.source_name, side=u.side)

    def _add_participant(self, cp: CandidateParticipants, block: ttk.Frame) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Добавить участника")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Имя:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Email:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        email_entry = ttk.Entry(dialog, width=30)
        email_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Сторона:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        side_var = tk.StringVar(value="performer")
        side_combo = ttk.Combobox(dialog, textvariable=side_var, values=["performer", "customer"], state="readonly", width=27)
        side_combo.grid(row=2, column=1, padx=5, pady=5)

        role_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Обязательный", variable=role_var).grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        def _do_add():
            name = name_entry.get().strip()
            email = email_entry.get().strip() or None
            if not name:
                messagebox.showwarning("Ошибка", "Введите имя участника", parent=dialog)
                return

            side = ParticipantSide.PERFORMER if side_var.get() == "performer" else ParticipantSide.CUSTOMER
            role = ParticipantRole.REQUIRED if role_var.get() else ParticipantRole.OPTIONAL

            resolved = ResolvedParticipant(
                full_name=name,
                email=email,
                side=side,
                role=role,
                source_name=name,
                match_source="user_added",
            )

            if side == ParticipantSide.PERFORMER:
                cp.performer.append(resolved)
            else:
                cp.customer.append(resolved)

            self._emit("participant_changed", candidate_id=cp.candidate_id)
            dialog.destroy()
            self.refresh(self.participants)

        ttk.Button(dialog, text="Добавить", command=_do_add).grid(row=4, column=0, columnspan=2, pady=10)

    def refresh(self, participants: list[CandidateParticipants]) -> None:
        self.participants = participants
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()