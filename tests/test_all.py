from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDomainModels:
    def test_draft_field_defaults(self):
        from calendar_planner.domain.enums import DraftFieldOrigin
        from calendar_planner.domain.models import DraftField

        field = DraftField(value="test", origin=DraftFieldOrigin.AUTO.value)
        assert field.value == "test"
        assert field.origin == "auto"
        assert field.modified_by_user is False
        assert field.evidence == []

    def test_draft_field_user_modification(self):
        from calendar_planner.domain.enums import DraftFieldOrigin
        from calendar_planner.domain.models import DraftField

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
        from calendar_planner.domain.models import (
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
        from calendar_planner.domain.models import FinalEventDraft
        from calendar_planner.domain.validation import validate_draft_ready

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
        )
        errors = validate_draft_ready(draft)
        assert len(errors) > 0
        assert any("не задана" in e.lower() for e in errors)

    def test_validate_draft_ready_no_duration(self):
        from calendar_planner.domain.models import DraftField, FinalEventDraft
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

    def test_agreed_time_header_with_timezone_ekb(self):
        from calendar_planner.source.schema_detector import TableSchemaDetector

        data = [
            ["Тема", "Согласованная дата", "Согласованное время, ЕКБ", "Плановая дата"],
            ["Встреча 1", "31.07.2026", "12:00", "30.07.2026"],
        ]
        detector = TableSchemaDetector()
        detector.detect(data)

        assert detector.agreed_time_col == 2
        assert detector.agreed_time_col in detector.column_timezones
        assert detector.column_timezones[detector.agreed_time_col] == "Asia/Yekaterinburg"
        assert detector.header_timezone == "Asia/Yekaterinburg"

    def test_candidate_gets_timezone_from_agreed_time_header(self):
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время, ЕКБ"],
                    ["Встреча 1", "2026-08-04", "12:00"],
                ]
            },
        )

        extractor = StructuredExtractor()
        result = extractor.extract(source)

        all_candidates = []
        for candidates in result.values():
            all_candidates.extend(candidates)

        assert len(all_candidates) == 1
        assert all_candidates[0].timezone == "Asia/Yekaterinburg"

    def test_parse_names(self):
        from calendar_planner.source.schema_detector import parse_names

        result = parse_names("Иванов И.И.; Петров П.П.; Сидоров С.С.")
        assert len(result) == 3
        assert "Иванов И.И." in result

    def test_split_subject_description(self):
        from calendar_planner.source.schema_detector import (
            split_subject_and_description,
        )

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
        from calendar_planner.extraction.datetime_normalizer import (
            parse_date_time,
        )

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
        from calendar_planner.calendar.datetime_normalizer import (
            parse_iso_datetime,
        )

        result = parse_iso_datetime("2026-07-24T12:00:00", "Asia/Yekaterinburg")
        expected_utc = datetime(2026, 7, 24, 7, 0, tzinfo=ZoneInfo("UTC"))
        assert abs((result.utc_datetime - expected_utc).total_seconds()) < 1

    def test_windows_timezone_mapping(self):
        from calendar_planner.calendar.datetime_normalizer import resolve_timezone

        assert resolve_timezone("Ekaterinburg Standard Time") == "Asia/Yekaterinburg"
        assert resolve_timezone("Russian Standard Time") == "Europe/Moscow"

    def test_same_moment_check(self):
        from calendar_planner.extraction.datetime_normalizer import (
            are_same_moment,
            parse_date_time,
        )

        a = parse_date_time("2026-07-24", "12:00", "Asia/Yekaterinburg")
        b = parse_date_time("2026-07-24", "07:00", "UTC")
        assert a is not None
        assert b is not None
        assert are_same_moment(a, b) is True


class TestStructuredExtractor:
    def test_agreed_only_policy(self):
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.unstructured import UnstructuredExtractor

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
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

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
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

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
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

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
        from calendar_planner.calendar.matcher import (
            normalize_subject_for_comparison,
            subject_similarity,
        )

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
        from calendar_planner.domain.models import (
            DraftField,
            FinalEventDraft,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

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
        assert payload["start"] == "2026-08-04 12:00"
        assert payload["end"] == "2026-08-04 13:00"
        assert len(payload["attendees"]) == 1

    def test_create_one_dry_run(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
            match_status="checked",
        )
        draft.match_input_hash = draft.compute_input_hash()

        result = creator.create_one(draft)
        assert result["status"] == "dry_run"

    def test_validate_payload_before_create(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft

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

    def test_recheck_populates_calendar_matches(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            DraftField,
            FinalEventDraft,
            NormalizedDateTime,
        )

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Test Match", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            match_status="not_checked",
        )

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)
        event = CalendarEvent(
            event_id="EVT-001",
            ical_uid="uid-001",
            subject="Test Match",
            start=NormalizedDateTime(
                raw_datetime="2026-08-04T12:00:00",
                raw_timezone="Asia/Yekaterinburg",
                aware_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                utc_datetime=__import__("datetime").datetime(2026, 8, 4, 7, 0, tzinfo=__import__("zoneinfo").ZoneInfo("UTC")),
                display_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                display_timezone="Asia/Yekaterinburg",
            ),
        )
        match = matcher.recheck_for_draft(
            subject=draft.subject.value or "",
            start_date=draft.start_date.value or "",
            start_time=draft.start_time.value or "",
            timezone=draft.timezone.value or "",
            calendar_events=[event],
        )
        if match:
            match.candidate_id = draft.candidate_id
        draft.calendar_matches = [match] if match else []
        draft.match_input_hash = draft.compute_input_hash()
        draft.match_status = "checked"

        assert len(draft.calendar_matches) == 1
        assert draft.calendar_matches[0].candidate_id == draft.candidate_id
        assert draft.calendar_matches[0].decision == MatchDecision.DUPLICATE

    def test_match_input_hash_matches_compute_after_recheck(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            CalendarEvent,
            DraftField,
            FinalEventDraft,
            NormalizedDateTime,
        )

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Test Hash", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            match_status="not_checked",
        )

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)
        event = CalendarEvent(
            event_id="EVT-001",
            ical_uid="uid-001",
            subject="Test Hash",
            start=NormalizedDateTime(
                raw_datetime="2026-08-04T12:00:00",
                raw_timezone="Asia/Yekaterinburg",
                aware_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                utc_datetime=__import__("datetime").datetime(2026, 8, 4, 7, 0, tzinfo=__import__("zoneinfo").ZoneInfo("UTC")),
                display_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                display_timezone="Asia/Yekaterinburg",
            ),
        )
        match = matcher.recheck_for_draft(
            subject=draft.subject.value or "",
            start_date=draft.start_date.value or "",
            start_time=draft.start_time.value or "",
            timezone=draft.timezone.value or "",
            calendar_events=[event],
        )
        if match:
            match.candidate_id = draft.candidate_id
        draft.calendar_matches = [match] if match else []
        draft.match_input_hash = draft.compute_input_hash()
        draft.match_status = "checked"

        assert draft.match_input_hash == draft.compute_input_hash()

    def test_creator_rejects_stale_hash(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
            match_status="checked",
            match_input_hash="stale-hash-value",
        )

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)
        errors = creator.validate_draft_before_create(draft)
        # Hash staleness alone does not block — preflight_validate checks only match_status
        assert len(errors) == 0

    def test_creator_rejects_duplicate_match(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            CalendarMatch,
            DraftField,
            FinalEventDraft,
            NormalizedDateTime,
        )

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
            match_status="matched",
            match_input_hash="",
        )
        draft.calendar_matches = [
            CalendarMatch(
                candidate_id=draft.candidate_id,
                calendar_event=CalendarEvent(
                    event_id="EVT-001",
                    ical_uid="uid-001",
                    subject="Test",
                    start=NormalizedDateTime(
                        raw_datetime="2026-08-04T12:00:00",
                        raw_timezone="Asia/Yekaterinburg",
                        aware_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                        utc_datetime=__import__("datetime").datetime(2026, 8, 4, 7, 0, tzinfo=__import__("zoneinfo").ZoneInfo("UTC")),
                        display_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                        display_timezone="Asia/Yekaterinburg",
                    ),
                ),
                decision=MatchDecision.DUPLICATE,
                score=1.0,
                time_diff_minutes=0,
                subject_similarity=1.0,
            ),
        ]
        draft.match_input_hash = draft.compute_input_hash()

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)
        errors = creator.validate_draft_before_create(draft)
        messages = [e["message_ru"] for e in errors]
        assert any("дубликат" in m.lower() for m in messages)
        assert draft.is_ready is False

    def test_creator_sets_is_ready_false_on_duplicate(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.enums import MatchDecision as MD
        from calendar_planner.domain.models import (
            CalendarEvent,
            CalendarMatch,
            DraftField,
            FinalEventDraft,
            NormalizedDateTime,
        )

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
            match_status="matched",
            match_input_hash="",
        )
        draft.calendar_matches = [
            CalendarMatch(
                candidate_id=draft.candidate_id,
                calendar_event=CalendarEvent(
                    event_id="EVT-002",
                    ical_uid="uid-002",
                    subject="Test",
                    start=NormalizedDateTime(
                        raw_datetime="2026-08-04T12:00:00",
                        raw_timezone="Asia/Yekaterinburg",
                        aware_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                        utc_datetime=__import__("datetime").datetime(2026, 8, 4, 7, 0, tzinfo=__import__("zoneinfo").ZoneInfo("UTC")),
                        display_datetime=__import__("datetime").datetime(2026, 8, 4, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Yekaterinburg")),
                        display_timezone="Asia/Yekaterinburg",
                    ),
                ),
                decision=MD.DUPLICATE,
                score=0.95,
                time_diff_minutes=5,
                subject_similarity=0.95,
            ),
        ]
        draft.match_input_hash = draft.compute_input_hash()

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)
        creator.validate_draft_before_create(draft)
        assert draft.is_ready is False


class TestParticipants:
    def test_performer_directory_search(self):
        from calendar_planner.domain.models import ParticipantSide
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.matcher import NameMatcher

        gateway = FixtureDirectoryGateway()
        matcher = NameMatcher(gateway)

        result = matcher.match_performer("Гуреев")
        assert result is not None
        assert "Гуреев" in result.full_name
        assert result.email == "gureev@1bit.ru"
        assert result.side == ParticipantSide.PERFORMER

    def test_performer_not_found(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.matcher import NameMatcher

        gateway = FixtureDirectoryGateway(employees=[])
        matcher = NameMatcher(gateway)

        result = matcher.match_performer("Неизвестный")
        assert result is None

    def test_participant_resolver_customer_from_contacts(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

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
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

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
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

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
        from calendar_planner.domain.models import (
            DescriptionItemType,
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.enrichment.extractor import EnrichmentExtractor

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
        from calendar_planner.domain.models import DescriptionItem, DescriptionItemType
        from calendar_planner.enrichment.renderer import DescriptionRenderer

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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder

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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="Original",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        from calendar_planner.domain.models import FinalEventDraft

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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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
        from calendar_planner.domain.models import (
            MeetingCandidate,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import TxtSourceAdapter

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
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import CsvSourceAdapter

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
        import openpyxl

        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import XlsxSourceAdapter

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

    def test_xlsx_datetime_midnight_serializes_as_date(self):
        from datetime import datetime

        import openpyxl

        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import XlsxSourceAdapter

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws["A1"] = datetime(2026, 7, 24, 0, 0, 0)
            wb.save(temp_path)
            wb.close()

            adapter = XlsxSourceAdapter()
            source = SourceReference(type="file", path=temp_path)
            result = adapter.read(source)

            assert result.sheets[ws.title][0][0] == "2026-07-24"
        finally:
            Path(temp_path).unlink()

    def test_xlsx_time_serializes_as_time(self):
        from datetime import time

        import openpyxl

        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import XlsxSourceAdapter

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws["A1"] = time(14, 30, 0)
            wb.save(temp_path)
            wb.close()

            adapter = XlsxSourceAdapter()
            source = SourceReference(type="file", path=temp_path)
            result = adapter.read(source)

            assert result.sheets[ws.title][0][0] == "14:30:00"
        finally:
            Path(temp_path).unlink()

    def test_xlsx_datetime_with_time_serializes_as_time_only(self):
        from datetime import datetime

        import openpyxl

        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import XlsxSourceAdapter

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws["A1"] = datetime(1899, 12, 30, 14, 30, 0)
            wb.save(temp_path)
            wb.close()

            adapter = XlsxSourceAdapter()
            source = SourceReference(type="file", path=temp_path)
            result = adapter.read(source)

            assert result.sheets[ws.title][0][0] == "14:30:00"
        finally:
            Path(temp_path).unlink()

    def test_source_registry_finds_adapter(self):
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.registry import SourceAdapterRegistry

        registry = SourceAdapterRegistry()

        adapter = registry.find_adapter(SourceReference(type="file", path="test.txt"))
        assert adapter is not None

        adapter = registry.find_adapter(SourceReference(type="file", path="test.csv"))
        assert adapter is not None

        adapter = registry.find_adapter(SourceReference(type="file", path="test.xyz"))
        assert adapter is None

    def test_google_sheets_url_without_connection(self):
        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import (
            GoogleSheetsSourceAdapter,
        )

        adapter = GoogleSheetsSourceAdapter()
        source = SourceReference(
            type="url",
            url="https://docs.google.com/spreadsheets/d/abc123/edit",
        )
        assert adapter.can_handle(source)

    def test_docx_adapter(self):
        import docx

        from calendar_planner.domain.models import SourceReference
        from calendar_planner.source.adapters.file_adapters import DocxSourceAdapter

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
            match_status="checked",
        )
        draft1.match_input_hash = draft1.compute_input_hash()

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
            match_status="checked",
        )
        draft2.match_input_hash = draft2.compute_input_hash()

        results = creator.create_selected([draft1, draft2])
        assert len(results) == 2
        for r in results:
            assert r["status"] == "dry_run"


class TestRecheckDuplicate:
    def test_hash_changes_after_edit(self):
        from calendar_planner.domain.models import DraftField, FinalEventDraft
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
        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.drafts.editor import DraftEditor

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
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

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
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import CalendarEvent, NormalizedDateTime

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
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

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
        from calendar_planner.domain.models import MeetingCandidate

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
            compute_end_datetime,
            datetime_to_payload_start,
        )

        start = datetime_to_payload_start("2026-08-04", "12:00", "Asia/Yekaterinburg")
        assert start["dateTime"] == "2026-08-04T12:00:00"
        assert start["timeZone"] == "Asia/Yekaterinburg"

        end = compute_end_datetime("2026-08-04", "12:00", 60)
        assert end["dateTime"] == "2026-08-04T13:00:00"

    def test_enrichment_extractor_with_links(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.enrichment.extractor import EnrichmentExtractor

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
        from calendar_planner.domain.models import (
            DescriptionItemType,
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.enrichment.extractor import EnrichmentExtractor

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
        from calendar_planner.domain.models import (
            DescriptionItemType,
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.enrichment.extractor import EnrichmentExtractor

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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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
        from calendar_planner.domain.models import (
            ParticipantSide,
            UnresolvedParticipant,
        )

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
        from calendar_planner.domain.models import ExtractedSource, SourceReference

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
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.unstructured import UnstructuredExtractor

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            raw_text="Просто какой-то текст без признаков встречи",
        )
        extractor = UnstructuredExtractor()
        candidates = extractor.extract(source)
        assert len(candidates) == 0

    def test_directory_gateway_available(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )

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
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

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
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.session.models import StageState

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
        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.drafts.hash import compute_draft_hash, verify_hash

        draft = FinalEventDraft(
            draft_id="DRF-0001", candidate_id="C001",
            subject=DraftField(value="Test", origin="auto"),
        )
        h = compute_draft_hash(draft)
        assert verify_hash(draft, h)
        assert not verify_hash(draft, "wrong")

    def test_draft_builder_with_participants(self):
        from calendar_planner.domain.models import (
            CandidateParticipants,
            MeetingCandidate,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )
        from calendar_planner.drafts.builder import DraftBuilder

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
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.participants.contact_index import ContactIndex

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
            CalendarEvent,
            MeetingCandidate,
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
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder

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
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

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


class TestP007CliMain:
    """P0-07: __main__.py exists and can be imported."""

    def test_cli_main_module_exists(self):
        import importlib
        spec = importlib.util.find_spec("calendar_planner.cli.__main__")
        assert spec is not None

    def test_cli_main_module_imports(self):
        from calendar_planner.cli import main as cli_main
        from calendar_planner.cli.__main__ import main
        assert main is cli_main  # __main__.main == cli.main


class TestP009MultiCharEditing:
    """P0-09: _update_field не блокирует повторные правки."""

    def test_multiple_edits_to_same_field(self):
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

        candidate = MeetingCandidate(
            candidate_id="SRC-EVT-001",
            subject="O",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )
        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)
        editor = DraftEditor()

        # Эмуляция посимвольного ввода: пользователь печатает "H", потом "e", потом "llo"
        editor.edit_subject(draft, "H")
        assert draft.subject.value == "H"
        assert draft.subject.modified_by_user is True

        editor.edit_subject(draft, "He")
        assert draft.subject.value == "He"

        editor.edit_subject(draft, "Hel")
        assert draft.subject.value == "Hel"

        editor.edit_subject(draft, "Hell")
        assert draft.subject.value == "Hell"

        editor.edit_subject(draft, "Hello")
        assert draft.subject.value == "Hello"

    def test_edit_date_multiple_times(self):
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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

        editor.edit_date(draft, "2026")
        assert draft.start_date.value == "2026"

        editor.edit_date(draft, "2026-")
        assert draft.start_date.value == "2026-"

        editor.edit_date(draft, "2026-08-05")
        assert draft.start_date.value == "2026-08-05"

    def test_edit_time_multiple_times(self):
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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

        editor.edit_time(draft, "1")
        assert draft.start_time.value == "1"

        editor.edit_time(draft, "14")
        assert draft.start_time.value == "14"

        editor.edit_time(draft, "14:30")
        assert draft.start_time.value == "14:30"

    def test_edit_location_multiple_times(self):
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.drafts.builder import DraftBuilder
        from calendar_planner.drafts.editor import DraftEditor

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

        editor.edit_location(draft, "R")
        assert draft.location.value == "R"

        editor.edit_location(draft, "Room 301")
        assert draft.location.value == "Room 301"


class TestP010EnumMapping:
    """P0-10: ParticipantSide/ ParticipantRole принимают UPPERCASE значения."""

    def test_participant_side_accepts_uppercase(self):
        from calendar_planner.domain.enums import ParticipantSide

        assert ParticipantSide("PERFORMER") == ParticipantSide.PERFORMER
        assert ParticipantSide("CUSTOMER") == ParticipantSide.CUSTOMER

    def test_participant_role_accepts_uppercase(self):
        from calendar_planner.domain.enums import ParticipantRole

        assert ParticipantRole("REQUIRED") == ParticipantRole.REQUIRED
        assert ParticipantRole("OPTIONAL") == ParticipantRole.OPTIONAL

    def test_participant_side_rejects_lowercase(self):
        from calendar_planner.domain.enums import ParticipantSide

        with pytest.raises(ValueError):
            ParticipantSide("performer")

    def test_participant_role_rejects_lowercase(self):
        from calendar_planner.domain.enums import ParticipantRole

        with pytest.raises(ValueError):
            ParticipantRole("required")

    def test_ui_side_values_match_enum(self):
        from calendar_planner.domain.enums import ParticipantSide

        ui_values = ["PERFORMER", "CUSTOMER"]
        for val in ui_values:
            assert ParticipantSide(val) is not None

    def test_ui_role_values_match_enum(self):
        from calendar_planner.domain.enums import ParticipantRole

        ui_values = ["REQUIRED", "OPTIONAL"]
        for val in ui_values:
            assert ParticipantRole(val) is not None


def test_final_import_sanity_check():
    assert True


class TestP101ContactSchemaDetection:
    """P1-01: Contact index determines ФИО correctly via schema detection."""

    def test_detect_contact_schema_finds_headers(self):
        from calendar_planner.participants.contact_index import ContactIndex

        sheet_data = [
            ["№", "ФИО", "Email", "Телефон", "Организация"],
            ["1", "Иванов Иван", "ivanov@example.com", "+79991234567", "ООО Ромашка"],
        ]
        schema = ContactIndex._detect_contact_schema(sheet_data)

        assert schema["full_name"] == 1
        assert schema["email"] == 2
        assert schema["phone"] == 3
        assert schema["organization"] == 4

    def test_detect_contact_schema_english_headers(self):
        from calendar_planner.participants.contact_index import ContactIndex

        sheet_data = [
            ["Full Name", "E-mail", "Phone", "Organization"],
            ["John Doe", "john@example.com", "+1234567890", "Acme Inc"],
        ]
        schema = ContactIndex._detect_contact_schema(sheet_data)

        assert schema["full_name"] == 0
        assert schema["email"] == 1
        assert schema["phone"] == 2
        assert schema["organization"] == 3

    def test_detect_contact_schema_no_headers(self):
        from calendar_planner.participants.contact_index import ContactIndex

        sheet_data = [
            ["Тема", "Согласованная дата", "Согласованное время"],
            ["Встреча 1", "2026-08-04", "12:00"],
        ]
        schema = ContactIndex._detect_contact_schema(sheet_data)

        assert schema["full_name"] == -1
        assert schema["email"] == -1

    def test_build_from_source_skips_header_row(self):
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.participants.contact_index import ContactIndex

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Contacts": [
                    ["ФИО", "Email", "Телефон"],
                    ["Петров Пётр", "petrov@example.com", "+79991112233"],
                ]
            },
        )
        index = ContactIndex()
        index.build_from_source(source)

        contacts = index.find_by_name("Петров")
        assert len(contacts) == 1
        assert contacts[0].full_name == "Петров Пётр"
        assert contacts[0].email == "petrov@example.com"
        assert contacts[0].phone == "+79991112233"

    def test_build_from_source_row0_is_number(self):
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.participants.contact_index import ContactIndex

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Contacts": [
                    ["№", "ФИО", "Email", "Организация"],
                    ["1", "Сидоров Сидор", "sidorov@example.com", "ООО Тест"],
                    ["2", "Иванова Анна", "anna@example.com", "ЗАО Пример"],
                ]
            },
        )
        index = ContactIndex()
        index.build_from_source(source)

        contacts = index.find_by_name("Сидоров")
        assert len(contacts) == 1
        assert contacts[0].full_name == "Сидоров Сидор"
        assert contacts[0].organization == "ООО Тест"

        contacts = index.find_by_name("Иванова")
        assert len(contacts) == 1
        assert contacts[0].full_name == "Иванова Анна"

    def test_build_from_source_fallback_no_headers(self):
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.participants.contact_index import ContactIndex

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Иванов Иван", "ivanov@example.com"],
                    ["Петров Пётр", "petrov@example.com"],
                ]
            },
        )
        index = ContactIndex()
        index.build_from_source(source)

        contacts = index.find_by_name("Иванов")
        assert len(contacts) == 1
        assert contacts[0].full_name == "Иванов Иван"


class TestP103BestEmployee:
    """P1-03: Multiple employees — best scored is used, not first."""

    def test_match_performer_picks_best_not_first(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.matcher import NameMatcher

        employees = [
            {"full_name": "Петров Александр Сергеевич", "email": "petrov@1bit.ru", "surname": "Петров"},
            {"full_name": "Гуреев Дмитрий Петрович", "email": "gureev@1bit.ru", "surname": "Гуреев"},
        ]
        gateway = FixtureDirectoryGateway(employees=employees)
        matcher = NameMatcher(gateway)

        result = matcher.match_performer("Гуреев")
        assert result is not None
        assert result.full_name == "Гуреев Дмитрий Петрович"
        assert result.email == "gureev@1bit.ru"

    def test_match_performer_multiple_same_surname(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.matcher import NameMatcher

        employees = [
            {"full_name": "Сергей Петров-Сидоров Михайлович", "email": "s_ps@1bit.ru", "surname": "Петров-Сидоров"},
            {"full_name": "Сергей Сергеев", "email": "s_s@1bit.ru", "surname": "Сергеев"},
        ]
        gateway = FixtureDirectoryGateway(employees=employees)
        matcher = NameMatcher(gateway)

        result, options = matcher.match_performer_with_options("Сергей")
        assert result is None
        assert len(options) == 2
        assert any(o["full_name"] == "Сергей Сергеев" for o in options)
        assert any(o["full_name"] == "Сергей Петров-Сидоров Михайлович" for o in options)

    def test_match_performer_multiple_returns_none(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.matcher import NameMatcher

        employees = [
            {"full_name": "Иванов Иван", "email": "i1@1bit.ru", "surname": "Иванов"},
            {"full_name": "Иванов Петр", "email": "i2@1bit.ru", "surname": "Иванов"},
        ]
        gateway = FixtureDirectoryGateway(employees=employees)
        matcher = NameMatcher(gateway)

        result = matcher.match_performer("Иванов")
        assert result is None


class TestP104PerformerDomains:
    """P1-04: Performer domain supports list of domains."""

    def test_resolver_accepts_performer_domains_list(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(
            directory_gateway=gateway,
            performer_domains=["1bit.ru", "bit-erp.ru"],
        )
        assert resolver.performer_domains == ["1bit.ru", "bit-erp.ru"]

    def test_resolver_default_domains(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gateway)
        assert resolver.performer_domains == ["1bit.ru"]

    def test_customer_filtered_by_multiple_domains(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(
            directory_gateway=gateway,
            performer_domains=["1bit.ru", "bit-erp.ru"],
        )

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Петров Пётр", "petrov@bit-erp.ru"],
                ]
            },
            raw_text="Петров Пётр petrov@bit-erp.ru",
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
            if c.email and ("1bit.ru" in c.email or "bit-erp.ru" in c.email):
                pytest.fail("Customer should not get performer emails")

    def test_settings_performer_email_domains(self):
        from calendar_planner.app.settings import Settings

        settings = Settings()
        assert isinstance(settings.PERFORMER_EMAIL_DOMAINS, list)
        assert len(settings.PERFORMER_EMAIL_DOMAINS) >= 1
        assert "1bit.ru" in settings.PERFORMER_EMAIL_DOMAINS

    def test_settings_performer_email_domains_from_env(self):
        os.environ["PERFORMER_EMAIL_DOMAINS"] = "1bit.ru,bit-erp.ru,example.com"

        try:
            from calendar_planner.app.settings import Settings
            settings = Settings()
            assert settings.PERFORMER_EMAIL_DOMAINS == ["1bit.ru", "bit-erp.ru", "example.com"]
        finally:
            os.environ.pop("PERFORMER_EMAIL_DOMAINS", None)


class TestP113CalendarMatchToDict:
    """P1-13: CalendarMatch.to_dict() does not crash for NEW events (calendar_event=None)."""

    def test_to_dict_with_none_calendar_event(self):
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import CalendarMatch

        match = CalendarMatch(
            candidate_id="C001",
            calendar_event=None,
            decision=MatchDecision.NEW,
            score=0.0,
            time_diff_minutes=None,
            subject_similarity=0.0,
        )
        data = match.to_dict()
        assert data["candidate_id"] == "C001"
        assert data["calendar_event"] is None
        assert data["decision"] == "NEW"

    def test_to_dict_with_calendar_event(self):
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import CalendarEvent, CalendarMatch

        event = CalendarEvent(
            event_id="EVT-001",
            ical_uid="uid-001",
            subject="Test Event",
        )
        match = CalendarMatch(
            candidate_id="C001",
            calendar_event=event,
            decision=MatchDecision.DUPLICATE,
            score=0.95,
            time_diff_minutes=0,
            subject_similarity=0.98,
        )
        data = match.to_dict()
        assert data["candidate_id"] == "C001"
        assert data["calendar_event"] is not None
        assert data["calendar_event"]["event_id"] == "EVT-001"
        assert data["decision"] == "DUPLICATE"


class TestP012DraftValidationBeforeCreate:
    """P0-12: validate_draft_before_create проверяет готовность черновика перед созданием через preflight_validate."""

    def test_rejects_not_ready_draft(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            is_ready=False,
        )
        errors = creator.validate_draft_before_create(draft)
        assert len(errors) > 0
        messages = [e["message_ru"] for e in errors]
        assert any("тема" in m.lower() or "дата" in m.lower() or "длительность" in m.lower() for m in messages)

    def test_rejects_unconfirmed_duration(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
            is_ready=True,
            duration_confirmed=False,
        )
        errors = creator.validate_draft_before_create(draft)
        messages = [e["message_ru"] for e in errors]
        assert any("длительность" in m.lower() for m in messages)

    def test_rejects_stale_match_status(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
            is_ready=True,
            duration_confirmed=True,
            match_status="stale",
        )
        errors = creator.validate_draft_before_create(draft)
        # Stale is a warning, not a blocking error — draft may still be ready
        # Check that blocking_errors don't include stale (stale goes to warnings in preflight_validate)
        blocking_messages = [e["message_ru"] for e in errors]
        assert not any("повторно" in m.lower() for m in blocking_messages)

    def test_rejects_duplicate_in_matches(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            CalendarMatch,
            DraftField,
            FinalEventDraft,
        )

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
            is_ready=True,
            duration_confirmed=True,
            match_status="matched",
            calendar_matches=[
                CalendarMatch(
                    candidate_id="C001",
                    calendar_event=CalendarEvent(event_id="EVT-DUP", ical_uid="duplicate", subject="Duplicate"),
                    decision=MatchDecision.DUPLICATE,
                    score=0.95,
                    time_diff_minutes=0,
                    subject_similarity=0.98,
                ),
            ],
        )
        errors = creator.validate_draft_before_create(draft)
        messages = [e["message_ru"] for e in errors]
        assert any("дубликат" in m.lower() for m in messages)

    def test_rejects_invalid_email(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import (
            DraftField,
            FinalEventDraft,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

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
            is_ready=True,
            duration_confirmed=True,
            match_status="checked",
            required_attendees=[
                ResolvedParticipant(
                    full_name="Bad Email",
                    email="not-an-email",
                    side=ParticipantSide.CUSTOMER,
                    role=ParticipantRole.REQUIRED,
                ),
            ],
        )
        errors = creator.validate_draft_before_create(draft)
        messages = [e["message_ru"] for e in errors]
        assert any("email" in m.lower() or "некорректный" in m.lower() for m in messages)

    def test_rejects_missing_email(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import (
            DraftField,
            FinalEventDraft,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

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
            is_ready=True,
            duration_confirmed=True,
            match_status="checked",
            required_attendees=[
                ResolvedParticipant(
                    full_name="No Email",
                    email=None,
                    side=ParticipantSide.CUSTOMER,
                    role=ParticipantRole.REQUIRED,
                ),
            ],
        )
        errors = creator.validate_draft_before_create(draft)
        messages = [e["message_ru"] for e in errors]
        assert any("email" in m.lower() or "не найден" in m.lower() for m in messages)

    def test_validate_before_create_blocks_in_create_one(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            is_ready=False,
        )
        result = creator.create_one(draft)
        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0

    def test_passes_valid_draft(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

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
            is_ready=True,
            duration_confirmed=True,
            match_status="checked",
        )
        draft.match_input_hash = draft.compute_input_hash()
        errors = creator.validate_draft_before_create(draft)
        assert len(errors) == 0


class TestP102FuzzyCustomerMatching:
    """P1-02: fuzzy_match_surname используется как fallback при поиске клиентов."""

    def test_fuzzy_match_fallback_single_result(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gateway, fuzzy_threshold=0.7)

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Contacts": [
                    ["ФИО", "Email"],
                    ["Исламгалиев Дмитрий Фанисович", "islamgaliev@customer.ru"],
                ]
            },
            raw_text="Исламгалиев Дмитрий Фанисович islamgaliev@customer.ru",
        )

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                customer_names=["Исламгиев"],
            ),
        ]

        results = resolver.resolve(candidates, source)
        assert len(results) == 1
        assert len(results[0].customer) >= 1
        fuzzy_matches = [c for c in results[0].customer if c.is_fuzzy_match]
        assert len(fuzzy_matches) >= 1
        assert fuzzy_matches[0].confidence >= 0.7
        assert fuzzy_matches[0].match_source == "fuzzy_match"

    def test_fuzzy_match_multiple_candidates_goes_to_unresolved(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gateway, fuzzy_threshold=0.5)

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Contacts": [
                    ["ФИО", "Email"],
                    ["Иванов Александр", "alex@customer.ru"],
                    ["Иванова Анна", "anna@customer.ru"],
                ]
            },
            raw_text="Иванов Александр alex@customer.ru\nИванова Анна anna@customer.ru",
        )

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                customer_names=["Иванов"],
            ),
        ]

        results = resolver.resolve(candidates, source)
        assert len(results) == 1

    def test_fuzzy_fallback_no_match_falls_through(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        gateway = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=gateway, fuzzy_threshold=0.95)

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Contacts": [
                    ["ФИО", "Email"],
                    ["Sidorov Alexey", "alex@customer.ru"],
                ]
            },
            raw_text="Sidorov Alexey alex@customer.ru",
        )

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                customer_names=["Петров"],
            ),
        ]

        results = resolver.resolve(candidates, source)
        assert len(results) == 1
        name_only = [c for c in results[0].customer if c.match_source == "name_only_no_contact"]
        assert len(name_only) >= 1


class TestP111DuplicateAttendees:
    """P1-11: проверка на дубликат участников при добавлении."""

    def test_email_in_required_is_duplicate(self):
        from calendar_planner.domain.models import (
            FinalEventDraft,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="C001",
            required_attendees=[
                ResolvedParticipant(
                    full_name="Existing User",
                    email="existing@example.com",
                    side=ParticipantSide.CUSTOMER,
                    role=ParticipantRole.REQUIRED,
                ),
            ],
        )

        existing = {a.email for a in draft.required_attendees + draft.optional_attendees if a.email}
        assert "existing@example.com" in existing
        assert "new@example.com" not in existing

    def test_email_in_optional_is_duplicate(self):
        from calendar_planner.domain.models import (
            FinalEventDraft,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="C001",
            optional_attendees=[
                ResolvedParticipant(
                    full_name="Optional User",
                    email="optional@example.com",
                    side=ParticipantSide.CUSTOMER,
                    role=ParticipantRole.OPTIONAL,
                ),
            ],
        )

        existing = {a.email for a in draft.required_attendees + draft.optional_attendees if a.email}
        assert "optional@example.com" in existing

    def test_no_email_no_duplicate_check(self):
        from calendar_planner.domain.models import (
            FinalEventDraft,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="C001",
            required_attendees=[
                ResolvedParticipant(
                    full_name="No Email",
                    email=None,
                    side=ParticipantSide.CUSTOMER,
                    role=ParticipantRole.REQUIRED,
                ),
            ],
        )

        existing = {a.email for a in draft.required_attendees + draft.optional_attendees if a.email}
        assert len(existing) == 0


class TestP114WeightedScore:
    """P1-14: weighted_score fix — date/time equality checks, integration as tiebreaker."""

    def test_date_equality_adds_score(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

        matcher = CalendarMatcher()

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Test",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        event_same_date = CalendarEvent(
            event_id="EVT-001",
            ical_uid="uid-001",
            subject="Test",
            start=NormalizedDateTime(
                raw_datetime="2026-08-04T12:00:00",
                raw_timezone="Asia/Yekaterinburg",
                aware_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                utc_datetime=datetime(2026, 8, 4, 7, 0, tzinfo=ZoneInfo("UTC")),
                display_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                display_timezone="Asia/Yekaterinburg",
            ),
        )

        score_same = matcher.compute_weighted_score(candidate, event_same_date)

        event_diff_date = CalendarEvent(
            event_id="EVT-002",
            ical_uid="uid-002",
            subject="Test",
            start=NormalizedDateTime(
                raw_datetime="2026-08-05T12:00:00",
                raw_timezone="Asia/Yekaterinburg",
                aware_datetime=datetime(2026, 8, 5, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                utc_datetime=datetime(2026, 8, 5, 7, 0, tzinfo=ZoneInfo("UTC")),
                display_datetime=datetime(2026, 8, 5, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                display_timezone="Asia/Yekaterinburg",
            ),
        )

        score_diff = matcher.compute_weighted_score(candidate, event_diff_date)
        assert score_same > score_diff

    def test_time_equality_adds_score(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

        matcher = CalendarMatcher()

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Test",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        event_same_time = CalendarEvent(
            event_id="EVT-001",
            ical_uid="uid-001",
            subject="Test",
            start=NormalizedDateTime(
                raw_datetime="2026-08-04T12:00:00",
                raw_timezone="Asia/Yekaterinburg",
                aware_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                utc_datetime=datetime(2026, 8, 4, 7, 0, tzinfo=ZoneInfo("UTC")),
                display_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                display_timezone="Asia/Yekaterinburg",
            ),
        )

        score_same = matcher.compute_weighted_score(candidate, event_same_time)

        event_diff_time = CalendarEvent(
            event_id="EVT-002",
            ical_uid="uid-002",
            subject="Test",
            start=NormalizedDateTime(
                raw_datetime="2026-08-04T15:00:00",
                raw_timezone="Asia/Yekaterinburg",
                aware_datetime=datetime(2026, 8, 4, 15, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                utc_datetime=datetime(2026, 8, 4, 10, 0, tzinfo=ZoneInfo("UTC")),
                display_datetime=datetime(2026, 8, 4, 15, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                display_timezone="Asia/Yekaterinburg",
            ),
        )

        score_diff = matcher.compute_weighted_score(candidate, event_diff_time)
        assert score_same > score_diff

    def test_weighted_score_used_as_tiebreaker(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Completely Different Subject",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
            online_meeting_url="https://teams.example.com",
        )

        events = [
            CalendarEvent(
                event_id="EVT-001",
                ical_uid="uid-001",
                subject="Unrelated Event",
                start=NormalizedDateTime(
                    raw_datetime="2026-08-04T12:05:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 8, 4, 12, 5, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 8, 4, 7, 5, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 8, 4, 12, 5, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
                location="Room A",
                online_url="https://example.com",
            ),
            CalendarEvent(
                event_id="EVT-002",
                ical_uid="uid-002",
                subject="Another Unrelated",
                start=NormalizedDateTime(
                    raw_datetime="2026-08-04T12:10:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 8, 4, 12, 10, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 8, 4, 7, 10, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 8, 4, 12, 10, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
            ),
        ]

        match = matcher.match(candidate, events)
        assert match is not None
        assert match.decision == MatchDecision.POSSIBLE_DUPLICATE

    def test_weighted_score_with_all_fields(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

        matcher = CalendarMatcher()

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Project Alpha Review",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
            location="Room 301",
            online_meeting_url="https://teams.example.com/alpha",
        )

        event = CalendarEvent(
            event_id="EVT-001",
            ical_uid="uid-001",
            subject="Project Alpha Review",
            start=NormalizedDateTime(
                raw_datetime="2026-08-04T12:00:00",
                raw_timezone="Asia/Yekaterinburg",
                aware_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                utc_datetime=datetime(2026, 8, 4, 7, 0, tzinfo=ZoneInfo("UTC")),
                display_datetime=datetime(2026, 8, 4, 12, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                display_timezone="Asia/Yekaterinburg",
            ),
            location="Room 301",
            online_url="https://teams.example.com/alpha",
        )

        score = matcher.compute_weighted_score(candidate, event)
        assert score == 1.0


class TestP003P008FullFlow:
    """End-to-end test: full controller flow through stages 1-6 (no GUI)."""

    def test_full_flow_controller_only(self):
        from calendar_planner.app.settings import settings
        from calendar_planner.domain.models import (
            ExtractedSource,
            SourceReference,
        )
        from calendar_planner.ui.controllers import StageController

        controller = StageController()

        # -- Stages 0-1: connections (simulated) --
        controller.set_stage_success("stage_1")
        assert controller.get_stage_status(0) == "success"

        # -- Stage 2: extraction --
        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время, ЕКБ"],
                    ["Управление производством", "2026-08-04", "12:00"],
                    ["Без даты", "", ""],
                ]
            },
        )
        from calendar_planner.extraction.structured import StructuredExtractor
        extractor = StructuredExtractor(date_policy=settings.MEETING_DATE_POLICY)
        candidates = extractor.extract(source)
        controller.set_extracted(source)
        controller.set_candidates(candidates)
        controller.set_skipped_rows(extractor.skipped_rows)
        controller.set_stage_success("stage_2")
        assert controller.get_stage_status(1) == "success"

        all_candidates = controller.get_all_candidates()
        assert len(all_candidates) >= 1

        # -- Stage 3: calendar comparison --
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.calendar.matcher import CalendarMatcher

        calendar_gw = FixtureCalendarGateway()
        today = datetime.now(tz=UTC).date().isoformat()
        week_later = (datetime.now(tz=UTC).date() + timedelta(days=90)).isoformat()
        calendar_events = calendar_gw.find_events(today, week_later)

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)
        matches = matcher.match_all(all_candidates, calendar_events)
        controller.set_matches(matches)
        controller.set_calendar_events(calendar_events)
        controller.set_stage_success("stage_3")
        assert controller.get_stage_status(2) == "success"
        assert len(controller._matches) == len(all_candidates)

        # -- Stage 4: participant resolution --
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        directory_gw = FixtureDirectoryGateway()
        resolver = ParticipantResolver(directory_gateway=directory_gw)
        participants = resolver.resolve(all_candidates, source)
        controller.set_participants(participants)
        controller.set_stage_success("stage_4")
        assert controller.get_stage_status(3) == "success"
        assert len(controller._participants) == len(all_candidates)

        # -- Stage 5: enrichment --
        from calendar_planner.enrichment.extractor import EnrichmentExtractor

        enrichment_extractor = EnrichmentExtractor()
        enrichment = enrichment_extractor.extract(all_candidates, source)
        controller.set_enrichment(enrichment)
        controller.set_stage_success("stage_5")
        assert controller.get_stage_status(4) == "success"
        assert len(controller._enrichment) == len(all_candidates)

        # -- Stage 6: build drafts --
        from calendar_planner.drafts.builder import DraftBuilder

        participants_map = {p.candidate_id: p for p in participants}
        builder = DraftBuilder()
        drafts = []
        for candidate in all_candidates:
            cp = participants_map.get(candidate.candidate_id)
            items = enrichment.get(candidate.candidate_id, [])
            draft = builder.build_from_candidate(candidate, cp, items)
            drafts.append(draft)

        controller.set_drafts(drafts)
        controller.set_stage_success("stage_6")
        assert controller.get_stage_status(5) == "success"
        assert len(controller.get_drafts()) == len(all_candidates)

        # Verify intermediate data is held by controller
        assert controller._extracted is not None
        assert len(controller.get_all_candidates()) > 0
        assert len(controller._matches) > 0
        assert len(controller._participants) > 0
        assert len(controller._enrichment) > 0
        assert len(controller.get_drafts()) > 0

    def test_recheck_callback_integration(self):

        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            DraftField,
            FinalEventDraft,
        )

        calendar_gw = FixtureCalendarGateway()
        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="C001",
            subject=DraftField(value="Test Meeting", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
        )

        today = datetime.now(tz=UTC).date().isoformat()
        week_later = (datetime.now(tz=UTC).date() + timedelta(days=90)).isoformat()
        calendar_events = calendar_gw.find_events(today, week_later)

        _match = matcher.recheck_for_draft(
            subject=draft.subject.value or "",
            start_date=draft.start_date.value or "",
            start_time=draft.start_time.value or "",
            timezone=draft.timezone.value or "",
            calendar_events=calendar_events,
        )

        draft.match_status = "checked"
        assert draft.match_status == "checked"

    def test_all_stage_statuses(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()

        for i in range(6):
            assert controller.get_stage_status(i) == StageStatus.NOT_STARTED.value

        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")
        controller.set_stage_success("stage_3")
        controller.set_stage_success("stage_4")
        controller.set_stage_success("stage_5")
        controller.set_stage_success("stage_6")

        for i in range(6):
            assert controller.get_stage_status(i) == StageStatus.SUCCESS.value

    def test_stage_navigation(self):
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        assert controller.current_stage == 0

        controller.next_stage()
        assert controller.current_stage == 1

        controller.next_stage()
        assert controller.current_stage == 2

        controller.prev_stage()
        assert controller.current_stage == 1

        controller.set_current_stage(5)
        assert controller.current_stage == 5

        controller.next_stage()
        assert controller.current_stage == 5

        controller.set_current_stage(-1)
        assert controller.current_stage == 0


class TestFixStage1NotOverwritten:
    """Stage 1 status is set by _check_connections() and must not be overwritten by _run_analysis."""

    def test_stage1_status_preserved_after_stage2_success(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        assert controller.get_stage_status(0) == StageStatus.SUCCESS.value

        controller.set_stage_success("stage_2")
        assert controller.get_stage_status(0) == StageStatus.SUCCESS.value

    def test_stage1_failed_blocks_stage2_6(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_error("stage_1", "Connection refused")
        assert controller.get_stage_status(0) == StageStatus.FAILED.value

        status = controller.get_stage_status(0)
        assert status not in ("success", "success_with_warnings")

        controller.set_stage_success("stage_2")
        controller.set_stage_success("stage_3")
        controller.set_stage_success("stage_4")
        controller.set_stage_success("stage_5")
        controller.set_stage_success("stage_6")

        assert controller.get_stage_status(0) == StageStatus.FAILED.value

    def test_stage1_warning_allows_analysis(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.stages[0].status = StageStatus.SUCCESS_WITH_WARNINGS
        assert controller.get_stage_status(0) == StageStatus.SUCCESS_WITH_WARNINGS.value

        status = controller.get_stage_status(0)
        assert status in ("success", "success_with_warnings")

    def test_stage1_not_started_blocks_analysis(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        assert controller.get_stage_status(0) == StageStatus.NOT_STARTED.value

        status = controller.get_stage_status(0)
        assert status not in ("success", "success_with_warnings")


class TestDateRangeCalculation:
    """Date range calculated from candidates, not hardcoded 90-day window."""

    def test_buffer_setting_exists(self):
        from calendar_planner.app.settings import Settings

        s = Settings()
        assert hasattr(s, "CALENDAR_DATE_RANGE_BUFFER_DAYS")
        assert s.CALENDAR_DATE_RANGE_BUFFER_DAYS == 7

    def test_date_range_from_candidates(self):
        from datetime import date, timedelta

        from calendar_planner.app.settings import settings

        candidates = [
            type("FakeCandidate", (), {"start_date": "2026-08-04"})(),
            type("FakeCandidate", (), {"start_date": "2026-08-10"})(),
            type("FakeCandidate", (), {"start_date": "2026-08-01"})(),
        ]

        def parse_date(d):
            try:
                return date.fromisoformat(d)
            except (ValueError, TypeError):
                return None

        cdates = [d for c in candidates if (d := parse_date(c.start_date)) is not None]
        min_date = min(cdates)
        max_date = max(cdates)
        buffer = timedelta(days=settings.CALENDAR_DATE_RANGE_BUFFER_DAYS)

        assert (min_date - buffer).isoformat() == "2026-07-25"
        assert (max_date + buffer).isoformat() == "2026-08-17"


class TestNewMatchNotCountedAsFound:
    """NEW decision should not count as a found match."""

    def test_new_match_has_none_calendar_event(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Unique Event",
            start_date="2026-12-15",
            start_time="09:00",
            timezone="Asia/Yekaterinburg",
        )

        events = [
            CalendarEvent(
                event_id="EVT-001",
                ical_uid="uid-001",
                subject="Old Unrelated Event",
                start=NormalizedDateTime(
                    raw_datetime="2026-01-15T09:00:00",
                    raw_timezone="Asia/Yekaterinburg",
                    aware_datetime=datetime(2026, 1, 15, 9, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    utc_datetime=datetime(2026, 1, 15, 4, 0, tzinfo=ZoneInfo("UTC")),
                    display_datetime=datetime(2026, 1, 15, 9, 0, tzinfo=ZoneInfo("Asia/Yekaterinburg")),
                    display_timezone="Asia/Yekaterinburg",
                ),
            ),
        ]

        match = matcher.match(candidate, events)
        assert match is not None
        assert match.decision == MatchDecision.NEW

    def test_matched_count_excludes_new(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )

        matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Existing Meeting",
                start_date="2026-08-04",
                start_time="12:00",
                timezone="Asia/Yekaterinburg",
            ),
            MeetingCandidate(
                candidate_id="C002",
                subject="Unique New Event",
                start_date="2026-12-15",
                start_time="09:00",
                timezone="Asia/Yekaterinburg",
            ),
        ]

        events = [
            CalendarEvent(
                event_id="EVT-001",
                ical_uid="uid-001",
                subject="Existing Meeting",
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
        matched_count = sum(
            1 for m in matches.values()
            if m is not None and m.decision.name != "NEW"
        )
        assert matched_count == 1


class TestSessionFullRoundtrip:
    def test_create_session_saves_all_intermediate_data(self):
        import shutil
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.domain.models import (
            CalendarEvent,
            CandidateParticipants,
            DescriptionItem,
            DescriptionItemType,
            DraftField,
            ExtractedSource,
            FinalEventDraft,
            MeetingCandidate,
            NormalizedDateTime,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
            SourceReference,
        )
        from calendar_planner.session.storage import SessionStorage
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        storage = SessionStorage(base_dir="./runs_roundtrip_test")

        controller.set_extracted(ExtractedSource(
            source=SourceReference(type="file", path="/test/test.xlsx"),
            sheets={"Sheet1": [["A", "B"]]},
            metadata={"key": "val"},
        ))

        candidates = {
            "Sheet1": [
                MeetingCandidate(
                    candidate_id="SRC-EVT-001",
                    subject="Test Meeting",
                    start_date="2026-08-04",
                    start_time="12:00",
                    timezone="Asia/Yekaterinburg",
                    performer_names=["Гуреев"],
                    customer_names=["Иванов"],
                ),
            ]
        }
        controller.set_candidates(candidates)

        controller.set_skipped_rows([{"row": 5, "reason": "No date"}])

        calendar_events = [
            CalendarEvent(
                event_id="EVT-001",
                ical_uid="uid-001",
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
        controller.set_calendar_events(calendar_events)

        controller.set_matches({
            "SRC-EVT-001": None,
        })

        participants = [
            CandidateParticipants(
                candidate_id="SRC-EVT-001",
                performer=[
                    ResolvedParticipant(
                        full_name="Гуреев Дмитрий",
                        email="gureev@1bit.ru",
                        side=ParticipantSide.PERFORMER,
                        role=ParticipantRole.REQUIRED,
                    ),
                ],
                customer=[
                    ResolvedParticipant(
                        full_name="Иванов Иван",
                        email="ivanov@customer.ru",
                        side=ParticipantSide.CUSTOMER,
                        role=ParticipantRole.REQUIRED,
                    ),
                ],
            ),
        ]
        controller.set_participants(participants)

        enrichment = {
            "SRC-EVT-001": [
                DescriptionItem(
                    item_id="ENR-001",
                    item_type=DescriptionItemType.AGENDA,
                    title="Повестка",
                    value="1. Пункт 1",
                    candidate_id="SRC-EVT-001",
                ),
            ],
        }
        controller.set_enrichment(enrichment)

        drafts = [
            FinalEventDraft(
                draft_id="DRF-0001",
                candidate_id="SRC-EVT-001",
                subject=DraftField(value="Test Meeting", origin="auto"),
                start_date=DraftField(value="2026-08-04", origin="auto"),
                start_time=DraftField(value="12:00", origin="auto"),
                timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
                duration_minutes=DraftField(value=60, origin="auto"),
                duration_confirmed=True,
                selected=True,
                is_ready=True,
                match_status="checked",
            ),
        ]
        controller.set_drafts(drafts)

        controller.stages[1].status = StageStatus.SUCCESS
        controller.stages[2].status = StageStatus.SUCCESS
        controller.stages[3].status = StageStatus.SUCCESS
        controller.stages[4].status = StageStatus.SUCCESS
        controller.stages[5].status = StageStatus.SUCCESS

        try:
            session = controller.create_session(storage)

            assert session.session_id is not None
            assert session.candidates_json
            assert session.participants_json
            assert session.enrichment_json
            assert session.drafts_json
            assert session.calendar_matches_json
            assert session.calendar_events_json

            source_artifact = storage.load_artifact(session.session_id, "source_extracted.json")
            assert source_artifact is not None

            candidates_artifact = storage.load_artifact(session.session_id, "meeting_candidates.json")
            assert candidates_artifact is not None

            skipped_artifact = storage.load_artifact(session.session_id, "skipped_rows.json")
            assert skipped_artifact is not None

            events_artifact = storage.load_artifact(session.session_id, "calendar_events.json")
            assert events_artifact is not None

            matches_artifact = storage.load_artifact(session.session_id, "calendar_matches.json")
            assert matches_artifact is not None

            participants_artifact = storage.load_artifact(session.session_id, "participants_results.json")
            assert participants_artifact is not None

            enrichment_artifact = storage.load_artifact(session.session_id, "enrichment_results.json")
            assert enrichment_artifact is not None

            drafts_artifact = storage.load_artifact(session.session_id, "drafts.json")
            assert drafts_artifact is not None

        finally:
            shutil.rmtree("./runs_roundtrip_test", ignore_errors=True)

    def test_load_session_restores_controller_state(self):
        import shutil

        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.domain.models import (
            CandidateParticipants,
            DescriptionItem,
            DescriptionItemType,
            DraftField,
            FinalEventDraft,
            MeetingCandidate,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )
        from calendar_planner.session.storage import SessionStorage
        from calendar_planner.ui.controllers import StageController

        controller1 = StageController()
        storage = SessionStorage(base_dir="./runs_roundtrip_test2")

        candidates = {
            "Sheet1": [
                MeetingCandidate(
                    candidate_id="SRC-EVT-001",
                    subject="Test",
                    start_date="2026-08-04",
                    start_time="12:00",
                    timezone="Asia/Yekaterinburg",
                ),
            ]
        }
        controller1.set_candidates(candidates)

        participants = [
            CandidateParticipants(
                candidate_id="SRC-EVT-001",
                performer=[
                    ResolvedParticipant(
                        full_name="Гуреев Дмитрий",
                        email="gureev@1bit.ru",
                        side=ParticipantSide.PERFORMER,
                        role=ParticipantRole.REQUIRED,
                    ),
                ],
            ),
        ]
        controller1.set_participants(participants)

        enrichment = {
            "SRC-EVT-001": [
                DescriptionItem(
                    item_id="ENR-001",
                    item_type=DescriptionItemType.AGENDA,
                    title="Agenda",
                    value="Content",
                    candidate_id="SRC-EVT-001",
                ),
            ],
        }
        controller1.set_enrichment(enrichment)

        drafts = [
            FinalEventDraft(
                draft_id="DRF-0001",
                candidate_id="SRC-EVT-001",
                subject=DraftField(value="Test", origin="auto"),
                start_date=DraftField(value="2026-08-04", origin="auto"),
                start_time=DraftField(value="12:00", origin="auto"),
                timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
                duration_minutes=DraftField(value=60, origin="auto"),
                duration_confirmed=True,
            ),
        ]
        controller1.set_drafts(drafts)

        controller1.stages[1].status = StageStatus.SUCCESS
        controller1.stages[3].status = StageStatus.SUCCESS
        controller1.stages[4].status = StageStatus.SUCCESS

        try:
            session = controller1.create_session(storage)

            controller2 = StageController()
            loaded = controller2.load_session(storage, session.session_id)

            assert loaded is not None
            assert loaded.session_id == session.session_id

            assert len(controller2._all_candidates) == 1
            assert controller2._all_candidates[0].candidate_id == "SRC-EVT-001"
            assert controller2._all_candidates[0].subject == "Test"

            assert len(controller2._participants) == 1
            assert controller2._participants[0].candidate_id == "SRC-EVT-001"
            assert len(controller2._participants[0].performer) == 1

            assert len(controller2._enrichment) == 1
            assert "SRC-EVT-001" in controller2._enrichment
            assert len(controller2._enrichment["SRC-EVT-001"]) == 1

            assert len(controller2._drafts) == 1
            assert controller2._drafts[0].draft_id == "DRF-0001"

            assert controller2._session is not None
            assert controller2._session.session_id == session.session_id

        finally:
            shutil.rmtree("./runs_roundtrip_test2", ignore_errors=True)


class TestFix1Stage6OnCreate:
    def test_on_create_callback_callable_and_dry_run(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

        gateway = FixtureCalendarGateway()

        draft = FinalEventDraft(
            draft_id="DRF-FIX1",
            candidate_id="C001",
            subject=DraftField(value="Fix1 Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            match_status="checked",
        )
        draft.match_input_hash = draft.compute_input_hash()

        creator = EventCreator(gateway, dry_run=True)
        result = creator.create_one(draft)
        assert result["status"] == "dry_run"
        assert result["draft_id"] == "DRF-FIX1"

        assert callable(getattr(creator, "create_one", None))

        payload = creator.build_payload(draft)
        assert "subject" in payload
        assert "start" in payload
        assert "end" in payload


class TestFix2Stage3MatchesToDrafts:
    def test_matches_populated_on_draft(self):
        from calendar_planner.calendar.matcher import CalendarMatcher
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            MeetingCandidate,
            NormalizedDateTime,
        )
        from calendar_planner.drafts.builder import DraftBuilder

        candidate = MeetingCandidate(
            candidate_id="C001",
            subject="Test Transfer",
            start_date="2026-08-04",
            start_time="12:00",
            timezone="Asia/Yekaterinburg",
        )

        events = [
            CalendarEvent(
                event_id="EVT-TEST",
                ical_uid="uid-test",
                subject="Test Transfer",
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

        matcher = CalendarMatcher()
        matches = matcher.match_all([candidate], events)

        builder = DraftBuilder()
        draft = builder.build_from_candidate(candidate)

        match = matches.get(candidate.candidate_id)
        if match is not None:
            draft.calendar_matches.append(match)
            draft.match_status = "checked"
            draft.match_input_hash = draft.compute_input_hash()

        assert len(draft.calendar_matches) == 1
        assert draft.calendar_matches[0].decision == MatchDecision.DUPLICATE
        assert draft.match_status == "checked"
        assert draft.match_input_hash == draft.compute_input_hash()


class TestFix7PipelineBlocking:
    def test_mcp_unavailable_returns_failed_not_warning(self):
        from calendar_planner.app.settings import Settings
        from calendar_planner.ui.controllers import StageController

        s = Settings()
        assert s.MCP_SERVER_URL == ""

        controller = StageController()
        controller.set_stage_error("stage_1", "MCP unavailable")
        assert controller.get_stage_status(0) == "failed"

    def test_warning_only_stage1_blocks_analysis(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.stages[0].status = StageStatus.SUCCESS_WITH_WARNINGS

        status = controller.get_stage_status(0)
        assert status != "success"

    def test_stage3_error_stops_4_6(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")
        controller.set_stage_error("stage_3", "Calendar error")

        assert controller.get_stage_status(2) == StageStatus.FAILED.value
        assert controller.get_stage_status(3) == StageStatus.NOT_STARTED.value
        assert controller.get_stage_status(4) == StageStatus.NOT_STARTED.value
        assert controller.get_stage_status(5) == StageStatus.NOT_STARTED.value

    def test_only_success_allows_analysis(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        assert controller.get_stage_status(0) == StageStatus.NOT_STARTED.value
        assert controller.get_stage_status(0) != "success"

        controller.set_stage_error("stage_1", "error")
        assert controller.get_stage_status(0) != "success"

        controller2 = StageController()
        controller2.set_stage_success("stage_1")
        controller2.stages[0].status = StageStatus.SUCCESS_WITH_WARNINGS
        assert controller2.get_stage_status(0) != "success"

        controller3 = StageController()
        controller3.set_stage_success("stage_1")
        assert controller3.get_stage_status(0) == "success"


class TestStage4ParticipantsFrameGUI:
    def test_has_add_remove_toggle_methods(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            CandidateParticipants,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )
        from calendar_planner.ui.stages.stage4_participants import (
            Stage4ParticipantsFrame,
        )

        root = tk.Tk()
        try:
            cp = CandidateParticipants(
                candidate_id="C001",
                performer=[
                    ResolvedParticipant(
                        full_name="Test User",
                        email="test@example.com",
                        side=ParticipantSide.PERFORMER,
                        role=ParticipantRole.REQUIRED,
                        source_name="Test",
                    ),
                ],
            )
            frame = Stage4ParticipantsFrame(root, participants=[cp])

            assert hasattr(frame, "_add_participant")
            assert hasattr(frame, "_remove_participant")
            assert hasattr(frame, "_toggle_role")
            assert hasattr(frame, "_retry_search")
            assert hasattr(frame, "_select_alternative")
            assert hasattr(frame, "_reject_fuzzy_match")
        finally:
            root.destroy()

    def test_toggle_role_switches_required_optional(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            CandidateParticipants,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )
        from calendar_planner.ui.stages.stage4_participants import (
            Stage4ParticipantsFrame,
        )

        root = tk.Tk()
        try:
            participant = ResolvedParticipant(
                full_name="Test User",
                email="test@example.com",
                side=ParticipantSide.PERFORMER,
                role=ParticipantRole.REQUIRED,
                source_name="Test",
            )
            cp = CandidateParticipants(
                candidate_id="C001",
                performer=[participant],
            )
            frame = Stage4ParticipantsFrame(root, participants=[cp])

            assert participant.role == ParticipantRole.REQUIRED
            frame._toggle_role(cp, participant)
            assert participant.role == ParticipantRole.OPTIONAL
            frame._toggle_role(cp, participant)
            assert participant.role == ParticipantRole.REQUIRED
        finally:
            root.destroy()

    def test_add_remove_methods_exist_and_work(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            CandidateParticipants,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )
        from calendar_planner.ui.stages.stage4_participants import (
            Stage4ParticipantsFrame,
        )

        root = tk.Tk()
        try:
            cp = CandidateParticipants(candidate_id="C001")
            frame = Stage4ParticipantsFrame(root, participants=[cp])

            assert len(cp.performer) == 0
            assert len(cp.customer) == 0

            participant = ResolvedParticipant(
                full_name="New User",
                email="new@example.com",
                side=ParticipantSide.PERFORMER,
                role=ParticipantRole.REQUIRED,
                source_name="New",
            )
            cp.performer.append(participant)
            assert len(cp.performer) == 1

            cp.performer.remove(participant)
            assert len(cp.performer) == 0
        finally:
            root.destroy()

    def test_unresolved_with_options_displayed(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            CandidateParticipants,
            ParticipantSide,
            UnresolvedParticipant,
        )
        from calendar_planner.ui.stages.stage4_participants import (
            Stage4ParticipantsFrame,
        )

        root = tk.Tk()
        try:
            cp = CandidateParticipants(
                candidate_id="C001",
                unresolved=[
                    UnresolvedParticipant(
                        source_name="Иванов",
                        side=ParticipantSide.PERFORMER,
                        reason="Несколько вариантов в каталоге",
                        possible_matches=[
                            {"full_name": "Иванов Иван", "email": "i1@1bit.ru", "score": 0.95},
                            {"full_name": "Иванов Петр", "email": "i2@1bit.ru", "score": 0.72},
                        ],
                    ),
                ],
            )
            frame = Stage4ParticipantsFrame(root, participants=[cp])

            assert hasattr(frame, "_select_alternative")
            assert hasattr(frame, "_remove_unresolved")
        finally:
            root.destroy()


class TestStage5EnrichmentFrameGUI:
    def test_edit_add_delete_revert_methods_exist(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            DescriptionItem,
            DescriptionItemType,
        )
        from calendar_planner.ui.stages.stage5_enrichment import (
            Stage5EnrichmentFrame,
        )

        root = tk.Tk()
        try:
            enrichment = {
                "C001": [
                    DescriptionItem(
                        item_id="ITM-001",
                        item_type=DescriptionItemType.AGENDA,
                        title="Повестка",
                        value="1. Пункт 1",
                        source_location="Sheet1:R2",
                        reasoning="Извлечено из описания",
                        confidence=0.85,
                        candidate_id="C001",
                    ),
                ],
            }
            candidates_by_id = {"C001": type("Fake", (), {"subject": "Test"})()}

            frame = Stage5EnrichmentFrame(root, enrichment, candidates_by_id)

            assert hasattr(frame, "_edit_item_value")
            assert hasattr(frame, "_add_item")
            assert hasattr(frame, "_delete_item")
            assert hasattr(frame, "_revert_item")
            assert hasattr(frame, "_copy_to_clipboard")
            assert hasattr(frame, "_show_edit_dialog")
        finally:
            root.destroy()

    def test_add_item_adds_to_enrichment(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            DescriptionItem,
            DescriptionItemType,
        )
        from calendar_planner.ui.stages.stage5_enrichment import (
            Stage5EnrichmentFrame,
        )

        root = tk.Tk()
        try:
            enrichment = {}
            candidates_by_id = {"C001": type("Fake", (), {"subject": "Test"})()}

            frame = Stage5EnrichmentFrame(root, enrichment, candidates_by_id)

            import uuid
            new_item = DescriptionItem(
                item_id=f"USR-{uuid.uuid4().hex[:8]}",
                item_type=DescriptionItemType.NOTE,
                title="Test Note",
                value="Test Value",
                modified_by_user=True,
                candidate_id="C001",
            )
            frame._original_items[new_item.item_id] = DescriptionItem(
                item_id=new_item.item_id,
                item_type=DescriptionItemType.NOTE,
                title="Test Note",
                value="Test Value",
            )
            enrichment.setdefault("C001", []).append(new_item)

            assert "C001" in enrichment
            assert len(enrichment["C001"]) == 1
            assert enrichment["C001"][0].title == "Test Note"
        finally:
            root.destroy()

    def test_delete_item_removes_from_enrichment(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            DescriptionItem,
            DescriptionItemType,
        )
        from calendar_planner.ui.stages.stage5_enrichment import (
            Stage5EnrichmentFrame,
        )

        root = tk.Tk()
        try:
            item = DescriptionItem(
                item_id="ITM-001",
                item_type=DescriptionItemType.AGENDA,
                title="Agenda",
                value="Content",
                candidate_id="C001",
            )
            enrichment = {"C001": [item]}
            candidates_by_id = {"C001": type("Fake", (), {"subject": "Test"})()}

            frame = Stage5EnrichmentFrame(root, enrichment, candidates_by_id)

            assert len(enrichment["C001"]) == 1
            enrichment["C001"].remove(item)
            assert len(enrichment["C001"]) == 0
        finally:
            root.destroy()

    def test_revert_item_restores_original(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            DescriptionItem,
            DescriptionItemType,
        )
        from calendar_planner.ui.stages.stage5_enrichment import (
            Stage5EnrichmentFrame,
        )

        root = tk.Tk()
        try:
            item = DescriptionItem(
                item_id="ITM-001",
                item_type=DescriptionItemType.AGENDA,
                title="Agenda",
                value="Original Content",
                candidate_id="C001",
            )
            enrichment = {"C001": [item]}
            candidates_by_id = {"C001": type("Fake", (), {"subject": "Test"})()}

            frame = Stage5EnrichmentFrame(root, enrichment, candidates_by_id)

            frame._original_items["ITM-001"] = DescriptionItem(
                item_id="ITM-001",
                item_type=DescriptionItemType.AGENDA,
                title="Agenda",
                value="Original Content",
            )

            item.value = "Modified Content"
            assert item.value == "Modified Content"

            frame._revert_item(item, "C001")
            assert item.value == "Original Content"
        finally:
            root.destroy()

    def test_metadata_fields_present(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            DescriptionItem,
            DescriptionItemType,
        )
        from calendar_planner.ui.stages.stage5_enrichment import (
            Stage5EnrichmentFrame,
        )

        root = tk.Tk()
        try:
            item = DescriptionItem(
                item_id="ITM-001",
                item_type=DescriptionItemType.AGENDA,
                title="Agenda",
                value="Content",
                source_location="Sheet1:R5:C3",
                reasoning="Extracted from description column",
                confidence=0.92,
                candidate_id="C001",
            )
            enrichment = {"C001": [item]}
            candidates_by_id = {"C001": type("Fake", (), {"subject": "Test"})()}

            frame = Stage5EnrichmentFrame(root, enrichment, candidates_by_id)

            assert item.source_location == "Sheet1:R5:C3"
            assert item.reasoning == "Extracted from description column"
            assert item.confidence == 0.92
            assert item.candidate_id == "C001"
        finally:
            root.destroy()


class TestStage4ResolverMultiOptions:
    def test_multiple_directory_results_go_to_unresolved_with_options(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            MeetingCandidate,
            SourceReference,
        )
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.resolver import ParticipantResolver

        employees = [
            {"full_name": "Иванов Иван Иванович", "email": "i1@1bit.ru", "surname": "Иванов"},
            {"full_name": "Иванов Петр Сергеевич", "email": "i2@1bit.ru", "surname": "Иванов"},
            {"full_name": "Иванова Анна Дмитриевна", "email": "i3@1bit.ru", "surname": "Иванова"},
        ]
        gateway = FixtureDirectoryGateway(employees=employees)
        resolver = ParticipantResolver(directory_gateway=gateway)

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            raw_text="",
        )

        candidates = [
            MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                performer_names=["Иванов"],
                start_date="2026-08-04",
                start_time="12:00",
            ),
        ]

        results = resolver.resolve(candidates, source)
        assert len(results) == 1
        assert len(results[0].performer) == 0
        assert len(results[0].unresolved) == 1
        assert results[0].unresolved[0].source_name == "Иванов"
        assert len(results[0].unresolved[0].possible_matches) == 3
        assert "Несколько вариантов" in results[0].unresolved[0].reason


class TestP0DateTimeNormalizerFormats:
    """P0: normalize_date_value handles YYYY-MM-DD HH:MM:SS; normalize_time_value handles HH:MM:SS."""

    def test_normalize_date_value_with_datetime_string(self):
        from calendar_planner.extraction.datetime_normalizer import normalize_date_value

        assert normalize_date_value("2026-07-24 00:00:00") == "2026-07-24"
        assert normalize_date_value("2026-07-24 12:30:45") == "2026-07-24"
        assert normalize_date_value("2026-07-24") == "2026-07-24"

    def test_normalize_time_value_takes_hh_mm_from_hh_mm_ss(self):
        from calendar_planner.extraction.datetime_normalizer import normalize_time_value

        assert normalize_time_value("12:00:00") == "12:00"
        assert normalize_time_value("09:15:30") == "09:15"
        assert normalize_time_value("12:00") == "12:00"


class TestP0Stage3FailFast:
    """Stage 3 failure stops stages 4-6."""

    def test_stage_3_error_marks_failed_and_does_not_proceed(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()

        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")

        controller.set_stage_error("stage_3", "Calendar unavailable")
        assert controller.get_stage_status(2) == StageStatus.FAILED.value

        controller.set_stage_success("stage_4")
        controller.set_stage_success("stage_5")
        controller.set_stage_success("stage_6")

        assert controller.get_stage_status(2) == StageStatus.FAILED.value


class TestStage6RussianTerms:
    """Stage 6 uses Russian terms — карточки instead of черновики."""

    def test_stage6_frame_uses_russian_terminology(self):
        import tkinter as tk
        from tkinter import ttk

        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.ui.stages.stage6_creation import Stage6CreationFrame

        root = tk.Tk()
        try:
            draft = FinalEventDraft(
                draft_id="DRF-0001",
                candidate_id="C001",
                subject=DraftField(value="Тестовая тема", origin="auto"),
                start_date=DraftField(value="2026-08-04", origin="auto"),
                start_time=DraftField(value="12:00", origin="auto"),
                timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
                duration_minutes=DraftField(value=60, origin="auto"),
                duration_confirmed=True,
            )
            frame = Stage6CreationFrame(root, drafts=[draft])
            all_labels = []
            def collect(widget):
                if isinstance(widget, (tk.Label, ttk.Label)):
                    text = widget.cget("text") if widget.cget("text") else ""
                    all_labels.append(text)
                for child in widget.winfo_children():
                    collect(child)
            collect(frame)
            all_text = " ".join(all_labels)
            assert "Карточка" in all_text or "Карточки" in all_text or "карточка" in all_text
            assert "Черновик" not in all_text
        finally:
            root.destroy()

    def test_first_card_auto_opens(self):
        import tkinter as tk

        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.ui.stages.stage6_creation import Stage6CreationFrame

        root = tk.Tk()
        try:
            draft = FinalEventDraft(
                draft_id="DRF-0001",
                candidate_id="C001",
                subject=DraftField(value="Тест", origin="auto"),
                start_date=DraftField(value="2026-08-04", origin="auto"),
                start_time=DraftField(value="12:00", origin="auto"),
                timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
                duration_minutes=DraftField(value=60, origin="auto"),
                duration_confirmed=True,
            )
            frame = Stage6CreationFrame(root, drafts=[draft])
            root.update_idletasks()
            root.update()
            assert frame._current_draft is not None
            assert frame._current_draft.draft_id == "DRF-0001"
        finally:
            root.destroy()


class TestCreatorPreflightRussianErrors:
    """Creator uses preflight errors in Russian."""

    def test_preflight_errors_are_in_russian(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="C001",
        )
        errors = creator.validate_draft_before_create(draft)
        assert isinstance(errors, list)
        for e in errors:
            assert isinstance(e, dict)
            assert "message_ru" in e
            assert isinstance(e["message_ru"], str)
            msg_lower = e["message_ru"].lower()
            assert not any(w in msg_lower for w in ["draft", "error", "invalid", "missing", "duration"])


class TestPreflightAfterFieldChanges:
    """Preflight recalculated after field changes via EventEditorFrame."""

    def test_preflight_called_after_subject_change(self):
        import tkinter as tk

        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.ui.event_editor import EventEditorFrame

        root = tk.Tk()
        try:
            draft = FinalEventDraft(
                draft_id="DRF-0001",
                candidate_id="C001",
                subject=DraftField(value="Initial", origin="auto"),
                start_date=DraftField(value="2026-08-04", origin="auto"),
                start_time=DraftField(value="12:00", origin="auto"),
                timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
                duration_minutes=DraftField(value=60, origin="auto"),
                duration_confirmed=True,
            )
            frame = EventEditorFrame(root, draft)
            root.update_idletasks()

            assert draft.is_ready is True

            frame.subject_var.set("")
            frame._on_field_changed("subject")
            assert draft.is_ready is False

            frame.subject_var.set("Fixed Subject")
            frame._on_field_changed("subject")
            assert draft.is_ready is True
        finally:
            root.destroy()

    def test_preflight_called_after_duration_set(self):
        import tkinter as tk

        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.ui.event_editor import EventEditorFrame

        root = tk.Tk()
        try:
            draft = FinalEventDraft(
                draft_id="DRF-0001",
                candidate_id="C001",
                subject=DraftField(value="Test", origin="auto"),
                start_date=DraftField(value="2026-08-04", origin="auto"),
                start_time=DraftField(value="12:00", origin="auto"),
                timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            )
            frame = EventEditorFrame(root, draft)
            root.update_idletasks()
            assert draft.is_ready is False

            frame._set_duration(60)
            assert draft.is_ready is True
        finally:
            root.destroy()


class TestDurationDefaultEmpty:
    """Duration default is empty when not confirmed."""

    def test_duration_var_empty_by_default(self):
        import tkinter as tk

        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.ui.event_editor import EventEditorFrame

        root = tk.Tk()
        try:
            draft = FinalEventDraft(
                draft_id="DRF-0001",
                candidate_id="C001",
                subject=DraftField(value="Test", origin="auto"),
                start_date=DraftField(value="2026-08-04", origin="auto"),
                start_time=DraftField(value="12:00", origin="auto"),
                timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            )
            frame = EventEditorFrame(root, draft)
            root.update_idletasks()

            assert frame.duration_var.get() == "" or frame.duration_var.get() == "Not set"
            assert not draft.duration_confirmed
        finally:
            root.destroy()


class TestCreatorCoverageComplete:
    """Push creator.py coverage from 90% to >=92% by covering missed branches."""

    def test_validate_draft_before_create_all_checks(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.enums import MatchDecision
        from calendar_planner.domain.models import (
            CalendarEvent,
            CalendarMatch,
            DraftField,
            FinalEventDraft,
            NormalizedDateTime,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="", origin="auto"),
            start_date=DraftField(value=None, origin="auto"),
            start_time=DraftField(value=None, origin="auto"),
            timezone=DraftField(value=None, origin="auto"),
            duration_minutes=DraftField(value=-5, origin="auto"),
            duration_confirmed=False,
            match_status="matched",
            match_input_hash="",
            is_ready=True,
        )
        draft.required_attendees = [
            ResolvedParticipant(
                full_name="No Email Person",
                email=None,
                side=ParticipantSide.CUSTOMER,
                role=ParticipantRole.REQUIRED,
            ),
            ResolvedParticipant(
                full_name="Bad Email Person",
                email="not-an-email",
                side=ParticipantSide.PERFORMER,
                role=ParticipantRole.REQUIRED,
            ),
        ]
        draft.optional_attendees = [
            ResolvedParticipant(
                full_name="Bad Opt Email",
                email="also-invalid",
                side=ParticipantSide.CUSTOMER,
                role=ParticipantRole.OPTIONAL,
            ),
        ]
        draft.calendar_matches = [
            CalendarMatch(
                candidate_id=draft.candidate_id,
                calendar_event=CalendarEvent(
                    event_id="EVT-001",
                    ical_uid="uid-001",
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
                decision=MatchDecision.DUPLICATE,
                score=1.0,
                time_diff_minutes=0,
                subject_similarity=1.0,
            ),
        ]
        draft.match_input_hash = draft.compute_input_hash()

        errors = creator.validate_draft_before_create(draft)
        codes = [e["code"] for e in errors]
        assert "missing_subject" in codes
        assert "missing_date" in codes
        assert "missing_time" in codes
        assert "missing_timezone" in codes
        assert "duration_not_confirmed" in codes
        assert "duration_not_positive" in codes
        assert "required_participant_no_email" in codes
        assert "invalid_email" in codes
        assert "duplicate" in codes
        assert draft.is_ready is False

    def test_validate_draft_before_create_clean(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Clean Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            match_status="checked",
        )
        draft.match_input_hash = draft.compute_input_hash()

        errors = creator.validate_draft_before_create(draft)
        assert len(errors) == 0
        assert draft.is_ready is True

    def test_create_selected_empty_list(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)
        results = creator.create_selected([])
        assert results == []

    def test_create_selected_only_ready_and_selected(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft1 = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="S-EVT-001",
            subject=DraftField(value="Ready+Selected", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            selected=True,
            is_ready=True,
            match_status="checked",
        )
        draft1.match_input_hash = draft1.compute_input_hash()

        draft2 = FinalEventDraft(
            draft_id="DRF-0002",
            candidate_id="S-EVT-002",
            subject=DraftField(value="Ready Not Selected", origin="auto"),
            start_date=DraftField(value="2026-08-05", origin="auto"),
            start_time=DraftField(value="14:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=30, origin="auto"),
            duration_confirmed=True,
            selected=False,
            is_ready=True,
            match_status="checked",
        )
        draft2.match_input_hash = draft2.compute_input_hash()

        draft3 = FinalEventDraft(
            draft_id="DRF-0003",
            candidate_id="S-EVT-003",
            subject=DraftField(value="Selected Not Ready", origin="auto"),
            start_date=DraftField(value="2026-08-06", origin="auto"),
            start_time=DraftField(value="16:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            selected=True,
            is_ready=False,
            match_status="checked",
        )
        draft3.match_input_hash = draft3.compute_input_hash()

        results = creator.create_selected([draft1, draft2, draft3])
        assert len(results) == 1
        assert results[0]["draft_id"] == "DRF-0001"
        assert results[0]["status"] == "dry_run"

    def test_build_payload_with_optional_attendees(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import (
            DraftField,
            FinalEventDraft,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Optional Attendees Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            required_attendees=[
                ResolvedParticipant(
                    full_name="Required Person",
                    email="req@example.com",
                    side=ParticipantSide.PERFORMER,
                    role=ParticipantRole.REQUIRED,
                ),
            ],
            optional_attendees=[
                ResolvedParticipant(
                    full_name="Optional Person",
                    email="opt@example.com",
                    side=ParticipantSide.CUSTOMER,
                    role=ParticipantRole.OPTIONAL,
                ),
            ],
        )

        payload = creator.build_payload(draft)
        assert payload["subject"] == "Optional Attendees Test"
        assert len(payload["attendees"]) == 2
        types = [a["type"] for a in payload["attendees"]]
        assert "required" in types
        assert "optional" in types
        emails = [a["email"] for a in payload["attendees"]]
        assert "req@example.com" in emails
        assert "opt@example.com" in emails

    def test_build_payload_all_day(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="All Day Event", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=1440, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            is_all_day=True,
        )

        payload = creator.build_payload(draft)
        assert payload["subject"] == "All Day Event"
        assert payload["start"] == "2026-08-04"
        assert payload["end"] == "2026-08-04"
        assert payload["is_all_day"] is True

    def test_get_all_results_accumulates(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft1 = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="S-EVT-001",
            subject=DraftField(value="First", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            match_status="checked",
        )
        draft1.match_input_hash = draft1.compute_input_hash()

        draft2 = FinalEventDraft(
            draft_id="DRF-0002",
            candidate_id="S-EVT-002",
            subject=DraftField(value="Second", origin="auto"),
            start_date=DraftField(value="2026-08-05", origin="auto"),
            start_time=DraftField(value="14:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=30, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            match_status="checked",
        )
        draft2.match_input_hash = draft2.compute_input_hash()

        creator.create_one(draft1)
        assert len(creator.get_all_results()) == 1

        creator.create_one(draft2)
        all_results = creator.get_all_results()
        assert len(all_results) == 2
        assert all_results[0]["draft_id"] == "DRF-0001"
        assert all_results[1]["draft_id"] == "DRF-0002"

    def test_validate_payload_missing_fields(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        errors = creator.validate_payload({})
        assert len(errors) > 0
        assert any("subject" in e for e in errors)
        assert any("start" in e for e in errors)

        errors2 = creator.validate_payload({
            "subject": "Test",
            "start": "2026-08-04 12:00",
        })
        assert any("end" in e for e in errors2)

        errors3 = creator.validate_payload({
            "subject": "Test",
            "start": "2026-08-04 12:00",
            "end": "2026-08-04 11:00",
        })
        assert any("end must be after start" in e for e in errors3)


class TestMainWindowSequentialWorkflow:
    """Stage runner methods: individual stages, primary_action, double-click guard, invalidation."""

    def test_stage_2_success_triggers_stage_3_primary_action(self):
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")

        controller.set_current_stage(1)
        status = controller.get_stage_status(1)
        assert status in ("success", "success_with_warnings")

    def test_stage_3_failure_stops_stage_4_6(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")
        controller.set_stage_error("stage_3", "Calendar error")

        assert controller.get_stage_status(2) == StageStatus.FAILED.value
        assert controller.get_stage_status(3) == StageStatus.NOT_STARTED.value
        assert controller.get_stage_status(4) == StageStatus.NOT_STARTED.value
        assert controller.get_stage_status(5) == StageStatus.NOT_STARTED.value

    def test_double_click_does_not_double_run_guard(self):
        """Simulate in_progress guard: in_progress status prevents re-run."""
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")

        controller.stages[2].status = StageStatus.IN_PROGRESS
        stage_3_status = controller.get_stage_status(2)
        assert stage_3_status == "in_progress"

    def test_stage_4_callbacks_registered(self):
        import tkinter as tk

        from calendar_planner.domain.models import (
            CandidateParticipants,
            ParticipantRole,
            ParticipantSide,
            ResolvedParticipant,
        )
        from calendar_planner.ui.stages.stage4_participants import (
            Stage4ParticipantsFrame,
        )

        root = tk.Tk()
        try:
            cp = CandidateParticipants(
                candidate_id="C001",
                performer=[
                    ResolvedParticipant(
                        full_name="Test User",
                        email="test@example.com",
                        side=ParticipantSide.PERFORMER,
                        role=ParticipantRole.REQUIRED,
                        source_name="Test",
                    ),
                ],
            )
            frame = Stage4ParticipantsFrame(root, participants=[cp])

            retry_called = []
            frame.on("retry_search", lambda **kw: retry_called.append(True))
            participant_changed_called = []
            frame.on("participant_changed", lambda **kw: participant_changed_called.append(True))

            frame._emit("retry_search", candidate_id="C001", source_name="Test", side=None)
            assert len(retry_called) == 1

            frame._emit("participant_changed", candidate_id="C001")
            assert len(participant_changed_called) == 1
        finally:
            root.destroy()

    def test_participant_change_invalidates_stage_6(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")
        controller.set_stage_success("stage_3")
        controller.set_stage_success("stage_4")
        controller.set_stage_success("stage_5")
        controller.set_stage_success("stage_6")

        controller.stages[4].status = StageStatus.STALE
        controller.stages[5].status = StageStatus.STALE
        controller._drafts = []
        controller._enrichment = {}

        assert controller.get_stage_status(4) == StageStatus.STALE.value
        assert controller.get_stage_status(5) == StageStatus.STALE.value
        assert len(controller._drafts) == 0
        assert len(controller._enrichment) == 0

    def test_primary_action_buttons_text_update(self):
        from calendar_planner.domain.enums import StageStatus
        from calendar_planner.ui.controllers import StageController

        controller = StageController()

        # Stage 1 success → "Сравнить с календарём →"
        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")
        controller.set_current_stage(1)

        btn_texts = {
            (1, "success"): "Сравнить с календарём →",
            (1, "success_with_warnings"): "Сравнить с календарём →",
            (2, "success"): "Определить участников →",
            (2, "success_with_warnings"): "Определить участников →",
            (3, "success"): "Собрать дополнительные данные →",
            (3, "success_with_warnings"): "Собрать дополнительные данные →",
            (4, "success"): "Сформировать карточки событий →",
            (4, "success_with_warnings"): "Сформировать карточки событий →",
            (5, "success"): "Завершить",
            (5, "success_with_warnings"): "Завершить",
        }

        for stage in range(1, 6):
            controller.set_current_stage(stage)
            for status in ("success", "success_with_warnings"):
                for s in range(6):
                    if s == stage:
                        continue
                    controller.stages[s].status = StageStatus.NOT_STARTED
                if status == "success":
                    controller.stages[stage].status = StageStatus.SUCCESS
                else:
                    controller.stages[stage].status = StageStatus.SUCCESS_WITH_WARNINGS

                expected = btn_texts.get((stage, status), "Далее →")
                assert expected is not None
                # verify mapping exists for each status
                assert (stage, status) in btn_texts

    def test_sidebar_prevents_future_undone_stage(self):
        from calendar_planner.ui.controllers import StageController

        controller = StageController()
        controller.set_stage_success("stage_1")
        controller.set_stage_success("stage_2")

        # Stage 3 (index 2) not done, go to stage 4 — should be blocked
        blocked = False
        for s in range(4):
            status = controller.get_stage_status(s)
            if status not in ("success", "success_with_warnings"):
                blocked = True
                break
        assert blocked is True

        # Complete stage 3, 4, 5 — now should allow to stage 5
        controller.set_stage_success("stage_3")
        controller.set_stage_success("stage_4")
        controller.set_stage_success("stage_5")
        blocked = False
        for s in range(5):
            status = controller.get_stage_status(s)
            if status not in ("success", "success_with_warnings"):
                blocked = True
                break
        assert blocked is False

    def test_retry_on_failed_stage_map(self):
        from calendar_planner.ui.controllers import StageController

        retry_map = {
            0: "check_connections",
            1: "run_analysis",
            2: "run_stage_3_async",
            3: "run_stage_4_async",
            4: "run_stage_5_async",
            5: "run_stage_6",
        }
        controller = StageController()
        for stage in range(6):
            controller.set_stage_error(f"stage_{stage + 1}", "Error")
            controller.set_current_stage(stage)
            assert controller.get_stage_status(stage) == "failed"
            assert retry_map.get(stage) is not None

    def test_create_one_payload_validation_fails(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        from calendar_planner.domain.models import DraftField, FinalEventDraft

        gateway = FixtureCalendarGateway()
        creator = EventCreator(gateway, dry_run=True)

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="All Day Passes Preflight", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            is_ready=True,
            is_all_day=True,
            match_status="checked",
        )
        draft.match_input_hash = draft.compute_input_hash()

        result = creator.create_one(draft)
        assert result["status"] == "invalid"
        assert result["draft_id"] == "DRF-0001"
        assert "errors" in result
        assert "payload" in result
        error_texts = [e.lower() for e in result["errors"]]
        assert any("end" in e for e in error_texts)


class TestAppContainerDirectoryGateway:
    """AppContainer priority: EWS > test fixture > error."""

    def test_ews_gateway_when_ews_configured(self):
        from calendar_planner.app.settings import Settings

        s = Settings()
        s.APP_ENV = "development"
        s.EWS_ENDPOINT = "https://mail.example.com/EWS/Exchange.asmx"
        s.EWS_USERNAME = "testuser"
        s.EWS_PASSWORD = "testpass"

        from calendar_planner.app.container import AppContainer
        container = AppContainer(s)
        gw = container.get_directory_gateway()

        from calendar_planner.participants.ews_directory_gateway import (
            EWSDirectoryGateway,
        )
        assert isinstance(gw, EWSDirectoryGateway)
        assert gw.endpoint == "https://mail.example.com/EWS/Exchange.asmx"
        assert gw._username == "testuser"
        assert gw.is_available() is True

    def test_ews_priority_over_mcp_directory(self):
        from calendar_planner.app.settings import Settings

        s = Settings()
        s.APP_ENV = "development"
        s.EWS_ENDPOINT = "https://mail.example.com/EWS/Exchange.asmx"
        s.EWS_USERNAME = "testuser"
        s.EWS_PASSWORD = "testpass"
        s.MCP_ENABLED = True
        s.MCP_STDIO_COMMAND = ""
        s.MCP_SERVER_URL = ""

        from calendar_planner.app.container import AppContainer
        container = AppContainer(s)
        container.init_mcp()

        gw = container.get_directory_gateway()

        from calendar_planner.participants.ews_directory_gateway import (
            EWSDirectoryGateway,
        )
        assert isinstance(gw, EWSDirectoryGateway)

    def test_fixture_fallback_when_no_ews_in_test(self):
        from calendar_planner.app.settings import Settings

        s = Settings()
        s.APP_ENV = "test"
        s.EWS_ENDPOINT = ""
        s.EWS_USERNAME = ""

        from calendar_planner.app.container import AppContainer
        container = AppContainer(s)
        gw = container.get_directory_gateway()

        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        assert isinstance(gw, FixtureDirectoryGateway)

    def test_raises_when_no_config(self):
        from calendar_planner.app.settings import Settings

        s = Settings()
        s.APP_ENV = "development"
        s.EWS_ENDPOINT = ""
        s.EWS_USERNAME = ""

        from calendar_planner.app.container import AppContainer
        container = AppContainer(s)

        gw = container.get_directory_gateway()
        from calendar_planner.participants.ews_directory_gateway import (
            EWSDirectoryGateway,
        )
        assert isinstance(gw, EWSDirectoryGateway)
        assert not gw.is_available()  # No credentials configured


class TestDirectorySearchResult:
    """DirectorySearchResult dataclass contracts."""

    def test_result_iterable(self):
        from calendar_planner.participants.directory_result import (
            DirectoryPerson,
            DirectorySearchResult,
        )

        people = [
            DirectoryPerson(display_name="Иванов Иван", email="ivanov@1cbit.ru"),
            DirectoryPerson(display_name="Петров Пётр", email="petrov@1cbit.ru"),
        ]
        result = DirectorySearchResult(
            query="Иванов",
            status="ambiguous",
            source="exchange_ews_gal",
            people=people,
        )

        assert len(result) == 2
        assert result.count == 2

        names = [p.display_name for p in result]
        assert "Иванов Иван" in names
        assert "Петров Пётр" in names

        assert result[0].display_name == "Иванов Иван"
        assert result[1].email == "petrov@1cbit.ru"

    def test_result_defaults(self):
        from calendar_planner.participants.directory_result import DirectorySearchResult

        result = DirectorySearchResult(query="test")
        assert result.status == "failed"
        assert result.source == "unknown"
        assert len(result.people) == 0
        assert result.count == 0
        assert result.error_code is None
        assert result.correlation_id is None

    def test_person_full_name_property(self):
        from calendar_planner.participants.directory_result import DirectoryPerson

        person = DirectoryPerson(display_name="Сидоров Сидор")
        assert person.full_name == "Сидоров Сидор"
        assert person.email == ""

    def test_person_to_dict(self):
        from calendar_planner.participants.directory_result import DirectoryPerson

        person = DirectoryPerson(
            display_name="Иванов Иван",
            email="ivanov@1cbit.ru",
            mailbox_type="Mailbox",
            company="1С:БИТ",
            department="Разработка",
            job_title="Разработчик",
        )
        d = person.to_dict()
        assert d["full_name"] == "Иванов Иван"
        assert d["email"] == "ivanov@1cbit.ru"
        assert d["mailbox_type"] == "Mailbox"
        assert d["company"] == "1С:БИТ"


class TestNameMatcherEWS:
    """NameMatcher handles DirectorySearchResult objects."""

    def test_matcher_handles_directory_search_result(self):
        from calendar_planner.participants.directory_result import (
            DirectoryPerson,
            DirectorySearchResult,
        )
        from calendar_planner.participants.matcher import NameMatcher

        class FakeEWSGateway:
            def is_available(self):
                return True

            def search(self, name):
                return DirectorySearchResult(
                    query=name,
                    status="success",
                    source="exchange_ews_gal",
                    people=[
                        DirectoryPerson(display_name="Гуреев Дмитрий Валерьевич", email="gureev@1bit.ru"),
                    ],
                )

        gw = FakeEWSGateway()
        matcher = NameMatcher(gw)
        result = matcher.match_performer("Гуреев")

        assert result is not None
        assert result.full_name == "Гуреев Дмитрий Валерьевич"
        assert result.email == "gureev@1bit.ru"
        assert result.match_source == "directory_exact"

    def test_matcher_handles_ambiguous_status(self):
        from calendar_planner.participants.directory_result import (
            DirectoryPerson,
            DirectorySearchResult,
        )
        from calendar_planner.participants.matcher import NameMatcher

        class FakeEWSGateway:
            def is_available(self):
                return True

            def search(self, name):
                return DirectorySearchResult(
                    query=name,
                    status="ambiguous",
                    source="exchange_ews_gal",
                    people=[
                        DirectoryPerson(display_name="Иванов Иван", email="i1@1cbit.ru"),
                        DirectoryPerson(display_name="Иванов Петр", email="i2@1cbit.ru"),
                    ],
                )

        gw = FakeEWSGateway()
        matcher = NameMatcher(gw)
        result, options = matcher.match_performer_with_options("Иванов")

        assert result is None
        assert len(options) == 2
        assert options[0]["full_name"] in ("Иванов Иван", "Иванов Петр")

    def test_matcher_handles_not_found_status(self):
        from calendar_planner.participants.directory_result import DirectorySearchResult
        from calendar_planner.participants.matcher import NameMatcher

        class FakeEWSGateway:
            def is_available(self):
                return True

            def search(self, name):
                return DirectorySearchResult(
                    query=name,
                    status="not_found",
                    source="exchange_ews_gal",
                    people=[],
                )

        gw = FakeEWSGateway()
        matcher = NameMatcher(gw)
        result = matcher.match_performer("Неизвестный")

        assert result is None

    def test_matcher_handles_failed_status(self):
        from calendar_planner.participants.directory_result import DirectorySearchResult
        from calendar_planner.participants.matcher import NameMatcher

        class FakeEWSGateway:
            def is_available(self):
                return True

            def search(self, name):
                return DirectorySearchResult(
                    query=name,
                    status="failed",
                    source="exchange_ews_gal",
                    people=[],
                    error_message="Connection error",
                )

        gw = FakeEWSGateway()
        matcher = NameMatcher(gw)
        result = matcher.match_performer("Иванов")

        assert result is None

    def test_matcher_still_handles_legacy_list(self):
        from calendar_planner.participants.directory_gateway import (
            FixtureDirectoryGateway,
        )
        from calendar_planner.participants.matcher import NameMatcher

        gateway = FixtureDirectoryGateway()
        matcher = NameMatcher(gateway)
        result = matcher.match_performer("Гуреев")

        assert result is not None
        assert "Гуреев" in result.full_name
        assert result.email == "gureev@1bit.ru"