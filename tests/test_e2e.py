from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_xlsx(filepath: str) -> None:
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
            "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432: \u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u043e\u043c\n- \u041f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435\n- \u041e\u0431\u0435\u0441\u043f\u0435\u0447\u0435\u043d\u0438\u0435\n- \u0412\u044b\u043f\u0443\u0441\u043a",
            "31.07.2026", "10:00", "01.08.2026", "09:00",
            "\u0413\u0443\u0440\u0435\u0435\u0432; \u0418\u0441\u043b\u0430\u043c\u0433\u0430\u043b\u0438\u0435\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432; \u041f\u0435\u0442\u0440\u043e\u0432",
            "https://teams.example.com/prod-demo",
        ],
        [
            "\u0421\u043e\u0437\u0432\u043e\u043d: \u041e\u0431\u0441\u0443\u0436\u0434\u0435\u043d\u0438\u0435 \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u0439",
            "01.08.2026", "14:00", "02.08.2026", "15:00",
            "\u041f\u0435\u0442\u0440\u043e\u0432",
            "\u0421\u0438\u0434\u043e\u0440\u043e\u0432",
            "https://zoom.us/j/12345",
        ],
        [
            "\u0412\u0441\u0442\u0440\u0435\u0447\u0430: \u0410\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u0430 \u0441\u0438\u0441\u0442\u0435\u043c\u044b",
            "02.08.2026", "11:00", "03.08.2026", "10:30",
            "\u0413\u0443\u0440\u0435\u0435\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432",
            "",
        ],
        [
            "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u0432\u0441\u0442\u0440\u0435\u0447\u0430: \u041f\u043b\u0430\u043d \u043c\u0438\u0433\u0440\u0430\u0446\u0438\u0438",
            "03.08.2026", "09:00", "04.08.2026", "08:00",
            "\u0418\u0441\u043b\u0430\u043c\u0433\u0430\u043b\u0438\u0435\u0432; \u0421\u0438\u0434\u043e\u0440\u043e\u0432\u0430",
            "\u041f\u0435\u0442\u0440\u043e\u0432",
            "https://teams.example.com/migration",
        ],
        [
            "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f: \u041e\u0442\u0447\u0451\u0442\u043d\u043e\u0441\u0442\u044c\n- \u0424\u043e\u0440\u043c\u0430 1\n- \u0424\u043e\u0440\u043c\u0430 2\n- \u042d\u043a\u0441\u043f\u043e\u0440\u0442",
            "04.08.2026", "16:00", "05.08.2026", "14:00",
            "\u0413\u0443\u0440\u0435\u0435\u0432; \u041f\u0435\u0442\u0440\u043e\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432",
            "https://teams.example.com/report",
        ],
        [
            "\u0421\u043e\u0432\u0435\u0449\u0430\u043d\u0438\u0435: \u0418\u0442\u043e\u0433\u0438 \u043d\u0435\u0434\u0435\u043b\u0438",
            "05.08.2026", "12:00", "06.08.2026", "11:00",
            "\u0413\u0443\u0440\u0435\u0435\u0432",
            "\u0421\u0438\u0434\u043e\u0440\u043e\u0432; \u041f\u0435\u0442\u0440\u043e\u0432",
            "",
        ],
        [
            "\u0412\u043d\u0435\u0434\u0440\u0435\u043d\u0438\u0435 \u043c\u043e\u0434\u0443\u043b\u044f CRM",
            "06.08.2026", "10:00", "07.08.2026", "09:00",
            "\u041f\u0435\u0442\u0440\u043e\u0432; \u0421\u0438\u0434\u043e\u0440\u043e\u0432\u0430",
            "\u0418\u0432\u0430\u043d\u043e\u0432",
            "https://crm.example.com",
        ],
        [
            "\u041e\u0431\u0443\u0447\u0435\u043d\u0438\u0435 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439",
            "07.08.2026", "15:00", "08.08.2026", "14:30",
            "\u0413\u0443\u0440\u0435\u0435\u0432; \u0418\u0441\u043b\u0430\u043c\u0433\u0430\u043b\u0438\u0435\u0432",
            "\u041f\u0435\u0442\u0440\u043e\u0432; \u0421\u0438\u0434\u043e\u0440\u043e\u0432",
            "",
        ],
        [
            "\u041d\u0435\u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u043d\u0430\u044f \u0432\u0441\u0442\u0440\u0435\u0447\u0430 1",
            "", "", "10.08.2026", "11:00",
            "\u041f\u0435\u0442\u0440\u043e\u0432",
            "\u0418\u0432\u0430\u043d\u043e\u0432",
            "",
        ],
        [
            "\u041d\u0435\u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u043d\u0430\u044f \u0432\u0441\u0442\u0440\u0435\u0447\u0430 2",
            "", "", "12.08.2026", "13:00",
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


def _make_calendar_event(event_id, subject, dt_str, tz_str):
    from calendar_planner.domain.models import CalendarEvent
    from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime

    start = parse_iso_datetime(dt_str, tz_str)
    end_dt = start.aware_datetime + timedelta(hours=1)
    from calendar_planner.domain.models import NormalizedDateTime

    end = NormalizedDateTime(
        raw_datetime=end_dt.isoformat(),
        raw_timezone=tz_str,
        aware_datetime=end_dt,
        utc_datetime=end_dt.astimezone(ZoneInfo("UTC")),
        display_datetime=end_dt,
        display_timezone=tz_str,
    )
    return CalendarEvent(
        event_id=event_id,
        ical_uid=f"uid-{event_id}",
        subject=subject,
        start=start,
        end=end,
    )


class TestE2EPipeline:

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self.temp_dir = tempfile.mkdtemp()
        self.xlsx_path = os.path.join(self.temp_dir, "test_schedule.xlsx")
        create_test_xlsx(self.xlsx_path)
        self.session_dir = os.path.join(self.temp_dir, "runs_e2e")
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.session_dir, ignore_errors=True)

    def test_full_pipeline_stages_1_8(self):
        from calendar_planner.domain.enums import (
            MeetingDatePolicy,
            MatchDecision,
            ParticipantSide,
            ParticipantRole,
            DescriptionItemType,
        )
        from calendar_planner.domain.models import SourceReference

        stage_results = []

        # ============================================================
        # STAGE 1: Container initialization and connection checks
        # ============================================================
        from calendar_planner.app.settings import Settings
        from calendar_planner.app.container import AppContainer

        os.environ["MCP_ENABLED"] = "false"
        os.environ["MCP_SERVER_URL"] = ""
        settings = Settings()
        container = AppContainer(settings)

        connections = container.check_all_connections()
        assert len(connections) > 0
        fixture_calendar = container.get_calendar_gateway()
        fixture_directory = container.get_directory_gateway()
        assert fixture_calendar.is_available()
        assert fixture_directory.is_available()

        stage_results.append("Stage 1: PASS")

        # ============================================================
        # STAGE 2: Read source + extract meetings (AGREED_ONLY)
        # ============================================================
        from calendar_planner.source.registry import registry
        from calendar_planner.extraction.structured import StructuredExtractor

        source_ref = SourceReference(type="file", path=self.xlsx_path)
        extracted_source = registry.read_source(source_ref)

        assert "План-график" in extracted_source.sheets
        assert "Контакты" in extracted_source.sheets
        assert len(extracted_source.sheets["План-график"]) == 11

        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        result_by_sheet = extractor.extract(extracted_source)

        all_candidates = []
        for candidates in result_by_sheet.values():
            all_candidates.extend(candidates)

        assert len(all_candidates) == 8
        assert len(extractor.skipped_rows) == 2
        assert all(c.timezone == "Asia/Yekaterinburg" for c in all_candidates if c.timezone)
        assert all(c.has_agreed_datetime for c in all_candidates)

        stage_results.append(
            f"Stage 2: PASS — {len(all_candidates)} candidates, "
            f"{len(extractor.skipped_rows)} skipped, TZ=Asia/Yekaterinburg"
        )

        # ============================================================
        # STAGE 3: Calendar comparison via matcher
        # ============================================================
        from calendar_planner.calendar.matcher import CalendarMatcher

        fixture_events = [
            _make_calendar_event(
                "EVT-001",
                "Демонстрация процессов: Управление производством",
                "2026-07-31T10:00:00", "Asia/Yekaterinburg",
            ),
            _make_calendar_event(
                "EVT-002",
                "Созвон: Обсуждение требований",
                "2026-08-01T14:00:00", "Asia/Yekaterinburg",
            ),
            _make_calendar_event(
                "EVT-003",
                "Старая встреча не в плане",
                "2026-01-15T09:00:00", "Asia/Yekaterinburg",
            ),
        ]
        fixture_calendar._events = fixture_events

        matcher = CalendarMatcher(
            tolerance_minutes=settings.CALENDAR_MATCH_TOLERANCE_MINUTES,
            subject_threshold=settings.CALENDAR_SUBJECT_THRESHOLD,
        )
        matches = matcher.match_all(all_candidates, fixture_events)

        assert len(matches) == 8
        duplicate_count = sum(
            1 for m in matches.values()
            if m is not None and m.decision == MatchDecision.DUPLICATE
        )
        new_count = sum(
            1 for m in matches.values()
            if m is not None and m.decision == MatchDecision.NEW
        )
        assert duplicate_count >= 2
        assert new_count > 0

        stage_results.append(
            f"Stage 3: PASS — {len(matches)} comparisons, "
            f"{duplicate_count} DUPLICATE, {new_count} NEW"
        )

        # ============================================================
        # STAGE 4: Resolve participants
        # ============================================================
        from calendar_planner.participants.resolver import ParticipantResolver

        resolver = ParticipantResolver(
            directory_gateway=fixture_directory,
            performer_domains=settings.PERFORMER_EMAIL_DOMAINS,
            fuzzy_threshold=settings.CONTACT_FUZZY_THRESHOLD,
        )
        participant_results = resolver.resolve(all_candidates, extracted_source)

        assert len(participant_results) == 8
        total_performers = sum(len(cp.performer) for cp in participant_results)
        total_customers = sum(len(cp.customer) for cp in participant_results)
        total_unresolved = sum(len(cp.unresolved) for cp in participant_results)
        assert total_performers > 0
        assert total_customers + total_unresolved > 0

        stage_results.append(
            f"Stage 4: PASS — {total_performers} performers, "
            f"{total_customers} customers, {total_unresolved} unresolved"
        )

        # ============================================================
        # STAGE 5: Extract enrichment items
        # ============================================================
        from calendar_planner.enrichment.extractor import EnrichmentExtractor

        enrich_extractor = EnrichmentExtractor()
        enrichment_map = enrich_extractor.extract(all_candidates, extracted_source)

        assert len(enrichment_map) == 8
        total_items = sum(len(items) for items in enrichment_map.values())
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
        assert total_items > 0
        assert agenda_items > 0
        assert link_or_url_items > 0

        stage_results.append(
            f"Stage 5: PASS — {total_items} items, "
            f"{agenda_items} agendas, {link_or_url_items} links/urls"
        )

        # ============================================================
        # STAGE 6: Build drafts, edit, validate, dry-run create
        # ============================================================
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.domain.models import ResolvedParticipant, DraftField

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

        editor.edit_subject(first_draft, "Новая тема после редактирования")
        assert first_draft.subject.value == "Новая тема после редактирования"
        assert first_draft.subject.modified_by_user is True

        new_attendee = ResolvedParticipant(
            full_name="Новый Участник",
            email="new@example.com",
            side=ParticipantSide.CUSTOMER,
            role=ParticipantRole.REQUIRED,
        )
        before_count = len(first_draft.required_attendees) + len(first_draft.optional_attendees)
        editor.add_attendee(first_draft, new_attendee)
        after_count = len(first_draft.required_attendees) + len(first_draft.optional_attendees)
        assert after_count == before_count + 1
        assert first_draft.match_status == "stale"

        editor.remove_attendee(first_draft, "new@example.com")
        assert len(first_draft.required_attendees) + len(first_draft.optional_attendees) == before_count

        first_draft.match_status = "checked"
        first_draft.match_input_hash = first_draft.compute_input_hash()
        recheck = matcher.recheck_for_draft(
            first_draft.subject.value or "",
            first_draft.start_date.value or "",
            first_draft.start_time.value or "",
            first_draft.timezone.value or "Asia/Yekaterinburg",
            fixture_events,
        )
        assert recheck is not None

        payload = creator.build_payload(first_draft)
        assert "subject" in payload
        assert "start" in payload
        assert "end" in payload
        assert payload["start"]["dateTime"] is not None
        assert payload["end"]["dateTime"] is not None

        payload_errors = creator.validate_payload(payload)
        assert len(payload_errors) == 0

        for draft in drafts:
            if not draft.duration_confirmed:
                editor.set_duration(draft, 60)
            if draft.match_status not in ("checked",):
                draft.match_status = "checked"
                draft.match_input_hash = draft.compute_input_hash()

        for draft in drafts:
            draft.is_ready = True
        ready = [d for d in drafts if d.duration_confirmed]

        all_creation_results = []
        for d in ready:
            result = creator.create_one(d)
            all_creation_results.append(result)

        assert len(all_creation_results) > 0
        dry_runs = [r for r in all_creation_results if r.get("status") == "dry_run"]
        assert len(dry_runs) > 0

        stage_results.append(
            f"Stage 6: PASS — {len(drafts)} drafts, "
            f"{len(dry_runs)} dry-run created, payload validates"
        )

        # ============================================================
        # STAGE 7: Save and restore session (full roundtrip)
        # ============================================================
        from calendar_planner.session.storage import SessionStorage
        from calendar_planner.session.models import StageState
        from calendar_planner.domain.enums import StageStatus

        storage = SessionStorage(base_dir=self.session_dir)
        session = storage.create_session(
            source_ref={"type": "file", "path": self.xlsx_path}
        )

        session.stages = [
            StageState(name="container", status=StageStatus.SUCCESS),
            StageState(name="extraction", status=StageStatus.SUCCESS, data={"candidates": 8, "skipped": 2}),
            StageState(name="comparison", status=StageStatus.SUCCESS, data={"matches": 8}),
            StageState(name="participants", status=StageStatus.SUCCESS, data={"performer_count": total_performers}),
            StageState(name="enrichment", status=StageStatus.SUCCESS, data={"total_items": total_items}),
            StageState(name="drafts", status=StageStatus.SUCCESS, data={"drafts": len(drafts)}),
        ]
        session.candidates_json = json.dumps(
            [c.to_dict() for c in all_candidates], ensure_ascii=False
        )
        session.drafts_json = json.dumps(
            [d.to_dict() for d in drafts], ensure_ascii=False
        )
        storage.save_session(session)

        loaded = storage.load_session(session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert len(loaded.stages) == 6
        assert loaded.stages[1].name == "extraction"
        assert loaded.stages[1].data.get("candidates") == 8
        assert loaded.candidates_json == session.candidates_json
        assert loaded.drafts_json == session.drafts_json

        stage_results.append("Stage 7: PASS — session roundtrip")

        # ============================================================
        # FINAL VERIFICATION
        # ============================================================
        assert not any(
            r.get("status") == "created" for r in all_creation_results
        ), "Real events must never be created in this test"

        found_real = any(
            r.get("status") == "created" for r in creator.get_all_results()
        )
        assert not found_real

        stage_results.append(
            "Stage 8: PASS — all stages verified, 0 real events created"
        )

        print("\n" + "\n".join(stage_results))
        assert len(stage_results) == 8
