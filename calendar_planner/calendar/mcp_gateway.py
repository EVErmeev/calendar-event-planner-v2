from __future__ import annotations

import json
import logging
import re

from calendar_planner.app.settings import settings
from calendar_planner.calendar.datetime_normalizer import parse_iso_datetime
from calendar_planner.domain.models import CalendarEvent

_logger = logging.getLogger(__name__)


class MCPCalendarGateway:
    def __init__(self, mcp_call_function=None, server_url: str = "", find_tool: str = "list_events", create_tool: str = "create_event"):
        self._mcp_call = mcp_call_function
        self._server_url = server_url
        self._find_tool = find_tool
        self._create_tool = create_tool
        self._available: bool | None = None
        self._last_response_raw: list[dict] = []
        self._tz_naive_count: int = 0

    def _health_probe_params(self) -> dict:
        tool_lower = self._find_tool.lower()
        if "exchange" in tool_lower or "find_events" in tool_lower:
            return {"days_back": 1, "days_ahead": 1}
        return {"start": "2000-01-01", "end": "2000-01-02"}

    def is_available(self) -> bool:
        if self._mcp_call is not None:
            try:
                self._mcp_call(self._find_tool, self._health_probe_params())
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
            self._tz_naive_count = 0

            # Do a real calendar read to count events and detect tz issues
            events = self.find_events("2026-07-26", "2026-09-01")
            parsed = len(events)
            naive = sum(1 for e in events if e.start and not e.start.raw_timezone)

            result = {
                "component": "MCP Calendar",
                "status": "success" if self._available else "failed",
                "message": f"{parsed} events received, {parsed} parsed" if parsed else "Connection OK",
                "event_count": parsed,
                "timezone_warnings": naive,
            }
            if naive > 0:
                result["status"] = "success"  # Don't fail, just warn
            return result
        except Exception as e:
            return {
                "component": "MCP Calendar",
                "status": "failed",
                "message": str(e),
            }

    def find_events(self, start_date: str, end_date: str) -> list[CalendarEvent]:
        if not self._mcp_call:
            _logger.warning("find_events: MCP call function not available — returning empty list")
            return []

        from datetime import date as date_type
        from datetime import datetime as dt_type
        today = date_type.today()
        start_dt = dt_type.strptime(start_date, "%Y-%m-%d").date()
        end_dt = dt_type.strptime(end_date, "%Y-%m-%d").date()

        delta_back = (today - start_dt).days
        delta_ahead = (end_dt - today).days

        raw_result = self._mcp_call(self._find_tool, {
            "days_back": max(0, delta_back),
            "days_ahead": max(1, delta_ahead),
        })

        # Normalize BEFORE parsing — call exactly once, use result throughout
        raw_events = self._normalize_response(raw_result)
        self._last_response_raw = raw_events

        if not raw_events:
            _logger.warning(
                "find_events: _normalize_response returned empty list for range %s–%s",
                start_date, end_date,
            )

        events = []
        for raw in raw_events:
            event = self._parse_calendar_event(raw)
            if event:
                events.append(event)

        return events

    def _normalize_response(self, raw_result) -> list[dict]:
        if isinstance(raw_result, list):
            filtered = [r for r in raw_result if isinstance(r, dict)]
            if len(filtered) < len(raw_result):
                _logger.warning(
                    "_normalize_response: dropped %d non-dict items from list",
                    len(raw_result) - len(filtered),
                )
            return filtered

        if isinstance(raw_result, dict):
            if "events" in raw_result:
                events = raw_result["events"]
                if isinstance(events, list):
                    filtered = [r for r in events if isinstance(r, dict)]
                    if len(filtered) < len(events):
                        _logger.warning(
                            "_normalize_response: dropped %d non-dict items from 'events'",
                            len(events) - len(filtered),
                        )
                    return filtered
                _logger.warning(
                    "_normalize_response: 'events' key is not a list (type=%s); "
                    "response keys=%s",
                    type(events).__name__, list(raw_result.keys()),
                )
            if "result" in raw_result:
                result = raw_result["result"]
                if isinstance(result, list):
                    filtered = [r for r in result if isinstance(r, dict)]
                    if len(filtered) < len(result):
                        _logger.warning(
                            "_normalize_response: dropped %d non-dict items from 'result'",
                            len(result) - len(filtered),
                        )
                    return filtered
                if isinstance(result, dict):
                    for key in ("events", "items", "data"):
                        if key in result and isinstance(result[key], list):
                            filtered = [r for r in result[key] if isinstance(r, dict)]
                            return filtered
                _logger.warning(
                    "_normalize_response: 'result' key has unexpected structure (type=%s); "
                    "response keys=%s",
                    type(result).__name__,
                    list(result.keys()) if isinstance(result, dict) else "N/A",
                )
            if any(k in raw_result for k in ("nextPageToken", "hasMore", "pagination")):
                _logger.warning(
                    "_normalize_response: response contains pagination placeholders "
                    "— possible incomplete result"
                )
            _logger.warning(
                "_normalize_response: dict response has no recognized structure; "
                "keys=%s",
                list(raw_result.keys()),
            )
            return []

        if isinstance(raw_result, str):
            try:
                parsed = json.loads(raw_result)
                return self._normalize_response(parsed)
            except json.JSONDecodeError:
                # Try to parse as Exchange MCP text response (Markdown format)
                text_events = self._parse_text_response(raw_result)
                if text_events:
                    _logger.info(
                        "_normalize_response: parsed %d events from text response",
                        len(text_events),
                    )
                    return text_events
                _logger.warning(
                    "_normalize_response: response is a non-JSON string: %s",
                    raw_result[:200],
                )
                return []

        _logger.warning(
            "_normalize_response: unexpected response type %s; value=%r",
            type(raw_result).__name__, raw_result,
        )
        return []

    def create_event(self, payload: dict, dry_run: bool = True) -> dict:
        if not self._mcp_call:
            return {"status": "error", "message": "MCP not available"}

        if dry_run:
            return {
                "status": "dry_run",
                "message": "Event would be created (dry-run)",
                "payload": payload,
            }

        from calendar_planner.calendar.creator import EventCreator
        mcp_payload = EventCreator.adapt_for_mcp(payload)
        result = self._mcp_call(self._create_tool, mcp_payload)
        return self._interpret_create_result(result, payload)

    @staticmethod
    def _success_markers() -> tuple[str, ...]:
        return (
            "событие создано", "создано успешно", "встреча создана",
            "created", "event created", "запись создана", "saved",
        )

    @staticmethod
    def _failure_markers() -> tuple[str, ...]:
        return (
            "ошибк", "не удалось", "не смог", "failed", "error",
            "отказано", "forbidden", "rejected", "нельзя", "недоступн",
        )

    def _interpret_create_result(self, result, payload: dict) -> dict:
        """Report the real outcome instead of assuming success.

        The Exchange MCP returns human-readable text; only a dict carrying an
        event id, or text signalling success, counts as created. Anything that
        looks like an error is surfaced as ``failed`` with the server message.
        """
        if isinstance(result, dict):
            if result.get("id") or result.get("event_id") or result.get("iCalUid"):
                return {
                    "status": "created",
                    "message": "Event created",
                    "result": result,
                    "payload": payload,
                    "event_id": result.get("id") or result.get("event_id") or result.get("iCalUid"),
                    "url": result.get("htmlLink") or result.get("url") or "",
                }
            text = str(result)
        else:
            text = str(result)

        low = text.lower()
        if any(m in low for m in self._success_markers()):
            return {
                "status": "created",
                "message": text.splitlines()[0] if text.strip() else "Event created",
                "result": result,
                "payload": payload,
                "url": self._extract_url(text),
            }
        if any(m in low for m in self._failure_markers()):
            return {
                "status": "failed",
                "error": "CREATE_REJECTED",
                "message": text.strip()[:300] or "Event creation rejected by server",
                "technical_message": text.strip()[:2000],
                "result": result,
                "payload": payload,
            }
        # Unknown response — do not claim success.
        return {
            "status": "failed",
            "error": "UNKNOWN_RESPONSE",
            "message": "Не удалось подтвердить создание события. Ответ сервера: "
                       + (text[:200] if text.strip() else "<пусто>"),
            "technical_message": text.strip()[:2000],
            "result": result,
            "payload": payload,
        }

    @staticmethod
    def _extract_url(text: str) -> str:
        m = re.search(r"https?://\S+", text)
        return m.group(0) if m else ""

    def get_last_raw_response(self) -> list[dict]:
        return self._last_response_raw

    def _parse_text_response(self, text: str) -> list[dict]:
        events = []
        current_date = None
        date_re = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})")
        event_re = re.compile(r"^\d+\.\s*\[(\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2})\]\s*(.+)")
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            dm = date_re.match(line)
            if dm:
                current_date = dm.group(1)
                continue
            if current_date is None:
                continue
            em = event_re.match(line)
            if em:
                st = em.group(1)
                et = em.group(2)
                rest = em.group(3).strip()
                url_match = re.search(r"\((https?://[^)]+)\)", rest)
                online_url = url_match.group(1) if url_match else None
                if url_match:
                    rest = rest[:url_match.start()].strip()
                attendees = [{"email": e} for e in re.findall(r"([\w.+-]+@[\w.-]+)", rest)]
                for e in re.findall(r"([\w.+-]+@[\w.-]+)", rest):
                    rest = rest.replace(e, "").strip()
                subject = re.sub(r"\s*[-–]\s*$", "", rest).strip()
                events.append({
                    "id": f"ex-{current_date}-{len(events) + 1}",
                    "subject": subject[:200],
                    "start": f"{current_date}T{st}:00",
                    "end": f"{current_date}T{et}:00",
                    "online_url": online_url,
                    "attendees": attendees,
                })
        return events

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
                    fallback_tz = settings.CALENDAR_MISSING_TIMEZONE
                    if not start_tz:
                        self._tz_naive_count += 1
                    start = parse_iso_datetime(start_str, start_tz, fallback_tz=fallback_tz)
                except Exception:
                    _logger.debug("Failed to parse start datetime: %s", start_str)

            end = None
            if end_str:
                try:
                    fallback_tz = settings.CALENDAR_MISSING_TIMEZONE
                    end = parse_iso_datetime(end_str, end_tz, fallback_tz=fallback_tz)
                except Exception:
                    _logger.debug("Failed to parse end datetime: %s", end_str)

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
            _logger.warning("_parse_calendar_event: failed to parse event dict", exc_info=True)
            return None