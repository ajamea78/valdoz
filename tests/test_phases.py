"""Unit tests for ValdoZ phase machine and reopen cascades."""

import pytest
from pathlib import Path
from valdoz.phases import (
    advance_phase,
    reopen_phase,
    PhaseTransitionError,
    ReopenConfirmationError,
)
from valdoz.state import (
    ValdozState,
    save_state,
    load_state,
)


@pytest.fixture
def project_at_phase_1(tmp_path: Path):
    state = ValdozState(project_name="phase-proj", current_phase=1)
    state.phases["1"].status = "in_progress"
    save_state(tmp_path, state)
    return tmp_path


def test_advance_phase_refuses_unapproved(project_at_phase_1: Path):
    with pytest.raises(PhaseTransitionError, match="is not approved"):
        advance_phase(project_at_phase_1)


def test_advance_phase_succeeds_when_approved(project_at_phase_1: Path):
    state = load_state(project_at_phase_1)
    state.phases["1"].status = "approved"
    save_state(project_at_phase_1, state)

    new_phase = advance_phase(project_at_phase_1)
    assert new_phase == 2

    reloaded = load_state(project_at_phase_1)
    assert reloaded.current_phase == 2
    assert reloaded.phases["2"].status == "in_progress"
    # Check deliverable stub generated
    assert (project_at_phase_1 / "docs" / "02-requirements.md").exists()


def test_reopen_phase_cascades_pending_reapproval(tmp_path: Path):
    state = ValdozState(project_name="cascade-test", current_phase=4)
    for p in range(1, 5):
        state.phases[str(p)].status = "approved"
        state.phases[str(p)].approval_hash = f"hash-{p}"
    save_state(tmp_path, state)

    # Reopen Phase 2
    reopen_phase(tmp_path, target_phase=2)

    reloaded = load_state(tmp_path)
    assert reloaded.current_phase == 2
    assert reloaded.phases["2"].status == "in_progress"
    assert reloaded.phases["2"].approval_hash is None

    # Downstream phases 3 and 4 must be pending_reapproval
    assert reloaded.phases["3"].status == "pending_reapproval"
    assert reloaded.phases["3"].approval_hash is None
    assert reloaded.phases["4"].status == "pending_reapproval"
    assert reloaded.phases["4"].approval_hash is None


def test_reopen_irreversible_phase_requires_confirmation(tmp_path: Path):
    state = ValdozState(project_name="deploy-proj", current_phase=8)
    state.phases["8"].status = "approved"
    save_state(tmp_path, state)

    # Reopen without typing project name must fail
    with pytest.raises(ReopenConfirmationError, match="IRREVERSIBLE side effects"):
        reopen_phase(tmp_path, target_phase=8, confirm_project_name="wrong-name")

    # Reopen with correct project name succeeds and generates CR stub
    reopen_phase(tmp_path, target_phase=8, confirm_project_name="deploy-proj")
    reloaded = load_state(tmp_path)
    assert reloaded.current_phase == 8
    assert reloaded.phases["8"].status == "in_progress"

    cr_stub = tmp_path / "docs" / "changes" / "CR-001-reopen-phase8.md"
    assert cr_stub.exists()
    assert "Live cloud infrastructure and DNS may diverge" in cr_stub.read_text()
