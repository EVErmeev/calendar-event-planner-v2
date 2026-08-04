"""Single source of truth for the application version.

All components (CLI --version, package metadata, About dialog, installer,
portable ZIP, release assets, diagnostics, component manifest) must read the
version from here — never hardcode it in multiple places.
"""

from __future__ import annotations

__version__ = "1.0.1"
APP_NAME = "Calendar Event Planner"
PACKAGE_NAME = "calendar-event-planner-v2"
CLI_LABEL = f"{PACKAGE_NAME} {__version__}"


def package_version() -> str:
    """Return the installed distribution version, falling back to __version__."""
    try:
        from importlib import metadata

        return metadata.version(PACKAGE_NAME)
    except Exception:
        return __version__