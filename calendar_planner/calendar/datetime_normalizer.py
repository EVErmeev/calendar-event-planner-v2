from __future__ import annotations

from datetime import datetime
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


def resolve_timezone(tz_str: str | None, fallback: str = "UTC") -> str:
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


def parse_iso_datetime(raw: str, raw_tz: str | None = None, fallback_tz: str = "UTC") -> NormalizedDateTime:
    warnings: list[str] = []
    tz_str = raw_tz or fallback_tz
    resolved_tz = resolve_timezone(tz_str)

    aware_dt: datetime

    if raw.endswith("Z"):
        try:
            aware_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            resolved_tz = "UTC"
        except ValueError:
            aware_dt = datetime.fromisoformat(raw)
    elif "+" in raw[10:] or (raw.count("-") >= 3 and "-" in raw[10:]):
        try:
            aware_dt = datetime.fromisoformat(raw)
        except ValueError:
            naive = datetime.fromisoformat(raw[:19])
            zone = ZoneInfo(resolved_tz)
            aware_dt = naive.replace(tzinfo=zone)
    else:
        naive = datetime.fromisoformat(raw)
        try:
            zone = ZoneInfo(resolved_tz)
            aware_dt = naive.replace(tzinfo=zone)
        except Exception:
            zone = ZoneInfo(fallback_tz)
            aware_dt = naive.replace(tzinfo=zone)
            resolved_tz = fallback_tz
            warnings.append(f"Cannot resolve timezone '{raw_tz}', using {fallback_tz}")

    utc_dt = aware_dt.astimezone(ZoneInfo("UTC"))
    try:
        display_zone = ZoneInfo(resolved_tz)
        display_dt = aware_dt.astimezone(display_zone)
    except Exception:
        display_dt = aware_dt

    return NormalizedDateTime(
        raw_datetime=raw,
        raw_timezone=raw_tz,
        aware_datetime=aware_dt,
        utc_datetime=utc_dt,
        display_datetime=display_dt,
        display_timezone=resolved_tz,
        warnings=warnings,
    )


def normalize_calendar_event_start(raw_event: dict) -> NormalizedDateTime | None:
    start_raw = raw_event.get("start") or raw_event.get("startDateTime") or {}
    if isinstance(start_raw, dict):
        dt_str = start_raw.get("dateTime")
        tz = start_raw.get("timeZone")
        if dt_str:
            return parse_iso_datetime(dt_str, tz)
    elif isinstance(start_raw, str):
        return parse_iso_datetime(start_raw)
    return None