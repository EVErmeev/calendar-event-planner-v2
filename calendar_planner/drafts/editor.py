from __future__ import annotations

from datetime import timedelta

from calendar_planner.domain.models import FinalEventDraft, DraftField, ResolvedParticipant
from calendar_planner.domain.enums import DraftFieldOrigin, ParticipantRole


class DraftEditor:
    def __init__(self):
        self.changes: list[dict] = []

    def edit_subject(self, draft: FinalEventDraft, new_value: str) -> None:
        self._update_field(draft, draft.subject, new_value, "subject")
        self._log_change(draft, "subject", draft.subject.value, new_value)

    def edit_date(self, draft: FinalEventDraft, new_value: str) -> None:
        self._update_field(draft, draft.start_date, new_value, "start_date")
        draft.match_status = "stale"
        self._log_change(draft, "start_date", draft.start_date.value, new_value)

    def edit_time(self, draft: FinalEventDraft, new_value: str) -> None:
        self._update_field(draft, draft.start_time, new_value, "start_time")
        draft.match_status = "stale"
        self._recalculate_end(draft)

    def edit_timezone(self, draft: FinalEventDraft, new_value: str) -> None:
        self._update_field(draft, draft.timezone, new_value, "timezone")
        draft.match_status = "stale"

    def set_duration(self, draft: FinalEventDraft, minutes: int) -> None:
        self._update_field(draft, draft.duration_minutes, minutes, "duration_minutes")
        draft.duration_confirmed = True
        draft.match_status = "stale"
        self._recalculate_end(draft)

    def edit_location(self, draft: FinalEventDraft, new_value: str) -> None:
        self._update_field(draft, draft.location, new_value, "location")

    def edit_url(self, draft: FinalEventDraft, new_value: str) -> None:
        self._update_field(draft, draft.online_meeting_url, new_value, "online_meeting_url")

    def edit_description(self, draft: FinalEventDraft, new_value: str) -> None:
        self._update_field(draft, draft.description, new_value, "description")

    def add_attendee(
        self,
        draft: FinalEventDraft,
        participant: ResolvedParticipant,
        role: ParticipantRole = ParticipantRole.REQUIRED,
    ) -> None:
        participant.role = role
        if role == ParticipantRole.REQUIRED:
            draft.required_attendees.append(participant)
        else:
            draft.optional_attendees.append(participant)
        draft.match_status = "stale"

    def remove_attendee(self, draft: FinalEventDraft, email: str) -> None:
        draft.required_attendees = [a for a in draft.required_attendees if a.email != email]
        draft.optional_attendees = [a for a in draft.optional_attendees if a.email != email]
        draft.match_status = "stale"

    def change_attendee_role(
        self,
        draft: FinalEventDraft,
        email: str,
        new_role: ParticipantRole,
    ) -> None:
        for att_list in [draft.required_attendees, draft.optional_attendees]:
            for att in att_list:
                if att.email == email:
                    att.role = new_role
                    if new_role == ParticipantRole.REQUIRED and att in draft.optional_attendees:
                        draft.optional_attendees.remove(att)
                        draft.required_attendees.append(att)
                    elif new_role == ParticipantRole.OPTIONAL and att in draft.required_attendees:
                        draft.required_attendees.remove(att)
                        draft.optional_attendees.append(att)
                    return

    def revert_to_auto(self, draft: FinalEventDraft, original: FinalEventDraft) -> None:
        for field_name in ["subject", "start_date", "start_time", "timezone", "duration_minutes",
                           "location", "online_meeting_url", "description"]:
            orig_field = getattr(original, field_name)
            curr_field = getattr(draft, field_name)
            curr_field.value = orig_field.value
            curr_field.modified_by_user = False
            curr_field.modified_at = None
        draft.required_attendees = list(original.required_attendees)
        draft.optional_attendees = list(original.optional_attendees)
        draft.duration_confirmed = original.duration_confirmed

    def _update_field(self, draft: FinalEventDraft, field: DraftField, new_value, field_name: str) -> None:
        if field.modified_by_user:
            return
        field.value = new_value
        field.modified_by_user = True
        import datetime as dt
        field.modified_at = dt.datetime.now().isoformat()

    def _recalculate_end(self, draft: FinalEventDraft) -> None:
        end_date, end_time = draft.compute_end_datetime()
        if end_date:
            draft.end_date.value = end_date
        if end_time:
            draft.end_time.value = end_time

    def _log_change(self, draft: FinalEventDraft, field_name: str, old_value, new_value) -> None:
        import datetime as dt
        self.changes.append({
            "draft_id": draft.draft_id,
            "field": field_name,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "timestamp": dt.datetime.now().isoformat(),
        })

    def get_changes(self) -> list[dict]:
        return list(self.changes)