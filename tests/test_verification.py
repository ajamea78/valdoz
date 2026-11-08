"""Unit tests for ValdoZ Full-Spectrum Non-Bypassable Verification Engine."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from valdoz.cli import app
from valdoz.verification import (
    discover_workspace_packages,
    run_project_verification,
    StepResult,
    VerificationReport,
)
from valdoz.checks import scan_monorepo_verification_integrity, run_valdoz_audit
from valdoz.slices import start_slice, done_slice, SliceGateConditionError
from valdoz.state import ValdozState, save_state

runner = CliRunner()


@pytest.fixture
def monorepo_project(tmp_path: Path):
    """Sets up a mock monorepo with backend root, staff-interface, and customer-portal."""
    state = ValdozState(project_name="monorepo-test", current_phase=6)
    save_state(tmp_path, state)

    # Root package.json (backend)
    root_pkg = {
        "name": "backend-api",
        "scripts": {
            "test": "node -e 'process.exit(0)'"
        }
    }
    (tmp_path / "package.json").write_text(json.dumps(root_pkg))

    # staff-interface (frontend app 1)
    staff_dir = tmp_path / "staff-interface"
    staff_dir.mkdir()
    staff_pkg = {
        "name": "staff-interface",
        "scripts": {
            "lint": "node -e 'process.exit(0)'",
            "build": "node -e 'process.exit(0)'"
        }
    }
    (staff_dir / "package.json").write_text(json.dumps(staff_pkg))

    # customer-portal (frontend app 2)
    portal_dir = tmp_path / "customer-portal"
    portal_dir.mkdir()
    portal_pkg = {
        "name": "customer-portal",
        "scripts": {
            "lint": "node -e 'process.exit(0)'",
            "build": "node -e 'process.exit(0)'"
        }
    }
    (portal_dir / "package.json").write_text(json.dumps(portal_pkg))

    return tmp_path


def test_discover_workspace_packages(monorepo_project: Path):
    packages = discover_workspace_packages(monorepo_project)
    names = [p.name for p in packages]
    rel_paths = [p.rel_path for p in packages]

    assert "backend-api" in names
    assert "staff-interface" in names
    assert "customer-portal" in names
    assert "." in rel_paths
    assert "staff-interface" in rel_paths
    assert "customer-portal" in rel_paths


def test_run_project_verification_multi_package_pass(monorepo_project: Path):
    report = run_project_verification(monorepo_project)
    assert report.passed is True
    assert report.used_root_verify is False
    assert len(report.steps) == 5  # root test, staff lint+build, portal lint+build
    assert any(s.step == "lint" and s.package == "staff-interface" for s in report.steps)
    assert any(s.step == "lint" and s.package == "customer-portal" for s in report.steps)
    assert any(s.step == "test" and s.package == "." for s in report.steps)


def test_run_project_verification_catches_lint_failure(monorepo_project: Path):
    # Simulate an undeclared identifier error (like isDir2) in staff-interface lint
    staff_pkg = {
        "name": "staff-interface",
        "scripts": {
            "lint": "node -e 'console.error(\"Layout.jsx:14:11: error: \\\"isDir2\\\" is not defined [no-undef]\"); process.exit(1)'",
            "build": "node -e 'process.exit(0)'"
        }
    }
    (monorepo_project / "staff-interface" / "package.json").write_text(json.dumps(staff_pkg))

    report = run_project_verification(monorepo_project)
    assert report.passed is False
    assert any(s.step == "lint" and s.package == "staff-interface" and not s.passed for s in report.steps)
    assert "isDir2" in report.summary or any("isDir2" in s.output for s in report.steps)


def test_run_project_verification_authoritative_root_verify(monorepo_project: Path):
    # Add root "verify" script
    root_pkg = {
        "name": "backend-api",
        "scripts": {
            "verify": "node -e 'console.log(\"Unified verify passed\"); process.exit(0)'"
        }
    }
    (monorepo_project / "package.json").write_text(json.dumps(root_pkg))

    report = run_project_verification(monorepo_project)
    assert report.passed is True
    assert report.used_root_verify is True
    assert len(report.steps) == 1
    assert report.steps[0].step == "root_verify"


def test_cli_verify_command(monorepo_project: Path, monkeypatch):
    monkeypatch.chdir(monorepo_project)
    res = runner.invoke(app, ["verify"], catch_exceptions=False)
    assert res.exit_code == 0
    assert "Full-Spectrum Verification Matrix" in res.output
    assert "PASS" in res.output

    res_help = runner.invoke(app, ["verify", "--help"])
    assert res_help.exit_code == 0
    assert "--subprojects" in res_help.output
    assert "--builds" in res_help.output


def test_monorepo_verification_integrity_audit_check(monorepo_project: Path):
    # Without root verify, audit check should warn about missing unified verify script
    res = scan_monorepo_verification_integrity(monorepo_project)
    assert res.passed is False
    assert res.severity == "warning"
    assert "unified root 'verify' script" in res.message

    # Now add root verify and ensure lint scripts exist
    root_pkg = {
        "name": "backend-api",
        "scripts": {
            "verify": "npm test"
        }
    }
    (monorepo_project / "package.json").write_text(json.dumps(root_pkg))
    res2 = scan_monorepo_verification_integrity(monorepo_project)
    assert res2.passed is True
    assert "Monorepo verification integrity verified" in res2.message


def test_slice_done_fails_when_frontend_lint_fails(monorepo_project: Path):
    # Setup valid spec
    slices_dir = monorepo_project / "docs" / "slices"
    slices_dir.mkdir(parents=True)
    spec_content = """# Slice: 01-layout
## Summary
Update layout.
## Acceptance Criteria
- Clean render
## Test Plan
- Full verification
## File Manifest
- staff-interface/Layout.jsx
"""
    (slices_dir / "01-layout.md").write_text(spec_content)
    start_slice(monorepo_project, "01-layout")

    # Inject undeclared variable error into staff-interface lint
    staff_pkg = {
        "name": "staff-interface",
        "scripts": {
            "lint": "node -e 'console.error(\"ReferenceError: isDir2 is not defined\"); process.exit(1)'"
        }
    }
    (monorepo_project / "staff-interface" / "package.json").write_text(json.dumps(staff_pkg))

    # Attempting to mark slice done without bypass should raise SliceGateConditionError
    with pytest.raises(SliceGateConditionError) as exc_info:
        done_slice(monorepo_project, "01-layout")

    assert "staff-interface:lint" in str(exc_info.value)
    assert "ReferenceError: isDir2 is not defined" in str(exc_info.value)


def test_mcp_verify_project(monorepo_project: Path):
    from valdoz.mcp_server import dispatch_tool
    res = dispatch_tool("valdoz_verify_project", {"subprojects": True, "builds": True}, monorepo_project)
    assert "passed" in res
    assert "packages_checked" in res
    assert res["passed"] is True
    assert len(res["steps"]) > 0
