"""Unit tests for ValdoZ universal automated checks: secrets, lockfile, imports, and audit."""

import pytest
from pathlib import Path
from valdoz.checks import (
    scan_secrets,
    scan_lockfile,
    scan_undeclared_imports,
    scan_semgrep,
    scan_package_hallucination,
    scan_license_compliance,
    scan_api_contract_drift,
    categorize_license,
    normalize_route_path,
    extract_routes_from_openapi,
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


def test_package_hallucination_no_manifests(temp_project: Path):
    res = scan_package_hallucination(temp_project)
    assert res.status == "skipped"
    assert res.passed is True
    assert "No external dependency declarations" in res.message


def test_package_hallucination_offline_clean(temp_project: Path):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic>=2.0.0",
    "fastapi",
    "rich",
]
""")
    res = scan_package_hallucination(temp_project, verify_registry=False)
    assert res.status == "ran"
    assert res.passed is True
    assert "Verified 3 dependencies against offline slopsquatting heuristics" in res.message


def test_package_hallucination_offline_typosquatting(temp_project: Path):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
    "reqeusts>=2.0.0",
]
""")
    res = scan_package_hallucination(temp_project, verify_registry=False)
    assert res.status == "ran"
    assert res.passed is False
    assert "Potential typosquatting/slopsquatting detected" in res.message
    assert "reqeusts" in res.message
    assert "requests" in res.message


def test_package_hallucination_registry_verification(temp_project: Path, monkeypatch):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
    "non-existent-hallucinated-package-xyz",
]
""")
    from valdoz import checks

    def mock_verify(pkg_name: str, ecosystem: str = "pypi", timeout: float = 3.5):
        if pkg_name == "pydantic":
            return True, "Found"
        return False, "Not found (404)"

    monkeypatch.setattr(checks, "verify_registry_package_existence", mock_verify)

    res = scan_package_hallucination(temp_project, verify_registry=True)
    assert res.status == "ran"
    assert res.passed is False
    assert "AI-hallucinated package(s) detected" in res.message
    assert "non-existent-hallucinated-package-xyz (PYPI)" in res.message


def test_package_hallucination_registry_all_clean(temp_project: Path, monkeypatch):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
    "fastapi",
]
""")
    from valdoz import checks

    monkeypatch.setattr(checks, "verify_registry_package_existence", lambda pkg, eco=None, timeout=None: (True, "Found"))

    res = scan_package_hallucination(temp_project, verify_registry=True)
    assert res.status == "ran"
    assert res.passed is True
    assert "All 2 dependencies verified genuine and registered" in res.message


def test_run_valdoz_audit_with_verify_packages_flag(temp_project: Path, monkeypatch):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
]
""")
    (temp_project / "uv.lock").write_text("# lock\n")

    from valdoz import checks
    monkeypatch.setattr(checks, "verify_registry_package_existence", lambda pkg, eco=None, timeout=None: (True, "Found"))

    report = run_valdoz_audit(temp_project, verify_packages=True)
    assert any(c.id == "package-hallucination" for c in report.checks)
    pkg_chk = next(c for c in report.checks if c.id == "package-hallucination")
    assert pkg_chk.passed is True


def test_categorize_license():
    assert categorize_license("MIT License") == ("permissive", "MIT")
    assert categorize_license("Apache 2.0") == ("permissive", "Apache-2.0")
    assert categorize_license("BSD-3-Clause") == ("permissive", "BSD")
    assert categorize_license("GPLv3") == ("strong-copyleft", "GPL")
    assert categorize_license("AGPL-3.0") == ("strong-copyleft", "AGPL")
    assert categorize_license("LGPL-2.1") == ("weak-copyleft", "LGPL")
    assert categorize_license("MPL-2.0") == ("weak-copyleft", "MPL")
    assert categorize_license("") == ("unknown", "Unknown")


def test_license_compliance_clean_permissive(temp_project: Path):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
    "rich",
]
""")
    res = scan_license_compliance(temp_project)
    assert res.status == "ran"
    assert res.passed is True
    assert "100% compliant with license policy" in res.message


def test_license_compliance_strong_copyleft_detected(temp_project: Path, monkeypatch):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
    "gpl-copyleft-package",
]
""")
    from valdoz import checks

    def mock_resolve(pkg, ecosystem="pypi", no_network=True):
        if pkg == "gpl-copyleft-package":
            return ("strong-copyleft", "GPL")
        return ("permissive", "MIT")

    monkeypatch.setattr(checks, "resolve_package_license", mock_resolve)

    res = scan_license_compliance(temp_project)
    assert res.status == "ran"
    assert res.passed is False
    assert "Strong copyleft dependencies detected" in res.message
    assert "gpl-copyleft-package" in res.message


def test_license_compliance_copyleft_allowed_for_gpl_project(temp_project: Path, monkeypatch):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "gpl-copyleft-package",
]
""")
    # Set project LICENSE to GPL
    (temp_project / "LICENSE").write_text("GNU GENERAL PUBLIC LICENSE Version 3")

    from valdoz import checks
    monkeypatch.setattr(checks, "resolve_package_license", lambda pkg, ecosystem="pypi", no_network=True: ("strong-copyleft", "GPL"))

    res = scan_license_compliance(temp_project)
    assert res.status == "ran"
    assert res.passed is True


def test_run_valdoz_audit_with_licenses_flag(temp_project: Path):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
]
""")
    (temp_project / "uv.lock").write_text("# lock\n")

    report = run_valdoz_audit(temp_project, licenses=True)
    assert any(c.id == "license-compliance" for c in report.checks)
    lic_chk = next(c for c in report.checks if c.id == "license-compliance")
    assert lic_chk.passed is True


def test_normalize_route_path():
    assert normalize_route_path("/api/v1/users/:id") == "/api/v1/users/{}"
    assert normalize_route_path("/api/v1/users/{userId}") == "/api/v1/users/{}"
    assert normalize_route_path("users") == "/users"
    assert normalize_route_path("/") == "/"


def test_api_contract_no_spec_no_api_framework(temp_project: Path):
    res = scan_api_contract_drift(temp_project)
    assert res.status == "skipped"
    assert res.passed is True
    assert "No OpenAPI specification" in res.message


def test_api_contract_no_spec_with_api_framework(temp_project: Path):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "api-app"
dependencies = [
    "fastapi>=0.100.0",
]
""")
    res = scan_api_contract_drift(temp_project)
    assert res.status == "ran"
    assert res.passed is False
    assert res.severity == "warning"
    assert "fastapi" in res.message


def test_api_contract_perfect_match(temp_project: Path):
    openapi_yaml = """
openapi: 3.0.3
info:
  title: Users API
  version: 1.0.0
paths:
  /api/v1/users:
    get:
      summary: List users
    post:
      summary: Create user
  /api/v1/users/{userId}:
    get:
      summary: Get user
"""
    (temp_project / "openapi.yaml").write_text(openapi_yaml)

    src_dir = temp_project / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.py").write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/v1/users")
def list_users(): return []

@app.post("/api/v1/users")
def create_user(): return {}

@app.get("/api/v1/users/{id}")
def get_user(id: int): return {}
""")

    res = scan_api_contract_drift(temp_project)
    assert res.status == "ran"
    assert res.passed is True
    assert "3 routes perfectly aligned with code implementation (0 drift)" in res.message


def test_api_contract_drift_unimplemented_and_undocumented(temp_project: Path):
    openapi_yaml = """
openapi: 3.0.3
info:
  title: Users API
  version: 1.0.0
paths:
  /api/v1/users:
    get:
      summary: List users
  /api/v1/users/{userId}:
    delete:
      summary: Delete user
"""
    (temp_project / "openapi.yaml").write_text(openapi_yaml)

    src_dir = temp_project / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.py").write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/v1/users")
def list_users(): return []

# Missing DELETE /api/v1/users/{userId}
# Undocumented extra endpoint:
@app.post("/api/v1/internal/reset")
def reset(): return {}
""")

    res = scan_api_contract_drift(temp_project)
    assert res.status == "ran"
    assert res.passed is False
    assert "API contract drift detected" in res.message
    assert "unimplemented in code" in res.message
    assert "DELETE /api/v1/users/{}" in res.message
    assert "undocumented in contract" in res.message
    assert "POST /api/v1/internal/reset" in res.message


def test_run_valdoz_audit_with_contract_flag(temp_project: Path):
    (temp_project / "pyproject.toml").write_text("""[project]
name = "my-app"
dependencies = [
    "pydantic",
]
""")
    (temp_project / "uv.lock").write_text("# lock\n")

    report = run_valdoz_audit(temp_project, contract=True)
    assert any(c.id == "api-contract-drift" for c in report.checks)





