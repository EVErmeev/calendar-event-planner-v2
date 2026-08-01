from __future__ import annotations

import hashlib

from calendar_planner.domain.models import FinalEventDraft


def compute_draft_hash(draft: FinalEventDraft) -> str:
    return draft.compute_input_hash()


def verify_hash(draft: FinalEventDraft, expected_hash: str) -> bool:
    return compute_draft_hash(draft) == expected_hash