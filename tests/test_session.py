"""Unit tests for ValdoZ session management and multi-role locking."""

import pytest
from pathlib import Path
from valdoz.session import (
    acquire_session,
    clear_sessions,
    get_active_sessions,
    release_session,
    SessionLockError,
)


@pytest.fixture
def temp_project(tmp_path: Path):
    valdoz_dir = tmp_path / ".valdoz"
    valdoz_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_acquire_builder_session(temp_project: Path):
    sess = acquire_session(temp_project, role="builder", agent_id="agent-build-1")
    assert sess.agent_id == "agent-build-1"
    active = get_active_sessions(temp_project)
    assert "builder" in active
    assert active["builder"].agent_id == "agent-build-1"


def test_invalid_role_raises_value_error(temp_project: Path):
    with pytest.raises(ValueError, match="Invalid role"):
        acquire_session(temp_project, role="hacker")


def test_dual_role_concurrency_allowed(temp_project: Path):
    """Builder and Scribe can run concurrently."""
    sess_b = acquire_session(temp_project, role="builder", agent_id="builder-agent")
    sess_s = acquire_session(temp_project, role="scribe", agent_id="scribe-agent")

    active = get_active_sessions(temp_project)
    assert len(active) == 2
    assert active["builder"].agent_id == "builder-agent"
    assert active["scribe"].agent_id == "scribe-agent"


def test_duplicate_builder_session_rejected(temp_project: Path, monkeypatch):
    """A second builder cannot start while first is active."""
    acquire_session(temp_project, role="builder", agent_id="builder-1")

    # Simulate another process trying to acquire
    # In same process, existing.pid == os.getpid() would re-claim unless PID differs.
    # We mock _is_pid_alive to simulate an active external PID
    from valdoz import session
    monkeypatch.setattr(session, "_is_pid_alive", lambda pid: True)

    lock = session.load_session_lock(temp_project)
    lock.roles["builder"].pid = 999999
    session.save_session_lock(temp_project, lock)

    with pytest.raises(SessionLockError, match="Role 'builder' is already active"):
        acquire_session(temp_project, role="builder", agent_id="builder-2")


def test_release_and_clear_session(temp_project: Path):
    acquire_session(temp_project, role="builder")
    assert "builder" in get_active_sessions(temp_project)

    released = release_session(temp_project, "builder")
    assert released is True
    assert "builder" not in get_active_sessions(temp_project)

    acquire_session(temp_project, role="scribe")
    clear_sessions(temp_project)
    assert len(get_active_sessions(temp_project)) == 0
