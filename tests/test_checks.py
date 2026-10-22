"""Unit tests for ValdoZ universal automated checks: secrets, lockfile, imports, and audit."""

import pytest
from pathlib import Path
from valdoz.checks import (
    scan_secrets,
    scan_lockfile,
    scan_undeclared_imports,
    run_valdoz_audit,
)
from valdoz.state import ValdozState, save_state


@pytest.fixture
def temp_project(tmp_path: Path):
    state = ValdozState(project_name="audit-test", packs=["base"])
    save_state(tmp_path, state)
    return tmp_path


def test_secrets_scanner(temp_project: Path):
    # 1. Clean project passes
    res_clean = scan_secrets(temp_project)
    assert res_clean.passed is True

    # 2. Hardcoded private key detected
    secret_file = temp_project / "src" / "crypto.py"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text("API_KEY = '-----BEGIN RSA PRIVATE KEY-----ABCDEF123456'\n")

    res_dirty = scan_secrets(temp_project)
    assert res_dirty.passed is False
    assert "Private Key" in res_dirty.message

    # 3. .env file detected
    secret_file.unlink()
    env_file = temp_project / ".env"
    env_file.write_text("DATABASE_URL=postgres://user:pass@localhost/db\n")

    res_env = scan_secrets(temp_project)
    assert res_env.passed is False
    assert ".env" in res_env.message


def test_lockfile_scanner(temp_project: Path):
    # 1. No package manifest -> skipped (passes)
    res_skipped = scan_lockfile(temp_project)
    assert res_skipped.status == "skipped"
    assert res_skipped.passed is True

    # 2. Manifest present without lockfile -> fails
    (temp_project / "pyproject.toml").write_text("[project]\nname='test'\n")
    res_fail = scan_lockfile(temp_project)
    assert res_fail.status == "ran"
    assert res_fail.passed is False

    # 3. Lockfile present -> passes
    (temp_project / "uv.lock").write_text("# lockfile\n")
    res_pass = scan_lockfile(temp_project)
    assert res_pass.status == "ran"
    assert res_pass.passed is True


def test_undeclared_imports_scanner(temp_project: Path):
    # Manifest with only 'pydantic' declared
    pyproject = temp_project / "pyproject.toml"
    pyproject.write_text("""[project]
dependencies = [
    "pydantic>=2.0.0",
]
""")
    src_file = temp_project / "src" / "main.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Using builtin + declared -> passes
    src_file.write_text("import sys\nimport os\nfrom pydantic import BaseModel\n")
    res_ok = scan_undeclared_imports(temp_project)
    assert res_ok.passed is True

    # 2. Using undeclared external package -> fails
    src_file.write_text("import requests\nfrom pydantic import BaseModel\n")
    res_fail = scan_undeclared_imports(temp_project)
    assert res_fail.passed is False
    assert "requests" in res_fail.message


def test_run_valdoz_audit(temp_project: Path):
    # Lockfile and pyproject
    (temp_project / "pyproject.toml").write_text("[project]\nname='ok'\ndependencies=['pydantic']\n")
    (temp_project / "uv.lock").write_text("# lock\n")
    src = temp_project / "src" / "app.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("import os\nfrom pydantic import BaseModel\n")

    report = run_valdoz_audit(temp_project)
    assert report.passed is True
    assert len(report.checks) >= 3
