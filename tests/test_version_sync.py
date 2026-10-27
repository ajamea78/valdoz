"""Version synchronization tests for ValdoZ Protocol."""

import re
from pathlib import Path
import tomllib

from valdoz import __version__


def test_version_matches_pyproject():
    root = Path(__file__).parent.parent
    pyproject_path = root / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml not found"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    pyproject_version = data["project"]["version"]
    assert __version__ == pyproject_version, (
        f"Version mismatch: __version__ is '{__version__}' but pyproject.toml is '{pyproject_version}'"
    )


def test_version_matches_changelog():
    root = Path(__file__).parent.parent
    changelog_path = root / "CHANGELOG.md"
    assert changelog_path.exists(), "CHANGELOG.md not found"

    content = changelog_path.read_text(encoding="utf-8")
    match = re.search(r"##\s*\[(\d+\.\d+\.\d+)\]", content)
    assert match is not None, "Could not find version header in CHANGELOG.md"

    changelog_version = match.group(1)
    assert __version__ == changelog_version, (
        f"Version mismatch: __version__ is '{__version__}' but CHANGELOG.md latest is '{changelog_version}'"
    )
