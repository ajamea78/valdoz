"""Unit tests for ValdoZ state repair from git history."""

import subprocess
import pytest
from pathlib import Path
from valdoz.repair import repair_state
from valdoz.state import (
    ValdozState,
    save_state,
    load_state,
    get_state_path,
    is_write_protected,
)


@pytest.fixture
def git_project(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True)
    return tmp_path


def test_state_repair_from_git_deliverables_and_log(git_project: Path):
    valdoz_dir = git_project / ".valdoz"
    valdoz_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = git_project / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create deliverable 01-intake.md and commit
    intake_file = docs_dir / "01-intake.md"
    intake_file.write_text("# Client Brief\nVerbatim client brief here.\n")
    subprocess.run(["git", "add", "docs/01-intake.md"], cwd=str(git_project), check=True)
    subprocess.run(["git", "commit", "-m", "docs: add intake brief for phase 1"], cwd=str(git_project), check=True)

    # 2. Append simulated approval to approvals.log
    approvals_log = valdoz_dir / "approvals.log"
    approvals_log.write_text(
        "[2026-10-22T10:00:00+00:00] Phase 1 (Intake) approved by lead at 2026-10-22T10:00:00+00:00. "
        "Composite hash: 1234567890abcdef1234567890abcdef... Deliverables hashed: 1.\n"
    )

    # 3. Create deliverable 02-requirements.md (in progress/gated)
    req_file = docs_dir / "02-requirements.md"
    req_file.write_text("# Requirements\nSpecification in progress.\n")

    # 4. State file is missing / deleted
    state_file = get_state_path(git_project)
    assert not state_file.exists()

    # 5. Run state repair
    reconstructed, logs = repair_state(git_project)

    assert state_file.exists()
    assert is_write_protected(state_file)

    # Phase 0 and 1 must be approved
    assert reconstructed.phases["0"].status == "approved"
    assert reconstructed.phases["1"].status == "approved"
    assert reconstructed.phases["1"].approved_by == "lead"
    assert "docs/01-intake.md" in reconstructed.phases["1"].deliverable_hashes

    # Current phase should be Phase 2
    assert reconstructed.current_phase == 2
    assert reconstructed.phases["2"].status == "in_progress"
