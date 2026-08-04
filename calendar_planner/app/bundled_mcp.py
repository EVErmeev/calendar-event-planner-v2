"""Bundled Exchange MCP resolution.

The app must locate the bundled MCP relative to the install directory, never via
a machine-specific path such as ``C:\\Users\\<user>\\AppData\\Local\\exchange-mcp``.

Expected install layout::

    <INSTALL_DIR>\\exchange-mcp\\exchange-mcp.ps1
    <INSTALL_DIR>\\exchange-mcp\\server\\server.py
    <INSTALL_DIR>\\runtime\\python.exe

Resolution order:
    1. ``<install_dir>/exchange-mcp/exchange-mcp.ps1`` wrapper
    2. direct python module: ``<install_dir>/runtime/python.exe -m exchange_mcp.server``
    3. any vendored server package importable from ``<install_dir>``
"""
from __future__ import annotations

import shutil
from pathlib import Path

WRAPPER_NAME = "exchange-mcp.ps1"
SERVER_REL = Path("exchange-mcp") / "server"
RUNTIME_REL = Path("runtime") / "python.exe"


def find_install_dir(override: Path | None = None) -> Path | None:
    """Best-effort locate of the install directory.

    Returns ``override`` if given (used in tests / portable). Otherwise looks
    relative to this package (dev checkout) and parent dirs.
    """
    if override:
        return Path(override)
    # package lives at <install>/app/... ; here <root>/calendar_planner/app/
    root = Path(__file__).resolve().parent.parent.parent
    return root


def resolve_bundled_mcp(install_dir: Path | None = None) -> dict:
    """Return a dict describing the resolved bundled MCP (no process started)."""
    root = find_install_dir(install_dir)
    assert root is not None, "install dir must resolve"
    mcp_dir = root / "exchange-mcp"
    # dev checkout layout: <root>/vendor/exchange_mcp
    vendor_mcp = root / "vendor" / "exchange_mcp"
    if not mcp_dir.exists() and vendor_mcp.exists():
        mcp_dir = vendor_mcp
    wrapper = mcp_dir / WRAPPER_NAME
    runtime_py = root / "runtime" / "python.exe"
    server_py = mcp_dir / "server" / "server.py"

    # direct python invocation if runtime is bundled
    if runtime_py.exists():
        direct_cmd = f'"{runtime_py}" -m exchange_mcp.server'
    else:
        py = shutil.which("python")
        direct_cmd = f'"{py}" -m exchange_mcp.server' if py else ""

    return {
        "install_dir": str(root),
        "mcp_dir": str(mcp_dir),
        "wrapper_exists": wrapper.exists(),
        "wrapper_path": str(wrapper) if wrapper.exists() else "",
        "server_exists": server_py.exists(),
        "server_path": str(server_py) if server_py.exists() else "",
        "runtime_python": str(runtime_py) if runtime_py.exists() else "",
        "has_bundled_runtime": runtime_py.exists(),
        "stdio_command": f'powershell -ExecutionPolicy Bypass -File "{wrapper}"' if wrapper.exists() else direct_cmd,
    }


def validate_bundled_mcp(install_dir: Path | None = None) -> dict:
    """Validate the bundled MCP: files present and the invitation fix applied.

    Never starts a process; only inspects files.
    """
    info = resolve_bundled_mcp(install_dir)
    checks = {
        "mcp_dir_exists": Path(info["mcp_dir"]).exists(),
        "wrapper_exists": info["wrapper_exists"],
        "server_exists": info["server_exists"],
        "invitation_fix_applied": False,
    }
    if info["server_exists"]:
        server_py = Path(info["server_path"])
        try:
            text = server_py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        checks["invitation_fix_applied"] = (
            "SEND_TO_ALL_AND_SAVE_COPY" in text and "SEND_AND_SAVE_COPY" not in text
        )
    ok = (
        checks["mcp_dir_exists"]
        and checks["wrapper_exists"]
        and checks["server_exists"]
        and checks["invitation_fix_applied"]
    )
    info["checks"] = checks
    info["valid"] = ok
    return info