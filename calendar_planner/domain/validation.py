from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def validate_candidate_has_datetime(candidate: Any) -> list[str]:
    errors = []
    if not candidate.start_date:
        errors.append("start_date is required")
    if not candidate.start_time:
        errors.append("start_time is required")
    if not candidate.timezone:
        errors.append("timezone is required")
    return errors


def validate_draft_ready(draft: Any) -> list[str]:
    errors = []

    if not draft.subject.value:
        errors.append("Тема не задана")
    if not draft.start_date.value:
        errors.append("Дата не задана")
    if not draft.start_time.value:
        errors.append("Время не задано")
    if not draft.timezone.value:
        errors.append("Часовой пояс не задан")
    if not draft.duration_confirmed:
        errors.append("Длительность не подтверждена")
    if draft.duration_minutes.value is not None and draft.duration_minutes.value <= 0:
        errors.append("Длительность должна быть положительной")

    end_date, end_time = draft.compute_end_datetime()
    if end_date is None or end_time is None:
        errors.append("Невозможно вычислить время окончания")

    for att in draft.required_attendees + draft.optional_attendees:
        if att.email and not validate_email(att.email):
            errors.append(f"Некорректный email: {att.email} ({att.full_name})")

    if draft.match_status == "stale":
        errors.append("Требуется повторная проверка дублей")

    if draft.match_status == "matched" and any(
        m.decision.value in ("DUPLICATE", "POSSIBLE_DUPLICATE")
        for m in draft.calendar_matches
    ):
        errors.append("Обнаружен дубль в календаре")

    if end_date and end_time and draft.start_date.value and draft.start_time.value:
        try:
            start_str = f"{draft.start_date.value}T{draft.start_time.value}"
            end_str = f"{end_date}T{end_time}"
            start_dt = __import__("datetime").datetime.fromisoformat(start_str)
            end_dt = __import__("datetime").datetime.fromisoformat(end_str)
            if end_dt <= start_dt:
                errors.append("Время окончания должно быть позже времени начала")
        except (ValueError, TypeError):
            errors.append("Некорректный формат даты/времени")

    return errors


def validate_payload(payload: dict) -> list[str]:
    import datetime as dt

    errors = []
    if not payload.get("subject"):
        errors.append("subject is required")

    start = payload.get("start", {})
    if not start.get("dateTime"):
        errors.append("start.dateTime is required")
    if not start.get("timeZone"):
        errors.append("start.timeZone is required")

    end = payload.get("end", {})
    if not end.get("dateTime"):
        errors.append("end.dateTime is required")

    try:
        start_dt = dt.datetime.fromisoformat(start["dateTime"])
        end_dt = dt.datetime.fromisoformat(end["dateTime"])
        if end_dt <= start_dt:
            errors.append("end must be after start")
    except (ValueError, TypeError, KeyError):
        pass

    return errors