from __future__ import annotations

from enum import Enum


class StageStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    SUCCESS_WITH_WARNINGS = "success_with_warnings"
    FAILED = "failed"
    REQUIRES_USER_ACTION = "requires_user_action"
    STALE = "stale"


class MeetingDatePolicy(str, Enum):
    AGREED_ONLY = "AGREED_ONLY"
    PLANNED_ONLY = "PLANNED_ONLY"
    ACTUAL_ONLY = "ACTUAL_ONLY"
    AGREED_THEN_PLANNED = "AGREED_THEN_PLANNED"


class MatchDecision(str, Enum):
    DUPLICATE = "DUPLICATE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    POSSIBLE_RESCHEDULE = "POSSIBLE_RESCHEDULE"
    NEW = "NEW"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"


class ParticipantSide(str, Enum):
    PERFORMER = "PERFORMER"
    CUSTOMER = "CUSTOMER"


class ParticipantRole(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


class DescriptionItemType(str, Enum):
    AGENDA = "agenda"
    GOAL = "goal"
    EXPECTED_RESULT = "expected_result"
    LINK = "link"
    MATERIAL = "material"
    LOCATION = "location"
    ONLINE_MEETING_URL = "online_meeting_url"
    PROTOCOL = "protocol"
    DOCUMENT = "document"
    TASK = "task"
    COMMENT = "comment"
    NOTE = "note"


class DraftFieldOrigin(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    UNCERTAIN = "uncertain"


class RunStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"