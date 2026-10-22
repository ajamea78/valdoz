"""Unit tests for ValdoZ state, write protection, and tamper detection."""

import pytest
from pathlib import Path
from valdoz.state import (
    ValdozState,
    load_state,
    save_state,
    get_state_path,
    is_write_protected,
    set_write_protection,
    compute_file_sha256,
    verify_phase_integrity,
    StateError,
)


@pytest.fixture
def temp_project(tmp_path: Path):
    return tmp_path


def test_state_initialization_and_serialization(temp_project: Path):
    state = ValdozState(project_name="test-project", language="en")
    save_state(temp_project, state)

    loaded = load_state(temp_project)
    assert loaded.project_name == "test-project"
    assert loaded.current_phase == 0
    assert "0" in loaded.phases
    assert loaded.phases["0"].status == "in_progress"


def test_write_protection_toggle(temp_project: Path):
    state = ValdozState(project_name="lock-test")
    save_state(temp_project, state, write_protect=True)

    state_file = get_state_path(temp_project)
    assert is_write_protected(state_file)

    # Attempting to overwrite directly via standard write fails or raises PermissionError
    with pytest.raises(PermissionError):
        state_file.write_text("tampered content")

    # save_state knows how to safely unlock, write, and re-lock
    state.project_name = "updated-name"
    save_state(temp_project, state, write_protect=True)

    loaded = load_state(temp_project)
    assert loaded.project_name == "updated-name"
    assert is_write_protected(state_file)


def test_tamper_detection(temp_project: Path):
    deliverable = temp_project / "docs" / "01-intake.md"
    deliverable.parent.mkdir(parents=True, exist_ok=True)
    deliverable.write_text("# Client Brief\nOriginal text\n")

    initial_hash = compute_file_sha256(deliverable)
    assert initial_hash is not None

    state = ValdozState(project_name="integrity-test", current_phase=1)
    state.phases["1"].status = "approved"
    state.phases["1"].deliverable_hashes = {"docs/01-intake.md": initial_hash}
    save_state(temp_project, state)

    # 1. Integrity check passes initially
    valid, violations = verify_phase_integrity(temp_project, 1)
    assert valid is True
    assert len(violations) == 0

    # 2. Tampering with file causes integrity check to fail
    deliverable.write_text("# Client Brief\nTampered text by unauthorized agent!\n")
    valid, violations = verify_phase_integrity(temp_project, 1)
    assert valid is False
    assert len(violations) == 1
    assert "Tampering detected" in violations[0]

    # 3. Deleting deliverable is also detected
    deliverable.unlink()
    valid, violations = verify_phase_integrity(temp_project, 1)
    assert valid is False
    assert "missing" in violations[0]
