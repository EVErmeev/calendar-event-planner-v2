from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestUpdateManager:
    def test_create_backup_preserves_config(self, tmp_path, monkeypatch):
        from calendar_planner.app import updates
        from calendar_planner.app.component_manifest import write_component_manifest

        monkeypatch.setattr(
            "calendar_planner.app.updates.default_config_dir", lambda: tmp_path / "userdata"
        )
        cfg = tmp_path / "userdata" / "config" / "settings.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text('{"first_run_completed": true, "ews_username": "u"}', encoding="utf-8")
        write_component_manifest(tmp_path / "component-manifest.json", install_dir=tmp_path)

        um = updates.UpdateManager(install_dir=tmp_path)
        backup = um.create_backup("test")
        assert backup.exists()
        assert (backup / "update-metadata.json").exists()
        assert "previous_app_version" in (backup / "update-metadata.json").read_text(encoding="utf-8")
        assert (backup / "settings.json").exists()

    def test_rollback_does_not_touch_user_data(self, tmp_path, monkeypatch):
        from calendar_planner.app import updates

        monkeypatch.setattr(
            "calendar_planner.app.updates.default_config_dir", lambda: tmp_path / "userdata"
        )
        um = updates.UpdateManager(install_dir=tmp_path)
        backup = um.create_backup("rb")
        res = um.rollback(backup)
        assert res["ok"] is True
        assert "user data" in res["note"].lower()

    def test_version_bound_to_release(self, tmp_path):
        from calendar_planner.app.component_manifest import write_component_manifest
        from calendar_planner.app.updates import UpdateManager

        write_component_manifest(tmp_path / "component-manifest.json", install_dir=tmp_path)
        um = UpdateManager(install_dir=tmp_path)
        info = um.version_mcp_bound()
        assert info["mcp_pinned"] is True
        assert info["app_version"]

    def test_mcp_bundle_version_constant(self):
        from calendar_planner.app.updates import UpdateManager

        assert UpdateManager(install_dir=Path(".")).mcp_bundle_version() == "1.0.0-cep.1"