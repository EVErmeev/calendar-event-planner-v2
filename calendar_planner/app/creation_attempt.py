"""Creation attempt diagnostics.

A single ``CreationAttemptResult`` captures everything about one attempt to
create a calendar event: the payload that was sent, the raw server response,
the classified outcome and, for created events, a post-create verification
result. Results are appended to ``runs/<session_id>/creation_attempts.jsonl``
and a rotating ``logs/creation.log``.

Secret values (passwords, tokens, cookies, authorizations) are stripped
before anything is written to disk.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from calendar_planner.app.settings import settings

_CREATION_STATUSES = (
    "validation_failed",
    "transport_failed",
    "server_rejected",
    "unknown_response",
    "created_unverified",
    "created_verified",
    "dry_run",
    "cancelled",
)

_SENSITIVE_KEYS = (
    "password",
    "passwd",
    "authorization",
    "token",
    "secret",
    "cookie",
    "credential",
    "api_key",
    "apikey",
    "access_key",
    "client_secret",
)


def sanitize_value(value: Any) -> Any:
    """Recursively redact sensitive fields for logging."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            low = str(k).lower()
            if any(s in low for s in _SENSITIVE_KEYS):
                out[k] = "[REDACTED]"
            else:
                out[k] = sanitize_value(v)
        return out
    if isinstance(value, list):
        return [sanitize_value(v) for v in value]
    return value


@dataclass
class CreationAttemptResult:
    attempt_id: str
    draft_id: str
    status: str
    created_at: str
    subject: str = ""
    error_code: str | None = None
    message: str = ""
    technical_message: str = ""
    payload: dict = field(default_factory=dict)
    raw: Any = None
    event_id: str | None = None
    url: str | None = None
    verification: dict | None = None
    session_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CreationAttemptResult:
        allowed = {
            "attempt_id", "draft_id", "status", "created_at", "subject",
            "error_code", "message", "technical_message", "payload", "raw",
            "event_id", "url", "verification", "session_id",
        }
        return cls(**{k: v for k, v in data.items() if k in allowed})


class CreationLogger:
    """Append-only JSONL writer + rotating text log with secret redaction."""

    def __init__(self, session_id: str | None = None, base_dir: Path | None = None):
        base_dir = base_dir or Path(settings.RUNS_DIR)
        base_dir = Path(base_dir)
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self._session_dir = base_dir / self.session_id
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._jsonl_path = self._session_dir / "creation_attempts.jsonl"
        self._lock = threading.Lock()
        self._text_logger = self._build_text_logger(base_dir)

    def _build_text_logger(self, base_dir: Path) -> logging.Logger:
        logger = logging.getLogger(f"creation.{self.session_id}")
        if logger.handlers:
            return logger
        logger.setLevel(logging.INFO)
        logs_dir = Path(settings.RUNS_DIR).parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            logs_dir / "creation.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
        return logger

    def record(self, result: CreationAttemptResult) -> str:
        attempt_id = result.attempt_id or str(uuid.uuid4())[:12]
        result.attempt_id = attempt_id
        result.session_id = self.session_id
        payload = sanitize_value(result.to_dict())
        line = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock:
            with self._jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            self._text_logger.info(
                "[%s] draft=%s status=%s code=%s msg=%s event=%s",
                attempt_id, result.draft_id, result.status,
                result.error_code, result.message[:120], result.event_id or "",
            )
        return attempt_id

    def path(self) -> Path:
        return self._jsonl_path

    def load(self) -> list[CreationAttemptResult]:
        if not self._jsonl_path.exists():
            return []
        results = []
        with self._jsonl_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(CreationAttemptResult.from_dict(json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    continue
        return results


def build_attempt(
    draft_id: str,
    status: str,
    subject: str = "",
    error_code: str | None = None,
    message: str = "",
    technical_message: str = "",
    payload: dict | None = None,
    raw: Any = None,
    event_id: str | None = None,
    url: str | None = None,
    verification: dict | None = None,
    created_at: str | None = None,
) -> CreationAttemptResult:
    return CreationAttemptResult(
        attempt_id=str(uuid.uuid4())[:12],
        draft_id=draft_id,
        status=status,
        created_at=created_at or datetime.now(UTC).isoformat(),
        subject=subject,
        error_code=error_code,
        message=message,
        technical_message=technical_message,
        payload=payload or {},
        raw=raw,
        event_id=event_id,
        url=url,
        verification=verification,
    )


def class_create_status(gateway_status: str, error_code: str | None) -> str:
    """Map gateway create outcome to a CreationAttemptResult status."""
    if gateway_status == "created":
        return "created_unverified"
    if gateway_status == "dry_run":
        return "dry_run"
    if gateway_status == "invalid":
        return "validation_failed"
    if gateway_status == "error":
        return "transport_failed"
    if gateway_status == "failed":
        if error_code == "UNKNOWN_RESPONSE":
            return "unknown_response"
        return "server_rejected"
    return "unknown_response"