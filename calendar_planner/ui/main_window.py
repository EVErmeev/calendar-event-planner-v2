from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from calendar_planner.domain.enums import StageStatus
from calendar_planner.session.storage import SessionStorage
from calendar_planner.ui.controllers import StageController


def _format_errors(errors: list) -> str:
    if not errors:
        return ""
    if isinstance(errors[0], dict):
        return ", ".join(e.get("message_ru", str(e)) for e in errors)
    return ", ".join(str(e) for e in errors)


class MainWindow:
    def __init__(self, root: tk.Tk, container=None):
        self.root = root
        self.root.title("Планировщик календарных событий v2")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        self.container = container
        self.controller = StageController()
        self.storage = SessionStorage()

        self._stage_frames: dict[int, tk.Widget] = {}

        self._build_ui()

        if self.container is not None:
            self._check_connections()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self._build_top_panel()
        self._build_progress_bar()
        self._build_stage_sidebar()
        self._build_main_area()
        self._build_bottom_panel()

    def _build_progress_bar(self) -> None:
        self._progress_frame = ttk.Frame(self.root)
        self._progress_frame.pack(fill=tk.X, padx=5, pady=(0, 0))
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(self._progress_frame, variable=self._progress_var, mode="determinate", length=400)
        self._progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._progress_label = ttk.Label(self._progress_frame, text="", font=("", 8))
        self._progress_label.pack(side=tk.LEFT)
        self._cancel_btn = ttk.Button(self._progress_frame, text="Отменить", command=self._cancel_analysis, state=tk.DISABLED)
        self._cancel_btn.pack(side=tk.RIGHT, padx=5)
        self._progress_frame.pack_forget()
        self._cancel_requested = False
        self._bg_thread: threading.Thread | None = None

    def _show_progress(self, label: str, value: int = 0) -> None:
        self._progress_frame.pack(fill=tk.X, padx=5, pady=(0, 0))
        self._progress_var.set(value)
        self._progress_label.config(text=label)
        self._cancel_btn.config(state=tk.NORMAL)

    def _hide_progress(self) -> None:
        self._progress_frame.pack_forget()
        self._cancel_btn.config(state=tk.DISABLED)

    def _cancel_analysis(self) -> None:
        self._cancel_requested = True
        self._progress_label.config(text="Отмена...")

    def _build_top_panel(self) -> None:
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Label(top_frame, text="Источник:").pack(side=tk.LEFT, padx=(0, 5))

        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(top_frame, textvariable=self.source_var, width=60)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(top_frame, text="Выбрать", command=self._select_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Вставить ссылку", command=self._paste_url).pack(side=tk.LEFT, padx=2)

    def _build_stage_sidebar(self) -> None:
        sidebar = ttk.LabelFrame(self.root, text="Этапы", padding=5)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.stage_labels: list[ttk.Label] = []
        self.stage_status_labels: list[ttk.Label] = []
        stage_names = [
            "1. Подключения",
            "2. Поиск встреч",
            "3. Сравнение",
            "4. Участники",
            "5. Дополнительные данные",
            "6. Создание",
        ]

        for i, name in enumerate(stage_names):
            frame = ttk.Frame(sidebar)
            frame.pack(fill=tk.X, pady=2)
            lbl = ttk.Label(frame, text=name, font=("", 9), cursor="hand2")
            lbl.pack(side=tk.LEFT)
            lbl.bind("<Button-1>", lambda e, s=i: self._go_to_stage(s))
            st_lbl = ttk.Label(frame, text="●", font=("", 8))
            st_lbl.pack(side=tk.RIGHT, padx=(10, 0))
            self.stage_labels.append(lbl)
            self.stage_status_labels.append(st_lbl)

        self._update_stage_indicators()

    def _build_main_area(self) -> None:
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.main_label = ttk.Label(
            self.main_frame,
            text="Welcome to Calendar Event Planner v2",
            font=("", 14),
        )
        self.main_label.pack(pady=20)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.info_text = tk.Text(self.content_frame, height=4, wrap=tk.WORD, font=("Consolas", 9))
        self.info_text.pack(fill=tk.X, pady=5)
        self.info_text.insert(tk.END, (
            "Этот проект - новый самостоятельный календарный планировщик.\n"
            "Он анализирует источник, находит встречи, сравнивает с календарем,\n"
            "определяет участников, собирает дополнительные данные и формирует черновики событий.\n"
            "Dry-run по умолчанию включен. Реальные события не создаются без подтверждения."
        ))

    def _build_bottom_panel(self) -> None:
        bottom = ttk.Frame(self.root, padding=5)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        ttk.Button(bottom, text="← Назад", command=self._prev_stage).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="Далее →", command=self._next_stage).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="Запустить анализ", command=self._run_analysis).pack(side=tk.LEFT, padx=10)
        ttk.Button(bottom, text="Подключения", command=self._show_stage_1).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="Проверить подключения", command=self._check_connections).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="Сохранить сессию", command=self._save_session).pack(side=tk.RIGHT, padx=2)
        ttk.Button(bottom, text="Копировать", command=self._copy_results).pack(side=tk.RIGHT, padx=2)

    def _select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл-источник",
            filetypes=[
                ("Все поддерживаемые", "*.xlsx;*.xlsm;*.csv;*.docx;*.pdf;*.txt;*.md;*.html"),
                ("Excel", "*.xlsx;*.xlsm"),
                ("CSV", "*.csv"),
                ("Word", "*.docx"),
                ("PDF", "*.pdf"),
                ("Text/Markdown", "*.txt;*.md"),
            ],
        )
        if path:
            self.source_var.set(path)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Выбран файл: {path}\nГотов к анализу.")

    def _paste_url(self) -> None:
        try:
            text = self.root.clipboard_get()
            if text:
                self.source_var.set(text)
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, f"Вставлена ссылка: {text}\nГотов к анализу.")
        except Exception:
            messagebox.showwarning("Ошибка", "Не удалось вставить из буфера обмена")

    def _run_analysis(self) -> None:
        source = self.source_var.get().strip()
        if not source:
            messagebox.showwarning("Внимание", "Укажите файл или ссылку")
            return

        stage_1_status = self.controller.get_stage_status(0)
        if stage_1_status == "not_started":
            self._check_connections()
            stage_1_status = self.controller.get_stage_status(0)

        if stage_1_status not in ("success", "success_with_warnings"):
            self.controller.set_current_stage(0)
            self._show_stage_content()
            self._update_stage_indicators()
            messagebox.showerror(
                "Подключения не готовы",
                "Проверка подключений не пройдена.\nОткройте экран «Подключения» или нажмите «Проверить подключения».",
            )
            return

        from calendar_planner.app.settings import settings
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.registry import registry

        if source.startswith("http"):
            src_ref = SourceReference(type="url", url=source)
        else:
            src_ref = SourceReference(type="file", path=source)

        def bg_work():
            try:
                self.root.after(0, lambda: self._show_progress("Чтение источника...", 10))
                extracted = registry.read_source(src_ref)
                if self._cancel_requested:
                    self.root.after(0, lambda: self.info_text.insert(tk.END, "\n[ОТМЕНЕНО]\n"))
                    self.root.after(0, self._hide_progress)
                    return

                from calendar_planner.extraction.structured import StructuredExtractor
                self.root.after(0, lambda: self._show_progress("Поиск встреч...", 30))
                extractor = StructuredExtractor(date_policy=settings.MEETING_DATE_POLICY)
                candidates = extractor.extract(extracted)
                if self._cancel_requested:
                    self.root.after(0, lambda: self.info_text.insert(tk.END, "\n[ОТМЕНЕНО]\n"))
                    self.root.after(0, self._hide_progress)
                    return

                self.root.after(0, lambda: self.info_text.delete(1.0, tk.END))
                self.root.after(0, lambda: self.info_text.insert(tk.END, f"Анализ источника: {source}\n{'=' * 60}\n"))
                self.root.after(0, lambda: self.info_text.insert(tk.END, f"Листов: {list(extracted.sheets.keys())}\n\n"))

                all_candidates = []
                for sheet_name, sheet_cands in candidates.items():
                    all_candidates.extend(sheet_cands)
                for c in all_candidates:
                    self.root.after(0, lambda c=c: self.info_text.insert(tk.END,
                        f"[{c.candidate_id}] {c.subject[:60]}\n  {c.start_date or '—'} {c.start_time or '—'} {c.timezone or '—'}\n"))
                self.root.after(0, lambda: self.info_text.insert(tk.END, f"\nНайдено: {len(all_candidates)} кандидатов\n"))

                self.controller.set_extracted(extracted)
                self.controller.set_candidates(candidates)
                self.controller.set_skipped_rows(extractor.skipped_rows)
                self.controller.set_stage_success("stage_2")

                self.root.after(0, self._hide_progress)
                self.root.after(0, lambda: self._update_stage_indicators())
                self.root.after(0, lambda: self.controller.set_current_stage(1))
                self.root.after(0, self._show_stage_content)

            except Exception as e:
                self.root.after(0, lambda e_=e: self.info_text.insert(tk.END, f"\nОШИБКА: {e_}\n"))
                self.root.after(0, lambda e_=e: self.controller.set_stage_error("stage_2", str(e_)))
                self.root.after(0, self._hide_progress)
                self.root.after(0, self._update_stage_indicators)

        self._bg_thread = threading.Thread(target=bg_work, daemon=True)
        self._bg_thread.start()
        self._cancel_requested = False

    def _run_stages_3_to_6_bg(self, extracted, all_candidates: list) -> None:
        if self._cancel_requested: return
        self.root.after(0, lambda: self.info_text.insert(tk.END, "\n[Этап 3] Сравнение с календарём...\n"))
        try:
            calendar_gw = self.container.get_calendar_gateway() if self.container else None
            from datetime import date, timedelta

            from calendar_planner.app.settings import settings
            from calendar_planner.calendar.matcher import CalendarMatcher
            calendar_events: list = []
            tool_name = getattr(calendar_gw, '_find_tool', 'unknown') if calendar_gw else 'unknown'
            range_start = ""
            range_end = ""
            raw_event_count = 0
            if calendar_gw:
                candidate_dates = [d for c in all_candidates if c.start_date and (d := self._parse_candidate_date(c.start_date)) is not None]
                buffer = timedelta(days=settings.CALENDAR_DATE_RANGE_BUFFER_DAYS)
                range_start = (min(candidate_dates) - buffer).isoformat() if candidate_dates else date.today().isoformat()
                range_end = (max(candidate_dates) + buffer).isoformat() if candidate_dates else (date.today() + timedelta(days=90)).isoformat()
                try:
                    self.root.after(0, lambda: self._show_progress("Получение событий календаря...", 60))
                    calendar_events = calendar_gw.find_events(range_start, range_end)
                    raw_event_count = len(calendar_gw.get_last_raw_response())
                except Exception as exc:
                    self.root.after(0, lambda e_=exc: self.info_text.insert(tk.END, f"  Ошибка: {e_}\n"))
                    self.root.after(0, lambda e_=exc: self.controller.set_stage_error("stage_3", str(e_)))
                    self.controller.set_stage3_diagnostics({
                        "tool_name": tool_name,
                        "range_start": range_start,
                        "range_end": range_end,
                        "raw_event_count": 0,
                        "parsed_event_count": 0,
                        "duplicate_count": 0,
                        "new_count": len(all_candidates),
                        "status": "error",
                        "error": str(exc),
                    })
                    return
            if self._cancel_requested: return
            matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)
            matches = matcher.match_all(all_candidates, calendar_events)
            self.controller.set_matches(matches)
            self.controller.set_calendar_events(calendar_events)
            matched_count = sum(1 for m in matches.values() if m is not None and m.decision.name != "NEW")
            new_count = sum(1 for m in matches.values() if m is not None and m.decision.name == "NEW")
            self.root.after(0, lambda: self.info_text.insert(tk.END, f"  Совпадений: {matched_count}, новых: {new_count}\n"))
            stage3_diag = {
                "tool_name": tool_name,
                "range_start": range_start,
                "range_end": range_end,
                "raw_event_count": raw_event_count,
                "parsed_event_count": len(calendar_events),
                "duplicate_count": matched_count,
                "new_count": new_count,
                "status": "success",
            }
            if len(calendar_events) == 0:
                stage3_diag["status"] = "success_with_warnings"
                stage3_diag["warning"] = "В календаре не найдено событий в указанном диапазоне."
                self.controller.set_stage3_diagnostics(stage3_diag)
                self.root.after(0, lambda: self.info_text.insert(
                    tk.END, "  В календаре не найдено событий в указанном диапазоне.\n",
                ))
                self.root.after(0, lambda: self.controller.set_stage_success("stage_3"))
                self.controller.stages[2].status = StageStatus.SUCCESS_WITH_WARNINGS
                self.controller.stages[2].warnings.append(
                    "В календаре не найдено событий в указанном диапазоне."
                )
            else:
                self.controller.set_stage3_diagnostics(stage3_diag)
                self.root.after(0, lambda: self.controller.set_stage_success("stage_3"))
        except Exception as exc:
            self.root.after(0, lambda e_=exc: self.info_text.insert(tk.END, f"  ОШИБКА этапа 3: {e_}\n"))
            self.root.after(0, lambda e_=exc: self.controller.set_stage_error("stage_3", str(e_)))
            self.controller.set_stage3_diagnostics({
                "tool_name": getattr(calendar_gw, '_find_tool', 'unknown') if 'calendar_gw' in dir() else 'unknown',
                "range_start": range_start if 'range_start' in dir() else "",
                "range_end": range_end if 'range_end' in dir() else "",
                "raw_event_count": 0,
                "parsed_event_count": 0,
                "duplicate_count": 0,
                "new_count": len(all_candidates),
                "status": "error",
                "error": str(exc),
            })
            return

        if self._cancel_requested: return
        self.root.after(0, lambda: self._show_progress("Определение участников...", 70))
        self.root.after(0, lambda: self.info_text.insert(tk.END, "[Этап 4] Участники...\n"))
        try:
            directory_gw = self.container.get_directory_gateway() if self.container else None
            from calendar_planner.participants.resolver import ParticipantResolver
            resolver = ParticipantResolver(directory_gateway=directory_gw)
            participants = resolver.resolve(all_candidates, extracted)
            self.controller.set_participants(participants)
            self.root.after(0, lambda: self.controller.set_stage_success("stage_4"))
        except Exception as exc:
            self.root.after(0, lambda e_=exc: self.controller.set_stage_error("stage_4", str(e_)))

        if self._cancel_requested: return
        self.root.after(0, lambda: self._show_progress("Сбор описания...", 80))
        self.root.after(0, lambda: self.info_text.insert(tk.END, "[Этап 5] Дополнительные данные...\n"))
        try:
            from calendar_planner.enrichment.extractor import EnrichmentExtractor
            enrichment = EnrichmentExtractor().extract(all_candidates, extracted)
            self.controller.set_enrichment(enrichment)
            self.root.after(0, lambda: self.controller.set_stage_success("stage_5"))
        except Exception as exc:
            self.root.after(0, lambda e_=exc: self.controller.set_stage_error("stage_5", str(e_)))

        if self._cancel_requested: return
        self.root.after(0, lambda: self._show_progress("Формирование черновиков...", 90))
        self.root.after(0, lambda: self.info_text.insert(tk.END, "[Этап 6] Черновики...\n"))
        try:
            from calendar_planner.drafts.builder import DraftBuilder
            participants_map = {p.candidate_id: p for p in self.controller._participants}
            builder = DraftBuilder()
            drafts = []
            for candidate in all_candidates:
                cp = participants_map.get(candidate.candidate_id)
                items = self.controller._enrichment.get(candidate.candidate_id, [])
                draft = builder.build_from_candidate(candidate, cp, items)
                match_obj = self.controller._matches.get(candidate.candidate_id)
                if match_obj is not None:
                    draft.calendar_matches.append(match_obj)
                    draft.match_status = "checked"
                    draft.match_input_hash = draft.compute_input_hash()
                drafts.append(draft)
            self.controller.set_drafts(drafts)
            self.root.after(0, lambda: self.controller.set_stage_success("stage_6"))
            self.root.after(0, lambda: self.info_text.insert(tk.END, f"  Черновиков: {len(drafts)}\n"))
        except Exception as exc:
            self.root.after(0, lambda e_=exc: self.controller.set_stage_error("stage_6", str(e_)))

        self.root.after(0, lambda: self.info_text.insert(tk.END, "\nАнализ завершён.\n"))

    def _run_stages_3_to_6(self, extracted, all_candidates: list) -> None:
        self.info_text.insert(tk.END, "\n" + "=" * 60 + "\n")
        self.info_text.insert(tk.END, "Выполнение этапов 3-6...\n\n")

        # --- Stage 3: Calendar Comparison ---
        self.info_text.insert(tk.END, "[Этап 3] Сравнение с календарём...\n")
        try:
            calendar_gw = self.container.get_calendar_gateway() if self.container else None
            from datetime import date, timedelta

            from calendar_planner.app.settings import settings
            from calendar_planner.calendar.matcher import CalendarMatcher

            calendar_events: list = []
            if calendar_gw:
                candidate_dates = [
                    d for c in all_candidates
                    if c.start_date and (d := self._parse_candidate_date(c.start_date)) is not None
                ]
                if candidate_dates:
                    min_date = min(candidate_dates)
                    max_date = max(candidate_dates)
                    buffer = timedelta(days=settings.CALENDAR_DATE_RANGE_BUFFER_DAYS)
                    range_start = (min_date - buffer).isoformat()
                    range_end = (max_date + buffer).isoformat()
                else:
                    today = date.today().isoformat()
                    range_start = today
                    range_end = (date.today() + timedelta(days=90)).isoformat()

                try:
                    calendar_events = calendar_gw.find_events(range_start, range_end)
                except Exception as exc:
                    self.info_text.insert(tk.END, f"  Ошибка получения событий календаря: {exc}\n")
                    self.controller.set_stage_error("stage_3", str(exc))
                    self._update_stage_indicators()
                    return

            matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)
            matches = matcher.match_all(all_candidates, calendar_events)
            self.controller.set_matches(matches)
            self.controller.set_calendar_events(calendar_events)

            matched_count = sum(
                1 for m in matches.values()
                if m is not None and m.decision.name != "NEW"
            )
            self.info_text.insert(tk.END, f"  Сравнено: {len(all_candidates)}, найдено совпадений: {matched_count}\n")
            self.controller.set_stage_success("stage_3")
        except Exception as exc:
            self.info_text.insert(tk.END, f"  ОШИБКА этапа 3: {exc}\n")
            self.controller.set_stage_error("stage_3", str(exc))
            self._update_stage_indicators()
            self._show_stage_content()
            return

        # --- Stage 4: Participant Resolution ---
        self.info_text.insert(tk.END, "[Этап 4] Определение участников...\n")
        try:
            directory_gw = self.container.get_directory_gateway() if self.container else None
            from calendar_planner.participants.resolver import ParticipantResolver

            resolver = ParticipantResolver(directory_gateway=directory_gw)
            participants = resolver.resolve(all_candidates, extracted)
            self.controller.set_participants(participants)

            resolved_perf = sum(len(cp.performer) for cp in participants)
            resolved_cust = sum(len(cp.customer) for cp in participants)
            unresolved = sum(len(cp.unresolved) for cp in participants)
            self.info_text.insert(
                tk.END,
                f"  Исполнителей: {resolved_perf}, Заказчиков: {resolved_cust}, "
                f"Не найдено: {unresolved}\n",
            )
            self.controller.set_stage_success("stage_4")
        except Exception as exc:
            self.info_text.insert(tk.END, f"  ОШИБКА этапа 4: {exc}\n")
            self.controller.set_stage_error("stage_4", str(exc))

        # --- Stage 5: Enrichment ---
        self.info_text.insert(tk.END, "[Этап 5] Сбор дополнительных данных...\n")
        try:
            from calendar_planner.enrichment.extractor import EnrichmentExtractor

            enrichment_extractor = EnrichmentExtractor()
            enrichment = enrichment_extractor.extract(all_candidates, extracted)
            self.controller.set_enrichment(enrichment)

            total_items = sum(len(items) for items in enrichment.values())
            self.info_text.insert(tk.END, f"  Найдено элементов описания: {total_items}\n")
            self.controller.set_stage_success("stage_5")
        except Exception as exc:
            self.info_text.insert(tk.END, f"  ОШИБКА этапа 5: {exc}\n")
            self.controller.set_stage_error("stage_5", str(exc))

        # --- Stage 6: Build Drafts ---
        self.info_text.insert(tk.END, "[Этап 6] Формирование черновиков...\n")
        try:
            from calendar_planner.drafts.builder import DraftBuilder

            participants_map = {p.candidate_id: p for p in self.controller._participants}
            builder = DraftBuilder()

            drafts: list = []
            for candidate in all_candidates:
                cp = participants_map.get(candidate.candidate_id)
                items = self.controller._enrichment.get(candidate.candidate_id, [])
                draft = builder.build_from_candidate(candidate, cp, items)

                existing_match = matches.get(candidate.candidate_id)
                if existing_match is not None:
                    draft.calendar_matches.append(existing_match)
                    draft.match_status = "checked"
                    draft.match_input_hash = draft.compute_input_hash()

                drafts.append(draft)

            self.controller.set_drafts(drafts)

            ready_count = sum(1 for d in drafts if d.is_ready)
            self.info_text.insert(
                tk.END,
                f"  Черновиков создано: {len(drafts)}, готово: {ready_count}\n",
            )
            self.controller.set_stage_success("stage_6")

            self.controller.set_current_stage(5)
        except Exception as exc:
            self.info_text.insert(tk.END, f"  ОШИБКА этапа 6: {exc}\n")
            self.controller.set_stage_error("stage_6", str(exc))

        self.info_text.insert(tk.END, "\n" + "=" * 60 + "\n")
        self.info_text.insert(tk.END, "Анализ завершён.\n")

        self._update_stage_indicators()
        self._show_stage_content()

    def _save_session(self) -> None:
        try:
            session = self.controller.create_session(self.storage)
            self.info_text.insert(tk.END, f"\nСессия сохранена: {session.session_id}\n")
            self.info_text.insert(tk.END, f"Каталог: runs/{session.session_id}/\n")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить сессию: {e}")

    def _prev_stage(self) -> None:
        self.controller.prev_stage()
        self._update_stage_indicators()
        self._show_stage_content()

    def _go_to_stage(self, stage: int) -> None:
        self.controller.set_current_stage(stage)
        self._update_stage_indicators()
        self._show_stage_content()

    def _next_stage(self) -> None:
        self.controller.next_stage()
        self._update_stage_indicators()
        self._show_stage_content()

    def _copy_results(self) -> None:
        text = self.info_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.info_text.insert(tk.END, "\n[Результаты скопированы в буфер обмена]\n")

    def _update_stage_indicators(self) -> None:
        colors = {
            "success": "green",
            "success_with_warnings": "orange",
            "failed": "red",
            "in_progress": "blue",
            "stale": "gray",
            "not_started": "lightgray",
        }
        for i, (lbl, st_lbl) in enumerate(zip(self.stage_labels, self.stage_status_labels)):
            status = self.controller.get_stage_status(i)
            color = colors.get(status, "lightgray")
            st_lbl.config(foreground=color)
            if i == self.controller.current_stage:
                lbl.config(font=("", 9, "bold"))
            else:
                lbl.config(font=("", 9))

    def _show_stage_content(self) -> None:
        for widget in self.content_frame.winfo_children():
            if isinstance(widget, tk.Text) and widget is self.info_text:
                continue
            if isinstance(widget, ttk.Frame) and widget is self.info_text.master:
                continue
            widget.destroy()

        stage = self.controller.current_stage

        if stage == 0:
            self._show_stage_1_content()

        self.info_text.pack_forget()

        if stage == 0:
            self.info_text.pack(fill=tk.X, pady=5)

        elif stage == 1:
            self._show_stage_2_content()

        elif stage == 2:
            self._show_stage_3_content()

        elif stage == 3:
            self._show_stage_4_content()

        elif stage == 4:
            self._show_stage_5_content()

        elif stage == 5:
            self._show_stage_6_content()

    def _show_stage_1_content(self) -> None:
        from calendar_planner.ui.stages.stage1_connections import Stage1ConnectionsFrame
        frame = Stage1ConnectionsFrame(self.content_frame, container=self.container)
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[0] = frame

    def _show_stage_1(self) -> None:
        self.controller.set_current_stage(0)
        self._update_stage_indicators()
        self._show_stage_content()

    def _show_stage_2_content(self) -> None:
        self.info_text.pack(fill=tk.BOTH, expand=True, pady=5)

    def _show_stage_3_content(self) -> None:
        from calendar_planner.ui.stages.stage3_comparison import Stage3ComparisonFrame

        matches = self.controller._matches
        candidates_by_id = {c.candidate_id: c for c in self.controller.get_all_candidates()}

        frame = Stage3ComparisonFrame(self.content_frame, matches, candidates_by_id)
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[2] = frame

    def _show_stage_4_content(self) -> None:
        from calendar_planner.app.settings import settings
        from calendar_planner.ui.stages.stage4_participants import (
            Stage4ParticipantsFrame,
        )

        participants = self.controller._participants

        frame = Stage4ParticipantsFrame(
            self.content_frame,
            participants,
            performer_domains=settings.PERFORMER_EMAIL_DOMAINS,
            fuzzy_threshold=settings.CONTACT_FUZZY_THRESHOLD,
        )
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[3] = frame

    def _show_stage_5_content(self) -> None:
        from calendar_planner.ui.stages.stage5_enrichment import Stage5EnrichmentFrame

        enrichment = self.controller._enrichment
        candidates_by_id = {c.candidate_id: c for c in self.controller.get_all_candidates()}

        frame = Stage5EnrichmentFrame(
            self.content_frame,
            enrichment,
            candidates_by_id,
        )
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[4] = frame

    def _show_stage_6_content(self) -> None:
        from calendar_planner.ui.stages.stage6_creation import Stage6CreationFrame

        drafts = self.controller.get_drafts()
        on_recheck = self._make_recheck_callback()
        on_create = self._make_create_callback()
        on_real_create = self._make_real_create_callback()

        frame = Stage6CreationFrame(
            self.content_frame, drafts,
            on_recheck=on_recheck, on_create=on_create, on_real_create=on_real_create,
        )
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[5] = frame

    def _parse_candidate_date(self, date_str: str):
        from datetime import date as date_type
        try:
            return date_type.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None

    def _make_recheck_callback(self):
        def recheck_draft(draft):
            if self.container is None:
                messagebox.showwarning("Ошибка", "Контейнер не инициализирован")
                return

            calendar_gw = self.container.get_calendar_gateway()
            from datetime import date, timedelta

            from calendar_planner.app.settings import settings
            from calendar_planner.calendar.matcher import CalendarMatcher

            draft_date = self._parse_candidate_date(draft.start_date.value or "")
            if draft_date is not None:
                buffer = timedelta(days=settings.CALENDAR_DATE_RANGE_BUFFER_DAYS)
                range_start = (draft_date - buffer).isoformat()
                range_end = (draft_date + buffer).isoformat()
            else:
                today = date.today().isoformat()
                range_start = today
                range_end = (date.today() + timedelta(days=90)).isoformat()

            try:
                calendar_events = calendar_gw.find_events(range_start, range_end)
            except Exception as exc:
                messagebox.showerror("Ошибка", f"Не удалось получить события календаря: {exc}")
                raise

            matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)
            match = matcher.recheck_for_draft(
                subject=draft.subject.value or "",
                start_date=draft.start_date.value or "",
                start_time=draft.start_time.value or "",
                timezone=draft.timezone.value or "",
                calendar_events=calendar_events,
            )

            draft.calendar_matches = []
            if match is not None:
                match.candidate_id = draft.candidate_id
                draft.calendar_matches.append(match)
            draft.match_status = "checked"
            draft.match_input_hash = draft.compute_input_hash()

        return recheck_draft

    def _make_create_callback(self):
        def create_callback(draft, frame=None):
            if self.container is None:
                messagebox.showwarning("Ошибка", "Контейнер не инициализирован")
                return

            from calendar_planner.calendar.creator import EventCreator

            calendar_gw = self.container.get_calendar_gateway()
            creator = EventCreator(calendar_gw, dry_run=True)
            result = creator.create_one(draft)
            payload = creator.build_payload(draft)
            errors = _format_errors(result.get("errors", []))
            frame_obj = frame if frame is not None else self._stage_frames.get(5)
            if frame_obj is not None:
                frame_obj.show_creation_result(
                    draft_id=draft.draft_id,
                    subject=draft.subject.value or "Без темы",
                    status=result.get("status", "error"),
                    event_id=result.get("event_id", ""),
                    url=result.get("url", ""),
                    errors=errors,
                )

        return create_callback

    def _make_real_create_callback(self):
        def real_create_callback(draft, frame=None):
            if self.container is None:
                messagebox.showwarning("Ошибка", "Контейнер не инициализирован")
                return

            from calendar_planner.calendar.creator import EventCreator
            from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

            calendar_gw = self.container.get_calendar_gateway()
            if not isinstance(calendar_gw, MCPCalendarGateway):
                messagebox.showerror(
                    "Ошибка",
                    "Реальное создание доступно только через MCP-подключение.\n"
                    f"Текущий gateway: {type(calendar_gw).__name__}",
                )
                return
            if not calendar_gw.is_available():
                messagebox.showerror("Ошибка", "MCP-календарь недоступен.")
                return

            # Recheck duplicate before real create
            on_recheck = self._make_recheck_callback()
            on_recheck(draft)

            if draft.match_status != "checked":
                messagebox.showerror("Ошибка", "Не выполнена проверка дубля. Выполните предпросмотр и проверку дубля перед созданием.")
                return

            creator = EventCreator(calendar_gw, dry_run=False)

            # Build and validate payload BEFORE creating
            payload = creator.build_payload(draft)
            payload_errors = creator.validate_payload(payload)

            if payload_errors:
                messagebox.showerror(
                    "Ошибки payload",
                    "Невозможно создать событие — payload содержит ошибки:\n\n"
                    + "\n".join(f"• {e}" for e in payload_errors),
                )
                return

            import json
            payload_preview = json.dumps(payload, ensure_ascii=False, indent=2)
            if not messagebox.askyesno(
                "Подтверждение создания — предпросмотр",
                f"Будет создано реальное календарное событие:\n\n"
                f"Тема: {payload.get('subject', '—')}\n"
                f"Начало: {payload['start'].get('dateTime', '—')} ({payload['start'].get('timeZone', '—')})\n"
                f"Окончание: {payload.get('end', {}).get('dateTime', '—')}\n"
                f"Участников: {len(payload.get('attendees', []))}\n"
                f"Место: {payload.get('location', '—')}\n"
                f"Ссылка: {payload.get('online_meeting_url', '—')}\n\n"
                f"--- JSON payload ---\n{payload_preview}\n\n"
                f"Создать событие?",
            ):
                return

            result = creator.create_one(draft)
            result["payload"] = payload
            import datetime as dt
            result["created_at"] = dt.datetime.now(dt.UTC).isoformat()

            # Save to session controller
            if hasattr(self.controller, 'add_creation_result'):
                self.controller.add_creation_result(result)

            frame_obj = frame if frame is not None else self._stage_frames.get(5)
            if frame_obj is not None:
                event_id = result.get("event_id", "") or result.get("result", {}).get("id", "")
                event_url = result.get("url", "") or result.get("result", {}).get("htmlLink", "")
                status = result.get("status", "error")
                errors = _format_errors(result.get("errors", []))
                frame_obj.show_creation_result(
                    draft_id=draft.draft_id,
                    subject=draft.subject.value or "Без темы",
                    status=status,
                    event_id=event_id,
                    url=event_url,
                    errors=errors,
                )

        return real_create_callback

    def _check_connections(self) -> None:
        if self.container is None:
            return

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "=== Проверка подключений ===\n")
        self.info_text.insert(tk.END, "=" * 50 + "\n")

        try:
            check_result = self.container.check_all_connections()
            results = check_result.get("results", [])
            ready = check_result.get("ready_for_analysis", False)
        except Exception as e:
            self.info_text.insert(tk.END, f"\nОШИБКА проверки: {e}\n")
            self.controller.set_stage_error("stage_1", str(e))
            self._update_stage_indicators()
            return

        has_errors = False
        for r in results:
            component = r.get("component", "?")
            status = r.get("status", "?")
            message = r.get("message", "")
            symbol = {"success": "[OK]", "warning": "[WARN]", "failed": "[FAIL]"}.get(status, "[?]")
            line = f"{symbol} {component}: {message}\n"
            self.info_text.insert(tk.END, line)
            if status == "failed":
                has_errors = True
                error_text = r.get("error", "")
                if error_text:
                    self.info_text.insert(tk.END, f"       Ошибка: {error_text}\n")
                cid = r.get("correlation_id", "")
                if cid:
                    self.info_text.insert(tk.END, f"       Correlation ID: {cid}\n")

        self.info_text.insert(tk.END, "\n" + "=" * 50 + "\n")

        if has_errors:
            self.controller.set_stage_error("stage_1", "Обнаружены ошибки подключения")
            self.info_text.insert(tk.END, "ИТОГ: Обнаружены ошибки подключения\n")
        elif ready:
            self.controller.set_stage_success("stage_1")
            self.info_text.insert(tk.END, "ИТОГ: Подключения готовы к анализу\n")
        else:
            self.controller.set_stage_success("stage_1")
            self.controller.stages[0].status = StageStatus.SUCCESS_WITH_WARNINGS
            self.info_text.insert(tk.END, "ИТОГ: Подключения работают с предупреждениями\n")

        self._update_stage_indicators()

    def _show_connection_error_actions(self, results: list[dict]) -> None:
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, ttk.Frame) and getattr(widget, "_action_bar", False):
                widget.destroy()

        action_bar = ttk.Frame(self.main_frame)
        action_bar._action_bar = True
        action_bar.pack(fill=tk.X, pady=5)

        ttk.Button(
            action_bar, text="Копировать",
            command=self._copy_results,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            action_bar, text="Повторить",
            command=self._check_connections,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            action_bar, text="Вставить ошибки",
            command=lambda: self._paste_error_details(results),
        ).pack(side=tk.LEFT, padx=2)

    def _paste_error_details(self, results: list[dict]) -> None:
        lines = []
        for r in results:
            if r.get("status") == "failed":
                cid = r.get("correlation_id", "")
                error = r.get("error", "")
                lines.append(
                    f"{r.get('component', '?')}: {r.get('message', '')}"
                )
                if error:
                    lines.append(f"  Ошибка: {error}")
                if cid:
                    lines.append(f"  Correlation ID: {cid}")

        if lines:
            text = "\n".join(lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.info_text.insert(tk.END, "\n[Детали ошибок скопированы в буфер обмена]\n")

    def _on_close(self) -> None:
        if self.controller.has_unsaved_changes():
            result = messagebox.askyesnocancel(
                "Несохранённые изменения",
                "У вас есть несохранённые изменения. Сохранить сессию перед выходом?",
            )
            if result is None:
                return
            if result:
                self._save_session()
        self.root.destroy()