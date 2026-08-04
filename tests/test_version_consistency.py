from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestVersionConsistency:
    """Пакетная версия == CLI версия == метаданные == единый источник."""

    def test_package_version_equals_metadata(self):
        from calendar_planner.version import PACKAGE_NAME, __version__

        try:
            metadata_version = importlib.metadata.version(PACKAGE_NAME)
        except importlib.metadata.PackageNotFoundError:
            metadata_version = __version__

        assert __version__ == metadata_version
        assert __version__ == "1.0.1"

    def test_cli_label_built_from_version(self):
        from calendar_planner.version import CLI_LABEL, PACKAGE_NAME, __version__

        assert CLI_LABEL == f"{PACKAGE_NAME} {__version__}"

    def test_bootstrap_uses_single_version_source(self):
        """bootstrap.py не содержит hardcoded версии и импортирует CLI_LABEL."""
        bootstrap_path = (
            Path(__file__).parent.parent
            / "calendar_planner"
            / "app"
            / "bootstrap.py"
        )
        content = bootstrap_path.read_text(encoding="utf-8")
        assert "CLI_LABEL" in content
        assert "calendar_planner.version" in content
        assert "1.0.0" not in content

    def test_pyproject_dynamic_version(self):
        pyproject_path = (
            Path(__file__).parent.parent / "pyproject.toml"
        )
        content = pyproject_path.read_text(encoding="utf-8")
        assert "dynamic = [\"version\"]" in content
        assert "attr = \"calendar_planner.version.__version__\"" in content