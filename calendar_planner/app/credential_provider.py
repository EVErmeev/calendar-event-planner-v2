"""Credential provider for EWS authentication.

Uses Python keyring for symmetric read/write/delete on Windows Credential Manager.
Session-only credentials supported as default mode.
Never stores passwords in .env, config files, logs, or session artifacts.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SERVICE_NAME = "calendar-event-planner-v2/ews"


@dataclass
class CredentialResult:
    username: str = ""
    password: str = ""
    source: str = "none"
    available: bool = False

    def __repr__(self) -> str:
        return f"CredentialResult(username={self.username!r}, source={self.source!r}, available={self.available!r})"


@dataclass
class CredentialOperationResult:
    success: bool
    source: str = "none"
    error_code: str | None = None
    safe_message: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


class CredentialProvider:
    """Manages EWS credentials. Session-only by default, optional persistent via keyring."""

    def __init__(self):
        self._session_username: str = ""
        self._session_password: str = ""

    def get_credentials(self) -> CredentialResult:
        if self._session_username and self._session_password:
            return CredentialResult(username=self._session_username, password=self._session_password, source="session", available=True)

        return CredentialResult(available=False)

    def set_session_credentials(self, username: str, password: str) -> None:
        self._session_username = username
        self._session_password = password

    def clear_session_credentials(self) -> None:
        self._session_username = ""
        self._session_password = ""

    def has_session_credentials(self) -> bool:
        return bool(self._session_username and self._session_password)

    def save_persistent(self, username: str, password: str) -> CredentialOperationResult:
        try:
            import keyring
            keyring.set_password(SERVICE_NAME, username, password)
            # Verify it was saved
            verify = keyring.get_password(SERVICE_NAME, username)
            if verify == password:
                self._session_username = username
                self._session_password = password
                return CredentialOperationResult(success=True, source="credential_manager", safe_message="Saved to Windows Credential Manager")
            return CredentialOperationResult(success=False, source="credential_manager", error_code="VERIFY_FAILED", safe_message="Saved but verification failed")
        except Exception as e:
            logger.warning("Credential Manager save failed: %s", e)
            return CredentialOperationResult(success=False, source="credential_manager", error_code="KEYRING_ERROR", safe_message=str(e)[:200])

    def delete_persistent(self, username: str) -> CredentialOperationResult:
        try:
            import keyring
            keyring.delete_password(SERVICE_NAME, username)
            self.clear_session_credentials()
            return CredentialOperationResult(success=True, source="credential_manager", safe_message="Deleted from Windows Credential Manager")
        except Exception as e:
            logger.warning("Credential Manager delete failed: %s", e)
            return CredentialOperationResult(success=False, source="credential_manager", error_code="DELETE_ERROR", safe_message=str(e)[:200])

    def load_persistent(self, username: str) -> CredentialResult:
        try:
            import keyring
            stored = keyring.get_password(SERVICE_NAME, username)
            if stored:
                self._session_username = username
                self._session_password = stored
                return CredentialResult(username=username, password=stored, source="credential_manager", available=True)
        except Exception:
            logger.debug("keyring load failed", exc_info=True)
        return CredentialResult(available=False)
