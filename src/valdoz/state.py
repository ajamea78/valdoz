"""ValdoZ State Engine.

Manages state.json schema, read-only write protection (chmod 444),
deliverable hashing (SHA-256), and tamper detection.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class PhaseState(BaseModel):
    name: str
    status: str = "pending"  # pending, in_progress, gated, approved, pending_reapproval
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    approval_hash: Optional[str] = None
    deliverable_hashes: Dict[str, str] = Field(default_factory=dict)


PHASE_NAMES: Dict[int, str] = {
    0: "Init",
    1: "Intake",
    2: "Requirements",
    3: "Stack Decision",
    4: "Architecture and Plan",
    5: "Project Setup",
    6: "Build",
    7: "Verify",
    8: "Deploy",
    9: "Handover",
    10: "Change Requests",
}


def default_phases() -> Dict[str, PhaseState]:
    phases = {}
    for num, name in PHASE_NAMES.items():
        initial_status = "in_progress" if num == 0 else "pending"
        phases[str(num)] = PhaseState(name=name, status=initial_status)
    return phases


def find_project_root() -> Path:
    """Finds repository root by searching upward for .valdoz or .git."""
    curr = Path.cwd().resolve()
    for parent in [curr, *curr.parents]:
        if (parent / ".valdoz").exists() or (parent / ".git").exists():
            return parent
    return curr


class GitIdentityState(BaseModel):
    profile_name: str
    github_username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class ValdozState(BaseModel):
    version: str = "3.0.0"
    project_name: str
    language: str = "en"
    current_phase: int = 0
    chosen_stack: Dict[str, str] = Field(default_factory=dict)
    packs: List[str] = Field(default_factory=lambda: ["base"])
    phases: Dict[str, PhaseState] = Field(default_factory=default_phases)
    profile: Optional[str] = None
    git_identity: Optional[GitIdentityState] = None


class StateError(Exception):
    pass


class TamperError(StateError):
    pass


def get_state_path(project_root: Path) -> Path:
    return project_root / ".valdoz" / "state.json"


def set_write_protection(path: Path, read_only: bool) -> None:
    """Toggle read-only permissions on a file."""
    if not path.exists():
        return
    current_mode = path.stat().st_mode
    if read_only:
        # Remove write bits for user, group, other (0o444)
        new_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    else:
        # Add write bit for user (0o644)
        new_mode = current_mode | stat.S_IWUSR
    os.chmod(path, new_mode)


def is_write_protected(path: Path) -> bool:
    """Check if file is read-only for owner."""
    if not path.exists():
        return False
    mode = path.stat().st_mode
    return not bool(mode & stat.S_IWUSR)


def compute_file_sha256(path: Path) -> Optional[str]:
    """Computes SHA-256 hash of a file. Returns None if file does not exist."""
    if not path.exists() or not path.is_file():
        return None
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_deliverables_hash(deliverable_hashes: Dict[str, str]) -> str:
    """Computes a composite hash of all deliverable hashes in deterministic order."""
    composite = hashlib.sha256()
    for rel_path in sorted(deliverable_hashes.keys()):
        h = deliverable_hashes[rel_path]
        composite.update(f"{rel_path}:{h}\n".encode("utf-8"))
    return composite.hexdigest()


def load_state(project_root: Path) -> ValdozState:
    """Loads state.json from project."""
    state_path = get_state_path(project_root)
    if not state_path.exists():
        raise StateError(f"State file not found at {state_path}. Run 'valdoz project init' first.")
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return ValdozState(**data)
    except Exception as e:
        raise StateError(f"Failed to parse state.json: {e}")


def save_state(project_root: Path, state: ValdozState, write_protect: bool = False) -> None:
    """Saves state.json safely, handling write-protection toggling."""
    state_path = get_state_path(project_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Unlock temporarily if locked
    was_protected = is_write_protected(state_path)
    if was_protected:
        set_write_protection(state_path, read_only=False)

    try:
        state_path.write_text(json.dumps(state.model_dump(), indent=2), encoding="utf-8")
    finally:
        if write_protect or was_protected:
            set_write_protection(state_path, read_only=True)


def verify_phase_integrity(project_root: Path, phase_num: int) -> Tuple[bool, List[str]]:
    """Verifies that deliverables of an approved phase have not been tampered with.

    Returns:
        (is_valid, list_of_violations)
    """
    state = load_state(project_root)
    phase_key = str(phase_num)
    if phase_key not in state.phases:
        return False, [f"Invalid phase number: {phase_num}"]

    phase = state.phases[phase_key]
    if phase.status != "approved":
        return True, []  # Unapproved phases have no frozen deliverables to verify

    violations: List[str] = []
    if not phase.deliverable_hashes:
        return True, []

    for rel_path, expected_hash in phase.deliverable_hashes.items():
        if rel_path == ".valdoz/state.json":
            continue
        file_path = project_root / rel_path
        if not file_path.exists():
            violations.append(f"Approved deliverable missing: '{rel_path}'")
            continue
        current_hash = compute_file_sha256(file_path)
        if current_hash != expected_hash:
            exp_disp = expected_hash[:10] if expected_hash else "None"
            cur_disp = current_hash[:10] if current_hash else "None"
            violations.append(
                f"Tampering detected in '{rel_path}': expected SHA-256 {exp_disp}..., got {cur_disp}..."
            )

    is_valid = len(violations) == 0
    return is_valid, violations
