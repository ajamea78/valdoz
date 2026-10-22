"""ValdoZ Session Management.

Manages multi-role agent session locks (.valdoz/session.lock).
Enforces dual-role concurrency model: at most one builder and one scribe.
"""

from __future__ import annotations

import json
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field


VALID_ROLES = {"builder", "scribe"}


class RoleSession(BaseModel):
    agent_id: str = "default"
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pid: int = Field(default_factory=os.getpid)


class SessionLock(BaseModel):
    version: str = "3.0.0"
    roles: Dict[str, RoleSession] = Field(default_factory=dict)


class SessionError(Exception):
    """Base exception for session operations."""
    pass


class SessionLockError(SessionError):
    """Raised when an agent tries to acquire a locked role."""
    pass


def get_session_lock_path(project_root: Path) -> Path:
    return project_root / ".valdoz" / "session.lock"


def _is_pid_alive(pid: int) -> bool:
    """Check if process with PID is currently running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def load_session_lock(project_root: Path) -> SessionLock:
    lock_path = get_session_lock_path(project_root)
    if not lock_path.exists():
        return SessionLock()
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        return SessionLock(**data)
    except Exception:
        # If lock file is corrupted, return empty SessionLock
        return SessionLock()


def save_session_lock(project_root: Path, lock: SessionLock) -> None:
    lock_path = get_session_lock_path(project_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock.model_dump(), indent=2), encoding="utf-8")


def acquire_session(
    project_root: Path,
    role: str,
    agent_id: Optional[str] = None,
    force_stale: bool = False,
) -> RoleSession:
    """Acquires a session lock for a specific role (builder or scribe).

    Raises:
        ValueError: If role is invalid.
        SessionLockError: If the role is currently occupied by an active process.
    """
    role = role.lower().strip()
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: '{role}'. Must be one of {sorted(VALID_ROLES)}")

    lock = load_session_lock(project_root)

    # Check if role is currently locked
    if role in lock.roles:
        existing = lock.roles[role]
        if _is_pid_alive(existing.pid) and not force_stale and existing.pid != os.getpid():
            raise SessionLockError(
                f"Role '{role}' is already active (PID {existing.pid}, Agent '{existing.agent_id}', "
                f"started at {existing.started_at}). Another session cannot be started for this role."
            )

    new_session = RoleSession(
        agent_id=agent_id or f"agent-{role}-{os.getpid()}",
        started_at=datetime.now(timezone.utc).isoformat(),
        pid=os.getpid(),
    )
    lock.roles[role] = new_session
    save_session_lock(project_root, lock)
    return new_session


def release_session(project_root: Path, role: str) -> bool:
    """Releases the session lock for a specific role."""
    role = role.lower().strip()
    lock = load_session_lock(project_root)
    if role in lock.roles:
        del lock.roles[role]
        save_session_lock(project_root, lock)
        return True
    return False


def clear_sessions(project_root: Path, role: Optional[str] = None) -> None:
    """Clears active sessions (interactively / administrative)."""
    if role and role.lower().strip() in VALID_ROLES:
        release_session(project_root, role.lower().strip())
    else:
        lock_path = get_session_lock_path(project_root)
        if lock_path.exists():
            lock_path.unlink()


def get_active_sessions(project_root: Path) -> Dict[str, RoleSession]:
    """Returns dictionary of active sessions, pruning any dead PIDs."""
    lock = load_session_lock(project_root)
    active: Dict[str, RoleSession] = {}
    modified = False

    for role, sess in list(lock.roles.items()):
        if _is_pid_alive(sess.pid):
            active[role] = sess
        else:
            # Clean up dead PID
            del lock.roles[role]
            modified = True

    if modified:
        save_session_lock(project_root, lock)

    return active
