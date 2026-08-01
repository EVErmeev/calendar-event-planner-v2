from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from calendar_planner.domain.models import FinalEventDraft

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


@dataclass
class PreflightResult:
    ready: bool
    blocking_errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


def preflight_validate(draft: FinalEventDraft) -> PreflightResult:
    blocking_errors: list[dict] = []
    warnings: list[dict] = []

    if not draft.subject.value:
        blocking_errors.append({
            "code": "missing_subject",
            "message_ru": "Не указана тема события",
            "field": "subject",
            "how_to_fix": "Введите тему события в поле «Тема».",
        })

    if not draft.start_date.value:
        blocking_errors.append({
            "code": "missing_date",
            "message_ru": "Не указана дата",
            "field": "start_date",
            "how_to_fix": "Укажите дату события в поле «Дата».",
        })

    if not draft.start_time.value:
        blocking_errors.append({
            "code": "missing_time",
            "message_ru": "Не указано время начала",
            "field": "start_time",
            "how_to_fix": "Укажите время начала в поле «Время начала».",
        })

    if not draft.timezone.value:
        blocking_errors.append({
            "code": "missing_timezone",
            "message_ru": "Не указан часовой пояс",
            "field": "timezone",
            "how_to_fix": "Укажите часовой пояс в поле «Час. пояс».",
        })

    if not draft.duration_confirmed:
        blocking_errors.append({
            "code": "duration_not_confirmed",
            "message_ru": "Не выбрана длительность",
            "field": "duration",
            "how_to_fix": "Нажмите на предустановленную длительность (15/30/45/60/90/120 мин) или введите свою.",
        })

    if draft.duration_minutes.value is not None and draft.duration_minutes.value <= 0:
        blocking_errors.append({
            "code": "duration_not_positive",
            "message_ru": "Длительность должна быть положительной",
            "field": "duration",
            "how_to_fix": "Выберите положительную длительность.",
        })

    end_date, end_time = draft.compute_end_datetime()
    if end_date and end_time and draft.start_date.value and draft.start_time.value:
        try:
            start_str = f"{draft.start_date.value}T{draft.start_time.value}"
            end_str = f"{end_date}T{end_time}"
            start_dt = __import__("datetime").datetime.fromisoformat(start_str)
            end_dt = __import__("datetime").datetime.fromisoformat(end_str)
            if end_dt <= start_dt:
                blocking_errors.append({
                    "code": "end_before_start",
                    "message_ru": "Время окончания должно быть позже времени начала",
                    "field": "duration",
                    "how_to_fix": "Увеличьте длительность или измените время начала.",
                })
        except (ValueError, TypeError):
            blocking_errors.append({
                "code": "invalid_datetime_format",
                "message_ru": "Некорректный формат даты/времени",
                "field": "start_date",
                "how_to_fix": "Проверьте формат даты и времени.",
            })

    for att in draft.required_attendees:
        if not att.email:
            blocking_errors.append({
                "code": "required_participant_no_email",
                "message_ru": f"Не найден email участника {att.full_name}",
                "field": "attendees",
                "how_to_fix": f"Укажите email для обязательного участника «{att.full_name}» или удалите его из состава.",
            })

    for att in draft.required_attendees + draft.optional_attendees:
        if att.email and not validate_email(att.email):
            blocking_errors.append({
                "code": "invalid_email",
                "message_ru": f"Некорректный email: {att.email}",
                "field": "attendees",
                "how_to_fix": f"Исправьте email участника «{att.full_name}».",
            })

    if draft.match_status in ("matched", "checked") and any(
        m.decision.value in ("DUPLICATE", "POSSIBLE_DUPLICATE")
        for m in draft.calendar_matches
    ):
        blocking_errors.append({
            "code": "duplicate",
            "message_ru": "Обнаружен дубликат в календаре",
            "field": "match",
            "how_to_fix": "Проверьте дубликаты в календаре. Возможно, событие уже существует.",
        })

    if draft.match_status == "stale":
        warnings.append({
            "code": "stale_match",
            "message_ru": "После изменений нужно повторно проверить дубли",
            "field": "match",
            "how_to_fix": "Нажмите кнопку «Проверить дубль».",
        })

    return PreflightResult(
        ready=len(blocking_errors) == 0,
        blocking_errors=blocking_errors,
        warnings=warnings,
    )


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

    if draft.match_status in ("matched", "checked") and any(
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