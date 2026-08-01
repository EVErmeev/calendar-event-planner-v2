from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from calendar_planner.domain.enums import RunStatus, StageStatus


@dataclass
class StageState:
    name: str
    status: StageStatus = StageStatus.NOT_STARTED
    data: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "data": self.data,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StageState:
        return cls(
            name=data["name"],
            status=StageStatus(data["status"]),
            data=data.get("data", {}),
            warnings=data.get("warnings", []),
            errors=data.get("errors", []),
        )


@dataclass
class RunSession:
    session_id: str
    status: RunStatus = RunStatus.ACTIVE
    created_at: str = ""
    updated_at: str = ""

    source_ref: dict = field(default_factory=dict)
    stages: list[StageState] = field(default_factory=list)

    candidates_json: str = ""
    calendar_events_json: str = ""
    calendar_matches_json: str = ""
    participants_json: str = ""
    enrichment_json: str = ""
    drafts_json: str = ""
    creation_results_json: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_ref": self.source_ref,
            "stages": [s.to_dict() for s in self.stages],
            "candidates_json": self.candidates_json,
            "calendar_events_json": self.calendar_events_json,
            "calendar_matches_json": self.calendar_matches_json,
            "participants_json": self.participants_json,
            "enrichment_json": self.enrichment_json,
            "drafts_json": self.drafts_json,
            "creation_results_json": self.creation_results_json,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunSession:
        session = cls(
            session_id=data["session_id"],
            status=RunStatus(data.get("status", "active")),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            source_ref=data.get("source_ref", {}),
            candidates_json=data.get("candidates_json", ""),
            calendar_events_json=data.get("calendar_events_json", ""),
            calendar_matches_json=data.get("calendar_matches_json", ""),
            participants_json=data.get("participants_json", ""),
            enrichment_json=data.get("enrichment_json", ""),
            drafts_json=data.get("drafts_json", ""),
            creation_results_json=data.get("creation_results_json", ""),
        )
        session.stages = [StageState.from_dict(s) for s in data.get("stages", [])]
        return session