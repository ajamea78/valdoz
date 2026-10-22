"""ValdoZ Approval Engine.

Enforces interactive-only, human approval of phases.
Refuses script or automated execution. Computes deliverable SHA-256 hashes
and write-protects state.json.
"""

from __future__ import annotations

import getpass
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from valdoz.phases import (
    PHASE_NAMES,
    append_approvals_log,
    get_required_deliverables,
)
from valdoz.state import (
    compute_deliverables_hash,
    compute_file_sha256,
    get_state_path,
    load_state,
    save_state,
    set_write_protection,
)


class ApprovalError(Exception):
    pass


class NonInteractiveApprovalError(ApprovalError):
    pass


class MissingDeliverableError(ApprovalError):
    pass


def approve_phase(
    project_root: Path,
    phase_num: Optional[int] = None,
    approver_name: Optional[str] = None,
    enforce_tty: bool = True,
    confirmation_input: Optional[str] = None,
) -> Dict[str, str]:
    """Interactively approves a project phase.

    Args:
        project_root: Project repository root.
        phase_num: Phase number to approve (defaults to state.current_phase).
        approver_name: Name of human approver.
        enforce_tty: When True, requires sys.stdin.isatty() == True.
        confirmation_input: User typed confirmation string.

    Returns:
        Dictionary of deliverable file paths to their computed SHA-256 hashes.

    Raises:
        NonInteractiveApprovalError: If called from non-interactive shell.
        MissingDeliverableError: If required deliverables are missing.
        ApprovalError: If phase name confirmation fails or state is invalid.
    """
    if enforce_tty and not sys.stdin.isatty():
        raise NonInteractiveApprovalError(
            "Security Violation: 'valdoz phase approve' requires an interactive terminal.\n"
            "AI agents and automated scripts are strictly prohibited from approving work."
        )

    state = load_state(project_root)
    target_num = phase_num if phase_num is not None else state.current_phase
    phase_key = str(target_num)

    if phase_key not in state.phases:
        raise ApprovalError(f"Invalid phase number: {target_num}")

    phase_name = PHASE_NAMES.get(target_num, f"Phase {target_num}")

    # Verify confirmation input
    expected_name = phase_name.lower().replace(" ", "-")
    if confirmation_input is not None:
        typed = confirmation_input.strip().lower().replace(" ", "-")
        if typed != expected_name and typed != str(target_num):
            raise ApprovalError(
                f"Approval aborted: confirmation string '{confirmation_input}' did not match phase '{expected_name}'."
            )

    # Check deliverables
    required_files = get_required_deliverables(target_num)
    missing: List[str] = []
    deliverable_hashes: Dict[str, str] = {}

    for rel_path in required_files:
        file_path = project_root / rel_path
        if not file_path.exists():
            missing.append(rel_path)
        else:
            file_hash = compute_file_sha256(file_path)
            if file_hash:
                deliverable_hashes[rel_path] = file_hash

    if missing:
        raise MissingDeliverableError(
            f"Cannot approve Phase {target_num} ({phase_name}): missing required deliverables:\n"
            + "\n".join(f" - {f}" for f in missing)
        )

    composite_hash = compute_deliverables_hash(deliverable_hashes)
    approver = approver_name or getpass.getuser()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Update phase state
    phase_state = state.phases[phase_key]
    phase_state.status = "approved"
    phase_state.approved_by = approver
    phase_state.approved_at = now_iso
    phase_state.approval_hash = composite_hash
    phase_state.deliverable_hashes = deliverable_hashes

    # Save state and apply read-only write protection (chmod 444)
    save_state(project_root, state, write_protect=True)

    append_approvals_log(
        project_root,
        f"Phase {target_num} ({phase_name}) approved by {approver} at {now_iso}. "
        f"Composite hash: {composite_hash[:16]}... "
        f"Deliverables hashed: {len(deliverable_hashes)}.",
    )

    return deliverable_hashes
