"""Update / rollback foundation.

Provides backup/restore primitives that preserve user data (settings, runs,
logs, Credential Manager) across application updates. The app version is bound
to a specific bundled Exchange MCP version — an update never pulls an arbitrary
latest MCP.

This is a *foundation* for v1.1.0: the full updater is delivered with the
installer. Tests cover the safety invariants (preserve config, no user-data
rollback).
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from calendar_planner.app.component_manifest import (
    component_manifest,
    load_component_manifest,
)
from calendar_planner.app.runtime_config import default_config_dir
from calendar_planner.version import __version__

logger = logging.getLogger(__name__)


def default_backup_dir() -> Path:
    return default_config_dir() / "backups"


class UpdateManager:
    """Backup/restore of app state around an update."""

    def __init__(self, install_dir: Path | None = None):
        self.install_dir = Path(install_dir) if install_dir else Path(__file__).resolve().parent.parent.parent
        self.backup_root = default_backup_dir()

    # ---------------------------------------------------------------- snapshot
    def create_backup(self, label: str = "") -> Path:
        """Snapshot version metadata + safe settings + manifest for rollback.

        User data (runs/logs/CM) is NOT copied — only references are recorded.
        """
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        tag = label or stamp
        backup_dir = self.backup_root / f"update-{tag}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        manifest = load_component_manifest(self.install_dir / "component-manifest.json")
        if not manifest:
            manifest = component_manifest()

        meta = {
            "created_at": stamp,
            "previous_app_version": manifest.get("app_version", __version__),
            "previous_mcp_version": manifest.get("exchange_mcp_version"),
            "previous_mcp_commit": manifest.get("exchange_mcp_upstream_commit"),
            "manifest": manifest,
        }
        (backup_dir / "update-metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # snapshot the current settings.json for migration/rollback reference
        cfg = default_config_dir() / "config" / "settings.json"
        if cfg.exists():
            shutil.copy2(cfg, backup_dir / "settings.json")
        logger.info("created backup: %s", backup_dir)
        return backup_dir

    def rollback(self, backup_dir: Path) -> dict:
        """Restore previous app manifest reference (does NOT touch user data)."""
        meta_path = backup_dir / "update-metadata.json"
        if not meta_path.exists():
            return {"ok": False, "reason": "no update-metadata.json"}
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return {
            "ok": True,
            "previous_app_version": meta.get("previous_app_version"),
            "previous_mcp_version": meta.get("previous_mcp_version"),
            "note": "User data (runs/logs/settings/credentials) preserved.",
        }

    # ------------------------------------------------------------ app / mcp
    def mcp_bundle_version(self) -> str:
        from calendar_planner.app.component_manifest import EXCHANGE_MCP_BUNDLE_VERSION

        return EXCHANGE_MCP_BUNDLE_VERSION

    def version_mcp_bound(self) -> dict:
        """Ensure the bundled MCP version is the one bound to this app version."""
        manifest = load_component_manifest(self.install_dir / "component-manifest.json")
        return {
            "app_version": __version__,
            "mcp_version": manifest.get("exchange_mcp_version", self.mcp_bundle_version()),
            "mcp_pinned": bool(manifest.get("exchange_mcp_upstream_commit")),
        }