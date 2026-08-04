"""Auto-detect installed Exchange MCP configuration."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class ExchangeMCPConfigDetector:
    """Detects Exchange MCP configuration from OpenCode and local install."""

    def detect(self) -> dict:
        result = {
            "found": False,
            "name": "exchange",
            "transport": "stdio",
            "command": "",
            "tools": [],
            "calendar_find_tool": "find_events",
            "calendar_create_tool": "create_event",
            "directory_search_tool": "search_emails",
        }

        # Try opencode mcp list
        try:
            proc = subprocess.run(
                ["opencode", "mcp", "list"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            output = proc.stdout + proc.stderr
        except Exception:
            output = ""
            logger.debug("opencode mcp list failed", exc_info=True)

        if "exchange" not in output.lower():
            return result

        # Extract exchange config from opencode.json
        config_paths = [
            Path.home() / ".config" / "opencode" / "opencode.jsonc",
            Path.home() / ".config" / "opencode" / "opencode.json",
            Path.home() / ".opencode" / "opencode.jsonc",
            Path.home() / ".opencode" / "opencode.json",
        ]

        for config_path in config_paths:
            if not config_path.exists():
                continue
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            mcp_servers = data.get("mcpServers") or data.get("mcp_servers") or {}
            exchange_cfg = mcp_servers.get("exchange", {})

            if not exchange_cfg:
                # opencode.json uses {"mcp": {"exchange": {"command": [...]}}}
                mcp_section = data.get("mcp") or {}
                exchange_cfg = mcp_section.get("exchange", {})

            if exchange_cfg:
                result["found"] = True
                raw_command = exchange_cfg.get("command", "")
                if isinstance(raw_command, list):
                    result["command"] = self._join_command(raw_command)
                elif isinstance(raw_command, str):
                    result["command"] = raw_command
                else:
                    result["command"] = ""
                result["transport"] = "stdio" if result["command"] else "http"
                result["tools"] = self._known_exchange_tools()
                return result

        # Fallback: known install path
        known_path = Path.home() / "AppData" / "Local" / "exchange-mcp" / "exchange-mcp.ps1"
        if known_path.exists():
            result["found"] = True
            result["command"] = (
                f"powershell -NoProfile -ExecutionPolicy Bypass -File {known_path}"
            )
            result["tools"] = self._known_exchange_tools()
            return result

        return result

    @staticmethod
    def _join_command(parts: list) -> str:
        """Join a command list into a shell string, quoting parts with spaces."""
        quoted = []
        for part in parts:
            part = str(part)
            if " " in part and not (part.startswith('"') and part.endswith('"')):
                part = f'"{part}"'
            quoted.append(part)
        return " ".join(quoted)

    @staticmethod
    def _known_exchange_tools() -> list[str]:
        return [
            "find_emails", "search_emails", "read_email", "mark_as_read",
            "list_folders", "send_email", "save_draft", "reply_to_email",
            "get_attachments", "find_events", "get_event", "create_event",
            "delete_event",
        ]
