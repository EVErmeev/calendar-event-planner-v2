from __future__ import annotations

from calendar_planner.domain.models import DescriptionItem


class RelevanceScorer:
    def score(self, item: DescriptionItem, candidate_subject: str) -> float:
        score = item.confidence
        subject_lower = candidate_subject.lower()
        value_lower = item.value.lower()

        if subject_lower in value_lower:
            score = min(1.0, score + 0.2)

        if "agenda" in str(item.item_type) or "agenda" in item.title.lower():
            score = max(score, 0.7)

        return score