from __future__ import annotations

import os
from pathlib import Path

from calendar_planner.domain.enums import MeetingDatePolicy


class Settings:
    def __init__(self) -> None:
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
        self.DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Yekaterinburg")
        self.DEFAULT_DURATION_SUGGESTION: int = int(os.getenv("DEFAULT_DURATION_SUGGESTION", "60"))
        self.MEETING_DATE_POLICY: MeetingDatePolicy = MeetingDatePolicy(
            os.getenv("MEETING_DATE_POLICY", "AGREED_ONLY")
        )
        self.CALENDAR_DATE_RANGE_BUFFER_DAYS: int = int(
            os.getenv("CALENDAR_DATE_RANGE_BUFFER_DAYS", "7")
        )
        self.CALENDAR_MATCH_TOLERANCE_MINUTES: int = int(
            os.getenv("CALENDAR_MATCH_TOLERANCE_MINUTES", "30")
        )
        self.CALENDAR_SUBJECT_THRESHOLD: float = float(
            os.getenv("CALENDAR_SUBJECT_THRESHOLD", "0.75")
        )
        self.CONTACT_FUZZY_THRESHOLD: float = float(
            os.getenv("CONTACT_FUZZY_THRESHOLD", "0.85")
        )
        self.PERFORMER_EMAIL_DOMAINS: list[str] = [
            d.strip() for d in os.getenv("PERFORMER_EMAIL_DOMAINS", "1bit.ru").split(",") if d.strip()
        ]
        self.RUNS_DIR: Path = Path(os.getenv("RUNS_DIR", "./runs"))
        self.MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

        self.MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "true").lower() == "true"
        self.MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "")
        self.MCP_STDIO_COMMAND: str = os.getenv("MCP_STDIO_COMMAND", "")
        self.MCP_CALENDAR_FIND_TOOL: str = os.getenv("MCP_CALENDAR_FIND_TOOL", "list_events")
        self.MCP_CALENDAR_CREATE_TOOL: str = os.getenv("MCP_CALENDAR_CREATE_TOOL", "create_event")
        self.MCP_DIRECTORY_SEARCH_TOOL: str = os.getenv("MCP_DIRECTORY_SEARCH_TOOL", "search_employees")

        self.GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
        self.GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")

        self.EXCHANGE_ENABLED: bool = os.getenv("EXCHANGE_ENABLED", "false").lower() == "true"

        self.EWS_ENDPOINT: str = os.getenv("EWS_ENDPOINT", "https://mail.1cbit.ru/EWS/Exchange.asmx")
        self.EWS_USERNAME: str = os.getenv("EWS_USERNAME", "")
        self.EWS_PASSWORD: str = os.getenv("EWS_PASSWORD", "")

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()