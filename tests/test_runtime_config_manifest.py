from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from calendar_planner.version import __version__


class TestRuntimeConfig:
    def test_defaults_never_persist_password(self, tmp_path):
        from calendar_planner.app.runtime_config import RuntimeConfig

        cfg = RuntimeConfig(tmp_path / "settings.json")
        data = cfg.save({"ews_password": "secret", "first_run_completed": True})
        assert "ews_password" not in data
        assert data["first_run_completed"] is True

    def test_save_load_roundtrip(self, tmp_path):
        from calendar_planner.app.runtime_config import RuntimeConfig

        cfg = RuntimeConfig(tmp_path / "settings.json")
        cfg.save({"default_timezone": "Asia/Yekaterinburg"})
        loaded = cfg.load()
        assert loaded["default_timezone"] == "Asia/Yekaterinburg"
        assert loaded["schema_version"] == 1

    def test_unknown_keys_dropped(self, tmp_path):
        from calendar_planner.app.runtime_config import RuntimeConfig

        cfg = RuntimeConfig(tmp_path / "settings.json")
        cfg.save({"not_a_real_key": "x", "ews_endpoint": "https://e/"})
        loaded = cfg.load()
        assert "not_a_real_key" not in loaded
        assert loaded["ews_endpoint"] == "https://e/"

    def test_import_legacy_env_safe_keys_only(self, tmp_path):
        from calendar_planner.app.runtime_config import RuntimeConfig

        env = tmp_path / ".env"
        env.write_text(
            "DEFAULT_TIMEZONE=Europe/Moscow\n"
            "EWS_ENDPOINT=https://example/EWS\n"
            "EWS_PASSWORD=super-secret\n",
            encoding="utf-8",
        )
        cfg = RuntimeConfig(tmp_path / "settings.json")
        cfg.import_legacy_env(env)
        data = cfg.load()
        assert data["default_timezone"] == "Europe/Moscow"
        assert data["ews_endpoint"] == "https://example/EWS"
        # password must never be imported into config
        assert "ews_password" not in data
        assert "EWS_PASSWORD" not in data

    def test_as_env_exports_safe_values(self, tmp_path):
        from calendar_planner.app.runtime_config import RuntimeConfig

        cfg = RuntimeConfig(tmp_path / "settings.json")
        cfg.save({"ews_username": "user", "mcp_find_tool": "find_events"})
        env = cfg.as_env()
        assert env["EWS_USERNAME"] == "user"
        assert env["MCP_ENABLED"] == "true"


class TestComponentManifest:
    def test_manifest_shape(self, tmp_path):
        from calendar_planner.app import component_manifest as cm

        m = cm.component_manifest()
        assert m["product"] == "Calendar Event Planner"
        assert m["app_version"] == __version__
        assert "exchange_mcp_local_patches" in m
        assert "send_meeting_invitations" in m["exchange_mcp_local_patches"]
        assert "uraldrone_meeting_v1" in m["schema_profiles"]

    def test_write_load_roundtrip(self, tmp_path):
        from calendar_planner.app import component_manifest as cm

        p = tmp_path / "manifest.json"
        cm.write_component_manifest(p, install_dir=tmp_path)
        loaded = cm.load_component_manifest(p)
        assert loaded["app_version"] == __version__
        assert loaded["install_dir"] == str(tmp_path)


class TestVersionStillConsistent:
    def test_version_is_1_1_0(self):
        from calendar_planner.version import __version__

        assert __version__ == "1.1.0"