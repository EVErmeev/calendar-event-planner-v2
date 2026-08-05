from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))



class TestDiagnostics:
    def test_run_all_structure(self, tmp_path):
        from calendar_planner.app.diagnostics import Diagnostics

        d = Diagnostics(install_dir=tmp_path)
        result = d.run_all()
        assert "checks" in result
        assert "version" in result
        assert "all_ok" in result
        # tmp_path has no app files, but environment check must be ok
        check_names = [c["check"] for c in result["checks"]]
        assert "bundled_mcp" in check_names
        assert "app_files" in check_names

    def test_bundle_excludes_secrets(self, tmp_path):
        from calendar_planner.app.diagnostics import Diagnostics

        # create a log with a secret-like line
        logs = tmp_path / "logsdir"
        logs.mkdir(parents=True)
        (logs / "app.log").write_text(
            "EWS_PASSWORD=super-secret-token\n"
            "Authorization: Bearer abcdef123\n"
            "normal line\n",
            encoding="utf-8",
        )
        # point user config dir to tmp to avoid touching real profile
        d = Diagnostics(install_dir=tmp_path)
        d.config.path = tmp_path / "cfg" / "settings.json"
        bundle = d.export_bundle(tmp_path / "diag", include_logs=True, logs_dir=tmp_path / "logsdir")

        assert bundle.exists()
        with zipfile.ZipFile(bundle) as zf:
            names = zf.namelist()
            assert any(n.endswith("diagnostics.json") for n in names)
            log_name = next((n for n in names if n.startswith("logs/")), None)
            assert log_name is not None
            content = zf.read(log_name).decode("utf-8", errors="replace")
            # secrets must be redacted
            assert "super-secret-token" not in content
            assert "abcdef" not in content
            # safe log body survives
            assert "=" in content

    def test_export_bundle_has_manifest(self, tmp_path):
        from calendar_planner.app.diagnostics import Diagnostics

        d = Diagnostics(install_dir=tmp_path)
        bundle = d.export_bundle(tmp_path / "out", include_logs=False)
        with zipfile.ZipFile(bundle) as zf:
            diag = json.loads(zf.read("diagnostics.json").decode("utf-8"))
        assert "manifest" in diag
        assert diag["manifest"]["product"] == "Calendar Event Planner"


class TestSanitize:
    def test_sanitize_redacts_secret_words(self):
        from calendar_planner.app.diagnostics import _sanitize

        assert "secret" not in _sanitize("secret=abc")
        assert "password" not in _sanitize("password=hunter2")
        assert _sanitize("hello world") == "hello world"

    def test_safe_log_redacts_secret_lines(self):
        from calendar_planner.app.diagnostics import _safe_log_text

        out = _safe_log_text("PASSWORD=hunter2\nfoo=bar")
        assert "hunter2" not in out
        assert "foo=bar" in out