"""Unit tests for ValdoZ universal automated checks: secrets, lockfile, imports, and audit."""

import pytest
from pathlib import Path
from valdoz.checks import (
    scan_secrets,
    scan_lockfile,
    scan_undeclared_imports,
    scan_semgrep,
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
    dummy_key = "-----BEGIN " + "RSA " + "PRIVATE KEY-----ABCDEF123456"
    secret_file.write_text(f"API_KEY = '{dummy_key}'\n")

    res_dirty = scan_secrets(temp_project)
    assert res_dirty.passed is False
    assert "Private Key" in res_dirty.message

    # 3. .env file detected without .gitignore -> fails
    secret_file.unlink()
    env_file = temp_project / ".env"
    env_file.write_text("DATABASE_URL=postgres://user:pass@localhost/db\n")

    res_env = scan_secrets(temp_project)
    assert res_env.passed is False
    assert ".env" in res_env.message

    # 4. .env file ignored in .gitignore -> passes
    gitignore = temp_project / ".gitignore"
    gitignore.write_text(".env\n")
    res_env_ignored = scan_secrets(temp_project)
    assert res_env_ignored.passed is True


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


def test_autofix_audit_issues(temp_project: Path):
    # Setup .env file without .gitignore
    (temp_project / ".env").write_text("SECRET=123\n")
    (temp_project / "pyproject.toml").write_text("[project]\nname='ok'\ndependencies=['pydantic']\n")
    (temp_project / "uv.lock").write_text("# lock\n")

    # Audit without fix fails
    report_before = run_valdoz_audit(temp_project, fix=False)
    assert report_before.passed is False

    # Audit with fix automatically remediates .env into .gitignore
    report_after = run_valdoz_audit(temp_project, fix=True)
    assert report_after.passed is True
    assert any("Added '.env' to .gitignore" in fix for fix in report_after.fixes_applied)
    assert (temp_project / ".gitignore").exists()
    assert ".env" in (temp_project / ".gitignore").read_text()


def test_scan_semgrep_missing_bin(temp_project: Path, monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    res = scan_semgrep(temp_project)
    assert res.status == "skipped"
    assert res.passed is True
    assert "not found in PATH" in res.message


def test_scan_semgrep_clean(temp_project: Path, monkeypatch):
    import shutil
    import subprocess
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/semgrep" if cmd == "semgrep" else None)

    class MockProcess:
        stdout = '{"version": "1.0.0", "results": []}'
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockProcess())
    res = scan_semgrep(temp_project)
    assert res.status == "ran"
    assert res.passed is True
    assert "Semgrep SAST scan clean" in res.message


def test_scan_semgrep_findings(temp_project: Path, monkeypatch):
    import shutil
    import subprocess
    import json
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/semgrep" if cmd == "semgrep" else None)

    findings = {
        "version": "1.0.0",
        "results": [
            {
                "check_id": "rules.python.security.sql_injection",
                "path": "src/db.py",
                "start": {"line": 42},
                "extra": {
                    "severity": "ERROR",
                    "message": "Potential SQL injection vulnerability",
                },
            }
        ],
    }

    class MockProcess:
        stdout = json.dumps(findings)
        stderr = ""
        returncode = 1

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockProcess())
    res = scan_semgrep(temp_project)
    assert res.status == "ran"
    assert res.passed is False
    assert "1 SAST vulnerabilities detected" in res.message
    assert "sql_injection" in res.message


def test_run_valdoz_audit_with_semgrep_flag(temp_project: Path, monkeypatch):
    (temp_project / "pyproject.toml").write_text("[project]\nname='ok'\ndependencies=['pydantic']\n")
    (temp_project / "uv.lock").write_text("# lock\n")

    import shutil
    import subprocess
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/semgrep" if cmd == "semgrep" else None)

    class MockProcess:
        stdout = '{"version": "1.0.0", "results": []}'
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockProcess())

    report = run_valdoz_audit(temp_project, semgrep=True)
    assert any(c.id == "semgrep-sast" for c in report.checks)


