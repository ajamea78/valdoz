"""End-to-end integration tests for ValdoZ CLI commands."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from valdoz.cli import app

runner = CliRunner()


@pytest.fixture
def run_in_tmp(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ValdoZ Protocol version 3.0.0" in result.output


def test_cli_project_init_and_status(run_in_tmp: Path):
    result = runner.invoke(app, ["project", "init", "--name", "demo-project", "--lang", "ar"])
    assert result.exit_code == 0
    assert "initialized for project 'demo-project' (ar)" in result.output
    assert (run_in_tmp / ".valdoz" / "state.json").exists()

    # Re-init is idempotent
    result2 = runner.invoke(app, ["project", "init"])
    assert result2.exit_code == 0
    assert "already initialized" in result2.output

    # Phase status command
    res_status = runner.invoke(app, ["phase", "status"])
    assert res_status.exit_code == 0
    assert "demo-project" in res_status.output
    assert "Phase 0" in res_status.output


def test_cli_session_lifecycle(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "session-demo"])

    # Start builder session
    res_start = runner.invoke(app, ["session", "start", "--role", "builder", "--agent-id", "agent-build-007"])
    assert res_start.exit_code == 0
    assert "Acquired session lock for role builder" in res_start.output

    # View session status
    res_status = runner.invoke(app, ["session", "status"])
    assert res_status.exit_code == 0
    assert "agent-build-007" in res_status.output

    # End session
    res_end = runner.invoke(app, ["session", "end", "--role", "builder"])
    assert res_end.exit_code == 0
    assert "released" in res_end.output


def test_cli_decision_and_research(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "cli-logs-test"])

    # Decision add
    res_dec = runner.invoke(
        app,
        ["decision", "add", "-q", "FastAPI or Flask?", "-c", "FastAPI", "-r", "Type safety and speed"],
    )
    assert res_dec.exit_code == 0
    assert "Recorded DEC-001" in res_dec.output
    assert (run_in_tmp / ".valdoz" / "decisions.md").exists()

    # Research pre-log
    res_rlog = runner.invoke(
        app,
        ["research", "log", "-u", "https://fastapi.tiangolo.com", "-c", "Async endpoint documentation"],
    )
    assert res_rlog.exit_code == 0
    assert "Pre-logged intent RES-001" in res_rlog.output

    # Research add
    res_radd = runner.invoke(
        app,
        ["research", "add", "-u", "https://fastapi.tiangolo.com", "-c", "Pydantic v2 support in FastAPI"],
    )
    assert res_radd.exit_code == 0
    assert "Logged finding RES-002" in res_radd.output
    assert (run_in_tmp / ".valdoz" / "research.md").exists()


def test_cli_doctor_and_repair(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "doc-test"])
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "state.json exists" in result.output
    assert "Python interpreter" in result.output

    # State repair command
    res_rep = runner.invoke(app, ["state", "repair"])
    assert res_rep.exit_code == 0
    assert "State repaired successfully" in res_rep.output


def test_cli_sync_runtimes(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "sync-cli-test"])

    # Dry run preview
    res_dry = runner.invoke(app, ["sync-runtimes", "--dry-run"])
    assert res_dry.exit_code == 0
    assert "Synchronizing Antigravity runtime files (Dry Run)" in res_dry.output
    assert not (run_in_tmp / "AGENTS.md").exists()

    # Actual sync
    res_sync = runner.invoke(app, ["sync-runtimes"])
    assert res_sync.exit_code == 0
    assert "Successfully synchronized" in res_sync.output
    assert (run_in_tmp / "AGENTS.md").exists()
    assert (run_in_tmp / "GEMINI.md").exists()
    assert (run_in_tmp / ".agent" / "skills" / "valdoz-phase-1-intake" / "SKILL.md").exists()


def test_cli_gate_check(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "gate-cli-test"])
    # Phase 0 gate check should pass (state.json exists)
    res_gate = runner.invoke(app, ["gate", "check", "--phase", "0"])
    assert res_gate.exit_code == 0
    assert "Gate Passed" in res_gate.output


def test_cli_slice_workflow(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "slice-cli-test"])

    # Create spec for slice 01
    spec_file = run_in_tmp / "docs" / "slices" / "01-login.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text("# Slice\n## Summary\nLogin.\n## Acceptance Criteria\nPass.\n## Test Plan\nTests.\n## File Manifest\nCode.\n")

    # Start slice
    res_start = runner.invoke(app, ["slice", "start", "01-login"])
    assert res_start.exit_code == 0
    assert "Slice '01-login' started" in res_start.output

    # Status
    res_status = runner.invoke(app, ["slice", "status"])
    assert res_status.exit_code == 0
    assert "01-login" in res_status.output

    # Done
    res_done = runner.invoke(app, ["slice", "done", "01-login"])
    assert res_done.exit_code == 0
    assert "completed successfully" in res_done.output


def test_cli_audit(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "audit-cli-test"])
    res_audit = runner.invoke(app, ["audit"])
    assert res_audit.exit_code == 0
    assert "ValdoZ Universal Audit" in res_audit.output
    assert "Audit Passed" in res_audit.output


def test_cli_pack_commands(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "pack-cli-test"])

    # List packs
    res_list = runner.invoke(app, ["pack", "list"])
    assert res_list.exit_code == 0
    assert "web-app" in res_list.output
    assert "base" in res_list.output

    # Add pack
    res_add = runner.invoke(app, ["pack", "add", "web-app"])
    assert res_add.exit_code == 0
    assert "Enabled pack 'web-app'" in res_add.output


def test_cli_hook_and_ci(run_in_tmp: Path):
    import subprocess
    subprocess.run(["git", "init"], cwd=str(run_in_tmp), check=True, stdout=subprocess.DEVNULL)
    runner.invoke(app, ["project", "init", "--name", "integration-cli-test"])

    # Hook install
    res_hook = runner.invoke(app, ["hook", "install"])
    assert res_hook.exit_code == 0
    assert "Pre-commit hook installed successfully" in res_hook.output
    assert (run_in_tmp / ".git" / "hooks" / "pre-commit").exists()

    # CI generate
    res_ci = runner.invoke(app, ["ci", "generate"])
    assert res_ci.exit_code == 0
    assert "GitHub Actions CI workflow generated" in res_ci.output
    assert (run_in_tmp / ".github" / "workflows" / "valdoz.yml").exists()


def test_cli_heal_ci_command(run_in_tmp: Path):
    runner.invoke(app, ["project", "init", "--name", "heal-cli-test"])
    
    # Passing state: heal ci should report already passing
    res_ci_pass = runner.invoke(app, ["heal", "ci"])
    assert res_ci_pass.exit_code == 0
    assert "All CI gate and audit checks are already passing" in res_ci_pass.output

    # Using log file
    log_file = run_in_tmp / "error.log"
    log_file.write_text("Audit failure: missing lockfile")
    res_log = runner.invoke(app, ["heal", "ci", "--log-file", str(log_file)])
    # Fails if AI provider not configured, or completes with mock
    assert "Inspecting failure state" in res_log.output


def test_cli_slice_done_auto_heal(run_in_tmp: Path, monkeypatch):
    import subprocess
    subprocess.run(["git", "init"], cwd=str(run_in_tmp), check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(run_in_tmp), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(run_in_tmp), check=True)

    runner.invoke(app, ["project", "init", "--name", "slice-heal-test"])
    
    # Advance to Phase 6
    from valdoz.state import load_state, save_state
    state = load_state(run_in_tmp)
    state.current_phase = 6
    save_state(run_in_tmp, state)

    # Create dummy initial commit
    (run_in_tmp / "README.md").write_text("# Demo")
    subprocess.run(["git", "add", "README.md"], cwd=str(run_in_tmp), check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(run_in_tmp), check=True)

    # Create slice spec & start slice
    slices_dir = run_in_tmp / "docs" / "slices"
    slices_dir.mkdir(parents=True)
    spec_content = """# Slice 01: Core
## Summary
Core slice description.
## Acceptance Criteria
- Unit tests pass
## Test Plan
- pytest
## File Manifest
- tests/test_core.py
"""
    (slices_dir / "01-core.md").write_text(spec_content)

    res_start = runner.invoke(app, ["slice", "start", "01-core"])
    assert res_start.exit_code == 0

    # Auto heal mock response
    mock_resp = """
Root Cause: Tests were missing assertion.

FILE: tests/test_core.py
```python
def test_core():
    assert True
```
"""
    monkeypatch.setenv("VALDOZ_HEAL_MOCK_RESPONSE", mock_resp)

    # When cov_delta is negative below threshold, done_slice fails gate condition (c)
    # With --auto-heal, it triggers healing loop and marks slice gated
    res_done = runner.invoke(app, ["slice", "done", "01-core", "--cov-delta", "-2.0", "--auto-heal"])
    assert res_done.exit_code == 0
    assert "completed successfully" in res_done.output

    # Verify slice is now gated
    from valdoz.slices import load_slice
    s = load_slice(run_in_tmp, "01-core")
    assert s.status == "gated"





