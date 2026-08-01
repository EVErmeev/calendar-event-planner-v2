from __future__ import annotations

import json
from pathlib import Path

from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime
from calendar_planner.domain.models import CalendarEvent


class FixtureCalendarGateway:
    def __init__(self, fixture_path: str | None = None):
        self._fixture_path = fixture_path
        self._events: list[CalendarEvent] = []
        if fixture_path:
            self._load_fixture(fixture_path)

    def _load_fixture(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for raw in data:
                    event = self._parse_from_fixture(raw)
                    if event:
                        self._events.append(event)
            elif isinstance(data, dict):
                for raw in data.get("events", []):
                    event = self._parse_from_fixture(raw)
                    if event:
                        self._events.append(event)

    def _parse_from_fixture(self, raw: dict) -> CalendarEvent | None:
        try:
            event_id = raw.get("id", "")
            ical_uid = raw.get("ical_uid")
            subject = raw.get("subject", "")
            start = parse_iso_datetime(raw["start"], raw.get("timezone")) if "start" in raw else None
            end = parse_iso_datetime(raw["end"], raw.get("timezone")) if "end" in raw else None
            return CalendarEvent(
                event_id=str(event_id),
                ical_uid=ical_uid,
                subject=subject,
                start=start,
                end=end,
                is_all_day=raw.get("is_all_day", False),
                location=raw.get("location"),
                online_url=raw.get("online_url"),
                attendees=raw.get("attendees", []),
                description=raw.get("description", ""),
                raw_data=raw,
            )
        except Exception:
            return None

    def is_available(self) -> bool:
        return True

    def check_connection(self) -> dict:
        return {
            "component": "Fixture Calendar",
            "status": "success",
            "message": f"Loaded {len(self._events)} fixture events",
        }

    def find_events(self, start_date: str, end_date: str) -> list[CalendarEvent]:
        if not self._events:
            return []
        return list(self._events)

    def create_event(self, payload: dict, dry_run: bool = True) -> dict:
        if dry_run:
            return {
                "status": "dry_run",
                "message": "DRY RUN: event would be created",
                "payload": payload,
            }
        return {
            "status": "created",
            "message": "Fixture: event recorded",
            "payload": payload,
            "event_id": "fixture-event-001",
        }