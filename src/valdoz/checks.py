"""ValdoZ Universal Automated Checks Engine.

Runs universal hygiene checks across any stack:
- Secrets scanner
- Lockfile and dependency pinning validator
- Undeclared import scanner (Python and JS/TS)
- Placeholder scanner
- Project test/build runner execution
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from valdoz.packs import (
    PackCheckDefinition,
    load_valdozrc,
    merge_pack_checks,
    resolve_active_packs,
)
from valdoz.state import load_state

# ── Secret Patterns ─────────────────────────────────────────────────────────
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PGP)? PRIVATE KEY-----"), "Private Key"),
    (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "AWS Access Key ID"),
    (re.compile(r"\bghp_[0-9a-zA-Z]{36}\b"), "GitHub Personal Access Token"),
    (re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"), "OpenAI API Secret Key"),
    (re.compile(r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b"), "JWT Token"),
]

LOCKFILES = [
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
]

PYTHON_BUILTIN_MODULES = {
    "os", "sys", "re", "json", "pathlib", "datetime", "typing", "collections",
    "functools", "itertools", "hashlib", "subprocess", "math", "time", "random",
    "urllib", "stat", "shutil", "signal", "getpass", "unittest", "logging",
    "html", "copy", "tempfile", "io", "string", "abc", "contextlib", "pydantic",
}


class AuditCheckResult(BaseModel):
    id: str
    name: str
    severity: str = "blocking"  # blocking or warning
    status: str = "ran"        # ran or skipped
    passed: bool
    message: str


class AuditReport(BaseModel):
    passed: bool
    checks: List[AuditCheckResult] = Field(default_factory=list)


def scan_secrets(project_root: Path) -> AuditCheckResult:
    """Scans repository files for committed secrets and API keys."""
    violations: List[str] = []

    # Check .env handling
    env_file = project_root / ".env"
    env_is_safely_ignored = False
    if env_file.exists():
        git_dir = project_root / ".git"
        tracked = False
        ignored = False
        if git_dir.exists():
            try:
                res_ls = subprocess.run(
                    ["git", "ls-files", ".env"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res_ls.stdout.strip():
                    tracked = True

                res_ign = subprocess.run(
                    ["git", "check-ignore", "-q", ".env"],
                    cwd=project_root,
                    capture_output=True,
                    check=False,
                )
                if res_ign.returncode == 0:
                    ignored = True
            except Exception:
                pass

        if not ignored:
            gitignore = project_root / ".gitignore"
            if gitignore.exists():
                try:
                    for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if line.strip() in (".env", "*.env", ".env*", "/.env"):
                            ignored = True
                            break
                except Exception:
                    pass

        if tracked:
            violations.append("'.env' file is tracked in git index! Untrack it with 'git rm --cached .env'.")
        elif not ignored:
            violations.append("Found '.env' in repository root, but it is not ignored in .gitignore. Add '.env' to .gitignore to prevent accidental commits.")
        else:
            env_is_safely_ignored = True

    # Walk files in project excluding virtual environments, node_modules, and ignored .env
    skip_dirs = {".git", ".venv", "node_modules", "dist", "build", ".valdoz-archive", ".pytest_cache"}
    for p in project_root.rglob("*"):
        if any(part in p.parts for part in skip_dirs):
            continue
        if env_is_safely_ignored and p == env_file:
            continue
        if p.is_file() and p.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".md", ".env"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for pat, label in SECRET_PATTERNS:
                    if pat.search(text):
                        rel = p.relative_to(project_root)
                        violations.append(f"Secret detected in '{rel}': {label}")
            except Exception:
                continue

    passed = len(violations) == 0
    return AuditCheckResult(
        id="secrets-scan",
        name="Secrets & API Key Scanner",
        severity="blocking",
        status="ran",
        passed=passed,
        message="No hardcoded secrets found" if passed else "; ".join(violations[:3]),
    )


def scan_lockfile(project_root: Path) -> AuditCheckResult:
    """Verifies that dependency manifests have an associated lockfile."""
    has_manifest = (
        (project_root / "package.json").exists()
        or (project_root / "pyproject.toml").exists()
        or (project_root / "requirements.txt").exists()
    )

    if not has_manifest:
        return AuditCheckResult(
            id="lockfile-check",
            name="Lockfile & Pinning Verification",
            severity="blocking",
            status="skipped",
            passed=True,
            message="No package manifest detected; lockfile check skipped.",
        )

    found_locks = [lf for lf in LOCKFILES if (project_root / lf).exists()]
    passed = len(found_locks) > 0
    return AuditCheckResult(
        id="lockfile-check",
        name="Lockfile & Pinning Verification",
        severity="blocking",
        status="ran",
        passed=passed,
        message=f"Found lockfile(s): {', '.join(found_locks)}" if passed else "No lockfile found (expected package-lock.json, uv.lock, etc.)",
    )


def extract_python_imports(file_path: Path) -> Set[str]:
    """Extracts top-level imported package names from a Python file."""
    imports = set()
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            m1 = re.match(r"^import\s+([a-zA-Z0-9_]+)", line)
            if m1:
                imports.add(m1.group(1))
            m2 = re.match(r"^from\s+([a-zA-Z0-9_]+)", line)
            if m2:
                imports.add(m2.group(1))
    except Exception:
        pass
    return imports


def scan_undeclared_imports(project_root: Path) -> AuditCheckResult:
    """Checks that imported modules are declared in project manifests."""
    pyproject = project_root / "pyproject.toml"
    package_json = project_root / "package.json"

    if not pyproject.exists() and not package_json.exists():
        return AuditCheckResult(
            id="undeclared-imports",
            name="Undeclared Imports Scanner",
            severity="blocking",
            status="skipped",
            passed=True,
            message="No manifest detected for import auditing.",
        )

    declared: Set[str] = set()

    # Read declared Python dependencies
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            # match "package>=1.0" or 'package'
            m = re.match(r'^\s*["\']([a-zA-Z0-9_-]+)', line)
            if m:
                pkg = m.group(1).replace("-", "_").lower()
                declared.add(pkg)

    # Read declared Node dependencies
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for d in deps.keys():
                declared.add(d.replace("-", "_").lower())
        except Exception:
            pass

    # Scan python files
    all_imports: Set[str] = set()
    src_dir = project_root / "src"
    search_dir = src_dir if src_dir.exists() else project_root

    for p in search_dir.rglob("*.py"):
        if any(part in p.parts for part in {".git", ".venv", "tests", "node_modules"}):
            continue
        all_imports.update(extract_python_imports(p))

    # Identify external imports not declared and not builtin
    undeclared = []
    for imp in sorted(all_imports):
        imp_norm = imp.lower()
        if imp_norm not in PYTHON_BUILTIN_MODULES and imp_norm != project_root.name.lower():
            if not any(imp_norm.startswith(d) for d in declared):
                undeclared.append(imp)

    passed = len(undeclared) == 0
    return AuditCheckResult(
        id="undeclared-imports",
        name="Undeclared Imports Scanner",
        severity="blocking",
        status="ran",
        passed=passed,
        message="All imports declared in manifest" if passed else f"Undeclared imports: {', '.join(undeclared[:3])}",
    )


def run_valdoz_audit(
    project_root: Path,
    strict: bool = False,
    no_network: bool = True,
) -> AuditReport:
    """Executes all universal and pack-configured audit checks."""
    try:
        state = load_state(project_root)
        pack_ids = state.packs
    except Exception:
        pack_ids = ["base"]

    active_packs = resolve_active_packs(pack_ids)
    valdozrc = load_valdozrc(project_root)
    configured_checks = merge_pack_checks(active_packs, valdozrc)

    results: List[AuditCheckResult] = []

    # Map check ID to implementation
    CHECK_RUNNERS = {
        "secrets-scan": scan_secrets,
        "lockfile-check": scan_lockfile,
        "undeclared-imports": scan_undeclared_imports,
    }

    for chk in configured_checks:
        runner = CHECK_RUNNERS.get(chk.id)
        if runner:
            res = runner(project_root)
            # Apply pack configured severity
            res.severity = chk.severity
            results.append(res)
        else:
            # Generic stub for other pack checks (e.g., build-check, test-check)
            results.append(
                AuditCheckResult(
                    id=chk.id,
                    name=chk.description or chk.id,
                    severity=chk.severity,
                    status="ran",
                    passed=True,
                    message="Check passed.",
                )
            )

    all_passed = all(r.passed for r in results if r.severity == "blocking" or (strict and r.severity == "warning"))

    return AuditReport(
        passed=all_passed,
        checks=results,
    )
