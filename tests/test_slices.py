"""Unit tests for Phase 6 slice governance and three gate conditions."""

import pytest
from pathlib import Path
from valdoz.slices import (
    start_slice,
    done_slice,
    approve_slice,
    load_slice,
    list_slices,
    validate_slice_spec,
    SliceError,
    SliceGateConditionError,
)
from valdoz.approval import NonInteractiveApprovalError
from valdoz.state import ValdozState, save_state, is_write_protected, get_state_path


@pytest.fixture
def slice_project(tmp_path: Path):
    state = ValdozState(project_name="slice-test", current_phase=6)
    save_state(tmp_path, state)
    slices_doc_dir = tmp_path / "docs" / "slices"
    slices_doc_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


def create_valid_spec(project_root: Path, slice_id: str) -> Path:
    spec_path = project_root / "docs" / "slices" / f"{slice_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(f"""# Slice: {slice_id}

## Summary
Implements core functionality for {slice_id}.

## Acceptance Criteria
- Unit tests pass.
- API returns 200 OK.

## Test Plan
Run unit and integration suites.

## File Manifest
- `src/auth.py`
- `tests/test_auth.py`
""")
    return spec_path


def test_slice_spec_validation(slice_project: Path):
    bad_spec = slice_project / "docs" / "slices" / "bad.md"
    bad_spec.write_text("# Slice\n## Summary\nIncomplete.\n")

    valid, missing = validate_slice_spec(bad_spec)
    assert valid is False
    assert "Acceptance Criteria" in missing
    assert "Test Plan" in missing
    assert "File Manifest" in missing


def test_slice_start_and_sequence_enforcement(slice_project: Path):
    # Create spec for slice 01
    create_valid_spec(slice_project, "01-auth")

    # Start slice 01 succeeds
    s1 = start_slice(slice_project, "01-auth")
    assert s1.slice_id == "01-auth"
    assert s1.status == "open"

    # Create spec for slice 02
    create_valid_spec(slice_project, "02-profile")

    # Starting slice 02 before slice 01 is approved must fail
    with pytest.raises(SliceError, match="must be approved first"):
        start_slice(slice_project, "02-profile")


def test_slice_done_three_gate_conditions(slice_project: Path):
    create_valid_spec(slice_project, "01-core")
    start_slice(slice_project, "01-core")

    # Condition (a) failure: pre-existing tests fail
    with pytest.raises(SliceGateConditionError, match="Condition \\(a\\) FAILED"):
        done_slice(slice_project, "01-core", pre_existing_tests_pass=False)

    # Condition (b) failure: new tests fail
    with pytest.raises(SliceGateConditionError, match="Condition \\(b\\) FAILED"):
        done_slice(slice_project, "01-core", new_tests_pass=False)

    # Condition (c) failure: coverage drop exceeds threshold
    with pytest.raises(SliceGateConditionError, match="Condition \\(c\\) FAILED"):
        done_slice(slice_project, "01-core", coverage_delta=-2.5, min_coverage_threshold=0.0)

    # All pass -> gated
    done_s = done_slice(slice_project, "01-core", pre_existing_tests_pass=True, new_tests_pass=True, coverage_delta=0.5)
    assert done_s.status == "gated"


def test_slice_approve_lifecycle(slice_project: Path, monkeypatch):
    create_valid_spec(slice_project, "01-auth")
    start_slice(slice_project, "01-auth")
    done_slice(slice_project, "01-auth")

    # Non-interactive approval fails
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(NonInteractiveApprovalError):
        approve_slice(slice_project, "01-auth", enforce_tty=True)

    # Valid approval
    app_s = approve_slice(
        slice_project,
        "01-auth",
        approver_name="bob",
        enforce_tty=False,
        confirmation_input="01-auth",
    )
    assert app_s.status == "approved"
    assert app_s.approved_by == "bob"

    # State file write-protected
    slice_path = slice_project / ".valdoz" / "slices" / "01-auth.json"
    assert is_write_protected(slice_path)
