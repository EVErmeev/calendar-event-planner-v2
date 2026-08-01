from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json

from calendar_planner.ui.controllers import StageController
from calendar_planner.session.storage import SessionStorage
from calendar_planner.session.models import RunSession
from calendar_planner.domain.enums import StageStatus


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
        self._build_stage_sidebar()
        self._build_main_area()
        self._build_bottom_panel()

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
            lbl = ttk.Label(frame, text=name, font=("", 9))
            lbl.pack(side=tk.LEFT)
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

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, f"Анализ источника: {source}\n")
        self.info_text.insert(tk.END, "=" * 60 + "\n")

        try:
            from calendar_planner.domain.models import SourceReference
            from calendar_planner.source.registry import registry
            from calendar_planner.extraction.structured import StructuredExtractor
            from calendar_planner.app.settings import settings

            if source.startswith("http"):
                src_ref = SourceReference(type="url", url=source)
            else:
                src_ref = SourceReference(type="file", path=source)

            extracted = registry.read_source(src_ref)
            self.info_text.insert(tk.END, f"Тип: {src_ref.type}\n")
            self.info_text.insert(tk.END, f"Листов загружено: {list(extracted.sheets.keys())}\n\n")

            extractor = StructuredExtractor(date_policy=settings.MEETING_DATE_POLICY)
            candidates = extractor.extract(extracted)

            self.controller.set_extracted(extracted)
            self.controller.set_candidates(candidates)
            self.controller.set_skipped_rows(extractor.skipped_rows)

            all_candidates = self.controller.get_all_candidates()

            for c in all_candidates:
                self.info_text.insert(tk.END, (
                    f"[{c.candidate_id}] {c.subject[:60]}\n"
                    f"  Дата: {c.start_date or '—'} | Время: {c.start_time or '—'} | TZ: {c.timezone or '—'}\n"
                ))

            self.info_text.insert(tk.END, f"\nВсего найдено: {len(all_candidates)} кандидатов\n")
            self.info_text.insert(tk.END, f"Пропущено: {len(extractor.skipped_rows)} строк\n")
            for sr in extractor.skipped_rows:
                self.info_text.insert(tk.END, f"  {sr['sheet']} R{sr['row']}: {sr['reason']}\n")

            self.controller.set_stage_success("stage_1")
            self.controller.set_stage_success("stage_2")

            self._run_stages_3_to_6(extracted, all_candidates)

        except Exception as e:
            self.info_text.insert(tk.END, f"\nОШИБКА: {e}\n")
            self.controller.set_stage_error("stage_2", str(e))
            self._update_stage_indicators()
            self._show_stage_content()

    def _run_stages_3_to_6(self, extracted, all_candidates: list) -> None:
        self.info_text.insert(tk.END, "\n" + "=" * 60 + "\n")
        self.info_text.insert(tk.END, "Выполнение этапов 3-6...\n\n")

        # --- Stage 3: Calendar Comparison ---
        self.info_text.insert(tk.END, "[Этап 3] Сравнение с календарём...\n")
        try:
            calendar_gw = self.container.get_calendar_gateway() if self.container else None
            from calendar_planner.calendar.matcher import CalendarMatcher

            calendar_events: list = []
            if calendar_gw:
                from datetime import date, timedelta
                today = date.today().isoformat()
                week_later = (date.today() + timedelta(days=90)).isoformat()
                try:
                    calendar_events = calendar_gw.find_events(today, week_later)
                except Exception as exc:
                    self.info_text.insert(tk.END, f"  Предупреждение: не удалось получить события календаря: {exc}\n")

            matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)
            matches = matcher.match_all(all_candidates, calendar_events)
            self.controller.set_matches(matches)
            self.controller.set_calendar_events(calendar_events)

            matched_count = sum(1 for m in matches.values() if m is not None)
            self.info_text.insert(tk.END, f"  Сравнено: {len(all_candidates)}, найдено совпадений: {matched_count}\n")
            self.controller.set_stage_success("stage_3")
        except Exception as exc:
            self.info_text.insert(tk.END, f"  ОШИБКА этапа 3: {exc}\n")
            self.controller.set_stage_error("stage_3", str(exc))

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
        from calendar_planner.ui.stages.stage4_participants import Stage4ParticipantsFrame

        participants = self.controller._participants

        frame = Stage4ParticipantsFrame(self.content_frame, participants)
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[3] = frame

    def _show_stage_5_content(self) -> None:
        from calendar_planner.ui.stages.stage5_enrichment import Stage5EnrichmentFrame

        enrichment = self.controller._enrichment
        candidates_by_id = {c.candidate_id: c for c in self.controller.get_all_candidates()}

        frame = Stage5EnrichmentFrame(self.content_frame, enrichment, candidates_by_id)
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[4] = frame

    def _show_stage_6_content(self) -> None:
        from calendar_planner.ui.stages.stage6_creation import Stage6CreationFrame

        drafts = self.controller.get_drafts()
        on_recheck = self._make_recheck_callback()

        frame = Stage6CreationFrame(self.content_frame, drafts, on_recheck=on_recheck)
        frame.pack(fill=tk.BOTH, expand=True)
        self._stage_frames[5] = frame

    def _make_recheck_callback(self):
        def recheck_draft(draft):
            if self.container is None:
                messagebox.showwarning("Ошибка", "Контейнер не инициализирован")
                return

            calendar_gw = self.container.get_calendar_gateway()
            from calendar_planner.calendar.matcher import CalendarMatcher
            from datetime import date, timedelta

            today = date.today().isoformat()
            week_later = (date.today() + timedelta(days=90)).isoformat()
            try:
                calendar_events = calendar_gw.find_events(today, week_later)
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

            if match is None:
                draft.match_status = "checked"
            else:
                draft.match_status = "checked"

        return recheck_draft

    def _check_connections(self) -> None:
        if self.container is None:
            return

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "=== Проверка подключений ===\n")
        self.info_text.insert(tk.END, "=" * 50 + "\n")

        try:
            results = self.container.check_all_connections()
        except Exception as e:
            self.info_text.insert(tk.END, f"\nОШИБКА проверки: {e}\n")
            self.controller.set_stage_error("stage_1", str(e))
            self._update_stage_indicators()
            return

        all_ok = True
        has_errors = False

        for r in results:
            component = r.get("component", "?")
            status = r.get("status", "?")
            message = r.get("message", "")
            symbol = {
                "success": "[OK]",
                "warning": "[WARN]",
                "failed": "[FAIL]",
            }.get(status, "[?]")

            line = f"{symbol} {component}: {message}\n"
            self.info_text.insert(tk.END, line)

            if status == "failed":
                has_errors = True
                all_ok = False
                error_text = r.get("error", "")
                if error_text:
                    self.info_text.insert(tk.END, f"       Ошибка: {error_text}\n")
                cid = r.get("correlation_id", "")
                if cid:
                    self.info_text.insert(tk.END, f"       Correlation ID: {cid}\n")
            elif status == "warning":
                all_ok = False

        self.info_text.insert(tk.END, "\n" + "=" * 50 + "\n")

        if has_errors:
            self.controller.set_stage_error("stage_1", "Обнаружены ошибки подключения")
            self.info_text.insert(tk.END, "ИТОГ: Обнаружены ошибки подключения\n")
        elif not all_ok:
            self.controller.set_stage_success("stage_1")
            self.controller.stages[0].status = StageStatus.SUCCESS_WITH_WARNINGS
            self.info_text.insert(tk.END, "ИТОГ: Подключения работают с предупреждениями\n")
        else:
            self.controller.set_stage_success("stage_1")
            self.info_text.insert(tk.END, "ИТОГ: Все подключения в порядке\n")

        self._update_stage_indicators()

        if has_errors:
            self._show_connection_error_actions(results)

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