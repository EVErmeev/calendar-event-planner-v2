from __future__ import annotations

from typing import Any

from calendar_planner.domain.models import FinalEventDraft
from calendar_planner.domain.validation import (
    preflight_validate,
    validate_creation_payload,
)


class EventCreator:
    def __init__(self, gateway, dry_run: bool = True):
        self.gateway = gateway
        self.dry_run = dry_run
        self.creation_results: list[dict] = []

    def build_payload(self, draft: FinalEventDraft) -> dict:
        payload: dict[str, Any] = {
            "subject": draft.subject.value or "",
            "start": {
                "dateTime": f"{draft.start_date.value}T{draft.start_time.value}:00",
                "timeZone": draft.timezone.value or "UTC",
            },
            "duration_minutes": draft.duration_minutes.value,
        }

        if draft.is_all_day:
            payload["start"] = {"date": draft.start_date.value, "timeZone": draft.timezone.value or "UTC"}
            payload["end"] = {"date": draft.start_date.value, "timeZone": draft.timezone.value or "UTC"}
            payload["is_all_day"] = True
        else:
            end_date, end_time = draft.compute_end_datetime()
            if end_date and end_time:
                payload["end"] = {
                    "dateTime": f"{end_date}T{end_time}:00",
                    "timeZone": draft.timezone.value or "UTC",
                }

        attendees = []
        for att in draft.required_attendees:
            if att.email:
                attendees.append({"emailAddress": {"address": att.email, "name": att.full_name}, "type": "required"})
        for att in draft.optional_attendees:
            if att.email:
                attendees.append({"emailAddress": {"address": att.email, "name": att.full_name}, "type": "optional"})
        if attendees:
            payload["attendees"] = attendees

        if draft.location.value:
            payload["location"] = {"displayName": draft.location.value}
        if draft.online_meeting_url.value:
            payload["onlineMeetingUrl"] = draft.online_meeting_url.value
        if draft.description.value:
            payload["body"] = {"contentType": "text", "content": draft.description.value}

        return payload

    @staticmethod
    def adapt_for_mcp(payload: dict) -> dict:
        """Convert canonical payload to Exchange MCP flat format."""
        mcp = {"subject": payload.get("subject", "")}
        start = payload.get("start", {})
        if isinstance(start, dict):
            dt = start.get("dateTime", "")
            if dt:
                mcp["start"] = dt.replace("T", " ")[:16]
        end = payload.get("end", {})
        if isinstance(end, dict):
            dt = end.get("dateTime", "")
            if dt:
                mcp["end"] = dt.replace("T", " ")[:16]
        atts = payload.get("attendees", [])
        if atts:
            emails = [a.get("emailAddress", {}).get("address", "") for a in atts if isinstance(a, dict)]
            mcp["attendees"] = ",".join(filter(None, emails))
        loc = payload.get("location", {})
        if isinstance(loc, dict) and loc.get("displayName"):
            mcp["location"] = loc["displayName"]
        body = payload.get("body", {})
        if isinstance(body, dict) and body.get("content"):
            mcp["body"] = body["content"]
        return mcp

    def create_one(self, draft: FinalEventDraft) -> dict:
        draft_errors = self.validate_draft_before_create(draft)
        if draft_errors:
            result = {
                "status": "invalid",
                "draft_id": draft.draft_id,
                "errors": draft_errors,
            }
            self.creation_results.append(result)
            return result

        payload = self.build_payload(draft)
        errors = validate_creation_payload(payload)

        if errors:
            result = {
                "status": "invalid",
                "draft_id": draft.draft_id,
                "errors": errors,
                "payload": payload,
            }
            self.creation_results.append(result)
            return result

        result = self._create(payload)
        result["draft_id"] = draft.draft_id
        self.creation_results.append(result)
        return result

    def create_selected(self, drafts: list[FinalEventDraft]) -> list[dict]:
        results = []
        for draft in drafts:
            if draft.selected and draft.is_ready:
                results.append(self.create_one(draft))
        return results

    def _create(self, payload: dict) -> dict:
        return self.gateway.create_event(payload, dry_run=self.dry_run)

    def get_all_results(self) -> list[dict]:
        return self.creation_results

    def validate_payload(self, payload: dict) -> list[str]:
        return validate_creation_payload(payload)

    def validate_draft_before_create(self, draft: FinalEventDraft) -> list[dict]:
        result = preflight_validate(draft)
        draft.is_ready = result.ready
        return result.blocking_errors