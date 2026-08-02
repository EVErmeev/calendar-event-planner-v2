"""Tests for CredentialProvider security."""
from __future__ import annotations

from calendar_planner.app.credential_provider import (
    CredentialProvider,
    CredentialResult,
)


class TestCredentialProvider:
    def test_session_credentials_available(self):
        cp = CredentialProvider()
        cp.set_session_credentials("test_user", "test_pass")
        creds = cp.get_credentials()
        assert creds.available
        assert creds.username == "test_user"
        assert creds.password == "test_pass"
        assert creds.source == "session"

    def test_clear_credentials(self):
        cp = CredentialProvider()
        cp.set_session_credentials("user", "pass")
        cp.clear_session_credentials()
        creds = cp.get_credentials()
        assert not creds.available

    def test_no_credentials_default(self):
        cp = CredentialProvider()
        creds = cp.get_credentials()
        assert not creds.available

    def test_has_session_credentials(self):
        cp = CredentialProvider()
        assert not cp.has_session_credentials()
        cp.set_session_credentials("u", "p")
        assert cp.has_session_credentials()

    def test_password_not_in_repr(self):
        cp = CredentialProvider()
        cp.set_session_credentials("user", "secret123")
        r = repr(cp)
        assert "secret123" not in r

    def test_result_repr_masks_password(self):
        cr = CredentialResult(username="user", password="s3cret", source="session", available=True)
        r = repr(cr)
        assert "s3cret" not in r.lower()

    def test_credential_manager_not_available_without_windows(self):
        cp = CredentialProvider()
        result = cp.load_persistent("unknown_user")
        assert not result.available
