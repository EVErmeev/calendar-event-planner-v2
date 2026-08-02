from __future__ import annotations

from typing import Any

from calendar_planner.domain.models import FinalEventDraft
from calendar_planner.domain.validation import preflight_validate, validate_payload


class EventCreator:
    def __init__(self, gateway, dry_run: bool = True):
        self.gateway = gateway
        self.dry_run = dry_run
        self.creation_results: list[dict] = []

    def build_payload(self, draft: FinalEventDraft) -> dict:
        payload: dict[str, Any] = {
            "subject": draft.subject.value or "",
            "start": f"{draft.start_date.value} {draft.start_time.value}",
        }

        if draft.is_all_day:
            payload["start"] = draft.start_date.value
            payload["end"] = draft.start_date.value
            payload["is_all_day"] = True
        else:
            end_date, end_time = draft.compute_end_datetime()
            if end_date and end_time:
                payload["end"] = f"{end_date} {end_time}"
            payload["timeZone"] = draft.timezone.value or "UTC"

        if draft.location.value:
            payload["location"] = draft.location.value
        if draft.online_meeting_url.value:
            payload["online_meeting_url"] = draft.online_meeting_url.value

        attendees = []
        for att in draft.required_attendees:
            if att.email:
                attendees.append(att.email)
        for att in draft.optional_attendees:
            if att.email:
                attendees.append(att.email)
        if attendees:
            payload["attendees"] = ",".join(attendees)

        if draft.description.value:
            payload["body"] = draft.description.value
        if draft.online_meeting_url.value:
            payload["online_meeting_url"] = draft.online_meeting_url.value

        if draft.description.value:
            payload["body"] = draft.description.value

        return payload

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
        errors = validate_payload(payload)

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
        return validate_payload(payload)

    def validate_draft_before_create(self, draft: FinalEventDraft) -> list[dict]:
        result = preflight_validate(draft)
        draft.is_ready = result.ready
        return result.blocking_errors