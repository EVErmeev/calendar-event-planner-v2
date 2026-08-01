from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones

from calendar_planner.domain.models import NormalizedDateTime

WINDOWS_TIMEZONE_MAP: dict[str, str] = {
    "Ekaterinburg Standard Time": "Asia/Yekaterinburg",
    "Russian Standard Time": "Europe/Moscow",
    "Moscow Standard Time": "Europe/Moscow",
    "Russia TZ 4 Standard Time": "Asia/Yekaterinburg",
    "Russia TZ 3 Standard Time": "Europe/Moscow",
}

KNOWN_TIMEZONE_ALIASES: dict[str, str] = {
    "екб": "Asia/Yekaterinburg",
    "ekb": "Asia/Yekaterinburg",
    "екатеринбург": "Asia/Yekaterinburg",
    "yekaterinburg": "Asia/Yekaterinburg",
    "мск": "Europe/Moscow",
    "msk": "Europe/Moscow",
    "москва": "Europe/Moscow",
    "moscow": "Europe/Moscow",
    "нск": "Asia/Novosibirsk",
    "nsk": "Asia/Novosibirsk",
    "новосибирск": "Asia/Novosibirsk",
    "novosibirsk": "Asia/Novosibirsk",
}


def resolve_timezone(tz_str: str | None, fallback: str = "Asia/Yekaterinburg") -> str:
    if not tz_str:
        return fallback
    tz_lower = tz_str.strip().lower()

    if tz_lower in KNOWN_TIMEZONE_ALIASES:
        return KNOWN_TIMEZONE_ALIASES[tz_lower]

    if tz_str in WINDOWS_TIMEZONE_MAP:
        return WINDOWS_TIMEZONE_MAP[tz_str]

    if tz_str in available_timezones():
        return tz_str

    for alias, iana in KNOWN_TIMEZONE_ALIASES.items():
        if alias in tz_lower:
            return iana

    return fallback


def parse_iso_datetime(raw: str, raw_tz: str | None = None, fallback_tz: str = "Asia/Yekaterinburg") -> NormalizedDateTime:
    warnings: list[str] = []
    tz_str = raw_tz or fallback_tz
    resolved_tz = resolve_timezone(tz_str)

    aware_dt: datetime

    if raw.endswith("Z"):
        try:
            aware_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            resolved_tz = "UTC"
        except ValueError:
            aware_dt = _parse_flexible(raw, "UTC")
    elif "+" in raw[10:] or raw.count("-") >= 3 and "-" in raw[10:]:
        try:
            aware_dt = datetime.fromisoformat(raw)
        except ValueError:
            aware_dt = _parse_flexible(raw, resolved_tz)
            warnings.append(f"Cannot parse offset from '{raw}', falling back to {resolved_tz}")
    else:
        naive = _parse_flexible(raw, resolved_tz)

        if naive.tzinfo is None:
            try:
                zone = ZoneInfo(resolved_tz)
                aware_dt = naive.replace(tzinfo=zone)
            except Exception:
                zone = ZoneInfo(fallback_tz)
                aware_dt = naive.replace(tzinfo=zone)
                resolved_tz = fallback_tz
                warnings.append(f"Cannot resolve timezone '{raw_tz}', using {fallback_tz}")
        else:
            aware_dt = naive

    utc_dt = aware_dt.astimezone(ZoneInfo("UTC"))
    try:
        display_zone = ZoneInfo(resolved_tz)
        display_dt = aware_dt.astimezone(display_zone)
    except Exception:
        display_dt = aware_dt
        resolved_tz = str(aware_dt.tzinfo) if aware_dt.tzinfo else "UTC"

    return NormalizedDateTime(
        raw_datetime=raw,
        raw_timezone=raw_tz,
        aware_datetime=aware_dt,
        utc_datetime=utc_dt,
        display_datetime=display_dt,
        display_timezone=resolved_tz,
        warnings=warnings,
    )


def _parse_flexible(raw: str, tz_name: str) -> datetime:
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None and fmt.endswith("%z"):
                pass
            return dt
        except ValueError:
            continue

    raise ValueError(f"Cannot parse datetime: '{raw}'")


def parse_date_time(
    date_str: str | None,
    time_str: str | None,
    tz_str: str | None = None,
    fallback_tz: str = "Asia/Yekaterinburg",
) -> NormalizedDateTime | None:
    if not date_str or not time_str:
        return None

    raw = f"{date_str}T{time_str}"

    try:
        return parse_iso_datetime(raw, tz_str, fallback_tz)
    except ValueError:
        raw = f"{date_str} {time_str}"
        return parse_iso_datetime(raw, tz_str, fallback_tz)


def normalize_date_value(value: str) -> str | None:
    if not value or not value.strip():
        return None

    cleaned = value.strip().replace("\u00a0", " ")

    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", cleaned):
        day, month, year = cleaned.split(".")
        return f"{year}-{month}-{day}"

    if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
        return cleaned

    if re.match(r"^\d{2}/\d{2}/\d{4}$", cleaned):
        month, day, year = cleaned.split("/")
        return f"{year}-{month}-{day}"

    return cleaned


def normalize_time_value(value: str) -> str | None:
    if not value or not value.strip():
        return None

    cleaned = value.strip().replace("\u00a0", " ")

    if re.match(r"^\d{1,2}:\d{2}$", cleaned):
        hour, minute = cleaned.split(":")
        return f"{int(hour):02d}:{minute}"

    if re.match(r"^\d{1,2}:\d{2}:\d{2}$", cleaned):
        return cleaned

    if re.match(r"^\d{1,2}\.\d{2}$", cleaned):
        hour, minute = cleaned.split(".")
        return f"{int(hour):02d}:{minute}"

    return cleaned


def datetime_to_payload_start(
    date_str: str,
    time_str: str,
    tz_str: str,
) -> dict:
    return {
        "dateTime": f"{date_str}T{time_str}:00",
        "timeZone": tz_str,
    }


def compute_end_datetime(
    start_date: str,
    start_time: str,
    duration_minutes: int,
) -> dict:
    start_dt = datetime.fromisoformat(f"{start_date}T{start_time}")
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return {
        "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def are_same_moment(a: NormalizedDateTime, b: NormalizedDateTime) -> bool:
    return abs((a.utc_datetime - b.utc_datetime).total_seconds()) < 1