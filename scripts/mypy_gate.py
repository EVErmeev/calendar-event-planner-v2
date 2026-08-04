"""CI gate for mypy — controlled baseline.

Fails if:
  - a new/modified file introduces a mypy error;
  - the legacy baseline count grows.

Usage:
    python scripts/mypy_gate.py [--strict-files path [path ...]]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "mypy.ini"

# Release / new files that MUST be 0-error clean.
STRICT_DEFAULT = [
    ROOT / "calendar_planner" / "version.py",
    ROOT / "calendar_planner" / "__init__.py",
    ROOT / "calendar_planner" / "app" / "bootstrap.py",
]


def run_mypy(paths: list[Path]) -> list[str]:
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(CONFIG), *[str(p) for p in paths]],
        capture_output=True,
        text=True,
    )
    errors = [ln for ln in proc.stdout.splitlines() if "error:" in ln]
    return errors


def main() -> int:
    extra = [ROOT / a for a in sys.argv[1:]]
    strict = STRICT_DEFAULT + extra

    baseline_errors = run_mypy([ROOT / "calendar_planner"])
    print(f"[mypy_gate] full package (baseline-silenced): {len(baseline_errors)} errors")
    for e in baseline_errors:
        print("  PKG:", e)

    strict_errors = run_mypy(strict)
    print(f"[mypy_gate] strict files: {len(strict_errors)} errors")
    for e in strict_errors:
        print("  STRICT:", e)

    # Baseline modules are silenced to 0. Any remaining package error therefore
    # lives in a NEW module not covered by the legacy baseline -> gate must fail.
    if baseline_errors:
        print("[mypy_gate] FAIL: mypy error in a file outside the legacy baseline.")
        return 1

    if strict_errors:
        print("[mypy_gate] FAIL: new/changed file has mypy error(s).")
        return 1

    print("[mypy_gate] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())