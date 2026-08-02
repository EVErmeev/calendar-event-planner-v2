from __future__ import annotations

from calendar_planner.domain.models import ExtractedSource, MeetingCandidate


class ExtractionAuditor:
    def audit(
        self,
        candidates: list[MeetingCandidate],
        source: ExtractedSource,
        skipped_rows: list[dict] | None = None,
    ) -> dict:
        result = {
            "total_candidates": len(candidates),
            "warnings": [],
            "skipped_rows": skipped_rows or [],
            "duplicates": [],
            "timezone_issues": [],
            "incomplete_candidates": [],
        }

        seen_keys: set[tuple] = set()
        for candidate in candidates:
            key = (candidate.subject, candidate.start_date, candidate.start_time)
            if key in seen_keys:
                result["duplicates"].append({
                    "candidate_id": candidate.candidate_id,
                    "subject": candidate.subject,
                })
            seen_keys.add(key)

            if not candidate.timezone:
                result["timezone_issues"].append({
                    "candidate_id": candidate.candidate_id,
                    "issue": "Часовой пояс не определён",
                })

            if not candidate.has_agreed_datetime:
                result["incomplete_candidates"].append({
                    "candidate_id": candidate.candidate_id,
                    "issue": "Нет согласованных даты и времени",
                })

        return result