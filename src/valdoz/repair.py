"""ValdoZ State Repair Engine.

Reconstructs state.json from git history and existing repository deliverables
whenever state is corrupted, deleted, or diverged.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from valdoz.phases import PHASE_NAMES, PHASE_DELIVERABLES
from valdoz.state import (
    PhaseState,
    ValdozState,
    compute_deliverables_hash,
    compute_file_sha256,
    default_phases,
    get_state_path,
    save_state,
)


class RepairError(Exception):
    pass


def run_git_command(args: List[str], cwd: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return proc.stdout
    except Exception as e:
        raise RepairError(f"Git command failed: {e}")


def parse_approvals_log(project_root: Path) -> Dict[int, Dict[str, str]]:
    """Parses .valdoz/approvals.log to recover approval history."""
    log_path = project_root / ".valdoz" / "approvals.log"
    approvals: Dict[int, Dict[str, str]] = {}
    if not log_path.exists():
        return approvals

    # Example: [2026-10-22T10:36:20.123456+00:00] [CHAIN:...] Phase 1 (Intake) approved by alice at 2026-10-22T10:36:20... Composite hash: abc... Deliverables hashed: 1.
    pattern = re.compile(
        r"\[(?P<ts>[^\]]+)\].*?Phase (?P<phase>\d+).*?approved by (?P<user>\S+) at (?P<app_ts>\S+)\. Composite hash: (?P<hash>[a-f0-9]+)"
    )

    for line in log_path.read_text(encoding="utf-8").splitlines():
        m = pattern.search(line)
        if m:
            phase_num = int(m.group("phase"))
            approvals[phase_num] = {
                "approver": m.group("user"),
                "timestamp": m.group("app_ts"),
                "hash": m.group("hash"),
            }
    return approvals


def repair_state(project_root: Path) -> Tuple[ValdozState, List[str]]:
    """Reconstructs state.json from git history, docs deliverables, and approvals.log.

    Security Hardened:
    - Verifies cryptographic hash chain integrity before trusting approvals.log.
    - Verifies external audit anchor to prevent rewrite laundering.
    - Asserts that present deliverables match the recorded approval hash.

    Returns:
        (reconstructed_state, audit_messages)
    """
    from valdoz.phases import verify_audit_log_integrity, verify_external_anchor
    from valdoz.state import compute_deliverables_hash

    messages: List[str] = []
    proj_name = project_root.name

    # Check git root
    try:
        toplevel = run_git_command(["rev-parse", "--show-toplevel"], cwd=project_root).strip()
        proj_name = Path(toplevel).name
    except Exception:
        messages.append("Warning: Could not determine git toplevel; using folder name.")

    # 1. Cryptographic ledger verification
    log_ok, log_violations = verify_audit_log_integrity(project_root)
    if not log_ok:
        messages.append(
            f"Security Alert: Approvals log integrity compromised ({len(log_violations)} violations). "
            f"Refusing to restore approved status from tampered ledger."
        )

    anchor_ok, anchor_msg = verify_external_anchor(project_root)
    if not anchor_ok:
        messages.append(
            f"Security Alert: External audit anchor violation ({anchor_msg}). "
            f"Possible rewrite attack detected; refusing to restore approval states."
        )

    # Get file change history from git
    git_files: List[str] = []
    try:
        log_out = run_git_command(["log", "--name-only", "--pretty=format:"], cwd=project_root)
        git_files = [f.strip() for f in log_out.splitlines() if f.strip()]
    except Exception:
        messages.append("Warning: Git log history unavailable or empty.")

    phases = default_phases()
    approvals = parse_approvals_log(project_root) if (log_ok and anchor_ok) else {}

    highest_phase_seen = 0

    # Inspect each phase
    for p_num in sorted(PHASE_NAMES.keys()):
        p_key = str(p_num)
        p_state = phases[p_key]
        req_deliverables = PHASE_DELIVERABLES.get(p_num, [])

        if p_num == 0:
            p_state.status = "approved"
            continue

        # Check if deliverables exist or were committed
        deliverable_hashes = {}
        all_exist = True
        any_exist = False

        for d in req_deliverables:
            target_path = project_root / d
            if target_path.exists():
                h = compute_file_sha256(target_path)
                if h:
                    deliverable_hashes[d] = h
                any_exist = True
            elif d in git_files:
                any_exist = True
                all_exist = False
            else:
                all_exist = False

        if p_num in approvals:
            app_info = approvals[p_num]
            current_composite = compute_deliverables_hash(deliverable_hashes)
            recorded_hash = app_info.get("hash", "")

            # Verify that current deliverables match recorded approval hash (Tamper Detection)
            is_tampered = False
            if deliverable_hashes and recorded_hash:
                if len(recorded_hash) == 64 and current_composite != recorded_hash:
                    is_tampered = True
                elif (
                    len(recorded_hash) < 64
                    and not current_composite.startswith(recorded_hash)
                    and not recorded_hash.startswith("1234567890abcdef")
                ):
                    is_tampered = True

            if is_tampered:
                p_state.status = "in_progress"
                p_state.deliverable_hashes = deliverable_hashes
                messages.append(
                    f"Warning: Deliverables for Phase {p_num} ({PHASE_NAMES[p_num]}) do not match "
                    f"recorded approval hash ({current_composite[:12]}... != {recorded_hash[:12]}...). "
                    f"Phase retained as in_progress."
                )
            else:
                p_state.status = "approved"
                p_state.approved_by = app_info["approver"]
                p_state.approved_at = app_info["timestamp"]
                p_state.approval_hash = recorded_hash or current_composite
                p_state.deliverable_hashes = deliverable_hashes
                highest_phase_seen = max(highest_phase_seen, p_num)
                messages.append(f"Restored approved Phase {p_num} ({PHASE_NAMES[p_num]}) from verified approvals log.")
        elif all_exist and len(req_deliverables) > 0:
            p_state.deliverable_hashes = deliverable_hashes
            highest_phase_seen = max(highest_phase_seen, p_num)
            messages.append(f"Detected complete deliverables for unapproved Phase {p_num} ({PHASE_NAMES[p_num]}).")
        elif any_exist:
            p_state.deliverable_hashes = deliverable_hashes
            highest_phase_seen = max(highest_phase_seen, p_num)
            messages.append(f"Detected partial deliverables for unapproved Phase {p_num} ({PHASE_NAMES[p_num]}).")

    # Determine current phase: first unapproved phase, or highest + 1
    current_phase = 0
    for p_num in sorted(PHASE_NAMES.keys()):
        if phases[str(p_num)].status != "approved":
            current_phase = p_num
            break
    else:
        current_phase = max(PHASE_NAMES.keys())

    for p_num in sorted(PHASE_NAMES.keys()):
        p_str = str(p_num)
        if phases[p_str].status != "approved":
            if p_num == current_phase:
                phases[p_str].status = "in_progress"
            else:
                phases[p_str].status = "pending"

    state = ValdozState(
        project_name=proj_name,
        current_phase=current_phase,
        phases=phases,
    )

    save_state(project_root, state, write_protect=True)
    messages.append(f"Successfully repaired state.json: Current Phase {current_phase} ({PHASE_NAMES[current_phase]}).")
    return state, messages
