"""Regression tests for v1.0.1 — MCP runtime application and EWS persistence.

Covers the TZ blocks:
  - configure_mcp_stdio updates settings/.env/transport/gateway in-process;
  - reload_mcp_from_settings;
  - EnvConfigWriter safety (unknown keys, no password, path with spaces);
  - keyring in pyproject deps and launcher dependency repair;
  - EWS persistent save success/failure, read-after-write, new-process load;
  - 0 create_event calls.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path
from unittest import mock

import pytest

from calendar_planner.app import env_config
from calendar_planner.app.container import AppContainer
from calendar_planner.app.credential_provider import (
    CredentialOperationResult,
    CredentialProvider,
    ews_save_decision,
)
from calendar_planner.app.settings import Settings

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fake stdio transport
# ---------------------------------------------------------------------------
class FakeStdioTransport:
    def __init__(self, command: str):
        self.command = command
        self.tools: list[dict] = []
        self._connected = False

    def connect(self) -> dict:
        self._connected = True
        self.tools = [
            {"name": "find_events"},
            {"name": "create_event"},
            {"name": "find_emails"},
            {"name": "search_emails"},
        ]
        return {"component": "MCP Transport", "status": "success", "tool_count": len(self.tools)}

    def is_connected(self) -> bool:
        return self._connected

    def list_tools(self) -> list[str]:
        return [t["name"] for t in self.tools]

    def call_tool(self, name: str, arguments: dict):
        if name == "find_events":
            return {
                "events": [{
                    "id": "evt-1",
                    "subject": "Sync",
                    "start": "2026-08-03T10:00:00",
                    "end": "2026-08-03T11:00:00",
                }]
            }
        return {"ok": True}

    def check_connection(self) -> dict:
        return {"component": "MCP Transport", "status": "success", "tool_count": len(self.tools)}

    def close(self) -> None:
        self._connected = False


# ---------------------------------------------------------------------------
# Fake keyring
# ---------------------------------------------------------------------------

class _FakeKeyring:
    def __init__(self):
        self._store: dict[tuple, str] = {}
        self.calls: list[str] = []

    def set_password(self, service, username, password):
        self.calls.append("set")
        self._store[(service, username)] = password

    def get_password(self, service, username):
        self.calls.append("get")
        return self._store.get((service, username))

    def delete_password(self, service, username):
        self.calls.append("delete")
        self._store.pop((service, username), None)


def _install_fake_keyring(monkeypatch) -> _FakeKeyring:
    fake = _FakeKeyring()
    mod = types.ModuleType("keyring")
    mod.set_password = fake.set_password
    mod.get_password = fake.get_password
    mod.delete_password = fake.delete_password
    monkeypatch.setitem(sys.modules, "keyring", mod)
    return fake


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_transport(monkeypatch):
    import calendar_planner.app.container as cmod
    monkeypatch.setattr(cmod, "StdioMCPTransport", FakeStdioTransport)
    return FakeStdioTransport


@pytest.fixture
def env_dir(monkeypatch):
    tmp = tempfile.mkdtemp()
    root = Path(tmp)
    monkeypatch.setattr(env_config, "_project_root", lambda: root)
    return root


@pytest.fixture
def container(env_dir, fake_transport):
    import os
    keys = ["MCP_ENABLED", "MCP_STDIO_COMMAND", "MCP_SERVER_URL",
            "MCP_CALENDAR_FIND_TOOL", "MCP_CALENDAR_CREATE_TOOL"]
    os_env = mock.patch.dict("os.environ", {"APP_ENV": "test"})
    os_env.start()
    try:
        c = AppContainer(Settings())
        yield c
    finally:
        os_env.stop()
        for k in keys:
            os.environ.pop(k, None)


def _fresh_settings_from(env_file: Path) -> Settings:
    import os
    for key, value in env_config.EnvConfigWriter(env_file).read_dict().items():
        os.environ[key] = value
    return Settings()


# ---------------------------------------------------------------------------
# MCP runtime configuration
# ---------------------------------------------------------------------------

class TestMCPConfigure:
    CMD = 'powershell -File "C:\\Users\\a b\\exchange-mcp.ps1"'

    def test_configure_updates_runtime_settings(self, container, env_dir):
        res = container.configure_mcp_stdio(self.CMD, "find_events", "create_event", persist=True)
        assert container.settings.MCP_ENABLED is True
        assert container.settings.MCP_STDIO_COMMAND == self.CMD
        assert container.settings.MCP_CALENDAR_FIND_TOOL == "find_events"
        assert container.settings.MCP_CALENDAR_CREATE_TOOL == "create_event"
        assert res["status"] == "success"

    def test_configure_saves_actual_env(self, container, env_dir):
        container.configure_mcp_stdio(self.CMD, "find_events", "create_event", persist=True)
        writer = env_config.EnvConfigWriter(env_dir / ".env")
        data = writer.read_dict()
        assert data["MCP_ENABLED"] == "true"
        assert data["MCP_STDIO_COMMAND"] == self.CMD
        assert data["MCP_CALENDAR_FIND_TOOL"] == "find_events"
        assert data["MCP_CALENDAR_CREATE_TOOL"] == "create_event"
        assert data.get("MCP_SERVER_URL", "") == ""

    def test_configure_connects_and_checks_tools(self, container, env_dir):
        res = container.configure_mcp_stdio(self.CMD, "find_events", "create_event", persist=True)
        assert res["connected"] is True
        assert res["find_events"] is True
        assert res["create_event"] is True
        assert res["tools_count"] >= 2
        assert res["calendar_gateway_ready"] is True

    def test_calendar_gateway_recreated_and_reads(self, container, env_dir):
        container.configure_mcp_stdio(self.CMD, "find_events", "create_event", persist=True)
        gw = container.get_calendar_gateway()
        events = gw.find_events("2026-08-03", "2026-08-04")
        assert len(events) == 1

    def test_new_process_loads_configuration(self, container, env_dir):
        container.configure_mcp_stdio(self.CMD, "find_events", "create_event", persist=True)
        fresh = _fresh_settings_from(env_dir / ".env")
        assert fresh.MCP_ENABLED is True
        assert fresh.MCP_STDIO_COMMAND == self.CMD
        assert fresh.MCP_CALENDAR_FIND_TOOL == "find_events"

    def test_reload_mcp_from_settings(self, container, env_dir):
        container.configure_mcp_stdio(self.CMD, "find_events", "create_event", persist=True)
        container._mcp_transport.close()
        container._calendar_gateway = None
        res = container.reload_mcp_from_settings()
        assert res["status"] == "success"
        assert res["connected"] is True
        assert container._calendar_gateway is not None

    def test_env_path_under_project_root(self):
        default_path = env_config.EnvConfigWriter.default().path
        assert default_path.name == ".env"
        assert REPO_ROOT in default_path.parents

    def test_self_heals_mcp_from_env_when_settings_empty(self, env_dir, monkeypatch):
        """A container whose Settings missed .env still picks up MCP from .env."""
        import calendar_planner.app.container as cmod
        monkeypatch.setattr(cmod, "StdioMCPTransport", FakeStdioTransport)
        (env_dir / ".env").write_text(
            "MCP_ENABLED=true\n"
            'MCP_STDIO_COMMAND=powershell -File "C:\\x y\\x.ps1"\n'
            "MCP_CALENDAR_FIND_TOOL=find_events\n"
            "MCP_CALENDAR_CREATE_TOOL=create_event\n",
            encoding="utf-8",
        )
        os_env = mock.patch.dict("os.environ", {"APP_ENV": "development"}, clear=False)
        os_env.start()
        try:
            for k in ("MCP_ENABLED", "MCP_STDIO_COMMAND", "MCP_SERVER_URL",
                      "MCP_CALENDAR_FIND_TOOL", "MCP_CALENDAR_CREATE_TOOL"):
                os.environ.pop(k, None)
            s = Settings()
            assert s.MCP_STDIO_COMMAND == ""
            c = AppContainer(s)
            res = c.init_mcp()
            assert res.get("status") == "success"
            assert "x.ps1" in s.MCP_STDIO_COMMAND
            assert s.MCP_STDIO_COMMAND.startswith("powershell")
        finally:
            os_env.stop()

    def test_zero_create_event_calls(self, container, env_dir):
        import calendar_planner.app.container as cmod
        calls = []

        class TrackingTransport(FakeStdioTransport):
            def call_tool(self, name, arguments):
                calls.append(name)
                return super().call_tool(name, arguments)

        cmod.StdioMCPTransport = TrackingTransport
        container.configure_mcp_stdio(self.CMD, "find_events", "create_event", persist=True)
        assert "create_event" not in calls
        gw = container.get_calendar_gateway()
        gw.find_events("2026-08-03", "2026-08-04")
        assert "find_events" in calls
        assert "create_event" not in calls


# ---------------------------------------------------------------------------
# EnvConfigWriter safety
# ---------------------------------------------------------------------------

class TestEnvConfigWriter:
    def test_preserves_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            p.write_text("TIMEZONE=UTC\nGOOGLE_API_KEY=abc\n", encoding="utf-8")
            w = env_config.EnvConfigWriter(p)
            w.set({"MCP_ENABLED": "true"})
            data = w.read_dict()
            assert data["TIMEZONE"] == "UTC"
            assert data["GOOGLE_API_KEY"] == "abc"
            assert data["MCP_ENABLED"] == "true"

    def test_does_not_write_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            p.write_text("", encoding="utf-8")
            w = env_config.EnvConfigWriter(p)
            w.set({"EWS_PASSWORD": "secret", "MCP_ENABLED": "true"})
            text = p.read_text(encoding="utf-8")
            assert "secret" not in text
            assert "EWS_PASSWORD" not in text
            assert "MCP_ENABLED=true" in text

    def test_path_with_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a b" / ".env"
            p.parent.mkdir()
            w = env_config.EnvConfigWriter(p)
            cmd = 'powershell -File "C:\\Users\\x y\\x.ps1"'
            w.set({"MCP_STDIO_COMMAND": cmd})
            assert w.read_dict()["MCP_STDIO_COMMAND"] == cmd

    def test_creates_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            w = env_config.EnvConfigWriter(p)
            w.set({"MCP_ENABLED": "true"})
            assert p.exists()

    def test_no_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            p.write_text("MCP_ENABLED=true\nMCP_ENABLED=false\n", encoding="utf-8")
            w = env_config.EnvConfigWriter(p)
            w.set({"MCP_ENABLED": "true"})
            lines = p.read_text(encoding="utf-8").splitlines()
            assert sum("MCP_ENABLED=" in l for l in lines) == 1


# ---------------------------------------------------------------------------
# EWS persistence
# ---------------------------------------------------------------------------

class TestEWSPersistence:
    def test_persistent_save_success_masks(self, monkeypatch):
        fake = _install_fake_keyring(monkeypatch)
        cp = CredentialProvider()
        result = cp.save_persistent("EVErmeev", "pw")
        assert result.success
        assert fake.calls == ["set", "get"]
        decision = ews_save_decision(True, result)
        assert decision["apply_mask"] is True
        assert decision["checkbox"] is True
        assert decision["status"] == "сохранён в Windows Credential Manager"

    def test_persistent_save_failure_keeps_field(self):
        decision = ews_save_decision(True, CredentialOperationResult(success=False, error_code="KEYRING_ERROR"))
        assert decision["apply_mask"] is False
        assert decision["clear_field"] is False
        assert decision["success"] is False
        assert decision["error_code"] == "KEYRING_ERROR"

    def test_session_only_status_explicit(self):
        decision = ews_save_decision(False, None)
        assert decision["session_only"] is True
        assert decision["status"] == "Пароль сохранён только до закрытия приложения"

    def test_read_after_write(self, monkeypatch):
        fake = _install_fake_keyring(monkeypatch)
        cp = CredentialProvider()
        result = cp.save_persistent("EVErmeev", "pw123")
        assert result.success
        assert cp.read_after_write("EVErmeev", "pw123") is True
        assert cp.read_after_write("EVErmeev", "wrong") is False

    def test_exact_username_lookup(self, monkeypatch):
        fake = _install_fake_keyring(monkeypatch)
        cp = CredentialProvider()
        cp.save_persistent("EVErmeev", "pw")
        # wrong-case / different username must not collide
        assert cp.read_after_write("EVermeev", "pw") is False

    def test_new_process_persistent_load(self, monkeypatch):
        fake = _install_fake_keyring(monkeypatch)
        cp1 = CredentialProvider()
        assert cp1.save_persistent("EVErmeev", "pw").success

        # new provider = new process
        cp2 = CredentialProvider()
        creds = cp2.load_persistent("EVErmeev")
        assert creds.available
        assert creds.source == "credential_manager"

    def test_directory_gateway_recreated(self, monkeypatch):
        fake = _install_fake_keyring(monkeypatch)
        c = AppContainer(Settings())
        assert c._directory_gateway is None
        c._directory_gateway = "cached"
        c.reload_persistent_ews_credentials()
        assert c._directory_gateway is None


# ---------------------------------------------------------------------------
# Placeholder date/time values (Stage 3 regression)
# ---------------------------------------------------------------------------

class TestPlaceholderDateTimes:
    def test_normalize_date_placeholder_returns_none(self):
        from calendar_planner.extraction.datetime_normalizer import normalize_date_value
        for v in ("-", "- -", "—", "–", "/", "н/д", "   "):
            assert normalize_date_value(v) is None

    def test_normalize_time_placeholder_returns_none(self):
        from calendar_planner.extraction.datetime_normalizer import normalize_time_value
        for v in ("-", "- -", "—", "–", "н/д"):
            assert normalize_time_value(v) is None

    def test_normalize_real_values_kept(self):
        from calendar_planner.extraction.datetime_normalizer import (
            normalize_date_value,
            normalize_time_value,
        )
        assert normalize_date_value("31.07.2026") == "2026-07-31"
        assert normalize_time_value("10:00") == "10:00"

    def test_extractor_skips_dash_rows_without_crash(self):
        from calendar_planner.domain.enums import MeetingDatePolicy
        from calendar_planner.domain.models import ExtractedSource, SourceReference
        from calendar_planner.extraction.structured import StructuredExtractor

        sheet = [
            ["№ 1", "Тема", "Согласованная дата", "Согласованное время"],
            ["1", "Обычная", "31.07.2026", "10:00"],
            ["2", "С прочерками", "-", "-"],
            ["3", "Ещё прочерк", "–", "—"],
        ]
        src = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={"План": sheet},
        )
        ex = StructuredExtractor(date_policy=MeetingDatePolicy.AGREED_ONLY)
        res = ex.extract(src)
        candidates = res.get("План", [])
        assert len(candidates) == 1
        assert candidates[0].start_date == "2026-07-31"


# ---------------------------------------------------------------------------
# create_event real outcome (participants / MCP regression)
# ---------------------------------------------------------------------------

class TestCreateInterpretation:
    def _gw(self, result):
        from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway
        def call(tool, args):
            assert tool == "create_event"
            return result
        return MCPCalendarGateway(mcp_call_function=call, create_tool="create_event")

    def test_dict_with_id_is_created(self):
        gw = self._gw({"id": "evt-123"})
        r = gw.create_event({"subject": "S", "start": "x"}, dry_run=False)
        assert r["status"] == "created"

    def test_success_text_is_created(self):
        gw = self._gw("Событие создано: Тестовая встреча")
        r = gw.create_event({"subject": "S", "start": "x"}, dry_run=False)
        assert r["status"] == "created"

    def test_error_text_is_failed_not_created(self):
        gw = self._gw("Ошибка: не удалось создать встречу (участники)")
        r = gw.create_event({"subject": "S", "start": "x"}, dry_run=False)
        assert r["status"] == "failed"
        assert r.get("error") == "CREATE_REJECTED"

    def test_unknown_text_is_failed(self):
        gw = self._gw("SERVER: no payload")
        r = gw.create_event({"subject": "S", "start": "x"}, dry_run=False)
        assert r["status"] == "failed"
        assert r.get("error") == "UNKNOWN_RESPONSE"

    def test_dry_run_untouched(self):
        gw = self._gw("whatever")
        r = gw.create_event({"subject": "S"}, dry_run=True)
        assert r["status"] == "dry_run"


# ---------------------------------------------------------------------------
# Duration hours column (header typo + unit inference)
# ---------------------------------------------------------------------------

class TestDurationHoursColumn:
    def test_header_typo_detected_as_hours(self):
        from calendar_planner.source.schema_detector import TableSchemaDetector
        det = TableSchemaDetector()
        det.detect([
            ["Тема", "Согласованная дата", "Согласованное время", "Длительнось, ч"],
            ["x", "31.07.2026", "10:00", "2"],
        ])
        assert det.duration_col == 3
        assert det.duration_unit == "hours"

    def test_value_2_hours_is_120_minutes(self):
        from calendar_planner.extraction.structured import StructuredExtractor
        ex = StructuredExtractor(numeric_duration_unit="auto")
        assert ex._parse_duration_cell("2", unit="hours") == 120
        assert ex._parse_duration_cell("4", unit="hours") == 240


# ---------------------------------------------------------------------------
# Packaging / launcher
# ---------------------------------------------------------------------------

class TestPackaging:
    def test_keyring_in_pyproject_dependencies(self):
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "keyring>=25.0.0" in text
        assert "dependencies" in text

    def test_launcher_dependency_repair(self):
        bat = (REPO_ROOT / "run_calendar_planner.bat").read_text(encoding="utf-8", errors="replace")
        assert "import calendar_planner, keyring, requests_ntlm" in bat
        assert "pip install -e ." in bat
        assert "keyring" in bat