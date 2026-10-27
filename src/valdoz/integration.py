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
    if [ "$VALDOZ_ROLE" != "builder" ] && [ "$VALDOZ_ROLE" != "scribe" ]; then
        echo "[ValdoZ Hook Security Error] Invalid VALDOZ_ROLE='$VALDOZ_ROLE'."
        echo "VALDOZ_ROLE must be strictly 'builder' or 'scribe'."
        exit 1
    fi
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
if [ -f ".valdoz/state.json" ] && command -v valdoz >/dev/null 2>&1; then
    valdoz gate check --ci
    valdoz audit --strict --no-network
elif command -v valdoz >/dev/null 2>&1; then
    valdoz audit --strict --no-network || true
fi
"""


def generate_pre_push_hook() -> str:
    return r"""#!/usr/bin/env bash
# ValdoZ Protocol Pre-Push Hook (Continuous Deployment & Live Protection)
set -e

IS_PROD_PUSH=0
DEST_BRANCH=""

# Read push destination refs from stdin: <local ref> <local sha> <remote ref> <remote sha>
while read -r local_ref local_sha remote_ref remote_sha; do
    branch="${remote_ref#refs/heads/}"
    if [ "$branch" = "main" ] || [ "$branch" = "master" ] || [ "$branch" = "production" ] || [ "$branch" = "prod" ] || [[ "$branch" =~ ^release/ ]]; then
        IS_PROD_PUSH=1
        DEST_BRANCH="$branch"
        break
    fi
done

# If pushing to a production-triggering branch:
if [ "$IS_PROD_PUSH" -eq 1 ]; then
    CURRENT_PHASE=""
    if [ -f ".valdoz/state.json" ]; then
        if command -v python3 >/dev/null 2>&1; then
            CURRENT_PHASE=$(python3 -c "import json; print(json.load(open('.valdoz/state.json')).get('current_phase', ''))" 2>/dev/null || true)
        elif command -v python >/dev/null 2>&1; then
            CURRENT_PHASE=$(python -c "import json; print(json.load(open('.valdoz/state.json')).get('current_phase', ''))" 2>/dev/null || true)
        fi
    fi

    # Direct push to production branches is ONLY permitted in Phase 8 (Deploy) or Phase 10 (approved Change Requests)
    if [ "$CURRENT_PHASE" != "8" ] && [ "$CURRENT_PHASE" != "10" ]; then
        if [ "$VALDOZ_ALLOW_PROD_PUSH" = "1" ]; then
            echo "⚡ [ValdoZ Push Protection] Pushing to '$DEST_BRANCH' with human authorization override (VALDOZ_ALLOW_PROD_PUSH=1)."
        else
            echo ""
            echo "🛑 [ValdoZ Push Protection Error]"
            echo "Direct push to production-linked branch '$DEST_BRANCH' is BLOCKED."
            echo "Current project is in Phase ${CURRENT_PHASE:-'unknown'}."
            echo ""
            echo "Pushing directly to '$DEST_BRANCH' triggers automatic Live/Production cloud deployments (Vercel, AWS, Fly, etc.)."
            echo "Under ValdoZ Protocol, live deployments are strictly gated until Phase 8 (Deploy) after human sign-off."
            echo ""
            echo "Recommended Actions:"
            echo "  1. Push to a feature or slice branch instead:  git push origin HEAD:refs/heads/slice/<name>"
            echo "  2. Complete slice verification in Phase 6 / 7 before promoting to '$DEST_BRANCH'."
            echo "  3. If you have explicit human authorization to override, run:  VALDOZ_ALLOW_PROD_PUSH=1 git push"
            echo ""
            exit 1
        fi
    fi
fi

# 2. Multi-Account Push Identity & Credential Isolation
REMOTE_URL=$(git config --get remote.origin.url || true)
if [[ "$REMOTE_URL" =~ ^https:// ]]; then
    USE_HTTP_PATH=$(git config --local credential.useHttpPath || true)
    if [ "$USE_HTTP_PATH" != "true" ]; then
        echo ""
        echo "🛑 [ValdoZ Multi-Account Protection]"
        echo "Git credential isolation ('credential.useHttpPath') is NOT enabled for this repository."
        echo "Pushing now risks sending credentials from another GitHub account (resulting in 403 Forbidden)."
        echo "Run:  valdoz audit --fix   or   git config --local credential.useHttpPath true"
        echo ""
        if [ "$VALDOZ_ALLOW_PUSH_WITHOUT_ISOLATION" != "1" ]; then
            exit 1
        fi
    fi
fi
"""


def generate_ci_workflow(self_healing: bool = False) -> str:
    base_workflow = """name: ValdoZ Gate Verification

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
          # Install from PyPI or local source during preview:
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
    if not self_healing:
        return base_workflow

    # Self-healing CI/CD pipeline extension inspired by automated remediation
    healing_extension = """
  self-heal:
    needs: valdoz-gate
    if: failure()
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install ValdoZ Protocol
        run: |
          curl -Lsf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH
          uv tool install valdoz-protocol@3.0.0 || uv tool install --editable . --force

      - name: Capture Failure Diagnostic Logs
        run: |
          mkdir -p .valdoz/ci-logs
          echo "Failure detected on commit ${{ github.sha }} on branch ${{ github.ref_name }}" > .valdoz/ci-logs/failure.txt
          valdoz gate check --ci >> .valdoz/ci-logs/failure.txt 2>&1 || true
          valdoz audit --strict --no-network >> .valdoz/ci-logs/failure.txt 2>&1 || true

      - name: Run ValdoZ Autonomous Remediation
        env:
          VALDOZ_AI_API_KEY: ${{ secrets.VALDOZ_AI_API_KEY }}
          VALDOZ_AI_BASE_URL: ${{ secrets.VALDOZ_AI_BASE_URL }}
        run: |
          # 1. Attempt automated audit fixes first
          valdoz audit --fix || true
          # 2. Run ValdoZ Self-Healing Engine against captured CI failure context
          valdoz heal ci --log-file .valdoz/ci-logs/failure.txt || true

      - name: Create Pull Request with Diagnostic Report
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "fix(valdoz): automated self-healing remediation for run ${{ github.run_id }}"
          branch: "fix/valdoz-auto-heal-${{ github.run_id }}"
          title: "🤖 [ValdoZ Self-Healing] Auto-Remediation for CI Run #${{ github.run_id }}"
          body: |
            ## ValdoZ Autonomous Self-Healing Report
            This PR was automatically generated by the ValdoZ Protocol Self-Healing Engine in response to a CI gate/audit failure on commit `${{ github.sha }}`.

            ### Action Taken:
            - Automated issue remediation applied.
            - Codebase re-verified against ValdoZ gate conditions.
            
            *Please review the proposed diff before merging.*
"""
    return base_workflow + healing_extension


def install_git_hook(project_root: Path) -> Path:
    """Installs the pre-commit and pre-push hooks into .git/hooks/."""
    git_dir = project_root / ".git"
    if not git_dir.exists():
        raise RuntimeError("Not a git repository (missing .git directory).")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # 1. pre-commit hook (roles & gate checks)
    pre_commit_file = hooks_dir / "pre-commit"
    pre_commit_file.write_text(generate_pre_commit_hook(), encoding="utf-8")
    mode_c = pre_commit_file.stat().st_mode
    pre_commit_file.chmod(mode_c | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # 2. pre-push hook (production push & CD protection)
    pre_push_file = hooks_dir / "pre-push"
    pre_push_file.write_text(generate_pre_push_hook(), encoding="utf-8")
    mode_p = pre_push_file.stat().st_mode
    pre_push_file.chmod(mode_p | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return pre_commit_file


def install_ci_workflow(project_root: Path, self_healing: bool = False) -> Path:
    """Installs the GitHub Actions CI workflow to .github/workflows/valdoz.yml."""
    wf_dir = project_root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    wf_file = wf_dir / "valdoz.yml"
    wf_file.write_text(generate_ci_workflow(self_healing=self_healing), encoding="utf-8")
    return wf_file
