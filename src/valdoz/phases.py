"""ValdoZ Phase State Machine.

Manages the 11 delivery phases, required deliverables, command whitelists,
side-effect classifications, and phase reopening cascades.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

from valdoz.state import (
    PHASE_NAMES,
    ValdozState,
    load_state,
    save_state,
    set_write_protection,
    get_state_path,
)


class SideEffectInfo(BaseModel):
    category: str
    reversible: bool
    description: str


SIDE_EFFECT_CLASSES: Dict[int, SideEffectInfo] = {
    0: SideEffectInfo(category="Files only", reversible=True, description="Local configuration files only"),
    1: SideEffectInfo(category="Files only", reversible=True, description="Client brief and intake markdown"),
    2: SideEffectInfo(category="Files only", reversible=True, description="Requirements specification markdown"),
    3: SideEffectInfo(category="Files only", reversible=True, description="Stack decision markdown and decisions log"),
    4: SideEffectInfo(category="Files only", reversible=True, description="Architecture and plan markdown files"),
    5: SideEffectInfo(category="Config & Tooling", reversible=True, description="Repository setup and CI workflows"),
    6: SideEffectInfo(category="Commits & Branches", reversible=True, description="Code commits and git feature branches"),
    7: SideEffectInfo(category="Test Artifacts", reversible=True, description="Verification logs and test coverage reports"),
    8: SideEffectInfo(category="Live Infrastructure", reversible=False, description="IRREVERSIBLE: Live deployments, cloud infrastructure, DNS, and database state"),
    9: SideEffectInfo(category="Access Transfer", reversible=False, description="IRREVERSIBLE: Credentials and repository ownership handover to client"),
    10: SideEffectInfo(category="Production Changes", reversible=False, description="Post-handover change requests"),
}


PHASE_DELIVERABLES: Dict[int, List[str]] = {
    0: [".valdoz/state.json"],
    1: ["docs/01-intake.md"],
    2: ["docs/02-requirements.md"],
    3: ["docs/03-stack-decision.md"],
    4: ["docs/04-architecture.md", "docs/04-plan.md"],
    5: ["README.md"],
    6: [],  # Dynamic per slice (docs/slices/NN-name.md)
    7: ["docs/07-verification.md"],
    8: ["docs/08-deploy.md"],
    9: ["docs/09-handover.md"],
    10: [],
}


PHASE_COMMAND_WHITELISTS: Dict[int, List[str]] = {
    0: ["valdoz *", "git status"],
    1: ["valdoz *", "git status", "git diff"],
    2: ["valdoz *", "git status", "git diff"],
    3: ["valdoz *", "git status", "git diff"],
    4: ["valdoz *", "git status", "git diff"],
    5: ["valdoz *", "git *", "uv *", "pip *", "npm *", "pytest *", "python *"],
    6: ["valdoz *", "git *", "uv *", "pip *", "npm *", "pytest *", "python *"],
    7: ["valdoz *", "git *", "pytest *", "npm test", "npm run lint"],
    8: ["valdoz *", "git *", "vercel *", "fly *", "aws *", "docker *"],
    9: ["valdoz *", "git *"],
    10: ["valdoz *", "git *"],
}


class PhaseTransitionError(Exception):
    pass


class ReopenConfirmationError(PhaseTransitionError):
    pass


def get_required_deliverables(phase_num: int) -> List[str]:
    return PHASE_DELIVERABLES.get(phase_num, [])


def get_phase_whitelist(phase_num: int) -> List[str]:
    return PHASE_COMMAND_WHITELISTS.get(phase_num, ["valdoz *", "git status"])


def get_side_effect_info(phase_num: int) -> SideEffectInfo:
    return SIDE_EFFECT_CLASSES.get(
        phase_num,
        SideEffectInfo(category="Unknown", reversible=True, description="Standard local changes"),
    )


GENESIS_HASH = "0" * 64


def get_last_audit_entry(project_root: Path) -> Tuple[str, Optional[str]]:
    """Returns (prev_hash, last_line_raw) from .valdoz/approvals.log."""
    import hashlib
    log_path = project_root / ".valdoz" / "approvals.log"
    if not log_path.exists():
        return GENESIS_HASH, None
    lines = [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return GENESIS_HASH, None
    last_line = lines[-1]
    match = re.search(r"\[CHAIN:([a-f0-9]{64})\]", last_line)
    if match:
        return match.group(1), last_line
    return hashlib.sha256(last_line.encode("utf-8")).hexdigest(), last_line


def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    """Serializes data structure into deterministic canonical JSON (RFC 8785)."""
    import json
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def append_approvals_log(project_root: Path, message: str) -> str:
    """Appends an entry to the cryptographic hash-chained append-only audit trail."""
    import hashlib
    log_path = project_root / ".valdoz" / "approvals.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    prev_hash, _ = get_last_audit_entry(project_root)
    payload_obj = {"prev": prev_hash, "ts": ts, "msg": message}
    entry_hash = hashlib.sha256(canonical_json_bytes(payload_obj)).hexdigest()
    entry_line = f"[{ts}] [CHAIN:{entry_hash}] [PREV:{prev_hash}] {message}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry_line)
    return entry_hash


def verify_audit_log_integrity(project_root: Path) -> Tuple[bool, List[str]]:
    """Cryptographically verifies the hash-chained approvals.log ledger."""
    import hashlib
    log_path = project_root / ".valdoz" / "approvals.log"
    if not log_path.exists():
        return True, []
    lines = [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return True, []

    violations: List[str] = []
    expected_prev: Optional[str] = None

    for idx, line in enumerate(lines, 1):
        chain_match = re.search(
            r"^\[(?P<ts>[^\]]+)\]\s+\[CHAIN:(?P<chain>[a-f0-9]{64})\]\s+\[PREV:(?P<prev>[a-f0-9]{64})\]\s+(?P<msg>.+)$",
            line,
        )
        if not chain_match:
            expected_prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
            continue

        ts = chain_match.group("ts")
        chain_hash = chain_match.group("chain")
        prev_hash = chain_match.group("prev")
        msg = chain_match.group("msg")

        if expected_prev is None:
            if prev_hash != GENESIS_HASH and len(prev_hash) != 64:
                violations.append(f"Line {idx}: Invalid genesis prev hash '{prev_hash}'")
        elif prev_hash != expected_prev:
            violations.append(f"Line {idx}: Hash chain link broken. Expected prev '{expected_prev[:12]}...', got '{prev_hash[:12]}...'")

        # Verify against canonical JSON hash first, with backward-compatible legacy fallback
        recalculated = hashlib.sha256(canonical_json_bytes({"prev": prev_hash, "ts": ts, "msg": msg})).hexdigest()
        if recalculated != chain_hash:
            legacy_recalculated = hashlib.sha256(f"{prev_hash}|{ts}|{msg}".encode("utf-8")).hexdigest()
            if legacy_recalculated != chain_hash:
                violations.append(f"Line {idx}: Entry payload tampering detected. Recalculated '{recalculated[:12]}...' != recorded '{chain_hash[:12]}...'")

        expected_prev = chain_hash

    return len(violations) == 0, violations


def anchor_audit_log(project_root: Path) -> Dict[str, Any]:
    """Anchors the current head hash of approvals.log to .valdoz/anchor.json and optional git tag.

    Prevents retroactive end-to-end rewrite attacks on mutable file storage.
    """
    import json
    import subprocess

    head_hash, last_line = get_last_audit_entry(project_root)
    if head_hash == GENESIS_HASH:
        return {"status": "skipped", "message": "No approvals logged to anchor yet."}

    now_iso = datetime.now(timezone.utc).isoformat()
    short_hash = head_hash[:12]
    tag_name = f"valdoz-anchor-{short_hash}"

    git_commit: Optional[str] = None
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        pass

    anchor_data = {
        "anchored_at": now_iso,
        "head_hash": head_hash,
        "short_hash": short_hash,
        "git_commit": git_commit,
        "git_tag": tag_name,
    }

    anchor_path = project_root / ".valdoz" / "anchor.json"
    anchor_path.parent.mkdir(parents=True, exist_ok=True)
    anchor_path.write_text(json.dumps(anchor_data, indent=2), encoding="utf-8")

    # Optionally create lightweight git tag if in a git repository
    if git_commit:
        try:
            subprocess.run(
                ["git", "tag", "-f", tag_name],
                cwd=project_root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    return {
        "status": "anchored",
        "head_hash": head_hash,
        "git_tag": tag_name,
        "git_commit": git_commit,
        "anchor_file": str(anchor_path),
    }


def verify_external_anchor(project_root: Path) -> Tuple[bool, str]:
    """Cross-verifies approvals.log against the external anchor record."""
    import json
    anchor_path = project_root / ".valdoz" / "anchor.json"
    if not anchor_path.exists():
        return True, "No anchor record configured (advisory)."

    try:
        data = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchored_hash = data.get("head_hash")
    except Exception as e:
        return False, f"Failed to read anchor record: {e}"

    if not anchored_hash:
        return False, "Malformed anchor record: missing 'head_hash'."

    log_path = project_root / ".valdoz" / "approvals.log"
    if not log_path.exists():
        return False, f"Anchor violation: approvals.log missing while anchor expects '{anchored_hash[:12]}...'"

    log_content = log_path.read_text(encoding="utf-8")
    if anchored_hash not in log_content:
        return False, f"Anchor violation: anchored hash '{anchored_hash[:12]}...' not found in approvals.log (possible rewrite attack)."

    return True, f"Verified against anchor (anchored at {data.get('anchored_at')})"


def create_deliverable_stubs(project_root: Path, phase_num: int) -> None:
    """Creates initial template files for deliverables if they do not exist."""
    deliverables = get_required_deliverables(phase_num)
    for rel_path in deliverables:
        target = project_root / rel_path
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            phase_name = PHASE_NAMES.get(phase_num, f"Phase {phase_num}")
            target.write_text(
                f"# {phase_name}\n\nGenerated deliverable template for Phase {phase_num}.\n",
                encoding="utf-8",
            )


def advance_phase(project_root: Path) -> int:
    """Advances project state to the next phase after approval.

    Returns the new current phase number.
    """
    state = load_state(project_root)
    curr_phase_key = str(state.current_phase)
    curr_phase = state.phases[curr_phase_key]

    if curr_phase.status != "approved":
        raise PhaseTransitionError(
            f"Cannot advance: Phase {state.current_phase} ('{curr_phase.name}') is not approved "
            f"(current status: '{curr_phase.status}'). Human approval is required."
        )

    next_num = state.current_phase + 1
    if next_num > max(PHASE_NAMES.keys()):
        raise PhaseTransitionError("Project is already in the final phase.")

    next_phase_key = str(next_num)
    state.current_phase = next_num
    state.phases[next_phase_key].status = "in_progress"
    state.phases[next_phase_key].entered_at = datetime.now(timezone.utc).isoformat()

    create_deliverable_stubs(project_root, next_num)
    save_state(project_root, state)
    append_approvals_log(
        project_root,
        f"Advanced from Phase {state.current_phase - 1} to Phase {next_num} ({PHASE_NAMES[next_num]}).",
    )
    try:
        from valdoz.webhooks import emit_webhook_event
        emit_webhook_event(
            project_root,
            "phase.advanced",
            {
                "from_phase": state.current_phase - 1,
                "to_phase": next_num,
                "to_phase_name": PHASE_NAMES.get(next_num, ""),
            },
        )
    except Exception:
        pass
    return next_num


def reopen_phase(
    project_root: Path,
    target_phase: int,
    confirm_project_name: Optional[str] = None,
) -> None:
    """Reopens a past phase: voids approval hashes and cascades pending_reapproval downstream."""
    state = load_state(project_root)
    if target_phase < 0 or target_phase > max(PHASE_NAMES.keys()):
        raise PhaseTransitionError(f"Invalid target phase number: {target_phase}")

    if target_phase > state.current_phase:
        raise PhaseTransitionError(
            f"Cannot reopen future phase {target_phase}; project is currently at Phase {state.current_phase}."
        )

    side_effect = get_side_effect_info(target_phase)
    if not side_effect.reversible:
        # Require typing the exact project name
        if not confirm_project_name or confirm_project_name.strip() != state.project_name:
            raise ReopenConfirmationError(
                f"Phase {target_phase} ({PHASE_NAMES[target_phase]}) has IRREVERSIBLE side effects:\n"
                f"{side_effect.description}\n"
                f"Confirmation required: must match project name '{state.project_name}', got '{confirm_project_name}'."
            )

    # 1. Void target phase approval
    target_key = str(target_phase)
    target_state = state.phases[target_key]
    target_state.status = "in_progress"
    target_state.entered_at = datetime.now(timezone.utc).isoformat()
    target_state.approval_hash = None
    target_state.approved_by = None
    target_state.approved_at = None

    # 2. Cascade pending_reapproval to all downstream phases up to current_phase
    for p in range(target_phase + 1, state.current_phase + 1):
        p_key = str(p)
        if p_key in state.phases:
            p_state = state.phases[p_key]
            if p_state.status in ("approved", "in_progress", "gated"):
                p_state.status = "pending_reapproval"
                p_state.approval_hash = None

    state.current_phase = target_phase

    # 3. If reopening Phase 8 (deploy), generate Change Request stub
    if target_phase == 8:
        cr_path = project_root / "docs" / "changes" / "CR-001-reopen-phase8.md"
        if not cr_path.exists():
            cr_path.parent.mkdir(parents=True, exist_ok=True)
            cr_path.write_text(
                "# Change Request: Phase 8 (Deploy) Reopened\n\n"
                "## Reason for Reopening\nDocument reason for re-opening deployment phase.\n\n"
                "## Divergence Acknowledgment\nLive cloud infrastructure and DNS may diverge from repo state.\n\n"
                "## Mitigation Plan\nSteps to synchronize remote infrastructure with repository deliverables.\n",
                encoding="utf-8",
            )

    save_state(project_root, state)
    append_approvals_log(
        project_root,
        f"WARNING: Phase {target_phase} ({PHASE_NAMES[target_phase]}) reopened. "
        f"Downstream phases marked pending re-approval. "
        f"Side-effect class: {side_effect.category}.",
    )
