"""Shared Pytest fixtures for ValdoZ Protocol test suites."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Generator

import pytest
from typer.testing import CliRunner

from valdoz.state import ValdozState, save_state


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provides a fresh Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Creates a temporary project root with initialized ValdoZ state."""
    state = ValdozState(project_name="fixture-project", language="en", current_phase=1)
    save_state(tmp_path, state)
    return tmp_path


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    """Creates a temporary directory initialized as a Git repository with valid config."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "ValdoZ Architect"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "architect@example.com"], cwd=str(tmp_path), check=True)
    return tmp_path
