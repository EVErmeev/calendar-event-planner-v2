"""Central .env writer.

Single place that owns the location of the runtime ``.env`` file and how it is
read/written. Guarantees:

* creates the file if it is missing;
* preserves unknown lines, comments and existing unrelated settings;
* never duplicates keys;
* preserves values containing spaces (e.g. paths);
* never writes a password (keys whose name contains ``PASSWORD``);
* UTF-8 encoding.

The rest of the app must go through ``EnvConfigWriter`` instead of re-parsing
``Path(__file__).parent...`` on its own.
"""

from __future__ import annotations

from pathlib import Path

SENSITIVE_KEY_HINT = "PASSWORD"


def _project_root() -> Path:
    """Root directory containing the ``calendar_planner`` package."""
    # this file lives at <root>/calendar_planner/app/env_config.py
    return Path(__file__).resolve().parent.parent.parent


class EnvConfigWriter:
    """Reads and writes the application ``.env`` file, preserving everything else."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @classmethod
    def default(cls) -> EnvConfigWriter:
        return cls(_project_root() / ".env")

    # ------------------------------------------------------------------ reads
    def exists(self) -> bool:
        return self.path.exists()

    def read_dict(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        data: dict[str, str] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            key = self._key_of(line)
            if key is None:
                continue
            _, _, value = line.strip().partition("=")
            data[key] = value.strip()
        return data

    # ------------------------------------------------------------------ write
    def set(self, updates: dict[str, str]) -> dict[str, str]:
        """Apply ``updates`` preserving existing lines. Returns the new file dict.

        Sensitive keys (containing ``PASSWORD``) are never written.
        """
        updates = {k: v for k, v in updates.items() if not self._is_sensitive(k)}

        lines: list[str] = []
        if self.path.exists():
            lines = self.path.read_text(encoding="utf-8").splitlines()

        # Map key -> first-occurrence line index; collect ordered key list.
        first_index: dict[str, int] = {}
        for i, line in enumerate(lines):
            key = self._key_of(line)
            if key is not None and key not in first_index:
                first_index[key] = i

        new_lines: list[str] = []
        handled: set[str] = set()
        for i, line in enumerate(lines):
            key = self._key_of(line)
            if key is not None and first_index.get(key) != i:
                continue  # drop duplicate key lines
            if key is not None and key in updates and key not in handled:
                new_lines.append(self._render(key, updates[key]))
                handled.add(key)
            else:
                new_lines.append(line)

        # Append keys that were not present before (preserve file order-ish).
        for key, value in updates.items():
            if key not in handled:
                new_lines.append(self._render(key, value))
                handled.add(key)

        while new_lines and new_lines[-1].strip() == "":
            new_lines.pop()
        text = "\n".join(new_lines)
        if text:
            text += "\n"
        self.path.write_text(text, encoding="utf-8")
        return self.read_dict()

    # ------------------------------------------------------------------- util
    @staticmethod
    def _key_of(line: str) -> str | None:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            return None
        return stripped.partition("=")[0].strip()

    @staticmethod
    def _render(key: str, value: str) -> str:
        return f"{key}={value}"

    @classmethod
    def _is_sensitive(cls, key: str) -> bool:
        return SENSITIVE_KEY_HINT in key.upper()