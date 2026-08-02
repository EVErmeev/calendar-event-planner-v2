from __future__ import annotations

import json

from calendar_planner.domain.enums import StageStatus
from calendar_planner.domain.models import (
    CandidateParticipants,
    DescriptionItem,
    ExtractedSource,
    FinalEventDraft,
    MeetingCandidate,
)
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
        self._creation_results: list[dict] = []
        self._stage3_diagnostics: dict = {}

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

    def add_creation_result(self, result: dict) -> None:
        self._creation_results.append(result)

    def set_stage3_diagnostics(self, diagnostics: dict) -> None:
        self._stage3_diagnostics = diagnostics

    def get_stage3_diagnostics(self) -> dict:
        return dict(self._stage3_diagnostics)

    def get_creation_results(self) -> list[dict]:
        return list(self._creation_results)

    def clear_creation_results(self) -> None:
        self._creation_results = []

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

        if self._calendar_events:
            storage.save_artifact(
                session.session_id,
                "calendar_events.json",
                [e.to_dict() if hasattr(e, 'to_dict') else e for e in self._calendar_events],
            )
            session.calendar_events_json = json.dumps(
                [e.to_dict() if hasattr(e, 'to_dict') else e for e in self._calendar_events],
                ensure_ascii=False,
                default=str,
            )

        if self._matches:
            serializable_matches: dict[str, dict | None] = {}
            for cid, match in self._matches.items():
                if match is not None and hasattr(match, 'to_dict'):
                    serializable_matches[cid] = match.to_dict()
                else:
                    serializable_matches[cid] = None
            storage.save_artifact(
                session.session_id,
                "calendar_matches.json",
                serializable_matches,
            )
            session.calendar_matches_json = json.dumps(
                serializable_matches, ensure_ascii=False, default=str
            )

        if self._participants:
            storage.save_artifact(
                session.session_id,
                "participants_results.json",
                [cp.to_dict() for cp in self._participants],
            )
            session.participants_json = json.dumps(
                [cp.to_dict() for cp in self._participants],
                ensure_ascii=False,
                default=str,
            )

        if self._enrichment:
            enrichment_serializable = {}
            for cid, items in self._enrichment.items():
                enrichment_serializable[cid] = [i.to_dict() for i in items]
            storage.save_artifact(
                session.session_id,
                "enrichment_results.json",
                enrichment_serializable,
            )
            session.enrichment_json = json.dumps(
                enrichment_serializable, ensure_ascii=False, default=str,
            )

        if self._drafts:
            storage.save_artifact(
                session.session_id,
                "drafts.json",
                [d.to_dict() for d in self._drafts],
            )
            session.drafts_json = json.dumps(
                [d.to_dict() for d in self._drafts],
                ensure_ascii=False,
                default=str,
            )

        session.stages = [StageState.from_dict(s.to_dict()) for s in self.stages]

        if self._creation_results:
            storage.save_artifact(
                session.session_id,
                "creation_results.json",
                self._creation_results,
            )
            session.creation_results_json = json.dumps(
                self._creation_results, ensure_ascii=False, default=str,
            )

        if self._stage3_diagnostics:
            storage.save_artifact(
                session.session_id,
                "stage3_diagnostics.json",
                self._stage3_diagnostics,
            )
            # сохраняем в data stage_3
            for s in session.stages:
                if s.name == "comparison":
                    s.data.update(self._stage3_diagnostics)
                    break

        storage.save_session(session)
        self._session = session
        return session

    def load_session(self, storage: SessionStorage, session_id: str) -> RunSession | None:
        session = storage.load_session(session_id)
        if not session:
            return None

        self._session = session

        if session.stages:
            self.stages = [StageState.from_dict(s.to_dict()) for s in session.stages]
            for s in self.stages:
                sidx = {
                    "connections": 0, "extraction": 1, "comparison": 2,
                    "participants": 3, "enrichment": 4, "creation": 5,
                }.get(s.name)
                if sidx is not None and s.status == StageStatus.SUCCESS:
                    self.current_stage = max(self.current_stage, sidx)

        if session.candidates_json:
            from calendar_planner.domain.models import MeetingCandidate
            candidates_data = json.loads(session.candidates_json)
            self._all_candidates = [MeetingCandidate.from_dict(c) for c in candidates_data]

        if session.calendar_events_json:
            from calendar_planner.domain.models import CalendarEvent
            events_data = json.loads(session.calendar_events_json)
            self._calendar_events = [CalendarEvent(
                event_id=e.get("event_id", ""),
                ical_uid=e.get("ical_uid"),
                subject=e.get("subject", ""),
            ) for e in events_data]

        if session.calendar_matches_json:
            self._matches = json.loads(session.calendar_matches_json)

        if session.participants_json:
            from calendar_planner.domain.models import CandidateParticipants
            participants_data = json.loads(session.participants_json)
            self._participants = [CandidateParticipants.from_dict(cp) for cp in participants_data]

        if session.enrichment_json:
            from calendar_planner.domain.models import DescriptionItem
            enrichment_data = json.loads(session.enrichment_json)
            self._enrichment = {
                cid: [DescriptionItem.from_dict(i) for i in items]
                for cid, items in enrichment_data.items()
            }

        if session.drafts_json:
            from calendar_planner.domain.models import FinalEventDraft
            drafts_data = json.loads(session.drafts_json)
            self._drafts = [FinalEventDraft.from_dict(d) for d in drafts_data]
            self._original_drafts = [
                FinalEventDraft.from_dict(d.to_dict()) for d in self._drafts
            ]

        if session.creation_results_json:
            self._creation_results = json.loads(session.creation_results_json)

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