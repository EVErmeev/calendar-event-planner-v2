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
        self.credentials_revision: int = 0

    def get_credentials(self) -> CredentialResult:
        if self._session_username and self._session_password:
            return CredentialResult(username=self._session_username, password=self._session_password, source="session", available=True)

        return CredentialResult(available=False)

    def set_session_credentials(self, username: str, password: str) -> None:
        self._session_username = username
        self._session_password = password
        self.credentials_revision += 1

    def clear_session_credentials(self) -> None:
        self._session_username = ""
        self._session_password = ""
        self.credentials_revision += 1

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
                self.credentials_revision += 1
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
            self.credentials_revision += 1
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
                self.credentials_revision += 1
                return CredentialResult(username=username, password=stored, source="credential_manager", available=True)
        except Exception:
            logger.debug("keyring load failed", exc_info=True)
        return CredentialResult(available=False)

    def read_after_write(self, username: str, expected: str) -> bool:
        """Read back a persisted credential in the same process and compare in memory."""
        try:
            import keyring
            stored = keyring.get_password(SERVICE_NAME, username)
            return stored == expected
        except Exception:
            logger.debug("read-after-write failed", exc_info=True)
            return False


def ews_save_decision(remember: bool, save_result: CredentialOperationResult | None) -> dict:
    """Decide UI behaviour after an EWS save attempt (pure, tkinter-free).

    Returns a dict consumed by the UI:
      apply_mask / clear_field / checkbox / status / success / error_code
    """
    if remember:
        if save_result is not None and save_result.success:
            return {
                "apply_mask": True,
                "clear_field": False,
                "checkbox": True,
                "success": True,
                "status": "сохранён в Windows Credential Manager",
            }
        error_code = (save_result.error_code if save_result is not None else None) or "SAVE_ERROR"
        return {
            "apply_mask": False,
            "clear_field": False,
            "checkbox": True,
            "success": False,
            "error_code": error_code,
            "status": f"ошибка сохранения ({error_code})",
        }
    return {
        "apply_mask": True,
        "clear_field": False,
        "checkbox": False,
        "success": True,
        "session_only": True,
        "status": "Пароль сохранён только до закрытия приложения",
    }
