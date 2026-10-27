"""Tests for ValdoZ Project-Scoped Credential Vault & Auth Engine."""

import os
import stat
import subprocess
from pathlib import Path
import pytest
from typer.testing import CliRunner

from valdoz.cli import app
from valdoz.auth import (
    clear_project_vault,
    ensure_vault_gitignored,
    get_project_vault_path,
    get_project_vault_status,
    setup_project_vault,
)
from valdoz.checks import scan_secrets

runner = CliRunner()


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test_auth_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    return repo


def test_setup_project_vault(temp_git_repo: Path):
    vault_file = setup_project_vault(
        temp_git_repo,
        username="testuser",
        token="gh_token_test_sample_value_12345",
    )
    assert vault_file.exists()
    assert vault_file == get_project_vault_path(temp_git_repo)

    # Verify chmod 600
    mode = vault_file.stat().st_mode & 0o777
    assert mode == 0o600

    # Verify gitignore
    gitignore = temp_git_repo / ".gitignore"
    assert gitignore.exists()
    assert ".valdoz/.git-credentials" in gitignore.read_text(encoding="utf-8")

    # Verify git config
    res_h = subprocess.run(
        ["git", "config", "--local", "credential.helper"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert f"store --file {vault_file.resolve()}" in res_h.stdout

    res_u = subprocess.run(
        ["git", "config", "--local", "credential.useHttpPath"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert res_u.stdout.strip() == "true"


def test_get_project_vault_status(temp_git_repo: Path):
    # Before setup
    s1 = get_project_vault_status(temp_git_repo)
    assert s1["vault_exists"] is False
    assert s1["permissions_secure"] is False

    # After setup
    setup_project_vault(
        temp_git_repo,
        username="jane_doe",
        token="tok_supersecrettoken123456789",
    )
    s2 = get_project_vault_status(temp_git_repo)
    assert s2["vault_exists"] is True
    assert s2["permissions_secure"] is True
    assert s2["is_gitignored"] is True
    assert s2["is_untracked"] is True
    assert s2["credential_helper_configured"] is True
    assert s2["credential_use_http_path"] is True
    assert s2["username"] == "jane_doe"
    assert "tok_" in s2["token_masked"]
    assert "supersecrettoken" not in s2["token_masked"]


def test_scan_secrets_with_vault(temp_git_repo: Path):
    vault_file = setup_project_vault(
        temp_git_repo,
        username="testuser",
        token="tok_dummy_credential_value_9999",
    )

    # 1. Ignored and secure: should pass
    r1 = scan_secrets(temp_git_repo)
    assert r1.passed is True

    # 2. Insecure permissions (e.g. 0644): should fail
    os.chmod(vault_file, 0o644)
    r2 = scan_secrets(temp_git_repo)
    assert r2.passed is False
    assert "Insecure permissions" in r2.message

    # Restore 600
    os.chmod(vault_file, 0o600)
    assert scan_secrets(temp_git_repo).passed is True


def test_clear_project_vault(temp_git_repo: Path):
    tok = "ghp_" + "dummyTestToken1234567890abcdef"
    vault_file = setup_project_vault(temp_git_repo, username="u", token=tok)
    assert vault_file.exists()

    cleared = clear_project_vault(temp_git_repo)
    assert cleared is True
    assert not vault_file.exists()

    # Helper should be unset
    res = subprocess.run(
        ["git", "config", "--local", "credential.helper"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode != 0


def test_cli_auth_workflow(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(temp_git_repo)

    # Setup via CLI
    res_setup = runner.invoke(app, [
        "auth", "setup",
        "--user", "cli_user",
        "--token", "tok_cli_custom_secure_token_12345",
    ])
    assert res_setup.exit_code == 0
    assert "Project Authentication Vault Configured" in res_setup.output

    # Status via CLI
    res_status = runner.invoke(app, ["auth", "status"])
    assert res_status.exit_code == 0
    assert "cli_user" in res_status.output
    assert "chmod 600" in res_status.output

    # Clear via CLI
    res_clear = runner.invoke(app, ["auth", "clear", "--yes"])
    assert res_clear.exit_code == 0
    assert "securely cleared" in res_clear.output

    # Status after clear
    res_status2 = runner.invoke(app, ["auth", "status"])
    assert "Not Configured" in res_status2.output
