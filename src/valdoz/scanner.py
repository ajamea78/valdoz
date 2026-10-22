"""ValdoZ Intelligent Project Scanner & Auto-Phase Placement Engine.

Scans an existing project directory to determine maturity, detect what
already exists (source code, tests, docs, CI/CD, deployments), and
automatically place the project at the correct phase — rather than
always starting from Phase 0.

Three project archetypes:
  - GREENFIELD:  Empty or near-empty directory → Phase 0
  - BROWNFIELD:  Active development, has code/tests but not deployed → Phase 5-7
  - PRODUCTION:  Running in production, has deploy configs, CI/CD → Phase 10
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ── Signal Detectors ────────────────────────────────────────────────────────

@dataclass
class ProjectSignals:
    """Raw signals detected by scanning the project directory."""
    # Source code
    has_source_code: bool = False
    source_languages: Set[str] = field(default_factory=set)
    source_file_count: int = 0

    # Tests
    has_tests: bool = False
    test_file_count: int = 0
    test_frameworks: Set[str] = field(default_factory=set)

    # Documentation
    has_docs_dir: bool = False
    has_readme: bool = False
    doc_file_count: int = 0

    # Package manifests & dependencies
    has_package_manifest: bool = False
    manifests_found: Set[str] = field(default_factory=set)
    has_lockfile: bool = False

    # CI/CD
    has_ci_config: bool = False
    ci_systems: Set[str] = field(default_factory=set)

    # Deployment & infrastructure
    has_dockerfile: bool = False
    has_docker_compose: bool = False
    has_k8s_configs: bool = False
    has_terraform: bool = False
    has_deploy_configs: bool = False

    # Git history
    has_git: bool = False
    git_commit_count: int = 0
    git_age_days: int = 0
    git_has_tags: bool = False

    # Environment & secrets
    has_env_file: bool = False
    env_file_gitignored: bool = False

    # Existing ValdoZ state
    has_existing_valdoz: bool = False

    # Linting & formatting
    has_linter_config: bool = False
    linter_configs: Set[str] = field(default_factory=set)


@dataclass
class MaturityAssessment:
    """The computed maturity verdict and recommended phase placement."""
    archetype: str  # "greenfield", "brownfield", "production"
    recommended_phase: int
    confidence: float  # 0.0 to 1.0
    pre_approved_phases: List[int] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    signals: Optional[ProjectSignals] = None
    detected_stack: Dict[str, str] = field(default_factory=dict)
    auto_remediations: List[str] = field(default_factory=list)


# ── Language Detection ──────────────────────────────────────────────────────

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React (JSX)",
    ".tsx": "React (TSX)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".swift": "Swift",
    ".dart": "Dart",
}

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".tox",
    ".valdoz-archive", ".next", ".nuxt", "target", "out",
    "vendor", "env", ".env",
}

MANIFEST_FILES = {
    "pyproject.toml": "Python (pyproject.toml)",
    "setup.py": "Python (setup.py)",
    "requirements.txt": "Python (requirements.txt)",
    "package.json": "JavaScript/TypeScript (package.json)",
    "Cargo.toml": "Rust (Cargo.toml)",
    "go.mod": "Go (go.mod)",
    "pom.xml": "Java (pom.xml)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "Gemfile": "Ruby (Gemfile)",
    "composer.json": "PHP (composer.json)",
    "pubspec.yaml": "Dart/Flutter (pubspec.yaml)",
}

LOCKFILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "uv.lock", "poetry.lock", "Pipfile.lock",
    "Cargo.lock", "go.sum", "Gemfile.lock", "composer.lock",
}

CI_CONFIGS = {
    ".github/workflows": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
    ".circleci": "CircleCI",
    ".travis.yml": "Travis CI",
    "bitbucket-pipelines.yml": "Bitbucket Pipelines",
    "azure-pipelines.yml": "Azure Pipelines",
}

LINTER_CONFIGS = {
    ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", ".eslintrc",
    "eslint.config.js", "eslint.config.mjs",
    ".prettierrc", ".prettierrc.json", ".prettierrc.yml",
    "ruff.toml", ".flake8", "mypy.ini", ".mypy.ini",
    ".pylintrc", "pylintrc",
    "biome.json", "biome.jsonc",
    ".editorconfig",
}

TEST_INDICATORS = {
    "tests/", "test/", "spec/", "__tests__/",
    "pytest.ini", "setup.cfg",  # pytest config
    "jest.config.js", "jest.config.ts", "jest.config.mjs",
    "vitest.config.ts", "vitest.config.js",
    "karma.conf.js", "cypress.config.js", "cypress.config.ts",
    "playwright.config.ts",
}


# ── Core Scanner ────────────────────────────────────────────────────────────

def scan_project(project_root: Path) -> ProjectSignals:
    """Performs a comprehensive scan of the project directory."""
    signals = ProjectSignals()

    # ── Source code detection ───────────────────────────────────────────
    for p in project_root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            ext = p.suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                signals.has_source_code = True
                signals.source_languages.add(LANGUAGE_EXTENSIONS[ext])
                signals.source_file_count += 1

    # ── Test detection ─────────────────────────────────────────────────
    for indicator in TEST_INDICATORS:
        check_path = project_root / indicator
        if check_path.exists():
            signals.has_tests = True
            break

    # Count test files
    test_patterns = ["test_*.py", "*_test.py", "*.test.js", "*.test.ts",
                     "*.spec.js", "*.spec.ts", "*.test.jsx", "*.test.tsx"]
    for pattern in test_patterns:
        for p in project_root.rglob(pattern):
            if not any(part in SKIP_DIRS for part in p.parts):
                signals.test_file_count += 1
    if signals.test_file_count > 0:
        signals.has_tests = True

    # Detect test frameworks
    if (project_root / "pytest.ini").exists() or (project_root / "conftest.py").exists():
        signals.test_frameworks.add("pytest")
    for jest_cfg in ["jest.config.js", "jest.config.ts", "jest.config.mjs"]:
        if (project_root / jest_cfg).exists():
            signals.test_frameworks.add("jest")
    pkg_json = project_root / "package.json"
    if pkg_json.exists():
        try:
            pj = json.loads(pkg_json.read_text(encoding="utf-8"))
            scripts = pj.get("scripts", {})
            if "test" in scripts:
                test_cmd = scripts["test"]
                if "jest" in test_cmd:
                    signals.test_frameworks.add("jest")
                elif "vitest" in test_cmd:
                    signals.test_frameworks.add("vitest")
                elif "mocha" in test_cmd:
                    signals.test_frameworks.add("mocha")
            dev_deps = pj.get("devDependencies", {})
            for fw in ["jest", "vitest", "mocha", "cypress", "playwright"]:
                if fw in dev_deps:
                    signals.test_frameworks.add(fw)
        except Exception:
            pass
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8")
            if "pytest" in text:
                signals.test_frameworks.add("pytest")
        except Exception:
            pass

    # ── Documentation ──────────────────────────────────────────────────
    docs_dir = project_root / "docs"
    if docs_dir.exists() and docs_dir.is_dir():
        signals.has_docs_dir = True
        signals.doc_file_count = sum(
            1 for f in docs_dir.rglob("*.md") if f.is_file()
        )
    for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
        if (project_root / readme_name).exists():
            signals.has_readme = True
            break

    # ── Package manifests & lockfiles ──────────────────────────────────
    for manifest_file, label in MANIFEST_FILES.items():
        if (project_root / manifest_file).exists():
            signals.has_package_manifest = True
            signals.manifests_found.add(label)
    for lockfile in LOCKFILES:
        if (project_root / lockfile).exists():
            signals.has_lockfile = True
            break

    # ── CI/CD ──────────────────────────────────────────────────────────
    for ci_path, ci_name in CI_CONFIGS.items():
        if (project_root / ci_path).exists():
            signals.has_ci_config = True
            signals.ci_systems.add(ci_name)

    # ── Deployment & infrastructure ────────────────────────────────────
    if (project_root / "Dockerfile").exists():
        signals.has_dockerfile = True
        signals.has_deploy_configs = True
    if (project_root / "docker-compose.yml").exists() or (project_root / "docker-compose.yaml").exists():
        signals.has_docker_compose = True
        signals.has_deploy_configs = True
    # Kubernetes
    for k8s_dir in ["k8s", "kubernetes", "deploy", "manifests", "helm"]:
        if (project_root / k8s_dir).exists():
            signals.has_k8s_configs = True
            signals.has_deploy_configs = True
            break
    # Terraform / IaC
    for tf_file in project_root.glob("*.tf"):
        signals.has_terraform = True
        signals.has_deploy_configs = True
        break
    for iac_dir in ["terraform", "infra", "infrastructure", "cdk"]:
        if (project_root / iac_dir).exists():
            signals.has_terraform = True
            signals.has_deploy_configs = True
            break

    # ── Git history ────────────────────────────────────────────────────
    git_dir = project_root / ".git"
    if git_dir.exists():
        signals.has_git = True
        try:
            res = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=project_root,
                capture_output=True, text=True, check=False,
            )
            if res.returncode == 0:
                signals.git_commit_count = int(res.stdout.strip())
        except Exception:
            pass
        try:
            res = subprocess.run(
                ["git", "log", "--reverse", "--format=%aI", "-1"],
                cwd=project_root,
                capture_output=True, text=True, check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                first_commit = datetime.fromisoformat(res.stdout.strip())
                now = datetime.now(timezone.utc)
                signals.git_age_days = (now - first_commit).days
        except Exception:
            pass
        try:
            res = subprocess.run(
                ["git", "tag", "-l"],
                cwd=project_root,
                capture_output=True, text=True, check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                signals.git_has_tags = True
        except Exception:
            pass

    # ── Environment ────────────────────────────────────────────────────
    env_file = project_root / ".env"
    if env_file.exists():
        signals.has_env_file = True
        gitignore = project_root / ".gitignore"
        if gitignore.exists():
            try:
                for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.strip() in (".env", "*.env", ".env*", "/.env"):
                        signals.env_file_gitignored = True
                        break
            except Exception:
                pass

    # ── Linter configs ─────────────────────────────────────────────────
    for lc in LINTER_CONFIGS:
        if (project_root / lc).exists():
            signals.has_linter_config = True
            signals.linter_configs.add(lc)

    # ── Existing ValdoZ state ──────────────────────────────────────────
    if (project_root / ".valdoz" / "state.json").exists():
        signals.has_existing_valdoz = True

    return signals


# ── Maturity Assessment Engine ──────────────────────────────────────────────

def assess_maturity(signals: ProjectSignals) -> MaturityAssessment:
    """Determines project archetype and recommended starting phase."""

    # ── Score computation ──────────────────────────────────────────────
    # Each score represents evidence that a phase is already complete
    phase_scores: Dict[int, float] = {i: 0.0 for i in range(11)}

    # Phase 0 (Init): Has a directory and possibly git
    if signals.has_git:
        phase_scores[0] += 1.0
    elif signals.has_source_code or signals.has_package_manifest:
        phase_scores[0] += 0.8

    # Phase 1 (Intake): Has README or docs describing the project
    if signals.has_readme:
        phase_scores[1] += 0.6
    if signals.has_docs_dir and signals.doc_file_count > 0:
        phase_scores[1] += 0.4

    # Phase 2 (Requirements): Hard to detect automatically, partial credit for docs
    if signals.has_docs_dir and signals.doc_file_count >= 2:
        phase_scores[2] += 0.5

    # Phase 3 (Stack Decision): Has package manifest → stack was chosen
    if signals.has_package_manifest:
        phase_scores[3] += 1.0

    # Phase 4 (Architecture): Has significant code structure → architecture exists
    if signals.source_file_count >= 10:
        phase_scores[4] += 0.7
    elif signals.source_file_count >= 5:
        phase_scores[4] += 0.4

    # Phase 5 (Project Setup): Has manifest + lockfile + linter
    if signals.has_package_manifest:
        phase_scores[5] += 0.4
    if signals.has_lockfile:
        phase_scores[5] += 0.3
    if signals.has_linter_config:
        phase_scores[5] += 0.2
    if signals.has_ci_config:
        phase_scores[5] += 0.1

    # Phase 6 (Build): Has substantial source code and tests
    if signals.source_file_count >= 5 and signals.has_tests:
        phase_scores[6] += 0.8
    elif signals.source_file_count >= 10:
        phase_scores[6] += 0.5
    elif signals.source_file_count >= 3:
        phase_scores[6] += 0.3

    # Phase 7 (Verify): Has CI + tests + linting
    if signals.has_ci_config and signals.has_tests and signals.has_linter_config:
        phase_scores[7] += 0.9
    elif signals.has_ci_config and signals.has_tests:
        phase_scores[7] += 0.6

    # Phase 8 (Deploy): Has deployment configs
    if signals.has_deploy_configs:
        phase_scores[8] += 0.7
    if signals.has_k8s_configs or signals.has_terraform:
        phase_scores[8] += 0.3

    # Phase 9 (Handover): Has tags + mature git history
    if signals.git_has_tags and signals.git_age_days > 30:
        phase_scores[9] += 0.7

    # Phase 10 (Change Requests): Production project with long history
    if signals.has_deploy_configs and signals.git_commit_count > 100 and signals.git_age_days > 60:
        phase_scores[10] += 0.8

    # ── Determine archetype ────────────────────────────────────────────
    if not signals.has_source_code and signals.source_file_count < 3:
        archetype = "greenfield"
        recommended_phase = 0
        confidence = 0.95
    elif signals.has_deploy_configs and signals.git_commit_count > 50:
        archetype = "production"
        recommended_phase = 10
        confidence = min(0.95, phase_scores[10] + 0.3)
    else:
        archetype = "brownfield"
        # Find highest phase with score >= 0.5 (clearly done)
        recommended_phase = 0
        for p_num in range(10, -1, -1):
            if phase_scores[p_num] >= 0.5:
                recommended_phase = p_num
                break
        # Start at the NEXT phase (the one that needs work)
        if recommended_phase < 10:
            recommended_phase = min(recommended_phase + 1, 10)
        confidence = 0.7

    # ── Determine pre-approved phases ──────────────────────────────────
    pre_approved = []
    for p_num in range(recommended_phase):
        if phase_scores[p_num] >= 0.5:
            pre_approved.append(p_num)

    # ── Stack detection ────────────────────────────────────────────────
    detected_stack: Dict[str, str] = {}
    if signals.source_languages:
        primary = max(
            signals.source_languages,
            key=lambda l: sum(1 for _ in [l]),  # placeholder; all equal
        )
        detected_stack["language"] = ", ".join(sorted(signals.source_languages))
    if signals.manifests_found:
        detected_stack["package_manager"] = ", ".join(sorted(signals.manifests_found))
    if signals.test_frameworks:
        detected_stack["test_framework"] = ", ".join(sorted(signals.test_frameworks))
    if signals.ci_systems:
        detected_stack["ci_system"] = ", ".join(sorted(signals.ci_systems))

    # ── Warnings ───────────────────────────────────────────────────────
    warnings: List[str] = []
    recommendations: List[str] = []

    if signals.has_source_code and not signals.has_tests:
        warnings.append("Source code exists but no tests detected. Test coverage is critical.")
        recommendations.append("Add tests before proceeding past Phase 6.")

    if signals.has_source_code and not signals.has_readme:
        warnings.append("No README.md found. Projects need documentation.")
        recommendations.append("Create a README.md describing the project.")

    if signals.has_package_manifest and not signals.has_lockfile:
        warnings.append("Package manifest found without a lockfile. Dependencies are unpinned.")
        recommendations.append("Run 'valdoz audit --fix' to generate a lockfile.")

    if signals.has_env_file and not signals.env_file_gitignored:
        warnings.append("'.env' file found but not in .gitignore. Credentials may leak.")
        recommendations.append("Run 'valdoz audit --fix' to secure the .env file.")

    if signals.has_source_code and not signals.has_ci_config:
        recommendations.append("Add CI/CD configuration for automated testing.")

    if signals.has_source_code and not signals.has_linter_config:
        recommendations.append("Add linter/formatter configuration for code quality.")

    # ── Auto-remediations that init should perform ─────────────────────
    auto_remediations: List[str] = []
    if signals.has_env_file and not signals.env_file_gitignored:
        auto_remediations.append("secure_env_file")
    if signals.has_package_manifest and not signals.has_lockfile:
        auto_remediations.append("generate_lockfile")

    return MaturityAssessment(
        archetype=archetype,
        recommended_phase=recommended_phase,
        confidence=confidence,
        pre_approved_phases=pre_approved,
        warnings=warnings,
        recommendations=recommendations,
        signals=signals,
        detected_stack=detected_stack,
        auto_remediations=auto_remediations,
    )


def scan_and_assess(project_root: Path) -> MaturityAssessment:
    """One-call convenience: scan the project and return the maturity assessment."""
    signals = scan_project(project_root)
    return assess_maturity(signals)
