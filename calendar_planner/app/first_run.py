"""First-run wizard logic.

Coordinates: EWS auth, Credential Manager, ResolveNames, bundled MCP init,
timezone/settings, and the final summary. The UI layer calls these functions;
this module is UI-agnostic and testable.

No real ``create_event`` is ever invoked here.
"""
from __future__ import annotations

import logging
from pathlib import Path

from calendar_planner.app.bundled_mcp import resolve_bundled_mcp, validate_bundled_mcp
from calendar_planner.app.runtime_config import RuntimeConfig
from calendar_planner.version import __version__

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://mail.1cbit.ru/EWS/Exchange.asmx"


def should_run_wizard(config: RuntimeConfig) -> bool:
    """Run wizard when first_run_completed != true."""
    return not bool(config.load().get("first_run_completed", False))


class FirstRunContext:
    """Holds state collected during the wizard."""

    def __init__(self, install_dir: Path | None = None):
        self.install_dir = Path(install_dir) if install_dir else Path(__file__).resolve().parent.parent.parent
        self.config = RuntimeConfig()
        self.ews_endpoint: str = DEFAULT_ENDPOINT
        self.ews_username: str = ""
        self.timezone: str = "Asia/Yekaterinburg"
        self.results: dict[str, dict] = {}
        self.mcp_info: dict = {}

    def load_existing(self) -> None:
        cfg = self.config.load()
        self.ews_endpoint = cfg.get("ews_endpoint") or DEFAULT_ENDPOINT
        self.ews_username = cfg.get("ews_username") or ""
        self.timezone = cfg.get("default_timezone") or "Asia/Yekaterinburg"

    # --------------------------------------------------------------- step checks
    def check_mcp(self) -> dict:
        info = resolve_bundled_mcp(self.install_dir)
        valid = validate_bundled_mcp(self.install_dir)
        self.mcp_info = {**info, **valid}
        # expose tools presence from static info (no process started here)
        return {
            "component": "Exchange MCP",
            "status": "ok" if valid.get("valid") else "failed",
            "detail": {
                "wrapper": info["wrapper_exists"],
                "server": info["server_exists"],
                "invitation_fix": valid["checks"]["invitation_fix_applied"],
            },
        }

    def check_directory(self, resolver_call=None, query: str = "") -> dict:
        """Run a read-only ResolveNames-style search.

        ``resolver_call`` is injected (real gateway or fixture) and must return
        an object with a ``status`` and (optionally) ``results``/``count``.
        """
        if resolver_call is None:
            return {"status": "failed", "detail": "no directory gateway"}
        try:
            result = resolver_call(query)
        except Exception as exc:
            logger.warning("directory probe failed: %s", exc)
            return {"status": "failed", "detail": str(exc)}
        status = getattr(result, "status", None)
        count = getattr(result, "count", None)
        return {
            "status": "ok" if status in ("success", "ambiguous") else "failed",
            "detail": f"status={status}, count={count}",
        }

    # ---------------------------------------------------------------- finalize
    def finalize(self, required_ok: bool, force: bool = False) -> bool:
        """Mark wizard complete if required components ready or user forced."""
        if required_ok or force:
            self.config.mark_first_run_completed(True)
            return True
        return False

    def save_settings(self) -> dict:
        return self.config.save({
            "ews_endpoint": self.ews_endpoint,
            "ews_username": self.ews_username,
            "default_timezone": self.timezone,
            "first_run_completed": True,
        })


def wizard_summary_table(ctx: FirstRunContext) -> list[dict]:
    """Build the final summary table rows for the wizard UI."""
    rows = [
        {"component": "Application runtime", "status": "OK", "detail": f"version {__version__}"},
    ]
    mcp = ctx.mcp_info or {}
    rows.append({"component": "Exchange MCP", "status": "OK" if mcp.get("valid") else "FAIL", "detail": "version 1.0.0-cep.1"})
    for name, r in ctx.results.items():
        rows.append({"component": name, "status": "OK" if r.get("status") == "ok" else "FAIL", "detail": str(r.get("detail", ""))})
    return rows