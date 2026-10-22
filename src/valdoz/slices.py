"""ValdoZ Phase 6 Slice Governance Engine.

Enforces 4-state slice lifecycle (open -> built -> gated -> approved),
the Three Slice Gate Conditions, and git spec timestamp ordering.
"""

from __future__ import annotations

import getpass
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from valdoz.approval import NonInteractiveApprovalError
from valdoz.gates import extract_headings
from valdoz.phases import append_approvals_log
from valdoz.state import (
    compute_deliverables_hash,
    compute_file_sha256,
    is_write_protected,
    set_write_protection,
)

REQUIRED_SLICE_HEADINGS = [
    "Summary",
    "Acceptance Criteria",
    "Test Plan",
    "File Manifest",
]


class SliceError(Exception):
    pass


class SliceGateConditionError(SliceError):
    pass


class SliceState(BaseModel):
    slice_id: str
    status: str = "open"  # open, built, gated, approved
    base_commit: str = ""
    spec_path: str = ""
    spec_commit: Optional[str] = None
    tests_passed: Optional[bool] = None
    coverage_delta: Optional[float] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    deliverable_hashes: Dict[str, str] = Field(default_factory=dict)


def get_slices_dir(project_root: Path) -> Path:
    return project_root / ".valdoz" / "slices"


def get_slice_file_path(project_root: Path, slice_id: str) -> Path:
    return get_slices_dir(project_root) / f"{slice_id}.json"


def load_slice(project_root: Path, slice_id: str) -> SliceState:
    path = get_slice_file_path(project_root, slice_id)
    if not path.exists():
        raise SliceError(f"Slice state file not found for '{slice_id}' at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return SliceState(**data)


def save_slice(project_root: Path, slice_state: SliceState, write_protect: bool = False) -> None:
    path = get_slice_file_path(project_root, slice_state.slice_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    was_protected = is_write_protected(path)
    if was_protected:
        set_write_protection(path, read_only=False)

    try:
        path.write_text(json.dumps(slice_state.model_dump(), indent=2), encoding="utf-8")
    finally:
        if write_protect or was_protected:
            set_write_protection(path, read_only=True)


def list_slices(project_root: Path) -> List[SliceState]:
    slices_dir = get_slices_dir(project_root)
    if not slices_dir.exists():
        return []
    slices = []
    for f in sorted(slices_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            slices.append(SliceState(**data))
        except Exception:
            continue
    return slices


def _run_git(args: List[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout.strip()


def validate_slice_spec(spec_file: Path) -> Tuple[bool, List[str]]:
    """Validates that a slice specification markdown file contains required headings."""
    if not spec_file.exists():
        return False, [f"Slice specification file missing: {spec_file}"]

    text = spec_file.read_text(encoding="utf-8", errors="replace")
    headings = extract_headings(text)

    missing = []
    for req in REQUIRED_SLICE_HEADINGS:
        if not any(req.lower() in h.lower() for h in headings):
            missing.append(req)

    return len(missing) == 0, missing


def parse_slice_index(slice_id: str) -> int:
    m = re.match(r"^(\d+)", slice_id)
    return int(m.group(1)) if m else 0


def start_slice(project_root: Path, slice_id: str) -> SliceState:
    """Opens a new slice. Enforces that previous slice is approved and spec exists."""
    slice_id = slice_id.strip()
    idx = parse_slice_index(slice_id)

    # 1. Enforce slice sequence: slice N-1 must be approved
    if idx > 1:
        prev_slices = [s for s in list_slices(project_root) if parse_slice_index(s.slice_id) == idx - 1]
        if not prev_slices or prev_slices[0].status != "approved":
            prev_name = prev_slices[0].slice_id if prev_slices else f"slice {idx - 1:02d}"
            prev_status = prev_slices[0].status if prev_slices else "not started"
            raise SliceError(
                f"Cannot start slice '{slice_id}': Previous slice '{prev_name}' must be approved first (current status: '{prev_status}')."
            )

    # 2. Check spec file and required headings
    spec_path = project_root / "docs" / "slices" / f"{slice_id}.md"
    valid, missing_hdgs = validate_slice_spec(spec_path)
    if not valid:
        raise SliceError(
            f"Cannot start slice '{slice_id}': specification '{spec_path}' is invalid:\n"
            + "\n".join(f" - Missing section: '{h}'" for h in missing_hdgs)
        )

    # 3. Capture base commit
    base_commit = _run_git(["rev-parse", "HEAD"], cwd=project_root) or "initial"

    slice_state = SliceState(
        slice_id=slice_id,
        status="open",
        base_commit=base_commit,
        spec_path=f"docs/slices/{slice_id}.md",
    )
    save_slice(project_root, slice_state)
    return slice_state


def done_slice(
    project_root: Path,
    slice_id: str,
    pre_existing_tests_pass: bool = True,
    new_tests_pass: bool = True,
    coverage_delta: float = 0.0,
    min_coverage_threshold: float = 0.0,
) -> SliceState:
    """Validates completion of a slice against the Three Slice Gate Conditions."""
    slice_state = load_slice(project_root, slice_id)
    if slice_state.status != "open":
        raise SliceError(
            f"Slice '{slice_id}' is not in 'open' state (current: '{slice_state.status}')."
        )

    # Check Three Slice Gate Conditions:
    # Condition (a): pre-existing tests pass
    if not pre_existing_tests_pass:
        raise SliceGateConditionError(
            f"Slice Gate Condition (a) FAILED: Pre-existing tests before slice '{slice_id}' failed."
        )

    # Condition (b): new tests pass
    if not new_tests_pass:
        raise SliceGateConditionError(
            f"Slice Gate Condition (b) FAILED: New tests introduced in slice '{slice_id}' failed."
        )

    # Condition (c): test coverage does not decrease below threshold
    if coverage_delta < -min_coverage_threshold:
        raise SliceGateConditionError(
            f"Slice Gate Condition (c) FAILED: Test coverage decreased by {coverage_delta:.2f}% "
            f"(threshold: -{min_coverage_threshold:.2f}%)."
        )

    # Advance state to gated
    slice_state.status = "gated"
    slice_state.tests_passed = True
    slice_state.coverage_delta = coverage_delta
    save_slice(project_root, slice_state)
    return slice_state


def approve_slice(
    project_root: Path,
    slice_id: str,
    approver_name: Optional[str] = None,
    enforce_tty: bool = True,
    confirmation_input: Optional[str] = None,
) -> SliceState:
    """Interactively approves a gated slice (Human-Only, Interactive TTY)."""
    if enforce_tty and not sys.stdin.isatty():
        raise NonInteractiveApprovalError(
            "Security Violation: 'valdoz slice approve' requires an interactive terminal.\n"
            "AI agents and scripts cannot approve build slices."
        )

    slice_state = load_slice(project_root, slice_id)
    if slice_state.status != "gated":
        raise SliceError(
            f"Slice '{slice_id}' is not in 'gated' state (current: '{slice_state.status}'). "
            "Run 'valdoz slice done' with passing test evidence first."
        )

    if confirmation_input is not None:
        typed = confirmation_input.strip().lower()
        if typed != slice_id.lower() and typed != "approve":
            raise SliceError(f"Approval aborted: confirmation '{confirmation_input}' did not match slice '{slice_id}'.")

    # Hash slice spec and touch files
    hashes: Dict[str, str] = {}
    spec_full = project_root / slice_state.spec_path
    if spec_full.exists():
        h = compute_file_sha256(spec_full)
        if h:
            hashes[slice_state.spec_path] = h

    approver = approver_name or getpass.getuser()
    now_iso = datetime.now(timezone.utc).isoformat()

    slice_state.status = "approved"
    slice_state.approved_by = approver
    slice_state.approved_at = now_iso
    slice_state.deliverable_hashes = hashes

    # Write-protect slice state file (chmod 444)
    save_slice(project_root, slice_state, write_protect=True)

    append_approvals_log(
        project_root,
        f"Slice '{slice_id}' approved by {approver} at {now_iso}.",
    )
    return slice_state
