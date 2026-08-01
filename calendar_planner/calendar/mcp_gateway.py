from __future__ import annotations

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from calendar_planner.domain.models import CalendarEvent
from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime


class MCPCalendarGateway:
    def __init__(self, mcp_call_function=None, server_url: str = "", find_tool: str = "list_events", create_tool: str = "create_event"):
        self._mcp_call = mcp_call_function
        self._server_url = server_url
        self._find_tool = find_tool
        self._create_tool = create_tool
        self._available: bool | None = None
        self._last_response_raw: list[dict] = []

    def is_available(self) -> bool:
        if self._mcp_call is not None:
            try:
                result = self._mcp_call(self._find_tool, {"start": "2000-01-01", "end": "2000-01-02"})
                self._available = True
            except Exception:
                self._available = False
        else:
            self._available = False
        return self._available

    def check_connection(self) -> dict:
        if not self._mcp_call:
            return {
                "component": "MCP Calendar",
                "status": "failed",
                "message": "MCP call function not provided",
            }
        try:
            self._available = self.is_available()
            return {
                "component": "MCP Calendar",
                "status": "success" if self._available else "failed",
                "message": "Connection OK" if self._available else "Cannot reach calendar",
            }
        except Exception as e:
            return {
                "component": "MCP Calendar",
                "status": "failed",
                "message": str(e),
            }

    def find_events(self, start_date: str, end_date: str) -> list[CalendarEvent]:
        if not self._mcp_call:
            return []

        raw_events = self._mcp_call(self._find_tool, {
            "start": start_date,
            "end": end_date,
        })

        self._last_response_raw = raw_events if isinstance(raw_events, list) else []

        events = []
        for raw in self._last_response_raw:
            event = self._parse_calendar_event(raw)
            if event:
                events.append(event)

        return events

    def create_event(self, payload: dict, dry_run: bool = True) -> dict:
        if not self._mcp_call:
            return {"status": "error", "message": "MCP not available"}

        if dry_run:
            return {
                "status": "dry_run",
                "message": "Event would be created (dry-run)",
                "payload": payload,
            }

        result = self._mcp_call(self._create_tool, payload)
        return {
            "status": "created",
            "message": "Event created",
            "result": result,
            "payload": payload,
        }

    def get_last_raw_response(self) -> list[dict]:
        return self._last_response_raw

    def _parse_calendar_event(self, raw: dict) -> CalendarEvent | None:
        try:
            event_id = raw.get("id") or raw.get("event_id") or raw.get("iCalUid") or ""
            ical_uid = raw.get("iCalUid") or raw.get("ical_uid")

            subject = raw.get("subject") or raw.get("title") or raw.get("summary") or ""

            start_raw = raw.get("start") or raw.get("startDateTime") or {}
            end_raw = raw.get("end") or raw.get("endDateTime") or {}

            start_str = None
            start_tz = None
            if isinstance(start_raw, dict):
                start_str = start_raw.get("dateTime") or start_raw.get("date_time")
                start_tz = start_raw.get("timeZone") or start_raw.get("timezone")
            elif isinstance(start_raw, str):
                start_str = start_raw

            end_str = None
            end_tz = None
            if isinstance(end_raw, dict):
                end_str = end_raw.get("dateTime") or end_raw.get("date_time")
                end_tz = end_raw.get("timeZone") or end_raw.get("timezone")
            elif isinstance(end_raw, str):
                end_str = end_raw

            start = None
            if start_str:
                try:
                    start = parse_iso_datetime(start_str, start_tz)
                except Exception:
                    pass

            end = None
            if end_str:
                try:
                    end = parse_iso_datetime(end_str, end_tz)
                except Exception:
                    pass

            attendees_list = raw.get("attendees", [])
            if isinstance(attendees_list, str):
                attendees_list = [{"email": e.strip()} for e in attendees_list.split(",") if e.strip()]

            description = raw.get("description") or raw.get("body") or raw.get("text") or ""

            return CalendarEvent(
                event_id=str(event_id),
                ical_uid=ical_uid,
                subject=subject,
                start=start,
                end=end,
                is_all_day=raw.get("isAllDay") or raw.get("is_all_day", False),
                location=raw.get("location") or raw.get("place"),
                online_url=raw.get("onlineUrl") or raw.get("online_meeting_url"),
                attendees=attendees_list,
                description=description,
                raw_data=raw,
            )
        except Exception:
            return None