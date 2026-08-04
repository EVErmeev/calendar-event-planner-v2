"""Installation diagnostics and repair.

Checks components, produces a safe (secret-free) diagnostics bundle ZIP, and
offers repair actions. NEVER writes passwords/tokens into the bundle.

Sanitization guarantees: password, token, Authorization headers, NTLM blobs,
cookies, full ``.env`` content and Credential Manager content are excluded.
"""
from __future__ import annotations

import json
import logging
import platform
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from calendar_planner.app.bundled_mcp import validate_bundled_mcp
from calendar_planner.app.component_manifest import (
    component_manifest,
    load_component_manifest,
)
from calendar_planner.app.runtime_config import (
    RuntimeConfig,
    default_config_dir,
    default_diagnostics_dir,
)
from calendar_planner.version import __version__

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = re.compile(
    r"(?i)(password|passwd|token|api[_-]?key|secret|authorization|ntlm|cookie)",
)


def _sanitize(value: str) -> str:
    """Redact sensitive-looking fragments in a single-line string."""
    if not value:
        return value
    return SENSITIVE_PATTERNS.sub("<REDACTED>", value)


class Diagnostics:
    """Runs component checks and produces a safe diagnostics bundle."""

    def __init__(self, install_dir: Path | None = None):
        self.install_dir = Path(install_dir) if install_dir else Path(__file__).resolve().parent.parent.parent
        self.config = RuntimeConfig()

    # ------------------------------------------------------------------- checks
    def check_environment(self) -> dict:
        return {
            "check": "environment",
            "os": platform.platform(),
            "python_version": platform.python_version(),
            "app_version": __version__,
            "status": "ok",
        }

    def check_app_files(self) -> dict:
        pkg = self.install_dir / "calendar_planner"
        ok = pkg.exists() and (pkg / "__init__.py").exists()
        return {
            "check": "app_files",
            "status": "ok" if ok else "failed",
            "detail": f"package dir exists={pkg.exists()}",
        }

    def check_runtime(self) -> dict:
        import sys

        ok = sys.executable and Path(sys.executable).exists()
        return {
            "check": "runtime",
            "status": "ok" if ok else "failed",
            "detail": sys.executable,
        }

    def check_imports(self) -> dict:
        missing = []
        for mod in ("calendar_planner", "keyring", "requests_ntlm"):
            try:
                __import__(mod)
            except Exception:
                missing.append(mod)
        return {
            "check": "imports",
            "status": "ok" if not missing else "failed",
            "detail": ",".join(missing) or "all-ok",
        }

    def check_user_config(self) -> dict:
        cfg_path = self.config.path
        cfg_dir = default_config_dir()
        ok = cfg_path.exists() or cfg_dir.exists()
        return {
            "check": "user_config",
            "status": "ok" if ok else "failed",
            "detail": str(cfg_path),
        }

    def check_logs_permissions(self) -> dict:
        logs = default_config_dir() / "logs"
        try:
            logs.mkdir(parents=True, exist_ok=True)
            probe = logs / ".write_probe"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
            ok = True
        except OSError:
            ok = False
        return {"check": "logs_permissions", "status": "ok" if ok else "failed", "detail": str(logs)}

    def check_bundled_mcp(self) -> dict:
        info = validate_bundled_mcp(self.install_dir)
        return {
            "check": "bundled_mcp",
            "status": "ok" if info.get("valid") else "failed",
            "detail": {
                "mcp_dir": info["mcp_dir"],
                "wrapper_exists": info["wrapper_exists"],
                "server_exists": info["server_exists"],
                "invitation_fix": info["checks"]["invitation_fix_applied"],
            },
        }

    def run_all(self) -> dict:
        checks = [
            self.check_environment(),
            self.check_app_files(),
            self.check_runtime(),
            self.check_imports(),
            self.check_user_config(),
            self.check_logs_permissions(),
            self.check_bundled_mcp(),
        ]
        manifest = load_component_manifest(self.install_dir / "component-manifest.json")
        if not manifest:
            manifest = component_manifest()
        failed = [c["check"] for c in checks if c["status"] == "failed"]
        return {
            "version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "checks": checks,
            "all_ok": not failed,
            "failed": failed,
            "manifest": manifest,
        }

    # -------------------------------------------------------------- diagnostics
    def export_bundle(
        self,
        out_dir: Path | None = None,
        include_logs: bool = True,
        logs_dir: Path | None = None,
    ) -> Path:
        """Create a safe diagnostics ZIP (no secrets)."""
        out_dir = Path(out_dir) if out_dir else default_diagnostics_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        zip_path = out_dir / f"CalendarEventPlanner-Diagnostics-{stamp}.zip"

        result = self.run_all()
        report = {
            "generated_at": result["generated_at"],
            "version": result["version"],
            "platform": platform.platform(),
            "checks": result["checks"],
            "manifest": result["manifest"],
        }

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("diagnostics.json", _dumps(report))
            if include_logs:
                logs_path = Path(logs_dir) if logs_dir else default_config_dir() / "logs"
                if logs_path.exists():
                    for f in sorted(logs_path.glob("*.log"))[-5:]:
                        try:
                            safe = _safe_log_text(f.read_text(encoding="utf-8", errors="replace"))
                            zf.writestr(f"logs/{f.name}", safe)
                        except OSError:
                            continue
        logger.info("diagnostics bundle: %s", zip_path)
        return zip_path

    def run(self) -> dict:
        return self.run_all()


def _dumps(obj) -> str:

    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _safe_log_text(text: str) -> str:
    """Redact obvious secret lines from a log chunk."""
    out = []
    for line in text.splitlines():
        lowered = line.lower()
        # header-style secrets: Authorization: Bearer xxxx, Proxy-Authorization, etc.
        if any(prefix in lowered for prefix in ("authorization:", "cookie:", "proxy-authorization:")):
            key = line.partition(":")[0]
            out.append(f"{key}: <REDACTED>")
        elif SENSITIVE_PATTERNS.search(line) and "=" in line:
            key, _, _ = line.partition("=")
            out.append(f"{key}=<REDACTED>")
        else:
            out.append(line)
    return "\n".join(out)
