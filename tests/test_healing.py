import os
import pytest
from pathlib import Path
from valdoz.healing import (
    HealingContext,
    HealingReport,
    collect_failure_context,
    build_diagnosis_prompt,
    parse_ai_patch_response,
    apply_patch,
    run_healing_loop,
)

def test_collect_failure_context(tmp_path: Path):
    doc = tmp_path / "src" / "math_app.py"
    doc.parent.mkdir()
    doc.write_text("def add(a, b): return a - b")

    error = f"AssertionError: in {doc}: add(1, 2) != 3"
    ctx = collect_failure_context(tmp_path, failure_type="slice_test", error_output=error)

    assert ctx.failure_type == "slice_test"
    assert "src/math_app.py" in ctx.failing_files
    assert "AssertionError" in ctx.error_trace

def test_build_diagnosis_prompt():
    ctx = HealingContext(
        failure_type="audit",
        error_trace="Found hardcoded secret in config.py",
        failing_files=["config.py"],
    )
    prompt = build_diagnosis_prompt(ctx)
    assert "ValdoZ Protocol Autonomous Self-Healing Engine" in prompt
    assert "Found hardcoded secret" in prompt

def test_parse_and_apply_patch(tmp_path: Path):
    ai_output = """
Root Cause: The function was subtracting instead of adding.

FILE: src/math_app.py
```python
def add(a, b):
    return a + b
```
"""
    patches = parse_ai_patch_response(ai_output)
    assert "src/math_app.py" in patches
    assert "return a + b" in patches["src/math_app.py"]

    applied = apply_patch(tmp_path, patches)
    assert "src/math_app.py" in applied
    assert (tmp_path / "src" / "math_app.py").read_text() == "def add(a, b):\n    return a + b\n"

def test_run_healing_loop_with_mock_llm(tmp_path: Path, monkeypatch):
    from valdoz.state import ValdozState, save_state
    state = ValdozState(project_name="healing-test", current_phase=1)
    save_state(tmp_path, state)

    target_file = tmp_path / "docs" / "01-intake.md"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("# Client Brief\nTODO: write brief\n")

    mock_llm_response = """
Root Cause: Found placeholder TODO in deliverable.

FILE: docs/01-intake.md
```markdown
# Client Brief
Client requests an e-commerce platform.
## Assumptions
Standard traffic assumptions.
## Risks
Payment gateway latency.
## Stakeholders
Product Manager, Lead Architect.
```
"""
    monkeypatch.setenv("VALDOZ_HEAL_MOCK_RESPONSE", mock_llm_response)

    ctx = HealingContext(
        failure_type="gate_check",
        error_trace="Placeholder TODO found in docs/01-intake.md",
        phase_num=1,
    )

    report = run_healing_loop(tmp_path, ctx, max_retries=2)
    assert "docs/01-intake.md" in report.applied_files
    assert report.attempt_count >= 1
    assert "TODO" not in target_file.read_text()


def test_apply_patch_prevents_directory_traversal(tmp_path: Path):
    patches = {
        "../../outside.txt": "evil content",
        "nested/../../another_outside.txt": "evil content",
        "src/valid.py": "x = 1\n",
    }
    applied = apply_patch(tmp_path, patches)
    assert "src/valid.py" in applied
    assert len(applied) == 1
    assert not (tmp_path.parent / "outside.txt").exists()
    assert (tmp_path / "src" / "valid.py").read_text() == "x = 1\n"


def test_verify_after_patch_ci(tmp_path: Path):
    from valdoz.healing import verify_after_patch
    from valdoz.state import ValdozState, save_state
    state = ValdozState(project_name="ci-test", current_phase=0)
    save_state(tmp_path, state)

    ctx = HealingContext(failure_type="ci", error_trace="CI failure")
    # State exists, Phase 0 has no deliverables required -> passes audit & gate
    assert verify_after_patch(tmp_path, ctx) is True

