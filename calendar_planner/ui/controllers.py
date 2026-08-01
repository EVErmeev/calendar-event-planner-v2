from __future__ import annotations

import json
from datetime import datetime

from calendar_planner.domain.models import (
    ExtractedSource,
    MeetingCandidate,
    FinalEventDraft,
    CandidateParticipants,
    DescriptionItem,
    ResolvedParticipant,
)
from calendar_planner.domain.enums import StageStatus
from calendar_planner.session.models import RunSession, StageState
from calendar_planner.session.storage import SessionStorage


class StageController:
    def __init__(self):
        self.current_stage = 0
        self.stages: list[StageState] = [
            StageState(name="connections", status=StageStatus.NOT_STARTED),
            StageState(name="extraction", status=StageStatus.NOT_STARTED),
            StageState(name="comparison", status=StageStatus.NOT_STARTED),
            StageState(name="participants", status=StageStatus.NOT_STARTED),
            StageState(name="enrichment", status=StageStatus.NOT_STARTED),
            StageState(name="creation", status=StageStatus.NOT_STARTED),
        ]

        self._extracted: ExtractedSource | None = None
        self._candidates: dict[str, list[MeetingCandidate]] = {}
        self._all_candidates: list[MeetingCandidate] = []
        self._skipped_rows: list[dict] = []
        self._calendar_events: list = []
        self._matches: dict[str, object] = {}
        self._participants: list[CandidateParticipants] = []
        self._enrichment: dict[str, list[DescriptionItem]] = {}
        self._drafts: list[FinalEventDraft] = []
        self._session: RunSession | None = None

        self._original_drafts: list[FinalEventDraft] = []

    def set_extracted(self, source: ExtractedSource) -> None:
        self._extracted = source

    def set_candidates(self, candidates: dict[str, list[MeetingCandidate]]) -> None:
        self._candidates = candidates
        self._all_candidates = []
        for sheet_cands in candidates.values():
            self._all_candidates.extend(sheet_cands)

    def set_skipped_rows(self, skipped: list[dict]) -> None:
        self._skipped_rows = skipped

    def set_calendar_events(self, events: list) -> None:
        self._calendar_events = events

    def set_matches(self, matches: dict) -> None:
        self._matches = matches

    def set_participants(self, participants: list[CandidateParticipants]) -> None:
        self._participants = participants

    def set_enrichment(self, enrichment: dict[str, list[DescriptionItem]]) -> None:
        self._enrichment = enrichment

    def set_drafts(self, drafts: list[FinalEventDraft]) -> None:
        self._drafts = drafts
        self._original_drafts = [
            FinalEventDraft.from_dict(d.to_dict()) for d in drafts
        ]

    def get_all_candidates(self) -> list[MeetingCandidate]:
        return self._all_candidates

    def get_candidates_for_sheet(self, sheet_name: str) -> list[MeetingCandidate]:
        return self._candidates.get(sheet_name, [])

    def set_stage_success(self, stage_key: str) -> None:
        idx_map = {
            "stage_1": 0, "stage_2": 1, "stage_3": 2,
            "stage_4": 3, "stage_5": 4, "stage_6": 5,
        }
        idx = idx_map.get(stage_key, self.current_stage)
        if idx < len(self.stages):
            self.stages[idx].status = StageStatus.SUCCESS

    def set_stage_error(self, stage_key: str, error: str) -> None:
        idx_map = {
            "stage_1": 0, "stage_2": 1, "stage_3": 2,
            "stage_4": 3, "stage_5": 4, "stage_6": 5,
        }
        idx = idx_map.get(stage_key, self.current_stage)
        if idx < len(self.stages):
            self.stages[idx].status = StageStatus.FAILED
            self.stages[idx].errors.append(error)

    def get_stage_status(self, idx: int) -> str:
        if 0 <= idx < len(self.stages):
            return self.stages[idx].status.value
        return "not_started"

    def set_current_stage(self, stage: int) -> None:
        self.current_stage = max(0, min(5, stage))

    def prev_stage(self) -> None:
        self.current_stage = max(0, self.current_stage - 1)

    def next_stage(self) -> None:
        self.current_stage = min(5, self.current_stage + 1)

    def create_session(self, storage: SessionStorage) -> RunSession:
        session = storage.create_session()

        if self._extracted:
            session.source_ref = {
                "type": self._extracted.source.type,
                "path": self._extracted.source.path,
                "url": self._extracted.source.url,
            }
            storage.save_artifact(
                session.session_id,
                "source_extracted.json",
                {
                    "sheets": {k: v for k, v in self._extracted.sheets.items()},
                    "metadata": self._extracted.metadata,
                },
            )

        if self._all_candidates:
            storage.save_artifact(
                session.session_id,
                "meeting_candidates.json",
                [c.to_dict() for c in self._all_candidates],
            )
            session.candidates_json = json.dumps(
                [c.to_dict() for c in self._all_candidates],
                ensure_ascii=False,
                default=str,
            )

        if self._skipped_rows:
            storage.save_artifact(
                session.session_id,
                "skipped_rows.json",
                self._skipped_rows,
            )

        session.stages = [StageState.from_dict(s.to_dict()) for s in self.stages]
        storage.save_session(session)
        self._session = session
        return session

    def load_session(self, storage: SessionStorage, session_id: str) -> RunSession | None:
        session = storage.load_session(session_id)
        if session:
            self._session = session
        return session

    def has_unsaved_changes(self) -> bool:
        if self._drafts:
            for d in self._drafts:
                if d.modified_by_user_check():
                    return True
        return False

    def get_drafts(self) -> list[FinalEventDraft]:
        return self._drafts

    def get_original_drafts(self) -> list[FinalEventDraft]:
        return self._original_drafts

    @staticmethod
    def _ensure_json_serializable(data: dict | list) -> dict | list:
        return json.loads(json.dumps(data, ensure_ascii=False, default=str))