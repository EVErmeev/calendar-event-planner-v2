from __future__ import annotations

from calendar_planner.domain.models import (
    FinalEventDraft,
    MeetingCandidate,
    DraftField,
    CandidateParticipants,
    DescriptionItem,
    ResolvedParticipant,
    ParticipantRole,
)
from calendar_planner.domain.enums import DraftFieldOrigin


class DraftBuilder:
    def __init__(self, sequence: int = 0):
        self._counter = sequence

    def build_from_candidate(
        self,
        candidate: MeetingCandidate,
        participants: CandidateParticipants | None = None,
        enrichment_items: list[DescriptionItem] | None = None,
    ) -> FinalEventDraft:
        self._counter += 1
        draft_id = f"DRF-{self._counter:04d}"

        subject_text = candidate.subject
        if subject_text:
            prefix_map = {
                "демонстрация процессов: ": "Демонстрация процессов: ",
                "демонстрация: ": "Демонстрация: ",
            }
            for key, val in prefix_map.items():
                if subject_text.lower().startswith(key):
                    subject_text = val + subject_text[len(key):]
                    break

        draft = FinalEventDraft(
            draft_id=draft_id,
            candidate_id=candidate.candidate_id,

            subject=DraftField(
                value=subject_text,
                origin=DraftFieldOrigin.AUTO.value,
                evidence=[
                    {"source": f"{candidate.sheet_name}:R{candidate.row_number}"}
                    if candidate.sheet_name else {},
                ],
            ),
            start_date=DraftField(
                value=candidate.start_date,
                origin=DraftFieldOrigin.AUTO.value,
                evidence=[{"method": "agreed_date"}] if candidate.has_agreed_datetime else [],
            ),
            start_time=DraftField(
                value=candidate.start_time,
                origin=DraftFieldOrigin.AUTO.value,
                evidence=[{"method": "agreed_time"}] if candidate.has_agreed_datetime else [],
            ),
            timezone=DraftField(
                value=candidate.timezone,
                origin=DraftFieldOrigin.AUTO.value,
                evidence=[{"method": "detected_from_header"}],
            ),

            duration_minutes=DraftField(
                value=candidate.duration_minutes,
                origin=DraftFieldOrigin.AUTO.value,
            ),
            duration_confirmed=candidate.duration_confirmed,

            location=DraftField(
                value=candidate.location,
                origin=DraftFieldOrigin.AUTO.value,
            ),
            online_meeting_url=DraftField(
                value=candidate.online_meeting_url,
                origin=DraftFieldOrigin.AUTO.value,
            ),
        )

        if participants:
            for p in participants.performer:
                draft.required_attendees.append(p)
            for p in participants.customer:
                draft.required_attendees.append(p)

        if enrichment_items:
            renderer = __import__("calendar_planner.enrichment.renderer", fromlist=["DescriptionRenderer"]).DescriptionRenderer()
            desc_text = renderer.render(enrichment_items, candidate.subject)
            draft.description = DraftField(
                value=desc_text,
                origin=DraftFieldOrigin.AUTO.value,
                evidence=[{"method": "enrichment_renderer"}],
            )

        draft.selected = candidate.included
        draft.is_ready = self._check_initial_ready(draft)

        return draft

    @staticmethod
    def _check_initial_ready(draft: FinalEventDraft) -> bool:
        if not draft.subject.value:
            return False
        if not draft.start_date.value:
            return False
        if not draft.start_time.value:
            return False
        if not draft.timezone.value:
            return False
        if not draft.duration_confirmed:
            return False
        return True

    def reset_counter(self) -> None:
        self._counter = 0