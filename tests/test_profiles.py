"""Tests for ValdoZ Multi-Account Git & GitHub Profile Management."""

import json
import os
import subprocess
from pathlib import Path
import pytest
from typer.testing import CliRunner

from valdoz.cli import app
from valdoz.profiles import (
    Profile,
    ProfilesConfig,
    add_profile,
    apply_profile_to_repo,
    get_profile,
    get_repo_git_identity,
    load_profiles,
    remove_profile,
    save_profiles,
)
from valdoz.checks import scan_git_identity, autofix_audit_issues
from valdoz.state import ValdozState, save_state

runner = CliRunner()


@pytest.fixture
def temp_profiles_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p_path = tmp_path / "profiles.json"
    monkeypatch.setenv("VALDOZ_PROFILES_PATH", str(p_path))
    return p_path


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    return repo


def test_profile_crud(temp_profiles_path: Path):
    # Initial load is empty
    cfg = load_profiles()
    assert len(cfg.profiles) == 0
    assert cfg.default is None

    # Add profile
    p1 = Profile(
        name="Personal User",
        email="personal@example.com",
        github_username="personaluser",
    )
    add_profile("personal", p1, set_default=True)

    loaded = load_profiles()
    assert "personal" in loaded.profiles
    assert loaded.default == "personal"
    assert loaded.profiles["personal"].email == "personal@example.com"

    # Add second profile
    p2 = Profile(
        name="Work User",
        email="work@corp.com",
        github_username="corpuser",
        ssh_key="~/.ssh/id_work",
    )
    add_profile("work", p2)

    loaded2 = load_profiles()
    assert len(loaded2.profiles) == 2
    assert loaded2.default == "personal"

    # Remove profile
    assert remove_profile("personal") is True
    loaded3 = load_profiles()
    assert "personal" not in loaded3.profiles
    assert loaded3.default == "work"


def test_apply_profile_to_repo(temp_profiles_path: Path, temp_git_repo: Path):
    p = Profile(
        name="Ahmad Test",
        email="ahmad@test.com",
        github_username="ahmadtest",
        ssh_key="~/.ssh/id_custom",
    )
    add_profile("tester", p)

    applied = apply_profile_to_repo(temp_git_repo, "tester")
    assert applied.email == "ahmad@test.com"

    # Verify local git configs
    info = get_repo_git_identity(temp_git_repo)
    assert info["local_name"] == "Ahmad Test"
    assert info["local_email"] == "ahmad@test.com"
    assert info["use_http_path"] == "true"
    assert "id_custom" in (info["ssh_command"] or "")


def test_scan_git_identity(temp_profiles_path: Path, temp_git_repo: Path):
    # Unconfigured repo: should fail because local email/name are missing
    res1 = scan_git_identity(temp_git_repo)
    assert res1.passed is False
    assert "Local 'user.email' is not set" in res1.message

    # Configure profile and state
    p = Profile(name="Ahmad", email="ahmad@test.com", github_username="ahmad")
    add_profile("primary", p)
    apply_profile_to_repo(temp_git_repo, "primary")

    state = ValdozState(project_name="test_proj", profile="primary")
    save_state(temp_git_repo, state)

    # Now should pass
    res2 = scan_git_identity(temp_git_repo)
    assert res2.passed is True

    # Intentionally mismatch local email
    subprocess.run(["git", "config", "--local", "user.email", "wrong@evil.com"], cwd=temp_git_repo, check=True)
    res3 = scan_git_identity(temp_git_repo)
    assert res3.passed is False
    assert "does not match bound profile" in res3.message


def test_autofix_git_identity(temp_profiles_path: Path, temp_git_repo: Path):
    # Setup remote and default profile
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/myorg/myrepo.git"], cwd=temp_git_repo, check=True)
    p = Profile(name="Auto Fixer", email="autofix@corp.com", github_username="autofixer")
    add_profile("default_prof", p, set_default=True)

    # Initially missing useHttpPath and email
    fixes = autofix_audit_issues(temp_git_repo)
    assert any("credential.useHttpPath = true" in f for f in fixes)
    assert any("default_prof" in f for f in fixes)

    info = get_repo_git_identity(temp_git_repo)
    assert info["use_http_path"] == "true"
    assert info["local_email"] == "autofix@corp.com"


def test_cli_profile_workflow(temp_profiles_path: Path, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(temp_git_repo)

    # 1. Profile add via CLI
    res_add = runner.invoke(app, [
        "profile", "add", "work",
        "--name", "Jane Doe",
        "--email", "jane@company.com",
        "--user", "janedoe",
        "--default"
    ])
    assert res_add.exit_code == 0
    assert "Profile 'work' saved successfully" in res_add.output

    # 2. Profile list
    res_list = runner.invoke(app, ["profile", "list"], env={"COLUMNS": "200"})
    assert res_list.exit_code == 0
    assert "work" in res_list.output
    assert "jane@company.com" in res_list.output

    # 3. Project init with profile
    res_init = runner.invoke(app, ["project", "init", "--name", "cli_test", "--profile", "work"])
    assert res_init.exit_code == 0

    # 4. Profile status
    res_status = runner.invoke(app, ["profile", "status"])
    assert res_status.exit_code == 0
    assert "jane@company.com" in res_status.output
    assert "credential.useHttpPath = true" in res_status.output

    # 5. Profile remove
    res_rm = runner.invoke(app, ["profile", "remove", "work"])
    assert res_rm.exit_code == 0
    assert "removed" in res_rm.output
