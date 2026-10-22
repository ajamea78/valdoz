import json
import pytest
from pathlib import Path
from valdoz.approval import (
    NonInteractiveApprovalError,
    approve_phase,
    generate_human_token,
    verify_human_token,
)
from valdoz.slices import approve_slice, start_slice, done_slice, save_slice, SliceState
from valdoz.state import ValdozState, save_state

def test_verify_human_token():
    token = generate_human_token("phase", "1")
    assert verify_human_token(token, "phase", "1")
    assert not verify_human_token(token, "phase", "2")
    assert not verify_human_token("invalid-token", "phase", "1")

def test_approve_phase_with_human_token(tmp_path: Path):
    state = ValdozState(
        project_name="bridge-test",
        language="en",
        current_phase=1,
    )
    save_state(tmp_path, state)

    # Required deliverable for Phase 1
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "01-intake.md").write_text("# Intake Brief\nConfirmed")

    # Without TTY or token, must fail with NonInteractiveApprovalError
    with pytest.raises(NonInteractiveApprovalError):
        approve_phase(tmp_path, phase_num=1, enforce_tty=True)

    # With valid human token, succeeds even without interactive TTY
    token = generate_human_token("phase", "1")
    hashes = approve_phase(
        tmp_path,
        phase_num=1,
        enforce_tty=True,
        human_token=token,
    )
    assert "docs/01-intake.md" in hashes

def test_approve_slice_with_human_token(tmp_path: Path):
    slices_dir = tmp_path / ".valdoz" / "slices"
    slices_dir.mkdir(parents=True)
    docs_slices = tmp_path / "docs" / "slices"
    docs_slices.mkdir(parents=True)
    spec = docs_slices / "01-auth.md"
    spec.write_text("## Summary\n## Acceptance Criteria\n## Test Plan\n## File Manifest")

    slice_state = SliceState(
        slice_id="01-auth",
        status="gated",
        spec_path="docs/slices/01-auth.md",
        tests_passed=True,
    )
    save_slice(tmp_path, slice_state)

    # Without token or TTY, must raise NonInteractiveApprovalError
    with pytest.raises(NonInteractiveApprovalError):
        approve_slice(tmp_path, "01-auth", enforce_tty=True)

    # With token, succeeds
    token = generate_human_token("slice", "01-auth")
    approved = approve_slice(tmp_path, "01-auth", enforce_tty=True, human_token=token)
    assert approved.status == "approved"
