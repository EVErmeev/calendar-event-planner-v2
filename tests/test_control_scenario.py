from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_control_xlsx(filepath: str) -> None:
    import openpyxl

    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "\u041f\u043b\u0430\u043d-\u0433\u0440\u0430\u0444\u0438\u043a"
    ws1.append([
        "\u0422\u0435\u043c\u0430",
        "\u0421\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u043d\u0430\u044f \u0434\u0430\u0442\u0430",
        "\u0421\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u0415\u041a\u0411",
        "\u041f\u043b\u0430\u043d\u043e\u0432\u0430\u044f \u0434\u0430\u0442\u0430",
        "\u041f\u043b\u0430\u043d\u043e\u0432\u043e\u0435 \u0432\u0440\u0435\u043c\u044f",
        "\u0421\u043e\u0441\u0442\u0430\u0432 \u043a\u043e\u043c\u0430\u043d\u0434\u044b \u0438\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044f",
        "\u0421\u043e\u0441\u0442\u0430\u0432 \u043a\u043e\u043c\u0430\u043d\u0434\u044b \u0437\u0430\u043a\u0430\u0437\u0447\u0438\u043a\u0430",
        "\u0421\u0441\u044b\u043b\u043a\u0430",
    ])

    schedule_rows = [
        [
            "\u0421\u043e\u0437\u0432\u043e\u043d: \u041e\u0431\u0441\u0443\u0436\u0434\u0435\u043d\u0438\u0435 \u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u044b",
            "03.08.2026", "10:00", "02.08.2026", "09:00",
            "\u0413\u0443\u0440\u0435\u0435\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432; \u041f\u0435\u0442\u0440\u043e\u0432",
            "https://teams.example.com/arch",
        ],
        [
            "\u0412\u0441\u0442\u0440\u0435\u0447\u0430: \u041f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0441\u043f\u0440\u0438\u043d\u0442\u0430",
            "03.08.2026", "14:00", "03.08.2026", "15:00",
            "\u041f\u0435\u0442\u0440\u043e\u0432",
            "\u0421\u0438\u0434\u043e\u0440\u043e\u0432",
            "",
        ],
        [
            "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432: \u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0437\u0430\u043f\u0430\u0441\u0430\u043c\u0438\n- \u0421\u043a\u043b\u0430\u0434\n- \u041b\u043e\u0433\u0438\u0441\u0442\u0438\u043a\u0430\n- \u0423\u0447\u0451\u0442",
            "04.08.2026", "11:00", "04.08.2026", "10:30",
            "\u0413\u0443\u0440\u0435\u0435\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432",
            "https://teams.example.com/inventory",
        ],
        [
            "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u0432\u0441\u0442\u0440\u0435\u0447\u0430: \u0410\u043d\u0430\u043b\u0438\u0437 \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u0439",
            "04.08.2026", "16:00", "05.08.2026", "08:00",
            "\u0418\u0441\u043b\u0430\u043c\u0433\u0430\u043b\u0438\u0435\u0432; \u0421\u0438\u0434\u043e\u0440\u043e\u0432\u0430",
            "\u041f\u0435\u0442\u0440\u043e\u0432",
            "",
        ],
        [
            "\u0421\u043e\u0432\u0435\u0449\u0430\u043d\u0438\u0435: \u0421\u0442\u0430\u0442\u0443\u0441 \u043f\u0440\u043e\u0435\u043a\u0442\u0430",
            "05.08.2026", "09:00", "05.08.2026", "08:00",
            "\u0413\u0443\u0440\u0435\u0435\u0432; \u041f\u0435\u0442\u0440\u043e\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432; \u0421\u0438\u0434\u043e\u0440\u043e\u0432",
            "https://teams.example.com/status",
        ],
        [
            "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f: \u041e\u0442\u0447\u0451\u0442\u043d\u043e\u0441\u0442\u044c\n- \u0424\u043e\u0440\u043c\u0430 1\n- \u0424\u043e\u0440\u043c\u0430 2\n- \u042d\u043a\u0441\u043f\u043e\u0440\u0442",
            "05.08.2026", "15:00", "06.08.2026", "14:00",
            "\u0413\u0443\u0440\u0435\u0435\u0432",
            "\u0421\u0438\u0434\u043e\u0440\u043e\u0432; \u041f\u0435\u0442\u0440\u043e\u0432",
            "https://teams.example.com/reporting",
        ],
        [
            "\u041e\u0431\u0443\u0447\u0435\u043d\u0438\u0435: \u041d\u043e\u0432\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c",
            "06.08.2026", "12:00", "07.08.2026", "11:00",
            "\u041f\u0435\u0442\u0440\u043e\u0432; \u0421\u0438\u0434\u043e\u0440\u043e\u0432\u0430",
            "\u0418\u0432\u0430\u043d\u043e\u0432",
            "",
        ],
        [
            "\u0412\u043d\u0435\u0434\u0440\u0435\u043d\u0438\u0435: \u041c\u043e\u0434\u0443\u043b\u044c \u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u0438",
            "06.08.2026", "17:00", "07.08.2026", "09:00",
            "\u0413\u0443\u0440\u0435\u0435\u0432; \u041f\u0435\u0442\u0440\u043e\u0432",
            "\u0421\u0438\u0434\u043e\u0440\u043e\u0432; \u0418\u0432\u0430\u043d\u043e\u0432",
            "https://crm.example.com/integration",
        ],
        [
            "\u041d\u0435\u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u043d\u0430\u044f \u0432\u0441\u0442\u0440\u0435\u0447\u0430 1",
            "", "", "07.08.2026", "11:00",
            "\u041f\u0435\u0442\u0440\u043e\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432",
            "",
        ],
        [
            "\u041d\u0435\u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u043d\u0430\u044f \u0432\u0441\u0442\u0440\u0435\u0447\u0430 2",
            "", "", "07.08.2026", "15:00",
            "\u0421\u0438\u0434\u043e\u0440\u043e\u0432\u0430",
            "\u0421\u0438\u0434\u043e\u0440\u043e\u0432",
            "",
        ],
    ]
    for row in schedule_rows:
        ws1.append(row)

    ws2 = wb.create_sheet("\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u044b")
    ws2.append(["\u0424\u0418\u041e", "Email", "\u0422\u0435\u043b\u0435\u0444\u043e\u043d", "\u041e\u0440\u0433\u0430\u043d\u0438\u0437\u0430\u0446\u0438\u044f"])
    contacts = [
        ["\u0418\u0432\u0430\u043d\u043e\u0432 \u0418\u0432\u0430\u043d \u0418\u0432\u0430\u043d\u043e\u0432\u0438\u0447", "ivanov@customer.ru", "+79991112233", "\u041e\u041e\u041e \u0417\u0430\u043a\u0430\u0437\u0447\u0438\u043a"],
        ["\u041f\u0435\u0442\u0440\u043e\u0432 \u041f\u0451\u0442\u0440 \u041f\u0435\u0442\u0440\u043e\u0432\u0438\u0447", "petrov@customer.com", "+79992223344", "\u0417\u0410\u041e \u041a\u043b\u0438\u0435\u043d\u0442"],
        ["\u0421\u0438\u0434\u043e\u0440\u043e\u0432 \u0421\u0435\u0440\u0433\u0435\u0439 \u0421\u0435\u0440\u0433\u0435\u0435\u0432\u0438\u0447", "sidorov@partner.org", "+79993334455", "\u041e\u041e\u041e \u041f\u0430\u0440\u0442\u043d\u0451\u0440"],
    ]
    for row in contacts:
        ws2.append(row)

    wb.save(filepath)
    wb.close()


class TestControlScenario:

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self.temp_dir = tempfile.mkdtemp()
        self.xlsx_path = os.path.join(self.temp_dir, "control_scenario.xlsx")
        create_control_xlsx(self.xlsx_path)
        self.session_dir = os.path.join(self.temp_dir, "runs_control")
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.session_dir, ignore_errors=True)

    def test_7_duplicate_1_new(self):
        from calendar_planner.app.container import AppContainer

        # ── STAGE 1: Container + gateways ────────────────────────────
        from calendar_planner.app.settings import Settings
        from calendar_planner.domain.enums import (
            DescriptionItemType,
            MatchDecision,
            MeetingDatePolicy,
            StageStatus,
        )

        os.environ["APP_ENV"] = "test"
        os.environ["MCP_ENABLED"] = "false"
        os.environ["MCP_SERVER_URL"] = ""
        settings = Settings()
        container = AppContainer(settings)

        fixture_calendar = container.get_calendar_gateway()
        fixture_directory = container.get_directory_gateway()
        assert fixture_calendar.is_available()
        assert fixture_directory.is_available()

        # ── Pre-load calendar with 7 matching events ────────────────
        # Row 1..7 from XLSX will match; row 8 (17:00 06.08.2026) has NO match
        calendar_events = [
            self._make_event(
                "EVT-001",
                "\u0421\u043e\u0437\u0432\u043e\u043d: \u041e\u0431\u0441\u0443\u0436\u0434\u0435\u043d\u0438\u0435 \u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u044b",
                "2026-08-03T10:00:00",
            ),
            self._make_event(
                "EVT-002",
                "\u0412\u0441\u0442\u0440\u0435\u0447\u0430: \u041f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0441\u043f\u0440\u0438\u043d\u0442\u0430",
                "2026-08-03T14:00:00",
            ),
            self._make_event(
                "EVT-003",
                "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432: \u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0437\u0430\u043f\u0430\u0441\u0430\u043c\u0438",
                "2026-08-04T11:00:00",
            ),
            self._make_event(
                "EVT-004",
                "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u0432\u0441\u0442\u0440\u0435\u0447\u0430: \u0410\u043d\u0430\u043b\u0438\u0437 \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u0439",
                "2026-08-04T16:00:00",
            ),
            self._make_event(
                "EVT-005",
                "\u0421\u043e\u0432\u0435\u0449\u0430\u043d\u0438\u0435: \u0421\u0442\u0430\u0442\u0443\u0441 \u043f\u0440\u043e\u0435\u043a\u0442\u0430",
                "2026-08-05T09:00:00",
            ),
            self._make_event(
                "EVT-006",
                "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f: \u041e\u0442\u0447\u0451\u0442\u043d\u043e\u0441\u0442\u044c",
                "2026-08-05T15:00:00",
            ),
            self._make_event(
                "EVT-007",
                "\u041e\u0431\u0443\u0447\u0435\u043d\u0438\u0435: \u041d\u043e\u0432\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c",
                "2026-08-06T12:00:00",
            ),
        ]
        fixture_calendar._events = calendar_events
        assert len(fixture_calendar._events) == 7

        # ── STAGE 2: Read source + extract meetings (AGREED_ONLY) ───
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.source.registry import registry

        source_ref = SourceReference(type="file", path=self.xlsx_path)
        extracted_source = registry.read_source(source_ref)

        assert "\u041f\u043b\u0430\u043d-\u0433\u0440\u0430\u0444\u0438\u043a" in extracted_source.sheets
        assert "\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u044b" in extracted_source.sheets
        assert len(extracted_source.sheets["\u041f\u043b\u0430\u043d-\u0433\u0440\u0430\u0444\u0438\u043a"]) == 11

        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        result_by_sheet = extractor.extract(extracted_source)

        all_candidates = []
        for candidates in result_by_sheet.values():
            all_candidates.extend(candidates)

        assert len(all_candidates) == 8, f"Expected 8 AGREED_ONLY candidates, got {len(all_candidates)}"
        assert len(extractor.skipped_rows) == 2, f"Expected 2 skipped rows, got {len(extractor.skipped_rows)}"
        assert all(c.timezone == "Asia/Yekaterinburg" for c in all_candidates if c.timezone)
        assert all(c.has_agreed_datetime for c in all_candidates)

        # ── STAGE 3: Calendar comparison → 7 DUPLICATE + 1 NEW ──────
        from calendar_planner.calendar.matcher import CalendarMatcher

        matcher = CalendarMatcher(
            tolerance_minutes=settings.CALENDAR_MATCH_TOLERANCE_MINUTES,
            subject_threshold=settings.CALENDAR_SUBJECT_THRESHOLD,
        )
        matches = matcher.match_all(all_candidates, fixture_calendar._events)

        assert len(matches) == 8, f"Expected 8 comparisons, got {len(matches)}"

        duplicate_count = sum(
            1 for m in matches.values()
            if m is not None and m.decision == MatchDecision.DUPLICATE
        )
        new_count = sum(
            1 for m in matches.values()
            if m is not None and m.decision == MatchDecision.NEW
        )

        assert duplicate_count == 7, f"Expected EXACTLY 7 DUPLICATE, got {duplicate_count}"
        assert new_count == 1, f"Expected EXACTLY 1 NEW, got {new_count}"

        new_candidate_id = next(
            cid for cid, m in matches.items()
            if m is not None and m.decision == MatchDecision.NEW
        )
        new_candidate = next(c for c in all_candidates if c.candidate_id == new_candidate_id)
        assert new_candidate.subject is not None

        # ── STAGE 4: Resolve participants ────────────────────────────
        from calendar_planner.participants.resolver import ParticipantResolver

        resolver = ParticipantResolver(
            directory_gateway=fixture_directory,
            performer_domains=settings.PERFORMER_EMAIL_DOMAINS,
            fuzzy_threshold=settings.CONTACT_FUZZY_THRESHOLD,
        )
        participant_results = resolver.resolve(all_candidates, extracted_source)

        assert len(participant_results) == 8
        for cp in participant_results:
            assert cp.candidate_id is not None
            assert len(cp.performer) + len(cp.customer) + len(cp.unresolved) > 0, \
                f"No participants resolved for {cp.candidate_id}"

        total_performers = sum(len(cp.performer) for cp in participant_results)
        total_customers = sum(len(cp.customer) for cp in participant_results)
        total_unresolved = sum(len(cp.unresolved) for cp in participant_results)
        assert total_performers > 0
        assert total_customers + total_unresolved > 0

        # ── STAGE 5: Enrichment extraction ───────────────────────────
        from calendar_planner.enrichment.extractor import EnrichmentExtractor

        enrich_extractor = EnrichmentExtractor()
        enrichment_map = enrich_extractor.extract(all_candidates, extracted_source)

        assert len(enrichment_map) == 8
        total_items = sum(len(items) for items in enrichment_map.values())
        assert total_items > 0

        agenda_items = sum(
            1 for items in enrichment_map.values()
            for i in items
            if (isinstance(i.item_type, DescriptionItemType) and i.item_type == DescriptionItemType.AGENDA)
            or i.item_type == "agenda"
        )
        link_or_url_items = sum(
            1 for items in enrichment_map.values()
            for i in items
            if i.item_type in (DescriptionItemType.LINK, "link")
            or i.item_type == DescriptionItemType.ONLINE_MEETING_URL
        )
        assert agenda_items > 0
        assert link_or_url_items > 0

        # ── STAGE 6: Build drafts, validate, dry-run create ──────────
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

        builder = DraftBuilder()
        editor = DraftEditor()
        creator = EventCreator(fixture_calendar, dry_run=True)

        drafts = []
        for candidate in all_candidates:
            cp = next((p for p in participant_results if p.candidate_id == candidate.candidate_id), None)
            enrich = enrichment_map.get(candidate.candidate_id, [])
            draft = builder.build_from_candidate(candidate, cp, enrich)
            drafts.append(draft)

        assert len(drafts) == 8
        assert all(d.draft_id for d in drafts)
        assert all(d.candidate_id for d in drafts)
        assert all(d.subject.value for d in drafts)

        first_draft = drafts[0]
        assert first_draft.draft_id == "DRF-0001"
        assert first_draft.start_date.value is not None
        assert first_draft.start_time.value is not None
        assert first_draft.timezone.value == "Asia/Yekaterinburg"
        assert first_draft.duration_confirmed is False

        editor.set_duration(first_draft, 60)
        assert first_draft.duration_minutes.value == 60
        assert first_draft.duration_confirmed is True

        end_date, end_time = first_draft.compute_end_datetime()
        assert end_date is not None
        assert end_time is not None

        for draft in drafts:
            if not draft.duration_confirmed:
                editor.set_duration(draft, 60)
            if draft.match_status not in ("checked",):
                draft.match_status = "checked"
                draft.match_input_hash = draft.compute_input_hash()
            draft.is_ready = True

        ready = [d for d in drafts if d.duration_confirmed]
        assert len(ready) == 8

        all_creation_results = []
        for d in ready:
            result = creator.create_one(d)
            all_creation_results.append(result)

        assert len(all_creation_results) == 8

        dry_runs = [r for r in all_creation_results if r.get("status") == "dry_run"]
        invalid = [r for r in all_creation_results if r.get("status") == "invalid"]
        assert len(dry_runs) > 0
        assert len(invalid) == 0, f"Unexpected invalid drafts: {invalid}"

        payload = creator.build_payload(ready[0])
        payload_errors = creator.validate_payload(payload)
        assert len(payload_errors) == 0

        # ── VERIFY 0 real events created ─────────────────────────────
        assert not any(
            r.get("status") == "created" for r in all_creation_results
        ), "Real events must never be created in this test"

        found_real = any(
            r.get("status") == "created" for r in creator.get_all_results()
        )
        assert not found_real

        # ── STAGE 7: Save session artifacts ──────────────────────────
        from calendar_planner.session.models import StageState
        from calendar_planner.session.storage import SessionStorage

        storage = SessionStorage(base_dir=self.session_dir)
        session = storage.create_session(
            source_ref={"type": "file", "path": self.xlsx_path}
        )

        session.stages = [
            StageState(name="container", status=StageStatus.SUCCESS),
            StageState(name="extraction", status=StageStatus.SUCCESS,
                       data={"candidates": 8, "skipped": 2}),
            StageState(name="comparison", status=StageStatus.SUCCESS,
                       data={"duplicate": 7, "new": 1}),
            StageState(name="participants", status=StageStatus.SUCCESS,
                       data={"performer_count": total_performers,
                             "customer_count": total_customers,
                             "unresolved_count": total_unresolved}),
            StageState(name="enrichment", status=StageStatus.SUCCESS,
                       data={"total_items": total_items}),
            StageState(name="drafts", status=StageStatus.SUCCESS,
                       data={"drafts": len(drafts)}),
            StageState(name="creation", status=StageStatus.SUCCESS,
                       data={"dry_runs": len(dry_runs), "real_events": 0}),
        ]
        session.candidates_json = json.dumps(
            [c.to_dict() for c in all_candidates], ensure_ascii=False
        )
        session.drafts_json = json.dumps(
            [d.to_dict() for d in drafts], ensure_ascii=False
        )

        session.calendar_events_json = json.dumps(
            [e.to_dict() for e in fixture_calendar._events], ensure_ascii=False
        )

        match_list = [
            {"candidate_id": cid, "match": m.to_dict() if m else None}
            for cid, m in matches.items()
        ]
        session.calendar_matches_json = json.dumps(match_list, ensure_ascii=False)

        session.creation_results_json = json.dumps(
            all_creation_results, ensure_ascii=False
        )

        storage.save_session(session)

        loaded = storage.load_session(session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert len(loaded.stages) == 7
        assert loaded.stages[1].name == "extraction"
        assert loaded.stages[1].data.get("candidates") == 8
        assert loaded.stages[2].name == "comparison"
        assert loaded.stages[2].data.get("duplicate") == 7
        assert loaded.stages[2].data.get("new") == 1
        assert loaded.candidates_json == session.candidates_json
        assert loaded.drafts_json == session.drafts_json

        print(
            "\nCONTROL SCENARIO PASSED: "
            "8 candidates (7 DUPLICATE + 1 NEW), "
            f"{len(dry_runs)} dry-run drafts, 0 real events, "
            "session saved & restored"
        )

    # ── helper ───────────────────────────────────────────────────────
    @staticmethod
    def _make_event(event_id: str, subject: str, dt_str: str):
        from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime
        from calendar_planner.domain.models import CalendarEvent, NormalizedDateTime

        tz = "Asia/Yekaterinburg"
        start = parse_iso_datetime(dt_str, tz)
        end_dt = start.aware_datetime + timedelta(hours=1)
        end = NormalizedDateTime(
            raw_datetime=end_dt.isoformat(),
            raw_timezone=tz,
            aware_datetime=end_dt,
            utc_datetime=end_dt.astimezone(ZoneInfo("UTC")),
            display_datetime=end_dt,
            display_timezone=tz,
        )
        return CalendarEvent(
            event_id=event_id,
            ical_uid=f"uid-{event_id}",
            subject=subject,
            start=start,
            end=end,
        )