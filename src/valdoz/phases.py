"""ValdoZ Phase State Machine.

Manages the 11 delivery phases, required deliverables, command whitelists,
side-effect classifications, and phase reopening cascades.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
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


def append_approvals_log(project_root: Path, message: str) -> None:
    log_path = project_root / ".valdoz" / "approvals.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


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

    create_deliverable_stubs(project_root, next_num)
    save_state(project_root, state)
    append_approvals_log(
        project_root,
        f"Advanced from Phase {state.current_phase - 1} to Phase {next_num} ({PHASE_NAMES[next_num]}).",
    )
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
