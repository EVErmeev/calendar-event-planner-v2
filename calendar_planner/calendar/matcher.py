from __future__ import annotations

from difflib import SequenceMatcher

from calendar_planner.domain.enums import MatchDecision
from calendar_planner.domain.models import (
    CalendarEvent,
    CalendarMatch,
    MeetingCandidate,
    NormalizedDateTime,
)
from calendar_planner.extraction.datetime_normalizer import parse_date_time


def normalize_subject_for_comparison(subject: str) -> str:
    prefixes = [
        "встреча:", "созвон:", "демонстрация процессов:", "демо нстрация:", "демонстрация:",
        "рабочая встреча:", "совещание:", "meeting:", "call:", "demo:", "review:",
        "демонстрация", "демо нстрация",
    ]
    result = subject.strip()
    for prefix in sorted(prefixes, key=len, reverse=True):
        if result.lower().startswith(prefix.lower()):
            result = result[len(prefix):].strip()
    return result


def subject_similarity(a: str, b: str) -> float:
    a_norm = normalize_subject_for_comparison(a).lower()
    b_norm = normalize_subject_for_comparison(b).lower()
    return SequenceMatcher(None, a_norm, b_norm).ratio()


class CalendarMatcher:
    def __init__(
        self,
        tolerance_minutes: int = 30,
        subject_threshold: float = 0.75,
    ):
        self.tolerance_minutes = tolerance_minutes
        self.subject_threshold = subject_threshold

    def match(
        self,
        candidate: MeetingCandidate,
        calendar_events: list[CalendarEvent],
    ) -> CalendarMatch | None:
        if not candidate.has_agreed_datetime or not candidate.timezone:
            return None

        candidate_start = parse_date_time(
            candidate.start_date,
            candidate.start_time,
            candidate.timezone,
        )
        if candidate_start is None:
            return None

        return self._find_match(candidate, candidate_start, calendar_events)

    def match_all(
        self,
        candidates: list[MeetingCandidate],
        calendar_events: list[CalendarEvent],
    ) -> dict[str, CalendarMatch | None]:
        results: dict[str, CalendarMatch | None] = {}
        for candidate in candidates:
            results[candidate.candidate_id] = self.match(candidate, calendar_events)
        return results

    def recheck_for_draft(
        self,
        subject: str,
        start_date: str,
        start_time: str,
        timezone: str,
        calendar_events: list[CalendarEvent],
    ) -> CalendarMatch | None:
        temp_candidate = MeetingCandidate(
            candidate_id="recheck",
            subject=subject,
            start_date=start_date,
            start_time=start_time,
            timezone=timezone,
        )
        return self.match(temp_candidate, calendar_events)

    def _find_match(
        self,
        candidate: MeetingCandidate,
        candidate_start: NormalizedDateTime,
        calendar_events: list[CalendarEvent],
    ) -> CalendarMatch | None:
        best_match: tuple[CalendarEvent, float, MatchDecision, int | None, float] | None = None

        for event in calendar_events:
            if event.start is None:
                continue

            time_diff = abs(
                (candidate_start.utc_datetime - event.start.utc_datetime).total_seconds()
            ) / 60

            sub_sim = subject_similarity(candidate.subject, event.subject)

            if time_diff <= self.tolerance_minutes and sub_sim >= self.subject_threshold:
                return CalendarMatch(
                    candidate_id=candidate.candidate_id,
                    calendar_event=event,
                    decision=MatchDecision.DUPLICATE,
                    score=1.0,
                    time_diff_minutes=int(time_diff),
                    subject_similarity=sub_sim,
                )

            weighted_score = self.compute_weighted_score(candidate, event)

            if time_diff <= self.tolerance_minutes and sub_sim < self.subject_threshold:
                match = (event, weighted_score, MatchDecision.POSSIBLE_DUPLICATE, int(time_diff), sub_sim)
                if best_match is None or weighted_score > best_match[1]:
                    best_match = match

            if time_diff > self.tolerance_minutes and time_diff <= 240 and sub_sim >= self.subject_threshold:
                match = (event, weighted_score, MatchDecision.POSSIBLE_RESCHEDULE, int(time_diff), sub_sim)
                if best_match is None or weighted_score > best_match[1]:
                    best_match = match

        if best_match:
            evt, score, decision, diff, sim = best_match
            return CalendarMatch(
                candidate_id=candidate.candidate_id,
                calendar_event=evt,
                decision=decision,
                score=score,
                time_diff_minutes=diff,
                subject_similarity=sim,
            )

        return CalendarMatch(
            candidate_id=candidate.candidate_id,
            calendar_event=None,  # type: ignore
            decision=MatchDecision.NEW,
            score=0.0,
            time_diff_minutes=None,
            subject_similarity=0.0,
            details={"message": "No matching events found"},
        )

    def compute_weighted_score(
        self,
        candidate: MeetingCandidate,
        event: CalendarEvent,
    ) -> float:
        weights = {
            "date": 0.25,
            "time": 0.20,
            "subject": 0.25,
            "attendees": 0.15,
            "url": 0.10,
            "location": 0.05,
        }
        total_weight = 0.0
        score = 0.0

        if candidate.start_date and event.start:
            total_weight += weights["date"]
            candidate_date = str(candidate.start_date)
            event_date = event.start.display_datetime.strftime("%Y-%m-%d")
            if candidate_date == event_date:
                score += weights["date"] * 1.0

        if candidate.start_time and event.start:
            total_weight += weights["time"]
            candidate_time = candidate.start_time
            event_time = event.start.display_datetime.strftime("%H:%M")
            if candidate_time == event_time:
                score += weights["time"] * 1.0

        sub_sim = subject_similarity(candidate.subject, event.subject)
        total_weight += weights["subject"]
        score += weights["subject"] * sub_sim

        if candidate.online_meeting_url and event.online_url:
            total_weight += weights["url"]
            if candidate.online_meeting_url == event.online_url:
                score += weights["url"]

        if candidate.location and event.location:
            total_weight += weights["location"]
            if candidate.location.lower() == (event.location or "").lower():
                score += weights["location"]

        if total_weight == 0:
            return 0.0

        return score / total_weight