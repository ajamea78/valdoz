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
