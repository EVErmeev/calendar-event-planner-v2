from __future__ import annotations

import re
from typing import Any

from calendar_planner.domain.validation import validate_draft_ready, validate_email, validate_payload


def validate_draft(draft: Any) -> list[str]:
    return validate_draft_ready(draft)


def validate_event_payload(payload: dict) -> list[str]:
    return validate_payload(payload)


def is_email_valid(email: str) -> bool:
    return validate_email(email)


def validate_draft_stale(draft: Any) -> bool:
    return draft.match_status == "stale"