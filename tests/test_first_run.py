from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class _FakeResolver:
    status = "success"
    count = 2


class TestFirstRun:
    def test_should_run_wizard_default(self, tmp_path):
        from calendar_planner.app.first_run import should_run_wizard
        from calendar_planner.app.runtime_config import RuntimeConfig

        cfg = RuntimeConfig(tmp_path / "settings.json")
        assert should_run_wizard(cfg) is True

    def test_should_run_wizard_after_complete(self, tmp_path):
        from calendar_planner.app.first_run import should_run_wizard
        from calendar_planner.app.runtime_config import RuntimeConfig

        cfg = RuntimeConfig(tmp_path / "settings.json")
        cfg.mark_first_run_completed(True)
        assert should_run_wizard(cfg) is False

    def test_finalize_requires_ok(self, tmp_path):
        from calendar_planner.app.first_run import FirstRunContext

        ctx = FirstRunContext(install_dir=tmp_path)
        ctx.config.path = tmp_path / "settings.json"
        assert ctx.finalize(required_ok=False, force=False) is False
        assert ctx.config.load()["first_run_completed"] is False
        assert ctx.finalize(required_ok=False, force=True) is True

    def test_save_settings_persists_safe(self, tmp_path):
        from calendar_planner.app.first_run import FirstRunContext

        ctx = FirstRunContext(install_dir=tmp_path)
        ctx.config.path = tmp_path / "settings.json"
        ctx.ews_username = "user"
        ctx.timezone = "Asia/Yekaterinburg"
        data = ctx.save_settings()
        assert data["ews_username"] == "user"
        assert data["default_timezone"] == "Asia/Yekaterinburg"
        assert data["first_run_completed"] is True

    def test_check_directory_ok(self, tmp_path):
        from calendar_planner.app.first_run import FirstRunContext

        ctx = FirstRunContext(install_dir=tmp_path)
        r = ctx.check_directory(resolver_call=lambda q: _FakeResolver(), query="Тест")
        assert r["status"] == "ok"

    def test_check_directory_failed(self, tmp_path):
        from calendar_planner.app.first_run import FirstRunContext

        ctx = FirstRunContext(install_dir=tmp_path)
        r = ctx.check_directory(resolver_call=lambda q: None)
        assert r["status"] == "failed"

    def test_mcp_check_reports_fix(self, tmp_path):
        from calendar_planner.app.first_run import FirstRunContext

        (tmp_path / "exchange-mcp" / "server").mkdir(parents=True)
        (tmp_path / "exchange-mcp" / "exchange-mcp.ps1").write_text("", encoding="utf-8")
        (tmp_path / "exchange-mcp" / "server" / "server.py").write_text(
            "SEND_TO_ALL_AND_SAVE_COPY\n", encoding="utf-8"
        )
        ctx = FirstRunContext(install_dir=tmp_path)
        r = ctx.check_mcp()
        assert r["status"] == "ok"

    def test_wizard_summary_rows(self, tmp_path):
        from calendar_planner.app.first_run import FirstRunContext, wizard_summary_table

        ctx = FirstRunContext(install_dir=tmp_path)
        ctx.results = {"EWS auth": {"status": "ok"}}
        rows = wizard_summary_table(ctx)
        assert any(r["component"] == "Application runtime" for r in rows)
        assert any(r["component"] == "EWS auth" for r in rows)