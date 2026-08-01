from __future__ import annotations

import logging
from unittest import mock

from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

# ---------------------------------------------------------------------------
# _parse_calendar_event
# ---------------------------------------------------------------------------


class TestParseCalendarEvent:
    def test_summary_field_instead_of_subject(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-1",
            "summary": "Weekly sync",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.subject == "Weekly sync"

    def test_is_all_day_true(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-2",
            "subject": "Holiday",
            "start": "2025-06-01T00:00:00",
            "end": "2025-06-01T23:59:59",
            "isAllDay": True,
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.is_all_day is True

    def test_online_url_field(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-3",
            "subject": "Online meeting",
            "start": "2025-06-10T14:00:00",
            "end": "2025-06-10T15:00:00",
            "onlineUrl": "https://teams.microsoft.com/meeting/123",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.online_url == "https://teams.microsoft.com/meeting/123"

    def test_place_instead_of_location(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-4",
            "subject": "Onsite meeting",
            "start": "2025-06-10T09:00:00",
            "end": "2025-06-10T10:00:00",
            "place": "Conference Room A",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.location == "Conference Room A"

    def test_string_start_not_dict(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-5",
            "subject": "Plain start",
            "start": "2025-06-10T08:00:00",
            "end": "2025-06-10T09:00:00",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.start is not None
        assert event.start.raw_datetime == "2025-06-10T08:00:00"

    def test_description_as_plain_text(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-6",
            "subject": "With description",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
            "description": "Please prepare slides",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.description == "Please prepare slides"

    def test_comma_separated_attendees_string(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-7",
            "subject": "Group call",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
            "attendees": "alice@example.com, bob@example.com, charlie@example.com",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert len(event.attendees) == 3
        assert event.attendees[0] == {"email": "alice@example.com"}
        assert event.attendees[1] == {"email": "bob@example.com"}
        assert event.attendees[2] == {"email": "charlie@example.com"}

    def test_empty_dict(self):
        gw = MCPCalendarGateway()
        event = gw._parse_calendar_event({})
        assert event is not None
        assert event.event_id == ""
        assert event.subject == ""
        assert event.start is None
        assert event.end is None

    def test_only_id_field(self):
        gw = MCPCalendarGateway()
        raw = {"id": "sole-id"}
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.event_id == "sole-id"
        assert event.subject == ""
        assert event.start is None
        assert event.end is None

    def test_title_fallback_for_subject(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-title",
            "title": "Titled event",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.subject == "Titled event"

    def test_event_id_fields_priority(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "primary-id",
            "event_id": "secondary-id",
            "iCalUid": "ical-uid",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.event_id == "primary-id"
        assert event.ical_uid == "ical-uid"

    def test_ical_uid_direct(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-ical",
            "subject": "ICAL test",
            "iCalUid": "uid-abc-123",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.ical_uid == "uid-abc-123"

    def test_attendees_list_of_dicts(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-att",
            "subject": "With attendees",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
            "attendees": [
                {"email": "a@example.com", "name": "A"},
                {"email": "b@example.com", "name": "B"},
            ],
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert len(event.attendees) == 2
        assert event.attendees[0]["name"] == "A"

    def test_online_meeting_url_fallback(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-om",
            "subject": "Online fallback",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
            "online_meeting_url": "https://zoom.us/j/999",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.online_url == "https://zoom.us/j/999"

    def test_description_body_fallback(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-body",
            "subject": "Body desc",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
            "body": "Body content here",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.description == "Body content here"

    def test_is_all_day_from_alternative_key(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-ad",
            "subject": "All day alt",
            "start": "2025-06-01T00:00:00",
            "end": "2025-06-01T23:59:59",
            "is_all_day": True,
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.is_all_day is True

    def test_start_as_dict_with_date_time(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-start-dict",
            "subject": "Dict start",
            "start": {
                "dateTime": "2025-06-15T09:00:00",
                "timeZone": "Europe/Moscow",
            },
            "end": {
                "dateTime": "2025-06-15T10:00:00",
                "timeZone": "Europe/Moscow",
            },
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.start is not None
        assert event.start.raw_datetime == "2025-06-15T09:00:00"
        assert event.start.raw_timezone == "Europe/Moscow"

    def test_start_and_end_with_date_time_alternative_keys(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-alt-keys",
            "subject": "Alt keys",
            "start": {
                "date_time": "2025-06-15T10:00:00",
                "timezone": "UTC",
            },
            "end": {
                "date_time": "2025-06-15T11:30:00",
                "timezone": "UTC",
            },
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.start is not None
        assert event.start.raw_datetime == "2025-06-15T10:00:00"
        assert event.end is not None
        assert event.end.raw_datetime == "2025-06-15T11:30:00"

    def test_unparseable_start_datetime(self, caplog):
        caplog.set_level(logging.DEBUG)
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-bad",
            "subject": "Bad date",
            "start": "not-a-date-at-all",
            "end": "2025-06-10T11:00:00",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.start is None
        assert "Failed to parse start datetime" in caplog.text

    def test_malformed_raw_returns_none(self):
        gw = MCPCalendarGateway()
        result = gw._parse_calendar_event({"id": None})
        assert result is not None

    def test_comma_separated_attendees_with_spaces_and_trailing(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-cs",
            "subject": "Comma spaced",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
            "attendees": "  a@x.com , b@x.com ,,  c@x.com  ",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert len(event.attendees) == 3
        emails = [a["email"] for a in event.attendees]
        assert emails == ["a@x.com", "b@x.com", "c@x.com"]

    def test_raw_data_stored(self):
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-rd",
            "subject": "Raw data",
            "start": "2025-06-10T10:00:00",
            "end": "2025-06-10T11:00:00",
            "custom_field": "extra",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.raw_data == raw


# ---------------------------------------------------------------------------
# _normalize_response
# ---------------------------------------------------------------------------


class TestNormalizeResponse:
    def test_plain_list(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response([
            {"id": "1"}, {"id": "2"}, {"id": "3"},
        ])
        assert len(result) == 3
        assert result[0]["id"] == "1"

    def test_plain_list_filters_non_dicts(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response([
            {"id": "1"}, "garbage", {"id": "2"}, 42,
        ])
        assert len(result) == 2
        assert "dropped 2 non-dict items from list" in caplog.text

    def test_events_key(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "events": [{"id": "a"}, {"id": "b"}],
        })
        assert len(result) == 2
        assert result[0]["id"] == "a"

    def test_events_key_filters_non_dicts(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "events": [{"id": "a"}, "bad", {"id": "b"}, None],
        })
        assert len(result) == 2
        assert "dropped 2 non-dict items from 'events'" in caplog.text

    def test_events_key_not_a_list(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "events": "not-a-list",
        })
        assert result == []
        assert "'events' key is not a list" in caplog.text

    def test_result_key_plain_list(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "result": [{"id": "x"}, {"id": "y"}],
        })
        assert len(result) == 2
        assert result[0]["id"] == "x"

    def test_result_key_with_events_nested(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "result": {
                "events": [{"id": "n1"}, {"id": "n2"}],
            },
        })
        assert len(result) == 2
        assert result[0]["id"] == "n1"

    def test_result_key_with_items_nested(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "result": {
                "items": [{"id": "i1"}, {"id": "i2"}],
            },
        })
        assert len(result) == 2
        assert result[0]["id"] == "i1"

    def test_result_key_with_data_nested(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "result": {
                "data": [{"id": "d1"}, {"id": "d2"}],
            },
        })
        assert len(result) == 2
        assert result[0]["id"] == "d1"

    def test_json_string(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response(
            '[{"id": "j1"}, {"id": "j2"}]',
        )
        assert len(result) == 2
        assert result[0]["id"] == "j1"

    def test_json_string_with_events_key(self):
        gw = MCPCalendarGateway()
        result = gw._normalize_response(
            '{"events": [{"id": "je1"}, {"id": "je2"}]}',
        )
        assert len(result) == 2
        assert result[0]["id"] == "je1"

    def test_invalid_json_string(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response("not-valid-json{{{")
        assert result == []
        assert "non-JSON string" in caplog.text

    def test_unrecognized_dict_structure(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({"unknown_key": [1, 2, 3]})
        assert result == []
        assert "no recognized structure" in caplog.text

    def test_pagination_placeholders_warning(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({
            "nextPageToken": "xyz",
            "hasMore": True,
        })
        assert result == []
        assert "pagination placeholders" in caplog.text

    def test_unexpected_type(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response(42)
        assert result == []
        assert "unexpected response type" in caplog.text

    def test_none_input(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response(None)
        assert result == []
        assert "unexpected response type" in caplog.text


# ---------------------------------------------------------------------------
# get_last_raw_response
# ---------------------------------------------------------------------------


class TestGetLastRawResponse:
    def test_returns_stored_data_after_find_events(self):
        mock_call = mock.MagicMock(return_value=[
            {"id": "1", "start": "2025-06-10T10:00:00", "end": "2025-06-10T11:00:00"},
            {"id": "2", "start": "2025-06-11T10:00:00", "end": "2025-06-11T11:00:00"},
        ])
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        gw.find_events("2025-06-01", "2025-06-30")

        raw = gw.get_last_raw_response()
        assert len(raw) == 2
        assert raw[0]["id"] == "1"
        assert raw[1]["id"] == "2"

    def test_returns_empty_when_no_calls(self):
        gw = MCPCalendarGateway()
        raw = gw.get_last_raw_response()
        assert raw == []


# ---------------------------------------------------------------------------
# find_events with mock mcp_call
# ---------------------------------------------------------------------------


class TestFindEvents:
    def test_find_events_with_mock_mcp_call(self):
        raw_events = [
            {
                "id": "evt-1",
                "subject": "Meeting A",
                "start": "2025-06-10T10:00:00",
                "end": "2025-06-10T11:00:00",
            },
            {
                "id": "evt-2",
                "subject": "Meeting B",
                "start": "2025-06-11T14:00:00",
                "end": "2025-06-11T15:00:00",
            },
        ]
        mock_call = mock.MagicMock(return_value=raw_events)
        gw = MCPCalendarGateway(
            mcp_call_function=mock_call,
            find_tool="list_events",
        )

        events = gw.find_events("2025-06-01", "2025-06-30")
        assert len(events) == 2
        assert events[0].subject == "Meeting A"
        assert events[1].subject == "Meeting B"

        mock_call.assert_called_once_with("list_events", {
            "days_back": mock.ANY,
            "days_ahead": mock.ANY,
        })

    def test_find_events_returns_empty_when_no_mcp_call(self, caplog):
        gw = MCPCalendarGateway()
        events = gw.find_events("2025-01-01", "2025-01-31")
        assert events == []
        assert "MCP call function not available" in caplog.text

    def test_find_events_normalizes_json_string_response(self):
        json_str = '[{"id": "js1", "subject": "JSON", "start": "2025-06-10T10:00:00", "end": "2025-06-10T11:00:00"}]'
        mock_call = mock.MagicMock(return_value=json_str)
        gw = MCPCalendarGateway(mcp_call_function=mock_call)

        events = gw.find_events("2025-06-01", "2025-06-30")
        assert len(events) == 1
        assert events[0].subject == "JSON"

    def test_find_events_normalizes_events_key_response(self):
        mock_call = mock.MagicMock(return_value={
            "events": [
                {"id": "ek1", "subject": "InEvents", "start": "2025-06-10T10:00:00", "end": "2025-06-10T11:00:00"},
            ],
        })
        gw = MCPCalendarGateway(mcp_call_function=mock_call)

        events = gw.find_events("2025-06-01", "2025-06-30")
        assert len(events) == 1
        assert events[0].subject == "InEvents"

    def test_find_events_skips_unparseable_events(self):
        mock_call = mock.MagicMock(return_value=[
            {},
            {"id": "ok", "subject": "OK", "start": "2025-06-10T10:00:00", "end": "2025-06-10T11:00:00"},
        ])
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        events = gw.find_events("2025-06-01", "2025-06-30")
        assert len(events) == 2

    def test_find_events_empty_normalize_logs_warning(self, caplog):
        mock_call = mock.MagicMock(return_value={"unknown": []})
        gw = MCPCalendarGateway(mcp_call_function=mock_call)

        events = gw.find_events("2025-06-01", "2025-06-30")
        assert events == []
        assert "_normalize_response returned empty list" in caplog.text


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    def test_sets_available_true_on_success(self):
        mock_call = mock.MagicMock()
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        assert gw.is_available() is True
        assert gw._available is True

    def test_sets_available_false_on_exception(self):
        mock_call = mock.MagicMock(side_effect=RuntimeError("boom"))
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        assert gw.is_available() is False
        assert gw._available is False

    def test_false_when_no_mcp_call(self):
        gw = MCPCalendarGateway()
        assert gw.is_available() is False

    def test_caches_result_on_second_call(self):
        mock_call = mock.MagicMock()
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        assert gw.is_available() is True
        assert gw._available is True
        call_count = mock_call.call_count
        assert gw.is_available() is True
        assert mock_call.call_count == call_count + 1


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------


class TestCheckConnection:
    def test_no_mcp_call_returns_failed(self):
        gw = MCPCalendarGateway()
        result = gw.check_connection()
        assert result["component"] == "MCP Calendar"
        assert result["status"] == "failed"
        assert "MCP call function not provided" in result["message"]

    def test_successful_connection(self):
        mock_call = mock.MagicMock()
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        result = gw.check_connection()
        assert result["status"] == "success"
        assert result["message"] == "Connection OK"

    def test_failed_connection(self):
        mock_call = mock.MagicMock(side_effect=RuntimeError("down"))
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        result = gw.check_connection()
        assert result["status"] == "failed"
        assert "Cannot reach calendar" in result["message"]


# ---------------------------------------------------------------------------
# create_event
# ---------------------------------------------------------------------------


class TestCreateEvent:
    def test_create_event_dry_run(self):
        mock_call = mock.MagicMock()
        gw = MCPCalendarGateway(mcp_call_function=mock_call)
        payload = {"subject": "Test", "start": "2025-06-10T10:00:00"}
        result = gw.create_event(payload, dry_run=True)
        assert result["status"] == "dry_run"
        assert result["payload"] == payload

    def test_create_event_no_mcp_call(self):
        gw = MCPCalendarGateway()
        result = gw.create_event({}, dry_run=False)
        assert result["status"] == "error"
        assert result["message"] == "MCP not available"

    def test_create_event_real_call(self):
        mock_call = mock.MagicMock(return_value={"id": "new-evt"})
        gw = MCPCalendarGateway(mcp_call_function=mock_call, create_tool="create_event")
        payload = {"subject": "Real"}
        result = gw.create_event(payload, dry_run=False)
        assert result["status"] == "created"
        assert result["result"] == {"id": "new-evt"}
        mock_call.assert_called_once_with("create_event", payload)


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_normalize_response_result_with_string_value(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({"result": "just-a-string"})
        assert result == []
        assert "unexpected structure" in caplog.text

    def test_unparseable_end_datetime(self, caplog):
        caplog.set_level(logging.DEBUG)
        gw = MCPCalendarGateway()
        raw = {
            "id": "evt-bad-end",
            "subject": "Bad end",
            "start": "2025-06-10T10:00:00",
            "end": "garbage-date",
        }
        event = gw._parse_calendar_event(raw)
        assert event is not None
        assert event.end is None
        assert "Failed to parse end datetime" in caplog.text

    def test_normalize_response_result_key_with_non_dict_list(self, caplog):
        gw = MCPCalendarGateway()
        result = gw._normalize_response({"result": 12345})
        assert result == []
        assert "unexpected structure" in caplog.text