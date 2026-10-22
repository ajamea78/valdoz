"""ValdoZ Integration Engine: Git Hooks and CI Workflows.

Manages:
- Git pre-commit hook enforcing role domain separation (builder vs scribe) and gate verification
- GitHub Actions CI workflow template with fail-fast bootstrap
"""

from __future__ import annotations

import os
import stat
from pathlib import Path


def generate_pre_commit_hook() -> str:
    return r"""#!/usr/bin/env bash
# ValdoZ Protocol Pre-Commit Hook
set -e

# 1. Role Domain Separation
STAGED_FILES=$(git diff --cached --name-only)
if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Detect role from VALDOZ_ROLE environment variable or session.lock
ROLE=""
if [ -n "$VALDOZ_ROLE" ]; then
    ROLE="$VALDOZ_ROLE"
elif [ -f ".valdoz/session.lock" ]; then
    if grep -q '"builder"' .valdoz/session.lock && ! grep -q '"scribe"' .valdoz/session.lock; then
        ROLE="builder"
    elif grep -q '"scribe"' .valdoz/session.lock && ! grep -q '"builder"' .valdoz/session.lock; then
        ROLE="scribe"
    fi
fi

if [ "$ROLE" = "builder" ]; then
    DOCS_TOUCHED=$(echo "$STAGED_FILES" | grep -E '^(docs/|CHANGELOG\.md)' || true)
    if [ -n "$DOCS_TOUCHED" ]; then
        echo "[ValdoZ Hook Error] Role 'builder' is prohibited from modifying documentation files:"
        echo "$DOCS_TOUCHED"
        echo "Documentation changes must be authored by the 'scribe' role."
        exit 1
    fi
elif [ "$ROLE" = "scribe" ]; then
    CODE_TOUCHED=$(echo "$STAGED_FILES" | grep -E '^(src/|tests/|package\.json|pyproject\.toml|tsconfig\.json)' || true)
    if [ -n "$CODE_TOUCHED" ]; then
        echo "[ValdoZ Hook Error] Role 'scribe' is prohibited from modifying code or test files:"
        echo "$CODE_TOUCHED"
        echo "Code and test changes must be authored by the 'builder' role."
        exit 1
    fi
fi

# 2. Gate and Audit Checks
if command -v valdoz >/dev/null 2>&1; then
    valdoz gate check --ci
    valdoz audit --strict --no-network
fi
"""


def generate_ci_workflow() -> str:
    return """name: ValdoZ Gate Verification

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  valdoz-gate:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Install ValdoZ Protocol
        run: |
          curl -Lsf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH
          # Install from PyPI or fail-fast bootstrap during preview:
          uv tool install valdoz-protocol@3.0.0 || {
            echo "::error::ValdoZ package not published on PyPI. Configure repo token."
            exit 1
          }
          valdoz --version

      - name: Verify Phase Gate
        run: valdoz gate check --ci

      - name: Run ValdoZ Audit
        run: valdoz audit --strict --no-network
"""


def install_git_hook(project_root: Path) -> Path:
    """Installs the pre-commit hook into .git/hooks/pre-commit."""
    git_dir = project_root / ".git"
    if not git_dir.exists():
        raise RuntimeError("Not a git repository (missing .git directory).")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"
    hook_file.write_text(generate_pre_commit_hook(), encoding="utf-8")

    # Make executable (chmod +x)
    current_mode = hook_file.stat().st_mode
    hook_file.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return hook_file


def install_ci_workflow(project_root: Path) -> Path:
    """Installs the GitHub Actions CI workflow to .github/workflows/valdoz.yml."""
    wf_dir = project_root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    wf_file = wf_dir / "valdoz.yml"
    wf_file.write_text(generate_ci_workflow(), encoding="utf-8")
    return wf_file
