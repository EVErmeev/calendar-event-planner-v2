"""v1.0.2 — Fixed positional schema profile (A:K) and creation diagnostics tests.

Covers:
  - fixed profile uraldrone_meeting_v1 (A:K, D always hours);
  - duration 2/3/4/1,5 -> 120/180/240/90 propagated to extract -> draft -> payload;
  - profile selected by google sheet id / sheet name, overrides headers;
  - CreationAttemptResult statuses + sanitize + JSONL + append-only;
  - create_event normalized keys (event_id / url / technical_message);
  - payload validation (duration / attendees);
  - 0 real create_event calls in profile/creation flows.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from calendar_planner.domain.enums import MeetingDatePolicy
from calendar_planner.domain.models import ExtractedSource, SourceReference
from calendar_planner.source.schema_profile import (
    URALDRONE_GOOGLE_SHEET_ID,
    URALDRONE_MEETING_V1,
)

SHEET_ID = URALDRONE_GOOGLE_SHEET_ID


def _aok_sheet():
    return [
        ["№", "Тема", "Заказчик", "Длительность, ч", "Исполнитель", "Согласованная дата", "Согласованное время"],
        ["1", "Строка служебная", "", "", "", "", ""],
        ["2", "Обзор проекта", "Заказчик 1", "2", "Исп1", "05.08.2026", "19:00"],
        ["3", "Синк 3 часа", "Заказчик 2", "3", "Исп2", "05.08.2026", "12:00"],
        ["4", "Демо 4 часа", "Заказчик 3", "4", "Исп3", "05.08.2026", "09:00"],
        ["5", "Полтора часа", "Заказчик 4", "1,5", "Исп4", "05.08.2026", "10:00"],
    ]


def _extract(sheet=None, sheet_id=SHEET_ID, sheet_name="24.07.26 - 05.08.26"):
    if sheet is None:
        sheet = _aok_sheet()
    from calendar_planner.extraction.structured import StructuredExtractor
    src = ExtractedSource(
        source=SourceReference(type="memory"),
        sheets={sheet_name: sheet},
        metadata={"google_sheet_id": sheet_id},
    )
    ex = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY, numeric_duration_unit="auto")
    res = ex.extract(src)
    return ex, res.get(sheet_name, [])


class TestProfileResolution:
    def test_resolve_by_sheet_id(self):
        from calendar_planner.source.schema_profile import resolve_schema_profile
        p = resolve_schema_profile(SHEET_ID, None)
        assert p is not None
        assert p.profile_id == "uraldrone_meeting_v1"

    def test_resolve_by_name(self):
        from calendar_planner.source.schema_profile import resolve_schema_profile
        p = resolve_schema_profile(None, "24.07.26 - 05.08.26")
        assert p is not None
        assert p.profile_id == "uraldrone_meeting_v1"

    def test_resolve_none_by_no_match(self):
        from calendar_planner.source.schema_profile import resolve_schema_profile
        assert resolve_schema_profile("other-id", "x") is None

    def test_layout(self):
        p = URALDRONE_MEETING_V1
        assert p.column("subject") == 1
        assert p.column("duration") == 3
        assert p.column("agreed_date") == 5
        assert p.column("agreed_time") == 6
        assert p.duration == "hours"


class TestDurationProfile:
    def test_profile_used_and_durations(self):
        ex, cands = _extract()
        assert ex.used_profile is not None
        by = {c.subject: c for c in cands}
        assert by["Обзор проекта"].duration_minutes == 120
        assert by["Синк 3 часа"].duration_minutes == 180
        assert by["Демо 4 часа"].duration_minutes == 240
        assert by["Полтора часа"].duration_minutes == 90

    def test_service_row_skipped(self):
        _, cands = _extract()
        assert all(c.subject != "Строка служебная" for c in cands)

    def test_duration_evidence(self):
        _, cands = _extract()
        c = next(x for x in cands if x.subject == "Обзор проекта")
        d = next(e for e in c.evidence if e.get("field") == "duration")
        assert d["raw"] == "2"
        assert d["unit"] == "hours"
        assert d["unit_source"] == "profile"
        assert d["minutes"] == 120

    def test_header_without_unit_still_hours_via_profile(self):
        sheet = [
            ["№", "Тема", "Заказчик", "Длительнось", "Исполнитель", "Согл. дата", "Согл. время"],
            ["2", "Встреча", "З", "5", "Исп", "05.08.2026", "11:00"],
        ]
        _, cands = _extract(sheet=sheet)
        assert cands[0].duration_minutes == 300

    def test_no_profile_keeps_auto_duration(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        src = ExtractedSource(source=SourceReference(type="memory"), sheets={"x": _aok_sheet()})
        ex = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY, numeric_duration_unit="auto")
        res = ex.extract(src)
        assert ex.used_profile is None


class TestParticipantHeaderColumns:
    """Profile must NOT override performer/customer columns — keep header detection."""

    def _extract_participant_sheet(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        sheet = [
            ["№", "Тема", "Заказчик", "Длительность, ч", "Исполнитель", "Согласованная дата", "Согласованное время"],
            ["1", "Обзор проекта", "Заказчик1", "2", "Исп1", "05.08.2026", "19:00"],
            ["2", "Синк планов", "Заказчик2", "1,5", "Исп2", "05.08.2026", "12:00"],
        ]
        src = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={"24.07.26 - 05.08.26": sheet},
            metadata={"google_sheet_id": SHEET_ID},
        )
        ex = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY, numeric_duration_unit="auto")
        res = ex.extract(src)
        return ex, res.get("24.07.26 - 05.08.26", [])

    def test_performer_customer_from_header_when_profile_applied(self):
        ex, cands = self._extract_participant_sheet()
        assert ex.used_profile is not None
        by = {c.subject: c for c in cands}
        # subject/duration come from the profile; performer/customer from header columns
        assert by["Обзор проекта"].performer_names == ["Исп1"]
        assert by["Обзор проекта"].customer_names == ["Заказчик1"]
        assert by["Синк планов"].performer_names == ["Исп2"]

    def test_duration_still_from_profile(self):
        _, cands = self._extract_participant_sheet()
        by = {c.subject: c for c in cands}
        assert by["Обзор проекта"].duration_minutes == 120
        assert by["Синк планов"].duration_minutes == 90


class TestDraftPropagation:
    def test_end_datetime_from_duration(self):
        from calendar_planner.drafts.builder import DraftBuilder
        _, cands = _extract()
        cand = next(x for x in cands if x.subject == "Обзор проекта")
        draft = DraftBuilder().build_from_candidate(cand)
        assert draft.duration_minutes.value == 120
        assert draft.duration_confirmed is True
        assert draft.end_time.value == "21:00"
        assert draft.end_date.value == "2026-08-05"

    def test_payload_duration_and_range(self):
        from calendar_planner.calendar.creator import EventCreator
        from calendar_planner.drafts.builder import DraftBuilder
        _, cands = _extract()
        cand = next(x for x in cands if x.subject == "Обзор проекта")
        draft = DraftBuilder().build_from_candidate(cand)
        payload = EventCreator(None).build_payload(draft)
        assert payload["duration_minutes"] == 120
        assert payload["start"]["dateTime"] == "2026-08-05T19:00:00"
        assert payload["end"]["dateTime"] == "2026-08-05T21:00:00"


class TestCreationAttempt:
    def test_build_and_log_jsonl(self):
        from calendar_planner.app.creation_attempt import CreationLogger, build_attempt
        with tempfile.TemporaryDirectory() as tmp:
            logger = CreationLogger(base_dir=Path(tmp))
            att = build_attempt("DRF-1", "server_rejected", subject="x",
                                error_code="CREATE_REJECTED", message="bad",
                                payload={"subject": "x"})
            aid = logger.record(att)
            assert logger.path().read_text(encoding="utf-8").splitlines().__len__() == 1
            loaded = logger.load()
            assert loaded[0].status == "server_rejected"
            assert loaded[0].attempt_id == aid
            assert loaded[0].session_id == logger.session_id

    def test_append_does_not_overwrite(self):
        from calendar_planner.app.creation_attempt import CreationLogger, build_attempt
        with tempfile.TemporaryDirectory() as tmp:
            logger = CreationLogger(base_dir=Path(tmp))
            logger.record(build_attempt("DRF-1", "dry_run"))
            logger.record(build_attempt("DRF-1", "server_rejected"))
            assert len(logger.load()) == 2

    def test_sanitize_secrets(self):
        from calendar_planner.app.creation_attempt import sanitize_value
        out = sanitize_value({
            "password": "s3cret",
            "Authorization": "Bearer x",
            "payload": {"nested_token": "abc", "ok": 1},
        })
        assert out["password"] == "[REDACTED]"
        assert out["Authorization"] == "[REDACTED]"
        assert out["payload"]["nested_token"] == "[REDACTED]"
        assert out["payload"]["ok"] == 1

    def test_sanitized_written_to_disk(self):
        from calendar_planner.app.creation_attempt import CreationLogger, build_attempt
        with tempfile.TemporaryDirectory() as tmp:
            logger = CreationLogger(base_dir=Path(tmp))
            logger.record(build_attempt("DRF", "dry_run", payload={"password": "hunter2", "ok": 1}))
            text = logger.path().read_text(encoding="utf-8")
            assert "hunter2" not in text

    def test_status_mapping(self):
        from calendar_planner.app.creation_attempt import class_create_status
        assert class_create_status("created", None) == "created_unverified"
        assert class_create_status("failed", "UNKNOWN_RESPONSE") == "unknown_response"
        assert class_create_status("failed", "CREATE_REJECTED") == "server_rejected"
        assert class_create_status("invalid", None) == "validation_failed"
        assert class_create_status("dry_run", None) == "dry_run"
        assert class_create_status("error", None) == "transport_failed"


class TestGatewayNormalization:
    def _gw(self, result):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway
        def call(tool, args):
            return result
        return MCPCalendarGateway(mcp_call_function=call, create_tool="create_event")

    def test_created_dict_event_id_url(self):
        r = self._gw({"id": "evt-9", "htmlLink": "https://ex/9"}).create_event({}, dry_run=False)
        assert r["status"] == "created"
        assert r["event_id"] == "evt-9"
        assert r["url"] == "https://ex/9"

    def test_created_text_extracts_url(self):
        r = self._gw("Событие создано https://outlook/evt/42").create_event({}, dry_run=False)
        assert r["status"] == "created"
        assert r["url"] == "https://outlook/evt/42"

    def test_rejected_technical_message(self):
        r = self._gw("Ошибка: не удалось создать").create_event({}, dry_run=False)
        assert r["status"] == "failed"
        assert r["error"] == "CREATE_REJECTED"
        assert "не удалось создать" in r["technical_message"]


class TestPayloadValidation:
    def test_valid(self):
        from calendar_planner.domain.validation import validate_creation_payload
        ok = {
            "subject": "s",
            "start": {"dateTime": "2026-08-05T19:00:00"},
            "end": {"dateTime": "2026-08-05T21:00:00"},
            "duration_minutes": 120,
            "attendees": [{"emailAddress": {"address": "a@b.ru"}}],
        }
        assert validate_creation_payload(ok) == []

    def test_missing_attendee_email(self):
        from calendar_planner.domain.validation import validate_creation_payload
        bad = {
            "subject": "s",
            "start": {"dateTime": "2026-08-05T19:00:00"},
            "end": {"dateTime": "2026-08-05T21:00:00"},
            "attendees": [{"emailAddress": {"address": ""}}],
        }
        assert any("missing email" in e for e in validate_creation_payload(bad))

    def test_non_positive_duration(self):
        from calendar_planner.domain.validation import validate_creation_payload
        bad = {
            "subject": "s",
            "start": {"dateTime": "2026-08-05T19:00:00"},
            "end": {"dateTime": "2026-08-05T19:30:00"},
            "duration_minutes": 0,
        }
        assert any("positive" in e for e in validate_creation_payload(bad))


class FakeStdioTransport:
    def __init__(self, command: str):
        self.command = command
        self.tools = []
        self._connected = False

    def connect(self):
        self._connected = True
        self.tools = [{"name": "find_events"}, {"name": "create_event"}]
        return {"status": "success"}

    def is_connected(self):
        return self._connected

    def list_tools(self):
        return [t["name"] for t in self.tools]

    def call_tool(self, name, arguments):
        if name == "find_events":
            return {"events": []}
        return {"ok": True}

    def check_connection(self):
        return {"status": "ok"}

    def close(self):
        self._connected = False


class TestZeroRealCreate:
    def test_profile_flow_no_create_calls(self, monkeypatch):
        import calendar_planner.app.container as cmod
        calls = []

        class Tracking(FakeStdioTransport):
            def call_tool(self, name, arguments):
                calls.append(name)
                return super().call_tool(name, arguments)

        monkeypatch.setattr(cmod, "StdioMCPTransport", Tracking)
        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings
        c = AppContainer(Settings())
        c.configure_mcp_stdio("powershell -File C:\\x.ps1", "find_events", "create_event", persist=False)
        ex, _ = _extract()
        assert ex.used_profile is not None
        assert "create_event" not in calls