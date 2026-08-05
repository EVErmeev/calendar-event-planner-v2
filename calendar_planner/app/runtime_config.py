"""Production user configuration: ``settings.json`` + migration from dev ``.env``.

In production the app must NOT rely on ``.env`` as the primary user mechanism.
The managed config lives in the user data dir::

    %LOCALAPPDATA%\\CalendarEventPlanner\\config\\settings.json

Secrets (EWS password) are NEVER stored here — they live in Windows Credential
Manager. This module reads/writes only safe fields.

Priority (highest first):

    CLI explicit override
    -> dev ``.env`` (only when APP_ENV=development)
    -> production settings.json
    -> defaults
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_SCHEMA_VERSION = 1

# Safe keys (password/token NEVER persisted here). Canonical set of managed
# user settings. New keys can be added without breaking migration.
SAFE_SETTINGS = {
    "first_run_completed": False,
    "ews_endpoint": "https://mail.1cbit.ru/EWS/Exchange.asmx",
    "ews_username": "",
    "mcp_transport": "bundled_stdio",
    "mcp_find_tool": "find_events",
    "mcp_create_tool": "create_event",
    "default_timezone": "Asia/Yekaterinburg",
    "calendar_missing_timezone": "UTC",
    "duration_numeric_unit": "auto",
    "source_schema_profile": "auto",
}

# Keys allowed to be imported from a legacy ``.env`` on first run.
ENV_IMPORT_MAP = {
    "DEFAULT_TIMEZONE": "default_timezone",
    "CALENDAR_MISSING_TIMEZONE": "calendar_missing_timezone",
    "DURATION_NUMERIC_UNIT": "duration_numeric_unit",
    "EWS_ENDPOINT": "ews_endpoint",
    "EWS_USERNAME": "ews_username",
}


def default_config_dir() -> Path:
    """User data dir: %LOCALAPPDATA%\\CalendarEventPlanner (fallback to home)."""
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if base:
        return Path(base) / "CalendarEventPlanner"
    return Path.home() / ".calendar_event_planner"


def default_config_path() -> Path:
    return default_config_dir() / "config" / "settings.json"


def default_logs_dir() -> Path:
    return default_config_dir() / "logs"


def default_runs_dir() -> Path:
    return default_config_dir() / "runs"


def default_diagnostics_dir() -> Path:
    return default_config_dir() / "diagnostics"


def _canonical(data: dict) -> dict:
    merged = dict(SAFE_SETTINGS)
    merged.update({k: v for k, v in data.items() if k in SAFE_SETTINGS})
    merged["schema_version"] = CONFIG_SCHEMA_VERSION
    return merged


class RuntimeConfig:
    """Read/write the production settings.json with migration support."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_config_path()

    def load(self) -> dict:
        if not self.path.exists():
            return _canonical({})
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return _canonical({})
        if not isinstance(data, dict):
            return _canonical({})
        return _canonical(data)

    def save(self, updates: dict) -> dict:
        data = self.load()
        data.update({k: v for k, v in updates.items() if k in SAFE_SETTINGS})
        data["schema_version"] = CONFIG_SCHEMA_VERSION
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return data

    # ------------------------------------------------------------------ export
    def as_env(self) -> dict[str, str]:
        """Expose safe settings as env-var style names for Settings compatibility."""
        cfg = self.load()
        return {
            "EWS_ENDPOINT": str(cfg.get("ews_endpoint", "")),
            "EWS_USERNAME": str(cfg.get("ews_username", "")),
            "DEFAULT_TIMEZONE": str(cfg.get("default_timezone", "")),
            "CALENDAR_MISSING_TIMEZONE": str(cfg.get("calendar_missing_timezone", "")),
            "DURATION_NUMERIC_UNIT": str(cfg.get("duration_numeric_unit", "")),
            "MCP_ENABLED": "true",
            "MCP_CALENDAR_FIND_TOOL": str(cfg.get("mcp_find_tool", "find_events")),
            "MCP_CALENDAR_CREATE_TOOL": str(cfg.get("mcp_create_tool", "create_event")),
        }

    # --------------------------------------------------------------- migration
    def import_legacy_env(self, env_path: Path) -> dict:
        """Import safe keys from a legacy ``.env`` (dev) file."""
        if not env_path.exists():
            return self.load()
        data: dict = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"')
            target = ENV_IMPORT_MAP.get(key.strip())
            if target:
                data[target] = value
        return self.save(data)

    def mark_first_run_completed(self, completed: bool = True) -> dict:
        return self.save({"first_run_completed": completed})