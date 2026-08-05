"""Component manifest for the distributed product.

Single source that describes what is bundled and what its versions/upstream
commit are. Used by: installer, portable ZIP, diagnostics, release assets and
CI verification. See ``component-manifest.json`` produced by the build scripts.
"""
from __future__ import annotations

import json
import platform
from pathlib import Path

from calendar_planner.version import __version__

EXCHANGE_MCP_BUNDLE_VERSION = "1.0.0-cep.1"
# Pinned upstream commit of the vendored exchange-mcp (see vendor/exchange_mcp).
EXCHANGE_MCP_UPSTREAM_COMMIT = "0000000000000000000000000000000000000000"
EXCHANGE_MCP_LOCAL_PATCHES = ["send_meeting_invitations"]
SCHEMA_PROFILES = ["uraldrone_meeting_v1"]


def python_version() -> str:
    return platform.python_version()


def component_manifest(install_dir: Path | None = None) -> dict:
    manifest = {
        "product": "Calendar Event Planner",
        "app_version": __version__,
        "installer_version": __version__,
        "python_version": python_version(),
        "exchange_mcp_version": EXCHANGE_MCP_BUNDLE_VERSION,
        "exchange_mcp_upstream_commit": EXCHANGE_MCP_UPSTREAM_COMMIT,
        "exchange_mcp_local_patches": list(EXCHANGE_MCP_LOCAL_PATCHES),
        "schema_profiles": list(SCHEMA_PROFILES),
    }
    if install_dir:
        manifest["install_dir"] = str(install_dir)
    return manifest


def write_component_manifest(path: Path, install_dir: Path | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(component_manifest(install_dir), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_component_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}