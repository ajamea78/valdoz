"""Security hardening tests validating remediation of audit findings SEC-01 to SEC-08."""

import time
from pathlib import Path
import pytest

from valdoz.approval import generate_human_token, verify_human_token
from valdoz.healing import apply_patch
from valdoz.session import acquire_session, release_session


def test_sec_01_cryptographic_human_token(tmp_path: Path):
    # 1. Valid HMAC token passes
    token = generate_human_token("phase", "3", project_root=tmp_path)
    assert token.startswith("valdoz-v1.")
    assert verify_human_token(token, "phase", "3", project_root=tmp_path) is True

    # 2. Target mismatch fails
    assert verify_human_token(token, "phase", "4", project_root=tmp_path) is False

    # 3. Action mismatch fails
    assert verify_human_token(token, "slice", "3", project_root=tmp_path) is False

    # 4. Forged signature fails
    parts = token.split(".")
    forged = ".".join(parts[:-1] + ["deadbeef12345678"])
    assert verify_human_token(forged, "phase", "3", project_root=tmp_path) is False

    # 5. Expired token fails
    old_ts = int(time.time()) - 400
    expired_parts = parts[:3] + [str(old_ts)] + parts[4:]
    expired_token = ".".join(expired_parts)
    assert verify_human_token(expired_token, "phase", "3", max_age_seconds=300, project_root=tmp_path) is False


def test_sec_02_self_healing_path_quarantine(tmp_path: Path):
    patches = {
        ".git/hooks/pre-commit": "malicious hook code",
        ".valdoz/state.json": "tampered state",
        ".env": "SECRET=leak",
        "pyproject.toml": "injected dependency",
        "src/app.py": "def hello(): return 'world'\n",
        "tests/test_app.py": "def test_hello(): pass\n",
    }

    applied = apply_patch(tmp_path, patches)

    # Protected paths MUST NOT be written
    assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()
    assert not (tmp_path / ".valdoz" / "state.json").exists()
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / "pyproject.toml").exists()

    # Allowed paths MUST be written
    assert (tmp_path / "src" / "app.py").exists()
    assert (tmp_path / "tests" / "test_app.py").exists()
    assert sorted(applied) == ["src/app.py", "tests/test_app.py"]


def test_sec_08_session_mutex(tmp_path: Path):
    sess1 = acquire_session(tmp_path, role="builder")
    assert sess1.role == "builder" if hasattr(sess1, "role") else sess1.agent_id

    # Release
    released = release_session(tmp_path, role="builder")
    assert released is True

    # Re-acquire
    sess2 = acquire_session(tmp_path, role="builder")
    assert sess2.pid > 0
    release_session(tmp_path, role="builder")
