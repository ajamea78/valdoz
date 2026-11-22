"""Unit tests for Directive 12 Hardening and Mechanical Pre-Commit Slice Guard (The Dania Guard)."""

import json
import pytest
import subprocess
from pathlib import Path

from valdoz.integration import generate_pre_commit_hook
from valdoz.checks import scan_slice_integrity
from valdoz.packs import BUILTIN_PACKS
from valdoz.slices import start_slice, done_slice
from valdoz.sync import get_core_agent_rules
from valdoz.state import ValdozState, save_state


@pytest.fixture
def temp_project(tmp_path: Path):
    state = ValdozState(project_name="slice-guard-test", current_phase=6, packs=["base"])
    save_state(tmp_path, state)
    return tmp_path


def test_core_agent_rules_has_hardened_directive_12():
    rules = get_core_agent_rules()
    assert "12. Autonomous Conversational Governance & Mechanical State Machine Execution" in rules
    assert "valdoz slice start" in rules
    assert "valdoz slice done" in rules
    assert "Verbal compliance without literal state machine execution is a Protocol Breach" in rules


def test_pre_commit_hook_includes_slice_guard_script():
    hook_script = generate_pre_commit_hook()
    assert "ValdoZ Slice Protection Error" in hook_script
    assert "valdoz slice start" in hook_script
    assert ".valdoz/slices" in hook_script


def test_scan_slice_integrity_passes_when_slice_exists(temp_project: Path):
    docs_slices = temp_project / "docs" / "slices"
    docs_slices.mkdir(parents=True, exist_ok=True)
    spec_file = docs_slices / "01-core.md"
    spec_file.write_text("""# Slice 01: Core
## Summary
Core logic.
## Acceptance Criteria
- AC1
## Test Plan
- TP1
## File Manifest
- src/core.py
""")

    start_slice(temp_project, "01-core")

    # Code exists in src/
    src = temp_project / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "core.py").write_text("def hello(): return 'world'\n")

    res = scan_slice_integrity(temp_project)
    assert res.passed is True
    assert "Active tracked slice(s) found" in res.message or "integrity verified" in res.message


def test_scan_slice_integrity_flags_un_sliced_code_in_phase_6(temp_project: Path):
    # In Phase 6, code exists in src/ but NO slice was ever started in .valdoz/slices/
    src = temp_project / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "feature.py").write_text("def feature(): pass\n")

    res = scan_slice_integrity(temp_project)
    assert res.passed is False
    assert "No tracked slices found in .valdoz/slices/" in res.message
    assert "valdoz slice start" in res.message


def test_builtin_base_pack_includes_slice_integrity_guard():
    base_pack = BUILTIN_PACKS["base"]
    check_ids = [c.id for c in base_pack.checks]
    assert "slice-integrity-guard" in check_ids
