from __future__ import annotations

import hashlib
import zoneinfo
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .enums import (
    DescriptionItemType,
    MatchDecision,
    ParticipantRole,
    ParticipantSide,
)


@dataclass
class DraftField:
    value: Any
    origin: str
    evidence: list[dict] = field(default_factory=list)
    modified_by_user: bool = False
    modified_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "origin": self.origin,
            "evidence": self.evidence,
            "modified_by_user": self.modified_by_user,
            "modified_at": self.modified_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DraftField:
        return cls(
            value=data.get("value"),
            origin=data.get("origin", "auto"),
            evidence=data.get("evidence", []),
            modified_by_user=data.get("modified_by_user", False),
            modified_at=data.get("modified_at"),
        )


@dataclass
class NormalizedDateTime:
    raw_datetime: str
    raw_timezone: str | None
    aware_datetime: datetime
    utc_datetime: datetime
    display_datetime: datetime
    display_timezone: str
    warnings: list[str] = field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NormalizedDateTime):
            return NotImplemented
        return self.utc_datetime == other.utc_datetime

    def to_dict(self) -> dict:
        return {
            "raw_datetime": self.raw_datetime,
            "raw_timezone": self.raw_timezone,
            "aware_datetime": self.aware_datetime.isoformat(),
            "utc_datetime": self.utc_datetime.isoformat(),
            "display_datetime": self.display_datetime.isoformat(),
            "display_timezone": self.display_timezone,
            "warnings": self.warnings,
        }


@dataclass
class StructuredMeetingRow:
    sheet_name: str
    row_number: int
    subject: str
    agreed_date: str | None
    agreed_time: str | None
    planned_date: str | None = None
    planned_time: str | None = None
    actual_date: str | None = None
    actual_time: str | None = None
    performer_names: list[str] = field(default_factory=list)
    customer_names: list[str] = field(default_factory=list)
    timezone: str | None = None
    timezone_source: str = "missing"
    timezone_confirmed: bool = False
    duration_minutes: int | None = None
    duration_source: str = "missing"
    duration_confirmed: bool = False
    raw_cells: dict[str, str] = field(default_factory=dict)
    description_lines: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    location: str | None = None

    def to_dict(self) -> dict:
        return {
            "sheet_name": self.sheet_name,
            "row_number": self.row_number,
            "subject": self.subject,
            "agreed_date": self.agreed_date,
            "agreed_time": self.agreed_time,
            "planned_date": self.planned_date,
            "planned_time": self.planned_time,
            "actual_date": self.actual_date,
            "actual_time": self.actual_time,
            "performer_names": self.performer_names,
            "customer_names": self.customer_names,
            "timezone": self.timezone,
            "timezone_source": self.timezone_source,
            "timezone_confirmed": self.timezone_confirmed,
            "duration_minutes": self.duration_minutes,
            "duration_source": self.duration_source,
            "duration_confirmed": self.duration_confirmed,
            "description_lines": self.description_lines,
            "links": self.links,
            "location": self.location,
        }


@dataclass
class MeetingCandidate:
    candidate_id: str
    subject: str
    description_base: str = ""
    start_date: str | None = None
    start_time: str | None = None
    timezone: str | None = None
    duration_minutes: int | None = None
    duration_source: str = "missing"
    duration_confirmed: bool = False
    timezone_source: str = "missing"
    timezone_confirmed: bool = False
    performer_names: list[str] = field(default_factory=list)
    customer_names: list[str] = field(default_factory=list)
    location: str | None = None
    online_meeting_url: str | None = None
    confidence: float = 0.0
    evidence: list[dict] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    sheet_name: str | None = None
    row_number: int | None = None
    included: bool = True
    inclusion_reason: str = ""

    @property
    def has_agreed_datetime(self) -> bool:
        return self.start_date is not None and self.start_time is not None

    @property
    def start_iso(self) -> str | None:
        if self.start_date and self.start_time:
            return f"{self.start_date}T{self.start_time}"
        return None

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "subject": self.subject,
            "description_base": self.description_base,
            "start_date": self.start_date,
            "start_time": self.start_time,
            "timezone": self.timezone,
            "duration_minutes": self.duration_minutes,
            "duration_source": self.duration_source,
            "duration_confirmed": self.duration_confirmed,
            "timezone_source": self.timezone_source,
            "timezone_confirmed": self.timezone_confirmed,
            "performer_names": self.performer_names,
            "customer_names": self.customer_names,
            "location": self.location,
            "online_meeting_url": self.online_meeting_url,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "reasoning": self.reasoning,
            "warnings": self.warnings,
            "links": self.links,
            "sheet_name": self.sheet_name,
            "row_number": self.row_number,
            "included": self.included,
            "inclusion_reason": self.inclusion_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MeetingCandidate:
        return cls(
            candidate_id=data["candidate_id"],
            subject=data.get("subject", ""),
            description_base=data.get("description_base", ""),
            start_date=data.get("start_date"),
            start_time=data.get("start_time"),
            timezone=data.get("timezone"),
            duration_minutes=data.get("duration_minutes"),
            duration_source=data.get("duration_source", "missing"),
            duration_confirmed=data.get("duration_confirmed", False),
            timezone_source=data.get("timezone_source", "missing"),
            timezone_confirmed=data.get("timezone_confirmed", False),
            performer_names=data.get("performer_names", []),
            customer_names=data.get("customer_names", []),
            location=data.get("location"),
            online_meeting_url=data.get("online_meeting_url"),
            confidence=data.get("confidence", 0.0),
            evidence=data.get("evidence", []),
            reasoning=data.get("reasoning", []),
            warnings=data.get("warnings", []),
            links=data.get("links", []),
            sheet_name=data.get("sheet_name"),
            row_number=data.get("row_number"),
            included=data.get("included", True),
            inclusion_reason=data.get("inclusion_reason", ""),
        )


@dataclass
class CalendarEvent:
    event_id: str
    ical_uid: str | None
    subject: str
    start: NormalizedDateTime | None = None
    end: NormalizedDateTime | None = None
    is_all_day: bool = False
    location: str | None = None
    online_url: str | None = None
    attendees: list[dict] = field(default_factory=list)
    description: str = ""
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "ical_uid": self.ical_uid,
            "subject": self.subject,
            "start": self.start.to_dict() if self.start else None,
            "end": self.end.to_dict() if self.end else None,
            "is_all_day": self.is_all_day,
            "location": self.location,
            "online_url": self.online_url,
            "attendees": self.attendees,
            "description": self.description,
        }


@dataclass
class CalendarMatch:
    candidate_id: str
    calendar_event: CalendarEvent | None
    decision: MatchDecision
    score: float
    time_diff_minutes: int | None
    subject_similarity: float
    details: dict = field(default_factory=dict)
    user_decision: str | None = None
    decision_origin: str = "auto"
    best_rejected: dict | None = None

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "calendar_event": self.calendar_event.to_dict() if self.calendar_event is not None else None,
            "decision": self.decision.value,
            "score": self.score,
            "time_diff_minutes": self.time_diff_minutes,
            "subject_similarity": self.subject_similarity,
            "details": self.details,
            "user_decision": self.user_decision,
            "decision_origin": self.decision_origin,
            "best_rejected": self.best_rejected,
        }


@dataclass
class ResolvedParticipant:
    full_name: str
    email: str | None
    side: ParticipantSide
    role: ParticipantRole = ParticipantRole.REQUIRED
    source_name: str = ""
    match_source: str = ""
    confidence: float = 1.0
    organization: str | None = None
    is_fuzzy_match: bool = False
    fuzzy_score: float | None = None

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "side": self.side.value,
            "role": self.role.value,
            "source_name": self.source_name,
            "match_source": self.match_source,
            "confidence": self.confidence,
            "organization": self.organization,
            "is_fuzzy_match": self.is_fuzzy_match,
            "fuzzy_score": self.fuzzy_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResolvedParticipant:
        return cls(
            full_name=data["full_name"],
            email=data.get("email"),
            side=ParticipantSide(data["side"]),
            role=ParticipantRole(data.get("role", "REQUIRED")),
            source_name=data.get("source_name", ""),
            match_source=data.get("match_source", ""),
            confidence=data.get("confidence", 1.0),
            organization=data.get("organization"),
            is_fuzzy_match=data.get("is_fuzzy_match", False),
            fuzzy_score=data.get("fuzzy_score"),
        )


@dataclass
class UnresolvedParticipant:
    source_name: str
    side: ParticipantSide
    reason: str = ""
    possible_matches: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "side": self.side.value,
            "reason": self.reason,
            "possible_matches": self.possible_matches,
        }

    @classmethod
    def from_dict(cls, data: dict) -> UnresolvedParticipant:
        return cls(
            source_name=data["source_name"],
            side=ParticipantSide(data["side"]),
            reason=data.get("reason", ""),
            possible_matches=data.get("possible_matches", []),
        )


@dataclass
class CandidateParticipants:
    candidate_id: str
    performer: list[ResolvedParticipant] = field(default_factory=list)
    customer: list[ResolvedParticipant] = field(default_factory=list)
    unresolved: list[UnresolvedParticipant] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "performer": [p.to_dict() for p in self.performer],
            "customer": [p.to_dict() for p in self.customer],
            "unresolved": [u.to_dict() for u in self.unresolved],
        }

    @classmethod
    def from_dict(cls, data: dict) -> CandidateParticipants:
        return cls(
            candidate_id=data["candidate_id"],
            performer=[ResolvedParticipant.from_dict(p) for p in data.get("performer", [])],
            customer=[ResolvedParticipant.from_dict(p) for p in data.get("customer", [])],
            unresolved=[UnresolvedParticipant.from_dict(u) for u in data.get("unresolved", [])],
        )


@dataclass
class ContactRecord:
    full_name: str
    surname: str
    email: str | None = None
    phone: str | None = None
    organization: str | None = None
    source_location: str = ""
    side: ParticipantSide | None = None

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "surname": self.surname,
            "email": self.email,
            "phone": self.phone,
            "organization": self.organization,
            "source_location": self.source_location,
            "side": self.side.value if self.side else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ContactRecord:
        side = None
        if data.get("side"):
            side = ParticipantSide(data["side"])
        return cls(
            full_name=data["full_name"],
            surname=data["surname"],
            email=data.get("email"),
            phone=data.get("phone"),
            organization=data.get("organization"),
            source_location=data.get("source_location", ""),
            side=side,
        )


@dataclass
class DescriptionItem:
    item_id: str
    item_type: DescriptionItemType | str
    title: str
    value: str
    source_location: str = ""
    reasoning: str = ""
    confidence: float = 0.5
    included: bool = True
    modified_by_user: bool = False
    candidate_id: str = ""

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type.value if isinstance(self.item_type, DescriptionItemType) else self.item_type,
            "title": self.title,
            "value": self.value,
            "source_location": self.source_location,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "included": self.included,
            "modified_by_user": self.modified_by_user,
            "candidate_id": self.candidate_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DescriptionItem:
        item_type = data["item_type"]
        try:
            item_type = DescriptionItemType(item_type)
        except ValueError:
            pass
        return cls(
            item_id=data["item_id"],
            item_type=item_type,
            title=data.get("title", ""),
            value=data.get("value", ""),
            source_location=data.get("source_location", ""),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 0.5),
            included=data.get("included", True),
            modified_by_user=data.get("modified_by_user", False),
            candidate_id=data.get("candidate_id", ""),
        )


@dataclass
class FinalEventDraft:
    draft_id: str
    candidate_id: str

    subject: DraftField = field(default_factory=lambda: DraftField(value="", origin="auto"))
    start_date: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))
    start_time: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))
    timezone: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))

    duration_minutes: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))
    duration_confirmed: bool = False

    end_date: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))
    end_time: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))

    location: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))
    online_meeting_url: DraftField = field(default_factory=lambda: DraftField(value=None, origin="auto"))
    description: DraftField = field(default_factory=lambda: DraftField(value="", origin="auto"))

    required_attendees: list[ResolvedParticipant] = field(default_factory=list)
    optional_attendees: list[ResolvedParticipant] = field(default_factory=list)

    selected: bool = False
    is_ready: bool = False
    is_all_day: bool = False

    match_status: str = "not_checked"
    match_input_hash: str | None = None
    calendar_matches: list[CalendarMatch] = field(default_factory=list)

    reminder_minutes: int = 15
    show_as: str = "busy"
    privacy: str = "private"

    def compute_input_hash(self) -> str:
        raw = (
            f"{self.subject.value}|{self.start_date.value}|{self.start_time.value}"
            f"|{self.timezone.value}|{self.duration_minutes.value}"
            f"|{','.join(sorted(a.email or '' for a in self.required_attendees))}"
            f"|{','.join(sorted(a.email or '' for a in self.optional_attendees))}"
            f"|{self.online_meeting_url.value}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def compute_end_datetime(self) -> tuple[str | None, str | None]:
        if not all([self.start_date.value, self.start_time.value, self.duration_minutes.value]):
            return None, None
        try:
            start_str = f"{self.start_date.value}T{self.start_time.value}"
            start_dt = datetime.fromisoformat(start_str)
            end_dt = start_dt + timedelta(minutes=self.duration_minutes.value)
            return end_dt.strftime("%Y-%m-%d"), end_dt.strftime("%H:%M")
        except (ValueError, TypeError):
            return None, None

    def to_dict(self) -> dict:
        return {
            "draft_id": self.draft_id,
            "candidate_id": self.candidate_id,
            "subject": self.subject.to_dict(),
            "start_date": self.start_date.to_dict(),
            "start_time": self.start_time.to_dict(),
            "timezone": self.timezone.to_dict(),
            "duration_minutes": self.duration_minutes.to_dict(),
            "duration_confirmed": self.duration_confirmed,
            "end_date": self.end_date.to_dict(),
            "end_time": self.end_time.to_dict(),
            "location": self.location.to_dict(),
            "online_meeting_url": self.online_meeting_url.to_dict(),
            "description": self.description.to_dict(),
            "required_attendees": [a.to_dict() for a in self.required_attendees],
            "optional_attendees": [a.to_dict() for a in self.optional_attendees],
            "selected": self.selected,
            "is_ready": self.is_ready,
            "is_all_day": self.is_all_day,
            "match_status": self.match_status,
            "match_input_hash": self.match_input_hash,
            "reminder_minutes": self.reminder_minutes,
            "show_as": self.show_as,
            "privacy": self.privacy,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FinalEventDraft:
        draft = cls(
            draft_id=data["draft_id"],
            candidate_id=data["candidate_id"],
            subject=DraftField.from_dict(data.get("subject", {})),
            start_date=DraftField.from_dict(data.get("start_date", {})),
            start_time=DraftField.from_dict(data.get("start_time", {})),
            timezone=DraftField.from_dict(data.get("timezone", {})),
            duration_minutes=DraftField.from_dict(data.get("duration_minutes", {})),
            duration_confirmed=data.get("duration_confirmed", False),
            end_date=DraftField.from_dict(data.get("end_date", {})),
            end_time=DraftField.from_dict(data.get("end_time", {})),
            location=DraftField.from_dict(data.get("location", {})),
            online_meeting_url=DraftField.from_dict(data.get("online_meeting_url", {})),
            description=DraftField.from_dict(data.get("description", {})),
            selected=data.get("selected", False),
            is_ready=data.get("is_ready", False),
            is_all_day=data.get("is_all_day", False),
            match_status=data.get("match_status", "not_checked"),
            match_input_hash=data.get("match_input_hash"),
            reminder_minutes=data.get("reminder_minutes", 15),
            show_as=data.get("show_as", "busy"),
            privacy=data.get("privacy", "private"),
        )
        draft.required_attendees = [
            ResolvedParticipant.from_dict(a) for a in data.get("required_attendees", [])
        ]
        draft.optional_attendees = [
            ResolvedParticipant.from_dict(a) for a in data.get("optional_attendees", [])
        ]
        return draft

    def modified_by_user_check(self) -> bool:
        fields = [
            self.subject, self.start_date, self.start_time, self.timezone,
            self.duration_minutes, self.end_date, self.end_time,
            self.location, self.online_meeting_url, self.description,
        ]
        return any(f.modified_by_user for f in fields)


@dataclass
class SourceReference:
    type: str
    path: str | None = None
    url: str | None = None
    format: str | None = None

    def __str__(self) -> str:
        return self.path or self.url or "unknown"


@dataclass
class ExtractedSource:
    source: SourceReference
    sheets: dict[str, list[list[str]]] = field(default_factory=dict)
    raw_text: str = ""
    metadata: dict = field(default_factory=dict)
    links: list[dict] = field(default_factory=list)
    merged_cells: list[dict] = field(default_factory=list)
    hyperlinks: dict[str, str] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": {"type": self.source.type, "path": self.source.path, "url": self.source.url},
            "sheets": {k: v for k, v in self.sheets.items()},
            "metadata": self.metadata,
            "links": self.links,
            "merged_cells": self.merged_cells,
        }


def calculate_end_datetime(
    start_date: str,
    start_time: str,
    timezone: str,
    duration_minutes: int,
) -> tuple[str, str]:
    naive = datetime.fromisoformat(f"{start_date}T{start_time}")
    try:
        tz = zoneinfo.ZoneInfo(timezone)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")
    aware = naive.replace(tzinfo=tz)
    end = aware + timedelta(minutes=duration_minutes)
    return end.strftime("%Y-%m-%d"), end.strftime("%H:%M")