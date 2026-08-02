"""Live source integration test for Google Sheets with 9 candidates."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


class TestLiveGoogleSheet:
    """Tests using the actual live Google Sheet structure (mock download)."""

    @pytest.fixture
    def live_xlsx_fixture(self):
        """Build a test XLSX matching the live Google Sheet structure."""

        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "План-график"

        # Headers matching live sheet
        ws.append([
            "Блок", "Согласованная дата", "Согласованное время, ЕКБ",
            "Плановая дата", "Плановое время",
            "Состав команды исполнителя", "Состав команды заказчика",
        ])

        # 9 agreed rows + 2 planned-only rows
        rows = [
            ["Управление производством\n- Планирование\n- Обеспечение", "2026-07-24 00:00:00", "12:00:00", "2026-07-23", "10:00", "Гуреев; Петров", "Иванов"],
            ["Управление доставкой", "2026-07-25 00:00:00", "14:00:00", "2026-07-24", "12:00", "Сидорова", "Петрова"],
            ["Управление складом", "2026-07-28 00:00:00", "16:00:00", "2026-07-27", "14:00", "Гуреев", "Смирнов"],
            ["Финансовый блок", "2026-07-30 00:00:00", "10:00:00", "2026-07-29", "10:00", "Петров", "Кузнецов"],
            ["Блок HR", "2026-08-03 00:00:00", "11:00:00", "2026-08-02", "11:00", "Сидорова", "Федорова"],
            ["Блок логистики", "2026-08-04 00:00:00", "09:00:00", "2026-08-03", "09:00", "Гуреев", "Николаев"],
            ["ИТ инфраструктура", "2026-08-05 00:00:00", "16:00:00", "2026-08-04", "14:00", "Петров", "Алексеев"],
            ["Маркетинг", "2026-08-06 00:00:00", "12:00:00", "2026-08-05", "12:00", "Сидорова", "Дмитриев"],
            ["Обучение", "2026-08-07 00:00:00", "10:00:00", "2026-08-06", "10:00", "Гуреев", "Антонов"],
            # Planned-only rows (should be skipped)
            ["Плановый блок A", "", "", "2026-08-10", "14:00", "", ""],
            ["Плановый блок B", "", "", "2026-08-11", "15:00", "", ""],
        ]
        for row in rows:
            ws.append(row)

        # Contact sheet
        ws2 = wb.create_sheet("Контакты")
        ws2.append(["ФИО", "Email", "Телефон", "Организация"])
        ws2.append(["Иванов Иван", "ivanov@example.com", "+79991234567", "Заказчик"])
        ws2.append(["Петрова Анна", "petrova@example.com", "+79997654321", "Заказчик"])
        ws2.append(["Смирнов Пётр", "smirnov@example.com", "+79991112233", "Заказчик"])

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name
        wb.save(temp_path)
        wb.close()

        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    def test_live_structure_9_candidates(self, live_xlsx_fixture):
        """Verify 9 candidates extracted, 2 skipped."""
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.source.registry import registry

        source = SourceReference(type="file", path=live_xlsx_fixture)
        extracted = registry.read_source(source)

        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        candidates_map = extractor.extract(extracted)

        all_candidates = []
        for cands in candidates_map.values():
            all_candidates.extend(cands)

        assert len(all_candidates) == 9, f"Expected 9, got {len(all_candidates)}"
        assert len(extractor.skipped_rows) == 2

    def test_live_date_normalization(self, live_xlsx_fixture):
        """Verify datetime values are normalized correctly."""
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.source.registry import registry

        source = SourceReference(type="file", path=live_xlsx_fixture)
        extracted = registry.read_source(source)
        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        result = extractor.extract(extracted)

        all_candidates = []
        for cands in result.values():
            all_candidates.extend(cands)

        # First candidate should have correct date
        c1 = all_candidates[0]
        assert c1.start_date == "2026-07-24", f"Got {c1.start_date}"
        assert c1.start_time == "12:00", f"Got {c1.start_time}"
        assert c1.timezone == "Asia/Yekaterinburg"

        # Third candidate
        c3 = all_candidates[2]
        assert c3.start_date == "2026-07-28", f"Got {c3.start_date}"
        assert c3.start_time == "16:00", f"Got {c3.start_time}"

        # Ninth candidate
        c9 = all_candidates[8]
        assert c9.start_date == "2026-08-07", f"Got {c9.start_date}"
        assert c9.start_time == "10:00", f"Got {c9.start_time}"

    def test_live_contact_sheet_loaded(self, live_xlsx_fixture):
        """Verify both sheets are loaded."""
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.registry import registry

        source = SourceReference(type="file", path=live_xlsx_fixture)
        extracted = registry.read_source(source)

        assert "План-график" in extracted.sheets or "Plan-grafik" in extracted.sheets
        assert "Контакты" in extracted.sheets or "Kontakty" in extracted.sheets

    def test_live_pipeline_stage_2_to_3(self, live_xlsx_fixture):
        """Verify Stage 2 → Stage 3 flow works against fixture calendar."""
        os.environ["APP_ENV"] = "test"
        os.environ["MCP_ENABLED"] = "false"

        from datetime import datetime
        from zoneinfo import ZoneInfo

        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.enums import MatchDecision, MeetingDatePolicy
        from calendar_planner.domain.models import (
            CalendarEvent,
            NormalizedDateTime,
            SourceReference,
        )
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.source.registry import registry

        # Stage 2
        source = SourceReference(type="file", path=live_xlsx_fixture)
        extracted = registry.read_source(source)
        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        result = extractor.extract(extracted)
        all_candidates = []
        for cands in result.values():
            all_candidates.extend(cands)

        assert len(all_candidates) == 9

        # Stage 3 — with 7 pre-loaded calendar events
        events = []
        for i in range(7):
            c = all_candidates[i]
            events.append(CalendarEvent(
                event_id=f"cal-{i}",
                ical_uid=f"uid-{i}",
                subject=c.subject,
                start=NormalizedDateTime(
                    raw_datetime=f"{c.start_date}T{c.start_time}:00",
                    raw_timezone=c.timezone,
                    aware_datetime=datetime.fromisoformat(f"{c.start_date}T{c.start_time}:00").replace(tzinfo=ZoneInfo(c.timezone)),
                    utc_datetime=datetime.fromisoformat(f"{c.start_date}T{c.start_time}:00").replace(tzinfo=ZoneInfo(c.timezone)).astimezone(ZoneInfo("UTC")),
                    display_datetime=datetime.fromisoformat(f"{c.start_date}T{c.start_time}:00").replace(tzinfo=ZoneInfo(c.timezone)),
                    display_timezone=c.timezone,
                ),
            ))

        matcher = CalendarMatcher()
        matches = matcher.match_all(all_candidates, events)

        dup_count = sum(1 for m in matches.values() if m and m.decision == MatchDecision.DUPLICATE)
        new_count = sum(1 for m in matches.values() if m and m.decision == MatchDecision.NEW)

        assert dup_count == 7, f"Expected 7 DUPLICATE, got {dup_count}"
        assert new_count == 2, f"Expected 2 NEW, got {new_count}"

        os.environ.pop("APP_ENV", None)
        os.environ.pop("MCP_ENABLED", None)
