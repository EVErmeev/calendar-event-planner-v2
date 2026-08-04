from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER_PY = ROOT / "vendor" / "exchange_mcp" / "server" / "server.py"


class TestInvitationModeFix:
    """Regression tests for the bundled send_meeting_invitations fix."""

    def test_bundle_contains_fix_not_bug(self):
        text = SERVER_PY.read_text(encoding="utf-8", errors="replace")
        assert "SEND_TO_ALL_AND_SAVE_COPY" in text
        assert "SEND_AND_SAVE_COPY" not in text

    def test_import_line_uses_valid_constant(self):
        text = SERVER_PY.read_text(encoding="utf-8", errors="replace")
        # the import must bring in the valid constant, not the legacy one
        assert "from exchangelib.items import SEND_TO_ALL_AND_SAVE_COPY" in text

    def test_invitation_mode_function_uses_fix(self):
        text = SERVER_PY.read_text(encoding="utf-8", errors="replace")
        # extract the _invitation_mode body and assert it returns the fixed constant
        import re

        match = re.search(
            r"return (SEND_[A-Z_]+) if attendees else (SEND_[A-Z_]+)",
            text,
        )
        assert match is not None, "could not locate _invitation_mode return"
        with_attendees, no_attendees = match.groups()
        assert with_attendees == "SEND_TO_ALL_AND_SAVE_COPY"
        assert no_attendees == "SEND_TO_NONE"


class TestBundledMcpResolution:
    def test_resolve_with_override(self, tmp_path):
        from calendar_planner.app.bundled_mcp import resolve_bundled_mcp

        (tmp_path / "exchange-mcp" / "server").mkdir(parents=True)
        (tmp_path / "exchange-mcp" / "exchange-mcp.ps1").write_text("#", encoding="utf-8")
        (tmp_path / "exchange-mcp" / "server" / "server.py").write_text(
            "SEND_TO_ALL_AND_SAVE_COPY\n", encoding="utf-8"
        )
        info = resolve_bundled_mcp(tmp_path)
        assert info["wrapper_exists"] is True
        assert info["server_exists"] is True
        assert info["has_bundled_runtime"] is False  # no runtime/python.exe yet

    def test_validate_detects_missing_fix(self, tmp_path):
        from calendar_planner.app.bundled_mcp import validate_bundled_mcp

        (tmp_path / "exchange-mcp" / "server").mkdir(parents=True)
        (tmp_path / "exchange-mcp" / "exchange-mcp.ps1").write_text("", encoding="utf-8")
        (tmp_path / "exchange-mcp" / "server" / "server.py").write_text(
            "SEND_AND_SAVE_COPY\n", encoding="utf-8"
        )
        result = validate_bundled_mcp(tmp_path)
        assert result["valid"] is False
        assert result["checks"]["invitation_fix_applied"] is False

    def test_validate_ok_with_fix(self, tmp_path):
        from calendar_planner.app.bundled_mcp import validate_bundled_mcp

        root = tmp_path
        (root / "exchange-mcp" / "server").mkdir(parents=True)
        (root / "exchange-mcp" / "exchange-mcp.ps1").write_text("", encoding="utf-8")
        (root / "exchange-mcp" / "server" / "server.py").write_text(
            "from exchangelib.items import SEND_TO_ALL_AND_SAVE_COPY, SEND_TO_NONE\n",
            encoding="utf-8",
        )
        result = validate_bundled_mcp(root)
        assert result["valid"] is True
        assert result["checks"]["invitation_fix_applied"] is True

    def test_bundled_runtime_preferred(self, tmp_path):
        from calendar_planner.app.bundled_mcp import resolve_bundled_mcp

        (tmp_path / "exchange-mcp" / "server").mkdir(parents=True)
        (tmp_path / "runtime").mkdir(parents=True)
        (tmp_path / "runtime" / "python.exe").write_text("", encoding="utf-8")
        (tmp_path / "exchange-mcp" / "exchange-mcp.ps1").write_text("", encoding="utf-8")
        info = resolve_bundled_mcp(tmp_path)
        assert info["has_bundled_runtime"] is True
        assert "runtime" in info["stdio_command"]