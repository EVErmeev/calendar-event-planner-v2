"""Credential provider for EWS authentication.

Supports:
- Session-only credentials (memory, cleared on exit)
- Windows Credential Manager (optional, with explicit user consent)
Never stores passwords in .env, config files, logs, or session artifacts.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CredentialResult:
    username: str = ""
    password: str = ""
    source: str = "none"
    available: bool = False

    def __repr__(self) -> str:
        masked = f"{self.password[:2]}***" if len(self.password) > 2 else "***"
        return (
            f"CredentialResult(username={self.username!r}, "
            f"password={masked!r}, source={self.source!r}, "
            f"available={self.available!r})"
        )


class CredentialProvider:
    """Manages EWS credentials without storing in files."""

    def __init__(self):
        self._session_username: str = ""
        self._session_password: str = ""
        self._credential_manager_target = "calendar-event-planner-v2/ews"

    def get_credentials(self) -> CredentialResult:
        """Get credentials from available sources.

        Priority: session → credential manager → env (deprecated, warning) → none
        """
        # 1. Session-only (already provided this run)
        if self._session_username and self._session_password:
            return CredentialResult(
                username=self._session_username,
                password=self._session_password,
                source="session",
                available=True,
            )

        # 2. Windows Credential Manager
        try:
            creds = self._read_from_credential_manager()
            if creds.available:
                return creds
        except Exception:
            logger.debug("Credential Manager read failed", exc_info=True)

        # Don't fall through to env — .env should not hold passwords
        return CredentialResult(available=False)

    def set_session_credentials(self, username: str, password: str) -> None:
        """Store credentials for current session only."""
        self._session_username = username
        self._session_password = password
        logger.info("Credentials stored for session (memory only)")

    def clear_session_credentials(self) -> None:
        """Clear session credentials."""
        self._session_username = ""
        self._session_password = ""
        logger.info("Session credentials cleared")

    def save_to_credential_manager(self, username: str, password: str) -> bool:
        """Save credentials to Windows Credential Manager.

        Returns True on success.
        """
        try:
            result = subprocess.run(
                [
                    "cmdkey", f"/generic:{self._credential_manager_target}",
                    f"/user:{username}",
                    f"/pass:{password}",
                ],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if result.returncode == 0:
                logger.info("Credentials saved to Windows Credential Manager")
                return True
            logger.warning("Credential Manager save failed: %s", result.stderr.strip())
            return False
        except Exception:
            logger.warning("Credential Manager save failed", exc_info=True)
            return False

    def remove_from_credential_manager(self) -> bool:
        """Remove stored credentials from Windows Credential Manager."""
        try:
            result = subprocess.run(
                ["cmdkey", f"/delete:{self._credential_manager_target}"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            return result.returncode == 0
        except Exception:
            logger.warning("Credential Manager delete failed", exc_info=True)
            return False

    def _read_from_credential_manager(self) -> CredentialResult:
        """Read credentials from Windows Credential Manager."""
        try:
            env = os.environ.copy()
            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    (
                        f"$c = Get-StoredCredential -Target '{self._credential_manager_target}' -ErrorAction Stop; "
                        "Write-Output ('USER:' + $c.UserName); "
                        "Write-Output ('PASS:' + $c.Password)"
                    ),
                ],
                capture_output=True, text=True, timeout=10, check=False, env=env,
            )
            if result.returncode != 0:
                return CredentialResult(available=False)

            username = ""
            password = ""
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("USER:"):
                    username = line[5:]
                elif line.startswith("PASS:"):
                    password = line[5:]

            if username and password:
                return CredentialResult(
                    username=username,
                    password=password,
                    source="credential_manager",
                    available=True,
                )
        except Exception:
            pass

        return CredentialResult(available=False)

    def has_session_credentials(self) -> bool:
        return bool(self._session_username and self._session_password)
