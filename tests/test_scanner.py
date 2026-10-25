import pytest
from pathlib import Path
from valdoz.scanner import (
    scan_project,
    assess_maturity,
    scan_and_assess,
    ProjectSignals,
)

def test_scan_greenfield(tmp_path: Path):
    signals = scan_project(tmp_path)
    assessment = assess_maturity(signals)
    assert assessment.archetype == "greenfield"
    assert assessment.recommended_phase == 0
    assert assessment.confidence >= 0.9

def test_scan_brownfield_in_development(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    for i in range(6):
        (src / f"module_{i}.py").write_text("def hello(): pass")
    
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text("def test_ok(): pass")
    
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'")
    (tmp_path / "uv.lock").write_text("# lock")

    signals = scan_project(tmp_path)
    assert signals.has_source_code
    assert signals.has_tests
    assert signals.has_package_manifest
    assert signals.has_lockfile
    assert "Python" in signals.source_languages

    assessment = assess_maturity(signals)
    assert assessment.archetype == "brownfield"
    # Given manifests, source code, and tests, it should place beyond Phase 0 (e.g. 6 or 7)
    assert assessment.recommended_phase >= 5
    assert 0 in assessment.pre_approved_phases
    assert 3 in assessment.pre_approved_phases

def test_scan_production_project(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    for i in range(12):
        (src / f"app_{i}.ts").write_text("export const x = 1;")
    
    (tmp_path / "package.json").write_text('{"name": "prod-app", "scripts": {"test": "jest"}}')
    (tmp_path / "package-lock.json").write_text('{"name": "prod-app"}')
    (tmp_path / "Dockerfile").write_text("FROM node:18\nCMD ['node']")
    (tmp_path / "docker-compose.yml").write_text("version: '3'")
    
    gh_actions = tmp_path / ".github" / "workflows"
    gh_actions.mkdir(parents=True)
    (gh_actions / "ci.yml").write_text("name: CI")

    signals = scan_project(tmp_path)
    # Mock git commit count & age
    signals.git_commit_count = 120
    signals.git_age_days = 90
    signals.has_git = True

    assessment = assess_maturity(signals)
    assert assessment.archetype == "production"
    assert assessment.recommended_phase == 10
    assert 0 in assessment.pre_approved_phases
    assert 8 in assessment.pre_approved_phases

def test_scan_env_warning(tmp_path: Path):
    (tmp_path / ".env").write_text("API_KEY=secret")
    signals = scan_project(tmp_path)
    assert signals.has_env_file
    assert not signals.env_file_gitignored

    assessment = assess_maturity(signals)
    assert any(".env" in w for w in assessment.warnings)
    assert "secure_env_file" in assessment.auto_remediations


def test_scan_nested_inside_skip_dir_name(tmp_path: Path):
    # If the project root itself is located inside a folder named 'build' or 'env'
    nested_root = tmp_path / "build" / "my_project"
    nested_root.mkdir(parents=True)

    src = nested_root / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello')")

    tests = nested_root / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_it(): pass")

    signals = scan_project(nested_root)
    assert signals.has_source_code
    assert signals.source_file_count == 2
    assert signals.has_tests
    assert signals.test_file_count == 1

