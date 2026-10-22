"""Unit tests for ValdoZ human gate approval engine."""

import pytest
from pathlib import Path
from valdoz.approval import (
    approve_phase,
    NonInteractiveApprovalError,
    MissingDeliverableError,
    ApprovalError,
)
from valdoz.state import (
    ValdozState,
    save_state,
    load_state,
    get_state_path,
    is_write_protected,
)


@pytest.fixture
def initialized_project(tmp_path: Path):
    state = ValdozState(project_name="approval-proj", current_phase=1)
    state.phases["1"].status = "in_progress"
    save_state(tmp_path, state)
    return tmp_path


def test_approval_refuses_non_interactive_tty(initialized_project: Path, monkeypatch):
    """Approval must refuse execution if not in a real TTY terminal."""
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(NonInteractiveApprovalError, match="requires an interactive terminal"):
        approve_phase(initialized_project, phase_num=1, enforce_tty=True)


def test_approval_fails_on_missing_deliverable(initialized_project: Path):
    """Approval fails if required deliverable does not exist on disk."""
    # Phase 1 requires docs/01-intake.md which has not been created yet
    with pytest.raises(MissingDeliverableError, match="missing required deliverables"):
        approve_phase(
            initialized_project,
            phase_num=1,
            enforce_tty=False,
            confirmation_input="intake",
        )


def test_approval_fails_on_wrong_confirmation(initialized_project: Path):
    doc = initialized_project / "docs" / "01-intake.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Client Intake Brief\nContent here.\n")

    with pytest.raises(ApprovalError, match="did not match"):
        approve_phase(
            initialized_project,
            phase_num=1,
            enforce_tty=False,
            confirmation_input="wrong-name",
        )


def test_successful_interactive_approval(initialized_project: Path):
    doc = initialized_project / "docs" / "01-intake.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Client Intake Brief\nVerified content.\n")

    hashes = approve_phase(
        initialized_project,
        phase_num=1,
        enforce_tty=False,
        confirmation_input="intake",
        approver_name="alice",
    )

    assert "docs/01-intake.md" in hashes

    state = load_state(initialized_project)
    phase1 = state.phases["1"]
    assert phase1.status == "approved"
    assert phase1.approved_by == "alice"
    assert phase1.approval_hash is not None
    assert phase1.deliverable_hashes["docs/01-intake.md"] == hashes["docs/01-intake.md"]

    # State file must be write-protected
    state_file = get_state_path(initialized_project)
    assert is_write_protected(state_file)

    # Approvals log must record approval
    log_file = initialized_project / ".valdoz" / "approvals.log"
    assert log_file.exists()
    assert "approved by alice" in log_file.read_text()
