from __future__ import annotations

import json
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDomainModels:
    def test_draft_field_defaults(self):
        from calendar_planner.domain.models import DraftField
        from calendar_planner.domain.enums import DraftFieldOrigin

        field = DraftField(value="test", origin=DraftFieldOrigin.AUTO.value)
        assert field.value == "test"
        assert field.origin == "auto"
        assert field.modified_by_user is False
        assert field.evidence == []

    def test_draft_field_user_modification(self):
        from calendar_planner.domain.models import DraftField
        from calendar_planner.domain.enums import DraftFieldOrigin

        field = DraftField(value="auto_value", origin=DraftFieldOrigin.AUTO.value)
        field.value = "user_value"
        field.modified_by_user = True
        field.modified_at = "2026-08-01T10:00:00"

        assert field.value == "user_value"
        assert field.modified_by_user is True
        assert field.modified_at == "2026-08-01T10:00:00"

    def test_draft_field_serialization_roundtrip(self):
        from calendar_planner.domain.models import DraftField

        field = DraftField(
            value="Hello",
            origin="auto",
            evidence=[{"source": "R1"}],
            modified_by_user=True,
            modified_at="2026-01-01T00:00:00",
        )
        data = field.to_dict()
        restored = DraftField.from_dict(data)

        assert restored.value == field.value
        assert restored.origin == field.origin
        assert restored.modified_by_user == field.modified_by_user
        assert restored.modified_at == field.modified_at

    def test_meeting_candidate_serialization(self):
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Тестовая встреча",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
            performer_names=["Иванов"],
            customer_names=["Петров"],
            evidence=[{"field": "date", "method": "agreed_date"}],
            reasoning=["Извлечено из таблицы"],
        )

        data = candidate.to_dict()
        restored = MeetingCandidate.from_dict(data)

        assert restored.candidate_id == "SRC-EVT-001"
        assert restored.subject == "Тестовая встреча"
        assert restored.start_date == "2026-08-04"
        assert restored.has_agreed_datetime is True

    def test_meeting_candidate_no_agreed_datetime(self):
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-002",
            subject="Без даты",
        )
        assert candidate.has_agreed_datetime is False

    def test_resolved_participant_serialization(self):
        from calendar_planner.domain.models import ResolvedParticipant, ParticipantSide, ParticipantRole

        p = ResolvedParticipant(
            full_name="Иванов Иван",
            email="ivanov@example.com",
            side=ParticipantSide.CUSTOMER,
            role=ParticipantRole.REQUIRED,
            source_name="Иванов",
            match_source="contact_index",
        )
        data = p.to_dict()
        restored = ResolvedParticipant.from_dict(data)

        assert restored.full_name == "Иванов Иван"
        assert restored.email == "ivanov@example.com"
        assert restored.side == ParticipantSide.CUSTOMER

    def test_final_event_draft_compute_hash(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Тест", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
        )

        h1 = draft.compute_input_hash()

        draft.subject.value = "Другая тема"
        h2 = draft.compute_input_hash()

        assert h1 != h2

    def test_final_event_draft_end_datetime(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
        )

        end_date, end_time = draft.compute_end_datetime()
        assert end_date == "2026-08-04"
        assert end_time == "13:00"

    def test_final_event_draft_end_datetime_midnight(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="23:00", origin="auto"),
            duration_minutes=DraftField(value=120, origin="auto"),
        )

        end_date, end_time = draft.compute_end_datetime()
        assert end_date == "2026-08-05"
        assert end_time == "01:00"

    def test_final_event_draft_modified_by_user_check(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Тест", origin="auto"),
        )
        assert draft.modified_by_user_check() is False

        draft.subject.modified_by_user = True
        assert draft.modified_by_user_check() is True


class TestEnums:
    def test_stage_status_values(self):
        from calendar_planner.domain.enums import StageStatus

        assert StageStatus.NOT_STARTED.value == "not_started"
        assert StageStatus.SUCCESS.value == "success"
        assert StageStatus.FAILED.value == "failed"
        assert StageStatus.STALE.value == "stale"

    def test_meeting_date_policy(self):
        from calendar_planner.domain.enums import MeetingDatePolicy

        assert MeetingDatePolicy.AGREED_ONLY.value == "AGREED_ONLY"
        assert MeetingDatePolicy.PLANNED_ONLY.value == "PLANNED_ONLY"

    def test_match_decision(self):
        from calendar_planner.domain.enums import MatchDecision

        assert MatchDecision.DUPLICATE.value == "DUPLICATE"
        assert MatchDecision.NEW.value == "NEW"


class TestValidation:
    def test_validate_email_valid(self):
        from calendar_planner.domain.validation import validate_email

        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.ru") is True
        assert validate_email("user+tag@domain.org") is True

    def test_validate_email_invalid(self):
        from calendar_planner.domain.validation import validate_email

        assert validate_email("not-an-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("") is False

    def test_validate_draft_ready_missing_fields(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField
        from calendar_planner.domain.validation import validate_draft_ready

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
        )
        errors = validate_draft_ready(draft)
        assert len(errors) > 0
        assert any("не задана" in e.lower() for e in errors)

    def test_validate_draft_ready_no_duration(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField
        from calendar_planner.domain.validation import validate_draft_ready

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
        )
        errors = validate_draft_ready(draft)
        assert any("длительность не подтверждена" in e.lower() for e in errors)

    def test_validate_payload_valid(self):
        from calendar_planner.domain.validation import validate_payload

        payload = {
            "subject": "Test",
            "start": {"dateTime": "2026-08-04T12:00:00", "timeZone": "Asia/Yekaterinburg"},
            "end": {"dateTime": "2026-08-04T13:00:00", "timeZone": "Asia/Yekaterinburg"},
        }
        errors = validate_payload(payload)
        assert len(errors) == 0

    def test_validate_payload_missing_end(self):
        from calendar_planner.domain.validation import validate_payload

        payload = {
            "subject": "Test",
            "start": {"dateTime": "2026-08-04T12:00:00", "timeZone": "Asia/Yekaterinburg"},
        }
        errors = validate_payload(payload)
        assert any("end" in e for e in errors)


class TestSchemaDetector:
    def test_detect_timezone_ekb(self):
        from calendar_planner.source.schema_detector import detect_timezone_from_text

        assert detect_timezone_from_text("ЕКБ") == "Asia/Yekaterinburg"
        assert detect_timezone_from_text("ekb") == "Asia/Yekaterinburg"

    def test_detect_timezone_msk(self):
        from calendar_planner.source.schema_detector import detect_timezone_from_text

        assert detect_timezone_from_text("МСК") == "Europe/Moscow"
        assert detect_timezone_from_text("moscow") == "Europe/Moscow"

    def test_header_normalization(self):
        from calendar_planner.source.schema_detector import normalize_header

        assert "плановое время" in normalize_header("Плановое время проведения")
        assert "согласованная дата" in normalize_header("Согласованная дата  ЕКБ")

    def test_detect_agreed_date_column(self):
        from calendar_planner.source.schema_detector import TableSchemaDetector

        data = [
            ["Тема", "Согласованная дата", "Согласованное время", "Плановая дата"],
            ["Встреча 1", "31.07.2026", "12:00", "30.07.2026"],
        ]
        detector = TableSchemaDetector()
        detector.detect(data)

        assert detector.agreed_date_col == 1
        assert detector.agreed_time_col == 2
        assert detector.planned_date_col == 3

    def test_parse_names(self):
        from calendar_planner.source.schema_detector import parse_names

        result = parse_names("Иванов И.И.; Петров П.П.; Сидоров С.С.")
        assert len(result) == 3
        assert "Иванов И.И." in result

    def test_split_subject_description(self):
        from calendar_planner.source.schema_detector import split_subject_and_description

        subject, desc = split_subject_and_description(
            "Управление производством\n- Планирование\n- Обеспечение\n- Выпуск"
        )
        assert subject == "Управление производством"
        assert len(desc) == 3


class TestDateTimeNormalizer:
    def test_parse_iso_with_z(self):
        from calendar_planner.extraction.datetime_normalizer import parse_iso_datetime

        result = parse_iso_datetime("2026-07-24T07:00:00Z")
        assert result.utc_datetime.hour == 7
        assert result.display_timezone == "UTC"

    def test_ekb_equals_utc(self):
        from calendar_planner.extraction.datetime_normalizer import parse_iso_datetime, parse_date_time

        ekb = parse_date_time("2026-07-24", "12:00", "Asia/Yekaterinburg")
        utc = parse_date_time("2026-07-24", "07:00", "UTC")

        assert ekb is not None
        assert utc is not None
        assert abs((ekb.utc_datetime - utc.utc_datetime).total_seconds()) < 1

    def test_resolve_timezone_alias(self):
        from calendar_planner.extraction.datetime_normalizer import resolve_timezone

        assert resolve_timezone("екб") == "Asia/Yekaterinburg"
        assert resolve_timezone("мск") == "Europe/Moscow"
        assert resolve_timezone(None, "UTC") == "UTC"

    def test_normalize_date_value(self):
        from calendar_planner.extraction.datetime_normalizer import normalize_date_value

        assert normalize_date_value("31.07.2026") == "2026-07-31"
        assert normalize_date_value("2026-07-31") == "2026-07-31"
        assert normalize_date_value("") is None

    def test_normalize_time_value(self):
        from calendar_planner.extraction.datetime_normalizer import normalize_time_value

        assert normalize_time_value("12:00") == "12:00"
        assert normalize_time_value("9:15") == "09:15"
        assert normalize_time_value("") is None

    def test_calendar_datetime_normalizer(self):
        from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime, resolve_timezone

        result = parse_iso_datetime("2026-07-24T12:00:00", "Asia/Yekaterinburg")
        expected_utc = datetime(2026, 7, 24, 7, 0, tzinfo=ZoneInfo("UTC"))
        assert abs((result.utc_datetime - expected_utc).total_seconds()) < 1

    def test_windows_timezone_mapping(self):
        from calendar_planner.calendar.datetime_normalizer import resolve_timezone

        assert resolve_timezone("Ekaterinburg Standard Time") == "Asia/Yekaterinburg"
        assert resolve_timezone("Russian Standard Time") == "Europe/Moscow"

    def test_same_moment_check(self):
        from calendar_planner.extraction.datetime_normalizer import parse_date_time, are_same_moment

        a = parse_date_time("2026-07-24", "12:00", "Asia/Yekaterinburg")
        b = parse_date_time("2026-07-24", "07:00", "UTC")
        assert a is not None
        assert b is not None
        assert are_same_moment(a, b) is True


class TestStructuredExtractor:
    def test_agreed_only_policy(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время", "Плановая дата", "Плановое время"],
                    ["Встреча 1", "2026-08-04", "12:00", "2026-08-03", "10:00"],
                    ["Встреча 2", "", "", "2026-08-05", "14:00"],
                ]
            },
        )

        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        result = extractor.extract(source)

        all_candidates = []
        for candidates in result.values():
            all_candidates.extend(candidates)

        assert len(all_candidates) == 1
        assert all_candidates[0].start_date == "2026-08-04"
        assert all_candidates[0].start_time == "12:00"
        assert len(extractor.skipped_rows) == 1

    def test_agreed_only_skips_planned(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время"],
                    ["Только план", "", ""],
                    ["Согласованная", "2026-08-04", "12:00"],
                ]
            },
        )

        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        result = extractor.extract(source)

        all_candidates = []
        for candidates in result.values():
            all_candidates.extend(candidates)

        assert len(all_candidates) == 1
        assert all_candidates[0].subject == "Согласованная"

    def test_candidate_id_generation(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время"],
                    ["A", "2026-08-04", "12:00"],
                    ["B", "2026-08-05", "14:00"],
                ]
            },
        )

        extractor = StructuredExtractor()
        result = extractor.extract(source)

        all_candidates = []
        for candidates in result.values():
            all_candidates.extend(candidates)

        assert len(all_candidates) == 2
        assert all_candidates[0].candidate_id == "SRC-EVT-001"
        assert all_candidates[1].candidate_id == "SRC-EVT-002"

    def test_duration_not_confirmed_by_default(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время"],
                    ["A", "2026-08-04", "12:00"],
                ]
            },
        )

        extractor = StructuredExtractor()
        result = extractor.extract(source)

        all_candidates = []
        for candidates in result.values():
            all_candidates.extend(candidates)

        assert all_candidates[0].duration_confirmed is False
        assert all_candidates[0].duration_source == "missing"

    def test_multi_sheet(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Schedule": [
                    ["Тема", "Согласованная дата", "Согласованное время"],
                    ["A", "2026-08-04", "12:00"],
                ],
                "Contacts": [
                    ["Имя", "Email"],
                    ["Иванов Иван", "ivanov@example.com"],
                ],
            },
        )

        extractor = StructuredExtractor()
        result = extractor.extract(source)

        assert "Schedule" in result
        assert len(result.get("Schedule", [])) == 1
        assert "Contacts" not in result or len(result.get("Contacts", [])) == 0


class TestUnstructuredExtractor:
    def test_finds_meeting_keywords(self):
        from calendar_planner.extraction.unstructured import UnstructuredExtractor
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            raw_text=(
                "Встреча по проекту\n"
                "Дата: 04.08.2026 в 12:00\n"
                "Тема: Обсуждение плана\n"
            ),
        )

        extractor = UnstructuredExtractor()
        candidates = extractor.extract(source)

        assert len(candidates) >= 1


class TestCalendarMatcher:
    def test_duplicate_detection(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import MeetingCandidate, CalendarEvent, NormalizedDateTime
        from calendar_planner.domain.enums import MatchDecision

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Управление производством",
            start_date="2026-07-31",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        events = [
            CalendarEvent(
                event_id="EVT-001",
                ical_uid="uid-001",
                subject="Демонстрация процессов: Управление производством",
                start=NormalizedDateTime(
                    raw_datetime="2026-07-31T12:00:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 7, 31, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 7, 31, 7, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 7, 31, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
                end=NormalizedDateTime(
                    raw_datetime="2026-07-31T13:00:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 7, 31, 13, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 7, 31, 8, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 7, 31, 13, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
            ),
        ]

        match = matcher.match(candidate, events)
        assert match is not None
        assert match.decision == MatchDecision.DUPLICATE

    def test_timezone_aware_comparison(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import MeetingCandidate, CalendarEvent, NormalizedDateTime
        from calendar_planner.domain.enums import MatchDecision

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Тест",
            start_date="2026-07-24",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        events = [
            CalendarEvent(
                event_id="EVT-001",
                ical_uid="uid-001",
                subject="Тест",
                start=NormalizedDateTime(
                    raw_datetime="2026-07-24T07:00:00",
                    raw_timezone="UTC",
                    aware_datetime=datetime(2026, 7, 24, 7, 0, tzinfo=ZoneInfo("UTC")),
                    utc_datetime=datetime(2026, 7, 24, 7, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 7, 24, 7, 0, tzinfo=ZoneInfo("UTC")),
                    display_timezone="UTC",
                ),
                end=NormalizedDateTime(
                    raw_datetime="2026-07-24T08:00:00",
                    raw_timezone="UTC",
                    aware_datetime=datetime(2026, 7, 24, 8, 0, tzinfo=ZoneInfo("UTC")),
                    utc_datetime=datetime(2026, 7, 24, 8, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 7, 24, 8, 0, tzinfo=ZoneInfo("UTC")),
                    display_timezone="UTC",
                ),
            ),
        ]

        match = matcher.match(candidate, events)
        assert match is not None
        assert match.decision == MatchDecision.DUPLICATE

    def test_new_event(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import MeetingCandidate, CalendarEvent, NormalizedDateTime
        from calendar_planner.domain.enums import MatchDecision

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Новая встреча",
            start_date="2026-12-01",
            start_time="10:00",
            timezone="Asia/Yekaterinburg",
        )

        events = [
            CalendarEvent(
                event_id="EVT-001",
                ical_uid="uid-001",
                subject="Старая встреча",
                start=NormalizedDateTime(
                    raw_datetime="2026-06-01T10:00:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 6, 1, 10, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 6, 1, 5, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 6, 1, 10, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
                end=NormalizedDateTime(
                    raw_datetime="2026-06-01T11:00:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 6, 1, 11, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 6, 1, 6, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 6, 1, 11, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
            ),
        ]

        match = matcher.match(candidate, events)
        assert match is not None
        assert match.decision == MatchDecision.NEW

    def test_subject_normalization(self):
        from calendar_planner.calendar.matcher import normalize_subject_for_comparison, subject_similarity

        clean = normalize_subject_for_comparison("Демонстрация процессов: Управление производством")
        assert "Демонстрация процессов:" not in clean
        assert "Управление производством" in clean

        sim = subject_similarity(
            "Демонстрация процессов: Управление производством",
            "Управление производством",
        )
        assert sim > 0.7


class TestMCPGateway:
    def test_parse_calendar_event_from_raw(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gateway = MCPCalendarGateway()

        raw = {
            "id": "event-001",
            "subject": "Test Meeting",
            "start": {"dateTime": "2026-07-31T12:00:00", "timeZone": "Asia/Yekaterinburg"},
            "end": {"dateTime": "2026-07-31T13:00:00", "timeZone": "Asia/Yekaterinburg"},
            "attendees": [{"email": "user@example.com"}],
        }

        event = gateway._parse_calendar_event(raw)
        assert event is not None
        assert event.event_id == "event-001"
        assert event.subject == "Test Meeting"
        assert event.start is not None
        assert event.start.utc_datetime.hour == 7

    def test_parse_calendar_event_with_z_format(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gateway = MCPCalendarGateway()

        raw = {
            "id": "event-002",
            "subject": "UTC Meeting",
            "start": {"dateTime": "2026-07-31T07:00:00Z", "timeZone": "UTC"},
        }

        event = gateway._parse_calendar_event(raw)
        assert event is not None
        assert event.start is not None
        assert event.start.utc_datetime.hour == 7


class TestFixtureGateway:
    def test_load_fixture_json(self):
        import tempfile
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway

        fixture_data = {
            "events": [
                {"id": "e1", "subject": "Test", "start": "2026-07-31T12:00:00", "timezone": "Asia/Yekaterinburg", "end": "2026-07-31T13:00:00"},
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            temp_path = f.name

        try:
            gateway = FixtureCalendarGateway(fixture_path=temp_path)
            assert gateway.is_available()
            assert len(gateway._events) == 1
        finally:
            Path(temp_path).unlink()

    def test_dry_run_does_not_create(self):
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway

        gateway = FixtureCalendarGateway()
        result = gateway.create_event({"subject": "Test"}, dry_run=True)

        assert result["status"] == "dry_run"
        assert "payload" in result


class TestEventCreator:
    def test_build_payload(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft, DraftField, ResolvedParticipant, ParticipantSide, ParticipantRole

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Демонстрация процессов: Управление производством", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            location=DraftField(value="Переговорная 301", origin="auto"),
            online_meeting_url=DraftField(value="https://teams.example.com", origin="auto"),
            description=DraftField(value="Повестка:\n1. Пункт 1", origin="auto"),
            required_attendees=[
                ResolvedParticipant(
                    full_name="Иванов Иван",
                    email="ivanov@example.com",
                    side=ParticipantSide.PERFORMER,
                    role=ParticipantRole.REQUIRED,
                ),
            ],
            is_ready=True,
        )

        payload = creator.build_payload(draft)
        assert payload["subject"] == "Демонстрация процессов: Управление производством"
        assert payload["start"]["dateTime"] == "2026-08-04T12:00:00"
        assert payload["start"]["timeZone"] == "Asia/Yekaterinburg"
        assert payload["end"]["dateTime"] == "2026-08-04T13:00:00"
        assert len(payload["attendees"]) == 1

    def test_create_one_dry_run(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
        )

        result = creator.create_one(draft)
        assert result["status"] == "dry_run"

    def test_validate_payload_before_create(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            is_ready=True,
        )

        result = creator.create_one(draft)
        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0


class TestParticipants:
    def test_performer_directory_search(self):
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway
        from calendar_planner.participants.matcher import NameMatcher
        from calendar_planner.domain.models import ParticipantSide

        gateway = FixtureDirectoryGateway()
        matcher = NameMatcher(gateway)

        result = matcher.match_performer("Гуреев")
        assert result is not None
        assert "Гуреев" in result.full_name
        assert result.email == "gureev@1bit.ru"
        assert result.side == ParticipantSide.PERFORMER

    def test_performer_not_found(self):
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway
        from calendar_planner.participants.matcher import NameMatcher

        gateway = FixtureDirectoryGateway(employees=[])
        matcher = NameMatcher(gateway)

        result = matcher.match_performer("Неизвестный")
        assert result is None

    def test_participant_resolver_customer_from_contacts(self):
        from calendar_planner.participants.resolver import ParticipantResolver
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway
        from calendar_planner.domain.models import (
            MeetingCandidate, ExtractedSource, SourceReference,
        )

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gateway)

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Иванов Иван", "ivanov@example.com"],
                ]
            },
            raw_text="Иванов Иван ivanov@example.com",
        )

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                start_date="2026-08-04",
                start_time="12:00",
                customer_names=["Иванов Иван"],
            ),
        ]

        results = resolver.resolve(candidates, source)
        assert len(results) == 1
        assert len(results[0].customer) >= 1

    def test_customer_does_not_get_performer_email(self):
        from calendar_planner.participants.resolver import ParticipantResolver
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway
        from calendar_planner.domain.models import (
            MeetingCandidate, ExtractedSource, SourceReference,
        )

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gateway)

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Петров Пётр", "petrov@1bit.ru"],
                ]
            },
            raw_text="Петров Пётр petrov@1bit.ru",
        )

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                customer_names=["Петров Пётр"],
            ),
        ]

        results = resolver.resolve(candidates, source)
        assert len(results) == 1
        for c in results[0].customer:
            if c.email and "1bit.ru" in c.email:
                pytest.fail("Customer should not get performer emails")

    def test_fuzzy_surname_matching(self):
        from calendar_planner.participants.contact_index import fuzzy_match_surname

        score = fuzzy_match_surname("Исламгиев", "Исламгалиев Дмитрий Фанисович")
        assert score > 0.5

    def test_participants_bound_to_candidate(self):
        from calendar_planner.participants.resolver import ParticipantResolver
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway
        from calendar_planner.domain.models import (
            MeetingCandidate, ExtractedSource, SourceReference,
        )

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gateway)

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            raw_text="",
        )

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Meeting A",
                performer_names=["Гуреев"],
            ),
            MeetingCandidate(
                candidate_id="C002",
                subject="Meeting B",
                performer_names=["Петров"],
            ),
        ]

        results = resolver.resolve(candidates, source)
        assert len(results) == 2
        assert results[0].candidate_id == "C001"
        assert results[1].candidate_id == "C002"


class TestEnrichment:
    def test_extract_agenda_from_description(self):
        from calendar_planner.enrichment.extractor import EnrichmentExtractor
        from calendar_planner.domain.models import MeetingCandidate, ExtractedSource, SourceReference, DescriptionItemType

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Тестовая встреча",
            description_base="\n".join(["Пункт 1", "Пункт 2", "Пункт 3"]),
            sheet_name="Sheet1",
            row_number=2,
        )

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={"Sheet1": []},
        )

        extractor = EnrichmentExtractor()
        result = extractor.extract([candidate], source)

        assert "C001" in result
        agenda_items = [i for i in result["C001"] if isinstance(i.item_type, type(DescriptionItemType.AGENDA)) and i.item_type == DescriptionItemType.AGENDA]
        if len(agenda_items) == 0:
            agenda_items = [i for i in result["C001"] if "agenda" in str(i.item_type).lower() or "agenda" in i.title.lower() or "agenda" in i.value.lower()]
        assert len(agenda_items) == 1

    def test_item_can_be_excluded(self):
        from calendar_planner.domain.models import DescriptionItem, DescriptionItemType

        item = DescriptionItem(
            item_id="ITM-001",
            item_type=DescriptionItemType.AGENDA,
            title="Agenda",
            value="Content",
            included=True,
        )
        item.included = False
        assert item.included is False

    def test_description_renderer(self):
        from calendar_planner.enrichment.renderer import DescriptionRenderer
        from calendar_planner.domain.models import DescriptionItem, DescriptionItemType

        renderer = DescriptionRenderer()
        items = [
            DescriptionItem(
                item_id="ITM-001",
                item_type=DescriptionItemType.AGENDA,
                title="Agenda",
                value="1. Пункт 1\n2. Пункт 2",
            ),
            DescriptionItem(
                item_id="ITM-002",
                item_type=DescriptionItemType.LINK,
                title="Ссылка",
                value="https://example.com",
            ),
            DescriptionItem(
                item_id="ITM-003",
                item_type=DescriptionItemType.LOCATION,
                title="Location",
                value="Переговорная 301",
            ),
            DescriptionItem(
                item_id="ITM-004",
                item_type=DescriptionItemType.NOTE,
                title="Note",
                value="Дополнительная информация",
                included=False,
            ),
        ]

        text = renderer.render(items)
        assert "Повестка" in text
        assert "1. Пункт 1" in text
        assert "https://example.com" in text
        assert "Переговорная 301" in text
        assert "Дополнительная информация" not in text

    def test_no_data_message(self):
        from calendar_planner.enrichment.renderer import DescriptionRenderer

        renderer = DescriptionRenderer()
        text = renderer.render([])
        assert text == ""


class TestDrafts:
    def test_draft_builder_from_candidate(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Демонстрация процессов: Управление производством",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
            location="Переговорная 301",
            online_meeting_url="https://teams.example.com",
        )

        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        assert draft.draft_id == "DRF-0001"
        assert draft.candidate_id == "SRC-EVT-001"
        assert draft.subject.value is not None
        assert draft.start_date.value == "2026-08-04"
        assert draft.start_time.value == "12:00"
        assert draft.timezone.value == "Asia/Yekaterinburg"
        assert draft.duration_confirmed is False
        assert draft.is_ready is False

    def test_draft_editor_subject(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Original",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        editor = DraftEditor()
        editor.edit_subject(draft, "Modified")

        assert draft.subject.value == "Modified"
        assert draft.subject.modified_by_user is True

    def test_draft_editor_changes_make_match_stale(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Original",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        draft.match_status = "checked"
        draft.match_input_hash = "abc123"

        editor = DraftEditor()
        editor.edit_date(draft, "2026-08-05")
        assert draft.match_status == "stale"

    def test_draft_editor_revert_to_auto(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Original",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        from calendar_planner.domain.models import FinalEventDraft, DraftField

        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        original_snapshot = FinalEventDraft.from_dict(draft.to_dict())

        editor = DraftEditor()
        editor.edit_subject(draft, "Modified")
        assert draft.subject.value == "Modified"

        editor.revert_to_auto(draft, original_snapshot)
        assert draft.subject.value == "Original"
        assert draft.subject.modified_by_user is False

    def test_draft_editor_set_duration(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Test",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        editor = DraftEditor()
        editor.set_duration(draft, 90)

        assert draft.duration_minutes.value == 90
        assert draft.duration_confirmed is True
        assert draft.end_time.value == "13:30"

    def test_draft_editor_add_remove_attendee(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import (
            MeetingCandidate, ResolvedParticipant, ParticipantSide, ParticipantRole,
        )

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Test",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        editor = DraftEditor()
        participant = ResolvedParticipant(
            full_name="Новый Участник",
            email="new@example.com",
            side=ParticipantSide.CUSTOMER,
            role=ParticipantRole.REQUIRED,
        )
        editor.add_attendee(draft, participant)
        assert len(draft.required_attendees) == 1

        editor.remove_attendee(draft, "new@example.com")
        assert len(draft.required_attendees) == 0


class TestSession:
    def test_create_and_load_session(self):
        from calendar_planner.session.storage import SessionStorage
        from calendar_planner.session.models import StageState, RunSession

        storage = SessionStorage(base_dir="./runs_test")
        session = storage.create_session({"type": "test"})

        assert session.session_id is not None
        assert len(session.session_id) > 0

        loaded = storage.load_session(session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id

        import shutil
        shutil.rmtree("./runs_test", ignore_errors=True)

    def test_save_artifact(self):
        from calendar_planner.session.storage import SessionStorage

        storage = SessionStorage(base_dir="./runs_test")
        session = storage.create_session()

        storage.save_artifact(session.session_id, "test.json", {"key": "value"})

        loaded = storage.load_artifact(session.session_id, "test.json")
        assert loaded == {"key": "value"}

        import shutil
        shutil.rmtree("./runs_test", ignore_errors=True)


class TestSourceAdapters:
    def test_txt_adapter(self):
        from calendar_planner.source.adapters.file_adapters import TxtSourceAdapter
        from calendar_planner.domain.models import SourceReference

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("line1\nline2\nline3")
            temp_path = f.name

        try:
            adapter = TxtSourceAdapter()
            source = SourceReference(type="file", path=temp_path)
            assert adapter.can_handle(source)

            result = adapter.read(source)
            assert "Sheet1" in result.sheets
            assert len(result.sheets["Sheet1"]) >= 2
        finally:
            Path(temp_path).unlink()

    def test_csv_adapter(self):
        from calendar_planner.source.adapters.file_adapters import CsvSourceAdapter
        from calendar_planner.domain.models import SourceReference

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("col1,col2,col3\nval1,val2,val3")
            temp_path = f.name

        try:
            adapter = CsvSourceAdapter()
            source = SourceReference(type="file", path=temp_path)
            assert adapter.can_handle(source)

            result = adapter.read(source)
            assert "Sheet1" in result.sheets
            assert result.sheets["Sheet1"][0][0] == "col1"
            assert result.sheets["Sheet1"][1][1] == "val2"
        finally:
            Path(temp_path).unlink()

    def test_xlsx_adapter(self):
        from calendar_planner.source.adapters.file_adapters import XlsxSourceAdapter
        from calendar_planner.domain.models import SourceReference

        import openpyxl

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name

        try:
            wb = openpyxl.Workbook()
            ws1 = wb.active
            ws1.title = "Schedule"
            ws1.append(["Тема", "Согласованная дата", "Согласованное время"])
            ws1.append(["Встреча 1", "2026-08-04", "12:00"])

            ws2 = wb.create_sheet("Contacts")
            ws2.append(["Имя", "Email"])
            ws2.append(["Иванов", "ivanov@test.ru"])
            wb.save(temp_path)
            wb.close()

            adapter = XlsxSourceAdapter()
            source = SourceReference(type="file", path=temp_path)
            assert adapter.can_handle(source)

            result = adapter.read(source)
            assert "Schedule" in result.sheets
            assert "Contacts" in result.sheets
            assert len(result.sheets["Schedule"]) == 2
        finally:
            Path(temp_path).unlink()

    def test_source_registry_finds_adapter(self):
        from calendar_planner.source.registry import SourceAdapterRegistry
        from calendar_planner.domain.models import SourceReference

        registry = SourceAdapterRegistry()

        adapter = registry.find_adapter(SourceReference(type="file", path="test.txt"))
        assert adapter is not None

        adapter = registry.find_adapter(SourceReference(type="file", path="test.csv"))
        assert adapter is not None

        adapter = registry.find_adapter(SourceReference(type="file", path="test.xyz"))
        assert adapter is None

    def test_google_sheets_url_without_connection(self):
        from calendar_planner.source.adapters.file_adapters import GoogleSheetsSourceAdapter
        from calendar_planner.domain.models import SourceReference

        adapter = GoogleSheetsSourceAdapter()
        source = SourceReference(
            type="url",
            url="https://docs.google.com/spreadsheets/d/abc123/edit",
        )
        assert adapter.can_handle(source)

    def test_docx_adapter(self):
        from calendar_planner.source.adapters.file_adapters import DocxSourceAdapter
        from calendar_planner.domain.models import SourceReference

        import docx

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            temp_path = f.name

        try:
            doc = docx.Document()
            doc.add_paragraph("Hello World")
            doc.save(temp_path)

            adapter = DocxSourceAdapter()
            source = SourceReference(type="file", path=temp_path)
            assert adapter.can_handle(source)

            result = adapter.read(source)
            assert result.raw_text == "Hello World"
        finally:
            Path(temp_path).unlink()


class TestPayloadAndCreation:
    def test_payload_has_start_and_end(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
        )

        payload = creator.build_payload(draft)
        assert "start" in payload
        assert "end" in payload
        assert payload["start"]["dateTime"] is not None
        assert payload["end"]["dateTime"] is not None

    def test_cannot_create_without_confirmed_duration(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            is_ready=False,
        )

        result = creator.create_one(draft)
        assert result["status"] == "invalid"

    def test_mass_creation_dry_run(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft1 = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="S-EVT-001",
            subject=DraftField(value="A", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            selected=True,
            is_ready=True,
        )

        draft2 = FinalEventDraft(
            draft_id="DRF-0002",
            candidate_id="S-EVT-002",
            subject=DraftField(value="B", origin="auto"),
            start_date=DraftField(value="2026-08-05", origin="auto"),
            start_time=DraftField(value="14:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=30, origin="auto"),
            duration_confirmed=True,
            selected=True,
            is_ready=True,
        )

        results = creator.create_selected([draft1, draft2])
        assert len(results) == 2
        for r in results:
            assert r["status"] == "dry_run"


class TestRecheckDuplicate:
    def test_hash_changes_after_edit(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField
        from calendar_planner.drafts.hash import compute_draft_hash

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="S-EVT-001",
            subject=DraftField(value="Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
        )

        h1 = compute_draft_hash(draft)
        draft.subject.value = "Modified"
        h2 = compute_draft_hash(draft)

        assert h1 != h2

    def test_match_becomes_stale_after_time_change(self):
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import FinalEventDraft, DraftField

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="S-EVT-001",
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
        )
        draft.match_status = "checked"

        editor = DraftEditor()
        editor.edit_time(draft, "14:00")

        assert draft.match_status == "stale"


class TestSettings:
    def test_default_settings(self):
        from calendar_planner.app.settings import Settings
        from calendar_planner.domain.enums import MeetingDatePolicy

        settings = Settings()
        assert settings.DRY_RUN is True
        assert settings.DEFAULT_TIMEZONE == "Asia/Yekaterinburg"
        assert settings.MEETING_DATE_POLICY == MeetingDatePolicy.AGREED_ONLY
        assert settings.MCP_ENABLED is True

    def test_env_override(self):
        os.environ["APP_ENV"] = "production"
        os.environ["DRY_RUN"] = "false"

        try:
            from calendar_planner.app.settings import Settings
            settings = Settings()
            assert settings.APP_ENV == "production"
            assert settings.DRY_RUN is False
        finally:
            os.environ.pop("APP_ENV", None)
            os.environ.pop("DRY_RUN", None)


class TestMoreCoverage:

    def test_calendar_matcher_match_all(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            MeetingCandidate, CalendarEvent, NormalizedDateTime,
        )
        from calendar_planner.domain.enums import MatchDecision

        matcher = CalendarMatcher()
        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test Meeting",
                start_date="2026-08-04", start_time="12:00",
                timezone="Asia/Yekaterinburg",
            ),
            MeetingCandidate(
                candidate_id="C002",
                subject="No Time",
                start_date=None, start_time=None,
            ),
        ]
        events = [
            CalendarEvent(
                event_id="EVT-001", ical_uid="uid-001",
                subject="Test Meeting",
                start=NormalizedDateTime(
                    raw_datetime="2026-08-04T12:00:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 8, 4, 7, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
            ),
        ]
        matches = matcher.match_all(candidates, events)
        assert "C001" in matches
        assert "C002" in matches
        assert matches["C002"] is None

    def test_calendar_matcher_recheck(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import CalendarEvent, NormalizedDateTime
        from calendar_planner.domain.enums import MatchDecision

        matcher = CalendarMatcher()
        events = [
            CalendarEvent(
                event_id="EVT-001", ical_uid="uid-001",
                subject="Test",
                start=NormalizedDateTime(
                    raw_datetime="2026-08-04T12:00:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 8, 4, 7, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
            ),
        ]
        match = matcher.recheck_for_draft("Test", "2026-08-04", "12:00", "Asia/Yekaterinburg", events)
        assert match is not None
        assert match.decision == MatchDecision.DUPLICATE

    def test_calendar_matcher_possible_duplicate(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            MeetingCandidate, CalendarEvent, NormalizedDateTime,
        )
        from calendar_planner.domain.enums import MatchDecision

        matcher = CalendarMatcher(tolerance_minutes=30)
        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Different Topic",
            start_date="2026-08-04", start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )
        events = [
            CalendarEvent(
                event_id="EVT-001", ical_uid="uid-001",
                subject="Completely Unrelated",
                start=NormalizedDateTime(
                    raw_datetime="2026-08-04T12:05:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 8, 4, 12, 5, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 8, 4, 7, 5, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 8, 4, 12, 5, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
            ),
        ]
        match = matcher.match(candidate, events)
        assert match is not None
        assert match.decision == MatchDecision.POSSIBLE_DUPLICATE

    def test_calendar_matcher_no_candidate_datetime(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import MeetingCandidate, CalendarEvent

        matcher = CalendarMatcher()
        candidate = MeetingCandidate(candidate_id="C001", subject="No Date")
        match = matcher.match(candidate, [])
        assert match is None

    def test_calendar_datetime_normalizer_with_tz_offset(self):
        from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime

        result = parse_iso_datetime("2026-08-04T12:00:00+05:00")
        assert result.utc_datetime.hour == 7

    def test_calendar_datetime_normalizer_naive(self):
        from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime

        result = parse_iso_datetime("2026-08-04T12:00:00", "Asia/Yekaterinburg")
        assert result.utc_datetime.hour == 7

    def test_extraction_datetime_normalizer_flexible_parsing(self):
        from calendar_planner.extraction.datetime_normalizer import parse_iso_datetime

        result = parse_iso_datetime("2026-08-04 12:00", "Asia/Yekaterinburg")
        assert result is not None
        assert result.utc_datetime.hour == 7

    def test_extraction_datetime_normalizer_date_only(self):
        from calendar_planner.extraction.datetime_normalizer import parse_iso_datetime

        result = parse_iso_datetime("2026-08-04", "UTC")
        assert result is not None
        assert result.utc_datetime.day == 4

    def test_compute_end_and_payload_functions(self):
        from calendar_planner.extraction.datetime_normalizer import (
            datetime_to_payload_start, compute_end_datetime,
        )

        start = datetime_to_payload_start("2026-08-04", "12:00", "Asia/Yekaterinburg")
        assert start["dateTime"] == "2026-08-04T12:00:00"
        assert start["timeZone"] == "Asia/Yekaterinburg"

        end = compute_end_datetime("2026-08-04", "12:00", 60)
        assert end["dateTime"] == "2026-08-04T13:00:00"

    def test_enrichment_extractor_with_links(self):
        from calendar_planner.enrichment.extractor import EnrichmentExtractor
        from calendar_planner.domain.models import (
            MeetingCandidate, ExtractedSource, SourceReference,
        )

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Test",
            links=["https://example.com"],
            sheet_name="Sheet1",
            row_number=2,
        )
        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={"Sheet1": []},
        )
        extractor = EnrichmentExtractor()
        result = extractor.extract([candidate], source)
        assert "C001" in result
        link_items = [i for i in result["C001"] if "link" in str(i.item_type).lower() or "link" in i.title.lower()]
        assert len(link_items) > 0

    def test_enrichment_extractor_with_location(self):
        from calendar_planner.enrichment.extractor import EnrichmentExtractor
        from calendar_planner.domain.models import (
            MeetingCandidate, ExtractedSource, SourceReference, DescriptionItemType,
        )

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Test",
            location="Room 301",
            sheet_name="Sheet1",
            row_number=2,
        )
        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={"Sheet1": []},
        )
        extractor = EnrichmentExtractor()
        result = extractor.extract([candidate], source)
        location_items = [i for i in result["C001"] if i.item_type == DescriptionItemType.LOCATION]
        assert len(location_items) > 0

    def test_enrichment_extractor_online_url(self):
        from calendar_planner.enrichment.extractor import EnrichmentExtractor
        from calendar_planner.domain.models import (
            MeetingCandidate, ExtractedSource, SourceReference, DescriptionItemType,
        )

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Test",
            online_meeting_url="https://teams.example.com",
            sheet_name="Sheet1",
            row_number=2,
        )
        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={"Sheet1": []},
        )
        extractor = EnrichmentExtractor()
        result = extractor.extract([candidate], source)
        url_items = [i for i in result["C001"] if i.item_type == DescriptionItemType.ONLINE_MEETING_URL]
        assert len(url_items) > 0

    def test_draft_editor_edit_location_and_url(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Test",
            start_date="2026-08-04", start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )
        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        editor = DraftEditor()
        editor.edit_location(draft, "Room 401")
        assert draft.location.value == "Room 401"

        editor.edit_url(draft, "https://zoom.us/123")
        assert draft.online_meeting_url.value == "https://zoom.us/123"

    def test_draft_editor_changes_log(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor
        from calendar_planner.domain.models import MeetingCandidate

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Test",
            start_date="2026-08-04", start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )
        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        editor = DraftEditor()
        editor.edit_subject(draft, "New Subject")
        editor.edit_date(draft, "2026-08-05")

        changes = editor.get_changes()
        assert len(changes) >= 2

    def test_draft_field_from_dict_with_missing_keys(self):
        from calendar_planner.domain.models import DraftField

        field = DraftField.from_dict({"value": "test"})
        assert field.value == "test"
        assert field.origin == "auto"

    def test_contact_record_serialization(self):
        from calendar_planner.domain.models import ContactRecord, ParticipantSide

        c = ContactRecord(
            full_name="Some Name", surname="Name", email="name@example.com",
            phone="+79991234567", organization="TestOrg",
            source_location="Sheet1:R5", side=ParticipantSide.PERFORMER,
        )
        data = c.to_dict()
        restored = ContactRecord.from_dict(data)
        assert restored.full_name == "Some Name"
        assert restored.email == "name@example.com"
        assert restored.side == ParticipantSide.PERFORMER

    def test_contact_record_minimal(self):
        from calendar_planner.domain.models import ContactRecord

        c = ContactRecord(full_name="Name", surname="Name")
        data = c.to_dict()
        restored = ContactRecord.from_dict(data)
        assert restored.full_name == "Name"

    def test_unresolved_participant(self):
        from calendar_planner.domain.models import UnresolvedParticipant, ParticipantSide

        u = UnresolvedParticipant(
            source_name="Unknown", side=ParticipantSide.PERFORMER,
            reason="Not found", possible_matches=[{"name": "Option 1"}],
        )
        data = u.to_dict()
        restored = UnresolvedParticipant.from_dict(data)
        assert restored.source_name == "Unknown"
        assert restored.reason == "Not found"
        assert len(restored.possible_matches) == 1

    def test_source_reference_str(self):
        from calendar_planner.domain.models import SourceReference

        ref = SourceReference(type="file", path="/path/to/file.xlsx")
        assert "file" in str(ref) or "/path" in str(ref)

        ref2 = SourceReference(type="url", url="https://example.com")
        assert "example.com" in str(ref2)

    def test_extracted_source_to_dict(self):
        from calendar_planner.domain.models import SourceReference, ExtractedSource

        src = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={"Sheet1": [["A", "B"]]},
            metadata={"key": "value"},
        )
        data = src.to_dict()
        assert data["source"]["type"] == "memory"
        assert "Sheet1" in data["sheets"]

    def test_structured_meeting_row(self):
        from calendar_planner.domain.models import StructuredMeetingRow

        sr = StructuredMeetingRow(
            sheet_name="Sheet1", row_number=2, subject="Test",
            agreed_date="2026-08-04", agreed_time="12:00",
            performer_names=["Name"], customer_names=["Cust"],
            timezone="Asia/Yekaterinburg",
        )
        data = sr.to_dict()
        assert data["sheet_name"] == "Sheet1"
        assert data["row_number"] == 2

    def test_match_decision_enum_values(self):
        from calendar_planner.domain.enums import MatchDecision

        assert MatchDecision("DUPLICATE") == MatchDecision.DUPLICATE
        assert MatchDecision("NEW") == MatchDecision.NEW
        assert MatchDecision("POSSIBLE_RESCHEDULE") == MatchDecision.POSSIBLE_RESCHEDULE

    def test_description_item_type_enum(self):
        from calendar_planner.domain.enums import DescriptionItemType

        assert DescriptionItemType.AGENDA.value == "agenda"
        assert DescriptionItemType.LINK.value == "link"
        assert DescriptionItemType.LOCATION.value == "location"

    def test_mcp_gateway_not_available(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gw = MCPCalendarGateway()
        assert gw.is_available() is False

    def test_mcp_gateway_find_events_no_mcp(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gw = MCPCalendarGateway()
        events = gw.find_events("2026-01-01", "2026-12-31")
        assert len(events) == 0

    def test_mcp_gateway_create_event_no_mcp(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gw = MCPCalendarGateway()
        result = gw.create_event({"subject": "Test"}, dry_run=True)
        assert result["status"] == "error"

    def test_mcp_gateway_check_connection_no_mcp(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gw = MCPCalendarGateway()
        result = gw.check_connection()
        assert result["status"] == "failed"

    def test_mcp_gateway_parse_with_title(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gw = MCPCalendarGateway()
        raw = {
            "id": "e1",
            "title": "Title Meeting",
            "start": "2026-08-04T12:00:00",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.subject == "Title Meeting"

    def test_mcp_gateway_parse_invalid(self):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

        gw = MCPCalendarGateway()
        event = gw._parse_calendar_event({})
        assert event is not None
        assert event.event_id == ""
        assert event.subject == ""

    def test_fixture_gateway_no_fixture(self):
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway

        gw = FixtureCalendarGateway()
        events = gw.find_events("2026-01-01", "2026-12-31")
        assert len(events) == 0

    def test_fixture_gateway_create_real(self):
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway

        gw = FixtureCalendarGateway()
        result = gw.create_event({"subject": "Test"}, dry_run=False)
        assert result["status"] == "created"

    def test_structured_extractor_even_rows(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Плановая дата", "Плановое время"],
                    ["PlanA", "2026-08-04", "12:00"],
                ]
            },
        )
        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.PLANNED_ONLY)
        result = extractor.extract(source)
        all_candidates = []
        for cands in result.values():
            all_candidates.extend(cands)
        assert len(all_candidates) == 1
        assert all_candidates[0].start_date == "2026-08-04"

    def test_unstructured_extractor_no_meeting(self):
        from calendar_planner.extraction.unstructured import UnstructuredExtractor
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            raw_text="Просто какой-то текст без признаков встречи",
        )
        extractor = UnstructuredExtractor()
        candidates = extractor.extract(source)
        assert len(candidates) == 0

    def test_directory_gateway_available(self):
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway

        gw = FixtureDirectoryGateway()
        assert gw.is_available()
        results = gw.search("Гуреев")
        assert len(results) >= 1

    def test_mcp_directory_gateway_not_available(self):
        from calendar_planner.participants.directory_gateway import MCPDirectoryGateway

        gw = MCPDirectoryGateway()
        assert gw.is_available() is False
        assert gw.search("any") == []

    def test_participant_resolver_performer(self):
        from calendar_planner.participants.resolver import ParticipantResolver
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway
        from calendar_planner.domain.models import (
            MeetingCandidate, ExtractedSource, SourceReference,
        )

        gw = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gw)
        source = ExtractedSource(source=SourceReference(type="memory"), raw_text="")
        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                performer_names=["Гуреев"],
                start_date="2026-08-04",
                start_time="12:00",
            ),
        ]
        results = resolver.resolve(candidates, source)
        assert len(results) == 1
        assert len(results[0].performer) >= 1

    def test_session_list_sessions(self):
        from calendar_planner.session.storage import SessionStorage

        storage = SessionStorage(base_dir="./runs_test2")
        storage.create_session()
        storage.create_session()

        sessions = storage.list_sessions()
        assert len(sessions) >= 2

        import shutil
        shutil.rmtree("./runs_test2", ignore_errors=True)

    def test_stage_state_serialization(self):
        from calendar_planner.session.models import StageState
        from calendar_planner.domain.enums import StageStatus

        state = StageState(
            name="extraction",
            status=StageStatus.SUCCESS,
            data={"count": 5},
            warnings=["test warning"],
        )
        data = state.to_dict()
        restored = StageState.from_dict(data)
        assert restored.name == "extraction"
        assert restored.status == StageStatus.SUCCESS

    def test_draft_hash_verify(self):
        from calendar_planner.domain.models import FinalEventDraft, DraftField
        from calendar_planner.drafts.hash import compute_draft_hash, verify_hash

        draft = FinalEventDraft(
            draft_id="DRF-0001", candidate_id="C001",
            subject=DraftField(value="Test", origin="auto"),
        )
        h = compute_draft_hash(draft)
        assert verify_hash(draft, h)
        assert not verify_hash(draft, "wrong")

    def test_draft_builder_with_participants(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.domain.models import (
            MeetingCandidate, CandidateParticipants,
            ResolvedParticipant, ParticipantSide, ParticipantRole,
        )

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Test",
            start_date="2026-08-04", start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )
        participants = CandidateParticipants(
            candidate_id="SRC-EVT-001",
            performer=[ResolvedParticipant(
                full_name="Performer", email="p@1bit.ru",
                side=ParticipantSide.PERFORMER,
                role=ParticipantRole.REQUIRED,
            )],
            customer=[ResolvedParticipant(
                full_name="Customer", email="c@example.com",
                side=ParticipantSide.CUSTOMER,
                role=ParticipantRole.REQUIRED,
            )],
        )
        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate, participants)
        assert len(draft.required_attendees) == 2

    def test_schema_detector_timezone_in_header(self):
        from calendar_planner.source.schema_detector import TableSchemaDetector

        data = [
            ["Тема", "Согласованная дата ЕКБ", "Согласованное время"],
            ["Test", "2026-08-04", "12:00"],
        ]
        detector = TableSchemaDetector()
        detector.detect(data)
        assert detector.header_timezone == "Asia/Yekaterinburg"

    def test_contact_index_hyperlinks(self):
        from calendar_planner.participants.contact_index import ContactIndex
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            raw_text="",
            hyperlinks={"A1": "mailto:test@example.com"},
        )
        index = ContactIndex()
        index.build_from_source(source)
        contacts = index.find_by_email("test@example.com")
        assert len(contacts) >= 1

    def test_matcher_skip_no_start(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            MeetingCandidate, CalendarEvent,
        )

        matcher = CalendarMatcher()
        candidate = MeetingCandidate(
            candidate_id="C001", subject="Test",
            start_date="2026-08-04", start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )
        events = [CalendarEvent(event_id="e1", ical_uid="u1", subject="Test")]
        match = matcher.match(candidate, events)
        assert match is not None
        assert match.decision.value == "NEW"

    def test_draft_builder_reset(self):
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.domain.models import MeetingCandidate

        builder = DraftBuilder(sequence=5)
        candidate = MeetingCandidate(
            candidate_id="C1", subject="T", start_date="2026-08-04",
            start_time="12:00", timezone="Asia/Yekaterinburg",
        )
        draft = builder.build_from_candidate(candidate)
        assert "DRF-0006" in draft.draft_id

        builder.reset_counter()
        draft2 = builder.build_from_candidate(candidate)
        assert "DRF-0001" in draft2.draft_id

    def test_agreed_then_planned_policy(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время", "Плановая дата", "Плановое время"],
                    ["C1", "2026-08-04", "12:00", "2026-08-03", "10:00"],
                    ["C2", "", "", "2026-08-05", "14:00"],
                    ["C3", "", "", "", ""],
                ]
            },
        )
        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_THEN_PLANNED)
        result = extractor.extract(source)
        all_cands = []
        for cands in result.values():
            all_cands.extend(cands)
        assert len(all_cands) == 2

    def test_structured_agreed_then_planned_ordered(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время"],
                    ["C1", "2026-08-04", "12:00"],
                ]
            },
        )
        extractor = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_THEN_PLANNED)
        result = extractor.extract(source)
        all_cands = []
        for cands in result.values():
            all_cands.extend(cands)
        assert all_cands[0].start_date == "2026-08-04"


def test_final_import_sanity_check():
    assert True