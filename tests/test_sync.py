"""Unit tests for ValdoZ runtime sync, managed block isolation, and skill generation."""

import yaml
import pytest
from pathlib import Path
from valdoz.sync import (
    sync_all_runtimes,
    inject_managed_block,
    generate_phase_playbook,
    CharLimitExceededError,
    CHAR_LIMIT,
    DELIMITER_START,
    DELIMITER_END,
)
from valdoz.state import ValdozState, save_state


@pytest.fixture
def temp_project(tmp_path: Path):
    state = ValdozState(project_name="sync-test")
    save_state(tmp_path, state)
    return tmp_path


def test_managed_block_isolation():
    user_header = "# Custom Project Rules by Tech Lead\n\n- Do not touch legacy database."
    user_footer = "## Custom Deployment Notes\n\nContact infra team on Slack."

    original_file = f"{user_header}\n\n{DELIMITER_START}\nold generated content\n{DELIMITER_END}\n\n{user_footer}\n"

    updated = inject_managed_block(original_file, "new brand new generated content")

    # Surrounding user content must be intact
    assert user_header in updated
    assert user_footer in updated
    # Old content replaced
    assert "old generated content" not in updated
    assert "new brand new generated content" in updated


def test_runtime_sync_all_files(temp_project: Path):
    outputs = sync_all_runtimes(temp_project, dry_run=False)

    # 1. Check generated files exist on disk
    assert (temp_project / "AGENTS.md").exists()
    assert (temp_project / "GEMINI.md").exists()
    assert (temp_project / ".agent" / "rules" / "00-core-discipline.md").exists()
    assert (temp_project / ".agent" / "rules" / "01-concurrency-roles.md").exists()
    assert (temp_project / ".agent" / "rules" / "02-research-adversarial.md").exists()

    # 2. Check all 10 phase playbooks exist
    for p in range(1, 11):
        skill_dirs = list((temp_project / ".agent" / "skills").glob(f"valdoz-phase-{p}-*"))
        assert len(skill_dirs) == 1, f"Missing skill folder for Phase {p}"
        skill_file = skill_dirs[0] / "SKILL.md"
        assert skill_file.exists(), f"Missing SKILL.md for Phase {p}"

        # Validate YAML frontmatter
        content = skill_file.read_text(encoding="utf-8")
        assert content.startswith("---")
        parts = content.split("---", 2)
        assert len(parts) >= 3
        fm = yaml.safe_load(parts[1])
        assert "name" in fm
        assert "description" in fm
        assert fm["name"].startswith(f"valdoz-phase-{p}-")


def test_size_limits_under_12k_chars(temp_project: Path):
    outputs = sync_all_runtimes(temp_project, dry_run=True)
    for path_str, content in outputs.items():
        size = len(content)
        assert size <= CHAR_LIMIT, f"File {path_str} exceeds limit: {size} > {CHAR_LIMIT}"
        # Assert healthy margin (under 6,000 characters for our clean playbooks)
        assert size < 6000, f"File {path_str} unexpectedly bloated: {size} chars"


def test_dry_run_does_not_write_files(tmp_path: Path):
    outputs = sync_all_runtimes(tmp_path, dry_run=True)
    assert len(outputs) >= 15
    # Files must not exist on disk
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "GEMINI.md").exists()
    assert not (tmp_path / ".agent").exists()


def test_sync_idempotency(temp_project: Path):
    # First sync
    outputs_1 = sync_all_runtimes(temp_project, dry_run=False)
    # Second sync
    outputs_2 = sync_all_runtimes(temp_project, dry_run=False)

    for path_str, content_1 in outputs_1.items():
        content_2 = outputs_2[path_str]
        assert content_1 == content_2, f"Idempotency violation in {path_str}"
