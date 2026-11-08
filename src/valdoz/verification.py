"""ValdoZ Full-Spectrum Non-Bypassable Verification Engine.

Discovers workspace packages, traverses monorepos, and executes the
Four Pillars of Verification (Lint, Typecheck, Test, Build) to prevent
untested code, undeclared identifiers, and runtime blank-screen crashes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

IGNORED_DIRS = {
    ".git",
    ".valdoz",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "out",
    ".output",
    ".next",
    ".turbo",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    ".idea",
    ".vscode",
}


class StepResult(BaseModel):
    step: str  # "lint", "typecheck", "test", "build", "root_verify"
    package: str  # package name or directory relative path
    command: List[str]
    passed: bool
    returncode: int
    output: str
    duration_seconds: float = 0.0


class VerificationReport(BaseModel):
    project_root: str
    passed: bool
    used_root_verify: bool = False
    packages_checked: List[str] = Field(default_factory=list)
    steps: List[StepResult] = Field(default_factory=list)
    summary: str = ""


class PackageDescriptor(BaseModel):
    name: str
    path: Path
    rel_path: str
    ecosystem: str  # "node", "python", "rust"
    manifest_path: Path
    scripts: Dict[str, str] = Field(default_factory=dict)
    has_tsconfig: bool = False


def discover_workspace_packages(project_root: Path, max_depth: int = 2) -> List[PackageDescriptor]:
    """Scans project_root and subdirectories up to max_depth for package manifests."""
    descriptors: List[PackageDescriptor] = []
    seen_paths: set = set()

    def inspect_dir(d: Path, current_depth: int):
        if d.name in IGNORED_DIRS or any(part in IGNORED_DIRS for part in d.parts):
            return

        pkg_json = d / "package.json"
        pyproject = d / "pyproject.toml"
        setup_py = d / "setup.py"
        cargo_toml = d / "Cargo.toml"

        rel = str(d.relative_to(project_root)) if d != project_root else "."

        if pkg_json.is_file() and d not in seen_paths:
            seen_paths.add(d)
            scripts = {}
            name = d.name if d != project_root else "root"
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                name = data.get("name", name)
                scripts = data.get("scripts", {})
            except Exception:
                pass

            descriptors.append(
                PackageDescriptor(
                    name=name,
                    path=d,
                    rel_path=rel,
                    ecosystem="node",
                    manifest_path=pkg_json,
                    scripts=scripts,
                    has_tsconfig=(d / "tsconfig.json").is_file(),
                )
            )

        elif (pyproject.is_file() or setup_py.is_file()) and d not in seen_paths:
            seen_paths.add(d)
            name = d.name if d != project_root else "root"
            descriptors.append(
                PackageDescriptor(
                    name=name,
                    path=d,
                    rel_path=rel,
                    ecosystem="python",
                    manifest_path=pyproject if pyproject.is_file() else setup_py,
                    scripts={},
                    has_tsconfig=False,
                )
            )

        elif cargo_toml.is_file() and d not in seen_paths:
            seen_paths.add(d)
            name = d.name if d != project_root else "root"
            descriptors.append(
                PackageDescriptor(
                    name=name,
                    path=d,
                    rel_path=rel,
                    ecosystem="rust",
                    manifest_path=cargo_toml,
                    scripts={},
                    has_tsconfig=False,
                )
            )

        if current_depth < max_depth:
            try:
                for entry in sorted(d.iterdir()):
                    if entry.is_dir() and entry.name not in IGNORED_DIRS and not entry.name.startswith("."):
                        inspect_dir(entry, current_depth + 1)
            except (PermissionError, OSError):
                pass

    inspect_dir(project_root, 0)
    return descriptors


def _run_cmd(cmd: List[str], cwd: Path, timeout: int = 120) -> Tuple[bool, int, str, float]:
    start = time.time()
    try:
        env = os.environ.copy()
        # Propagate current sys.path to PYTHONPATH for python child processes
        existing_pythonpath = env.get("PYTHONPATH", "")
        paths = [p for p in sys.path if p and Path(p).exists()]
        if existing_pythonpath:
            env["PYTHONPATH"] = f"{existing_pythonpath}:{':'.join(paths)}"
        else:
            env["PYTHONPATH"] = ":".join(paths)

        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        duration = round(time.time() - start, 2)
        combined = (proc.stdout + "\n" + proc.stderr).strip()
        return proc.returncode == 0, proc.returncode, combined, duration
    except subprocess.TimeoutExpired:
        duration = round(time.time() - start, 2)
        return False, -1, f"Command timed out after {timeout}s: {' '.join(cmd)}", duration
    except FileNotFoundError:
        duration = round(time.time() - start, 2)
        return False, 127, f"Executable not found: {cmd[0]}", duration
    except Exception as e:
        duration = round(time.time() - start, 2)
        return False, 1, f"Execution failed: {e}", duration


def run_project_verification(
    project_root: Path,
    include_subprojects: bool = True,
    run_builds: bool = True,
    timeout: int = 120,
) -> VerificationReport:
    """Executes full-spectrum project verification.

    Discipline:
    1. If a root 'verify' script exists in package.json, run it as the authoritative gate.
    2. Otherwise, auto-discover all packages (root + sub-apps) and run the 4 pillars:
       - Pillar 1: Linting (npm run lint, ruff, flake8)
       - Pillar 2: Typecheck (npm run typecheck, tsc --noEmit, mypy)
       - Pillar 3: Tests (npm test, pytest, cargo test)
       - Pillar 4: Builds (npm run build, cargo build)
    """
    root_pkg_json = project_root / "package.json"
    used_root_verify = False

    # Check for authoritative root verify script
    if root_pkg_json.is_file():
        try:
            data = json.loads(root_pkg_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "verify" in scripts:
                used_root_verify = True
                cmd = ["npm", "run", "verify"]
                passed, code, output, dur = _run_cmd(cmd, project_root, timeout=timeout)
                step = StepResult(
                    step="root_verify",
                    package="root",
                    command=cmd,
                    passed=passed,
                    returncode=code,
                    output=output,
                    duration_seconds=dur,
                )
                summary = (
                    "✓ Root verification suite passed."
                    if passed
                    else "✗ Root verification script ('npm run verify') failed."
                )
                return VerificationReport(
                    project_root=str(project_root),
                    passed=passed,
                    used_root_verify=True,
                    packages_checked=["root"],
                    steps=[step],
                    summary=summary,
                )
        except Exception:
            pass

    # Fallback to multi-package 4-pillar auto-discovery
    packages = discover_workspace_packages(project_root, max_depth=2 if include_subprojects else 0)
    steps: List[StepResult] = []
    checked_names: List[str] = []

    for pkg in packages:
        checked_names.append(pkg.rel_path)

        # ── Node Ecosystem ──
        if pkg.ecosystem == "node":
            # 1. Lint Pillar
            if "lint" in pkg.scripts:
                cmd = ["npm", "run", "lint"]
                passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="lint",
                        package=pkg.rel_path,
                        command=cmd,
                        passed=passed,
                        returncode=code,
                        output=out,
                        duration_seconds=dur,
                    )
                )

            # 2. Typecheck Pillar
            if "typecheck" in pkg.scripts:
                cmd = ["npm", "run", "typecheck"]
                passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="typecheck",
                        package=pkg.rel_path,
                        command=cmd,
                        passed=passed,
                        returncode=code,
                        output=out,
                        duration_seconds=dur,
                    )
                )
            elif pkg.has_tsconfig and shutil.which("npx"):
                cmd = ["npx", "tsc", "--noEmit"]
                passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="typecheck",
                        package=pkg.rel_path,
                        command=cmd,
                        passed=passed,
                        returncode=code,
                        output=out,
                        duration_seconds=dur,
                    )
                )

            # 3. Test Pillar
            if "test" in pkg.scripts:
                cmd = ["npm", "test"]
                passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="test",
                        package=pkg.rel_path,
                        command=cmd,
                        passed=passed,
                        returncode=code,
                        output=out,
                        duration_seconds=dur,
                    )
                )

            # 4. Build Pillar
            if run_builds and "build" in pkg.scripts:
                cmd = ["npm", "run", "build"]
                passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="build",
                        package=pkg.rel_path,
                        command=cmd,
                        passed=passed,
                        returncode=code,
                        output=out,
                        duration_seconds=dur,
                    )
                )

        # ── Python Ecosystem ──
        elif pkg.ecosystem == "python":
            # 1. Lint Pillar (ruff if available)
            if shutil.which("ruff"):
                cmd = ["ruff", "check", "."]
                passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="lint",
                        package=pkg.rel_path,
                        command=cmd,
                        passed=passed,
                        returncode=code,
                        output=out,
                        duration_seconds=dur,
                    )
                )

            # 2. Typecheck Pillar (mypy if available and configured)
            if (pkg.path / "mypy.ini").is_file() or (pkg.path / ".mypy.ini").is_file():
                if shutil.which("mypy"):
                    cmd = ["mypy", "."]
                    passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                    steps.append(
                        StepResult(
                            step="typecheck",
                            package=pkg.rel_path,
                            command=cmd,
                            passed=passed,
                            returncode=code,
                            output=out,
                            duration_seconds=dur,
                        )
                    )

            # 3. Test Pillar
            tests_dir = pkg.path / "tests"
            if tests_dir.is_dir() or (pkg.path / "pyproject.toml").is_file():
                import sys
                cmd = [sys.executable, "-m", "pytest", "-q"]
                passed, code, out, dur = _run_cmd(cmd, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="test",
                        package=pkg.rel_path,
                        command=cmd,
                        passed=passed,
                        returncode=code,
                        output=out,
                        duration_seconds=dur,
                    )
                )

        # ── Rust Ecosystem ──
        elif pkg.ecosystem == "rust":
            if shutil.which("cargo"):
                # Clippy Lint
                cmd_lint = ["cargo", "clippy", "--", "-D", "warnings"]
                p_lint, c_lint, out_lint, dur_lint = _run_cmd(cmd_lint, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="lint",
                        package=pkg.rel_path,
                        command=cmd_lint,
                        passed=p_lint,
                        returncode=c_lint,
                        output=out_lint,
                        duration_seconds=dur_lint,
                    )
                )
                # Test
                cmd_test = ["cargo", "test"]
                p_test, c_test, out_test, dur_test = _run_cmd(cmd_test, pkg.path, timeout=timeout)
                steps.append(
                    StepResult(
                        step="test",
                        package=pkg.rel_path,
                        command=cmd_test,
                        passed=p_test,
                        returncode=c_test,
                        output=out_test,
                        duration_seconds=dur_test,
                    )
                )
                # Build
                if run_builds:
                    cmd_build = ["cargo", "build"]
                    p_build, c_build, out_build, dur_build = _run_cmd(cmd_build, pkg.path, timeout=timeout)
                    steps.append(
                        StepResult(
                            step="build",
                            package=pkg.rel_path,
                            command=cmd_build,
                            passed=p_build,
                            returncode=c_build,
                            output=out_build,
                            duration_seconds=dur_build,
                        )
                    )

    if not steps:
        # No automated steps discovered
        return VerificationReport(
            project_root=str(project_root),
            passed=True,
            used_root_verify=False,
            packages_checked=checked_names,
            steps=[],
            summary="No automated verification commands detected across packages.",
        )

    all_passed = all(s.passed for s in steps)
    failed_steps = [f"[{s.package}:{s.step}]" for s in steps if not s.passed]

    if all_passed:
        summary = f"✓ All {len(steps)} verification checks passed across {len(packages)} package(s)."
    else:
        summary = f"✗ Verification failed in {len(failed_steps)} step(s): {', '.join(failed_steps)}"

    return VerificationReport(
        project_root=str(project_root),
        passed=all_passed,
        used_root_verify=False,
        packages_checked=checked_names,
        steps=steps,
        summary=summary,
    )
