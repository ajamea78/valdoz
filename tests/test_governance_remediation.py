"""Comprehensive test suite for ValdoZ security hardening, bug remediations, and governance enhancements.

Covers:
- Legacy token bypass elimination
- Full 256-bit HMAC tokens
- Hash-chained audit trail integrity & tamper detection
- Central state.json tamper detection (BUG-03)
- M-of-N quorum approval
- Time-locked phases
- Behavioral budget tracking & anomaly detection
- Semantic diff review
- Intent declaration validation
- 'valdoz explain' executive narrative CLI
- Webhook event dispatching
- Dashboard HTML escaping
- Undeclared imports scanning with tomllib (BUG-06)
- Slice gate real test verification & healing preview
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typer.testing import CliRunner

from valdoz.approval import (
    approve_phase,
    generate_human_token,
    verify_human_token,
    NonInteractiveApprovalError,
    QuorumNotMetError,
    TimeLockViolationError,
)
from valdoz.checks import PYTHON_BUILTIN_MODULES, scan_undeclared_imports
from valdoz.cli import app
from valdoz.dashboard import generate_dashboard_html
from valdoz.healing import HealingContext, run_healing_loop
from valdoz.oversight import (
    check_behavioral_budget,
    declare_phase_intent,
    generate_semantic_diff_summary,
    track_behavioral_action,
    validate_phase_intent,
)
from valdoz.phases import (
    append_approvals_log,
    verify_audit_log_integrity,
)
from valdoz.slices import done_slice, start_slice, save_slice, SliceState, SliceGateConditionError
from valdoz.state import (
    ValdozState,
    load_state,
    save_state,
    verify_phase_integrity,
)
from valdoz.webhooks import emit_webhook_event

runner = CliRunner()


# ── 1. Security & Cryptographic Hardening ──────────────────────────────────

def test_legacy_token_bypass_strictly_rejected():
    """Asserts that unauthenticated legacy tokens cannot bypass human gates."""
    now_ts = int(datetime.now(timezone.utc).timestamp())
    legacy_token = f"valdoz-human-phase-1-{now_ts}"
    assert not verify_human_token(legacy_token, "phase", "1")
    assert not verify_human_token(f"valdoz-human-slice-01-core-{now_ts}", "slice", "01-core")


def test_256_bit_hmac_signatures():
    """Asserts tokens contain full 64-char hex digests (256-bit) and reject truncated signatures."""
    token = generate_human_token("phase", "1")
    parts = token.split(".")
    assert len(parts) == 6
    sig = parts[5]
    assert len(sig) == 64  # Full 256-bit SHA256 hex digest

    assert verify_human_token(token, "phase", "1")

    # A truncated 16-char signature must be rejected
    truncated_token = f"{'.'.join(parts[:5])}.{sig[:16]}"
    assert not verify_human_token(truncated_token, "phase", "1")


# ── 2. Hash-Chained Audit Trail & State Tamper Detection (BUG-03) ────────────

def test_hash_chained_audit_trail_tamper_detection(tmp_path: Path):
    """Verifies that tampering with any line in approvals.log is caught."""
    h1 = append_approvals_log(tmp_path, "Phase 0 (Init) approved.")
    h2 = append_approvals_log(tmp_path, "Phase 1 (Intake) approved.")
    h3 = append_approvals_log(tmp_path, "Phase 2 (Requirements) approved.")

    is_valid, violations = verify_audit_log_integrity(tmp_path)
    assert is_valid
    assert not violations

    # Tamper with middle line in approvals.log
    log_file = tmp_path / ".valdoz" / "approvals.log"
    content = log_file.read_text(encoding="utf-8")
    tampered_content = content.replace("Phase 1 (Intake)", "Phase 1 (Tampered)")
    log_file.write_text(tampered_content, encoding="utf-8")

    is_valid, violations = verify_audit_log_integrity(tmp_path)
    assert not is_valid
    assert any("Entry payload tampering detected" in v or "Hash chain link broken" in v for v in violations)


def test_state_json_tamper_detection(tmp_path: Path):
    """BUG-03: Manually modifying state.json to mark a phase approved is detected."""
    state = ValdozState(project_name="tamper-test", current_phase=1)
    save_state(tmp_path, state)
    append_approvals_log(tmp_path, "Phase 0 (Init) approved by lead at 2026-10-26T10:00:00+00:00. Composite hash: init123... Deliverables hashed: 1.")

    # Required deliverable
    doc = tmp_path / "docs" / "01-intake.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Client Intake Brief\nLegit brief.\n")

    # Manually tamper with state.json: mark phase 1 approved without recording in approvals.log
    state_disk = load_state(tmp_path)
    state_disk.phases["1"].status = "approved"
    state_disk.phases["1"].approval_hash = "forged-hash-12345"
    save_state(tmp_path, state_disk)

    # verify_phase_integrity must detect the forgery
    is_valid, violations = verify_phase_integrity(tmp_path, 1)
    assert not is_valid
    assert any("Tampering detected in state.json" in v for v in violations)


# ── 3. Governance Policies: Quorum & Time-Locks ─────────────────────────────

def test_m_of_n_quorum_approval(tmp_path: Path):
    """Requires M distinct human approval tokens when configured."""
    state = ValdozState(project_name="quorum-test", current_phase=8)
    save_state(tmp_path, state)

    # Deliverable for Phase 8
    doc = tmp_path / "docs" / "08-deploy.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Deploy Guide\nDeployment verified.\n")

    # Configure 2-of-N quorum for Phase 8 in .valdozrc.json
    valdozrc = tmp_path / ".valdozrc.json"
    valdozrc.write_text(json.dumps({
        "governance": {
            "quorum": { "8": 2 }
        }
    }))

    tok1 = generate_human_token("phase", "8", project_root=tmp_path)

    # Single token fails quorum check
    with pytest.raises(QuorumNotMetError, match="requires 2 distinct human approvals"):
        approve_phase(
            tmp_path,
            phase_num=8,
            enforce_tty=True,
            human_token=tok1,
            confirmation_input="deploy",
        )

    # Generating second token
    tok2 = generate_human_token("phase", "8", project_root=tmp_path)

    # Supplying both tokens succeeds
    hashes = approve_phase(
        tmp_path,
        phase_num=8,
        enforce_tty=True,
        human_tokens=[tok1, tok2],
        confirmation_input="deploy",
    )
    assert "docs/08-deploy.md" in hashes
    state_approved = load_state(tmp_path)
    assert state_approved.phases["8"].status == "approved"
    assert len(state_approved.phases["8"].approvals) == 2


def test_time_locked_phase_enforcement(tmp_path: Path):
    """Prevents rushing by enforcing a minimum review dwell time."""
    now_iso = datetime.now(timezone.utc).isoformat()
    state = ValdozState(project_name="timelock-test", current_phase=4)
    state.phases["4"].entered_at = now_iso
    save_state(tmp_path, state)

    # Required deliverables
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "04-architecture.md").write_text("# Architecture\nDetailed plan.\n")
    (docs / "04-plan.md").write_text("# Plan\nMilestones.\n")

    # Configure 10-minute time-lock for Phase 4
    valdozrc = tmp_path / ".valdozrc.json"
    valdozrc.write_text(json.dumps({
        "governance": {
            "time_locks": { "4": 10 }
        }
    }))

    token = generate_human_token("phase", "4", project_root=tmp_path)

    # Attempting instant approval triggers TimeLockViolationError
    with pytest.raises(TimeLockViolationError, match="Time-lock active: Phase 4 requires at least 10m"):
        approve_phase(
            tmp_path,
            phase_num=4,
            enforce_tty=True,
            human_token=token,
            confirmation_input="architecture-and-plan",
        )

    # Emergency bypass allows manual override
    hashes = approve_phase(
        tmp_path,
        phase_num=4,
        enforce_tty=True,
        human_token=token,
        confirmation_input="architecture-and-plan",
        emergency_bypass=True,
    )
    assert "docs/04-architecture.md" in hashes


# ── 4. AI Agent Oversight: Budgets, Diffs & Intents ──────────────────────────

def test_behavioral_budget_tracking(tmp_path: Path):
    """Tracks tool actions and warns if agent exceeds baseline budget."""
    valdozrc = tmp_path / ".valdozrc.json"
    valdozrc.write_text(json.dumps({
        "oversight": {
            "behavioral_budget": { "1": 3 }
        }
    }))

    for i in range(3):
        track_behavioral_action(tmp_path, phase_num=1, action_type="file_write", target=f"file_{i}.txt")
    ok, _ = check_behavioral_budget(tmp_path, phase_num=1)
    assert ok

    # Exceeding budget
    track_behavioral_action(tmp_path, phase_num=1, action_type="file_write", target="file_runaway.txt")
    ok, err = check_behavioral_budget(tmp_path, phase_num=1)
    assert not ok
    assert "Behavioral budget exceeded in Phase 1" in err


def test_semantic_diff_and_intent_declaration(tmp_path: Path):
    """Verifies intent declaration validation and semantic diff summarization."""
    # Intent declaration
    intent_path = declare_phase_intent(
        tmp_path,
        phase_num=6,
        intent_text="Refactoring authentication layer.\nAdding unit tests for token expiration.\nVerifying zero regressions.",
    )
    assert intent_path.exists()
    ok, msg = validate_phase_intent(tmp_path, 6)
    assert ok

    # Semantic diff summary
    diff_text = """--- a/src/auth.py
+++ b/src/auth.py
@@ -10,3 +10,4 @@
 def verify():
+    # added token null check
     return True
"""
    summary = generate_semantic_diff_summary(diff_text, project_root=tmp_path)
    assert summary
    history_file = tmp_path / ".valdoz" / "history" / "semantic_diffs.jsonl"
    assert history_file.exists()
    assert "auth.py" in history_file.read_text()


# ── 5. Developer Experience: valdoz explain, Webhooks & Dashboard ────────────

def test_valdoz_explain_cli(tmp_path: Path, monkeypatch):
    """Tests 'valdoz explain' executive narrative generator."""
    monkeypatch.chdir(tmp_path)
    state = ValdozState(project_name="explain-proj", current_phase=1)
    save_state(tmp_path, state)
    append_approvals_log(tmp_path, "Phase 0 (Init) approved by lead at 2026-10-26T12:00:00+00:00. Composite hash: 1234567890abcdef... Deliverables hashed: 1.")

    export_file = tmp_path / "narrative.md"
    res = runner.invoke(app, ["explain", "-o", str(export_file)])
    assert res.exit_code == 0
    assert export_file.exists()
    content = export_file.read_text()
    assert "# Executive Narrative: explain-proj" in content
    assert "Phase 0: Init" in content


def test_webhook_event_emission(tmp_path: Path):
    """Verifies webhook dispatcher gracefully handles endpoints and invalid schemes."""
    valdozrc = tmp_path / ".valdozrc.json"
    valdozrc.write_text(json.dumps({
        "webhooks": ["ftp://invalid-scheme.com", "http://127.0.0.1:99999/test"]
    }))

    results = emit_webhook_event(tmp_path, "phase.approved", {"phase": 1})
    assert len(results) == 2
    assert results[0]["status"] == "failed"
    assert "Invalid scheme" in results[0]["error"]


def test_dashboard_html_sanitization(tmp_path: Path):
    """Verifies XSS and HTML special characters are escaped in generated dashboard."""
    xss_name = 'Portal <script>alert("xss")</script> & More'
    state = ValdozState(project_name=xss_name, current_phase=0)
    save_state(tmp_path, state)

    html_out = generate_dashboard_html(tmp_path)
    assert '<script>alert("xss")</script>' not in html_out
    assert "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt; &amp; More" in html_out


# ── 6. Imports Scanner (BUG-06) & Slice Gate Real Tests ──────────────────────

def test_pydantic_not_in_builtins_and_tomllib_scanner(tmp_path: Path):
    """BUG-06: Asserts pydantic is not considered a builtin module."""
    assert "pydantic" not in PYTHON_BUILTIN_MODULES

    # Create dummy project with undeclared import
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "worker.py").write_text("import pydantic\nimport requests\n")

    # pyproject.toml with only pydantic declared
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "demo"
dependencies = [
    "pydantic>=2.0.0",
]
""")
    rep = scan_undeclared_imports(tmp_path)
    assert not rep.passed
    assert "requests" in rep.message
    assert "pydantic" not in rep.message  # pydantic is properly recognized as declared


def test_slice_done_fails_on_real_failing_tests(tmp_path: Path):
    """Asserts that done_slice executes real tests and catches failures."""
    slices_dir = tmp_path / "docs" / "slices"
    slices_dir.mkdir(parents=True)
    (slices_dir / "01-test.md").write_text("# Slice 01\n## Summary\nSum\n## Acceptance Criteria\nAC\n## Test Plan\nTP\n## File Manifest\nFM")

    start_slice(tmp_path, "01-test")

    # Create failing test in tests/
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text("def test_fail():\n    assert 1 == 2\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n")

    with pytest.raises(SliceGateConditionError, match="Automated tests failed for slice '01-test'"):
        done_slice(tmp_path, "01-test")


def test_self_healing_preview_mode(tmp_path: Path, monkeypatch):
    """Asserts --preview generates diff without touching files on disk."""
    failing_file = tmp_path / "src" / "calc.py"
    failing_file.parent.mkdir(parents=True)
    failing_file.write_text("def add(a, b):\n    return a - b\n")

    mock_resp = """Root Cause: Subtraction operator used instead of addition.

FILE: src/calc.py
```python
def add(a, b):
    return a + b
```
"""
    monkeypatch.setenv("VALDOZ_HEAL_MOCK_RESPONSE", mock_resp)

    ctx = HealingContext(
        failure_type="slice_gate",
        error_trace="AssertionError in test_calc",
        failing_files=["src/calc.py"],
    )
    report = run_healing_loop(tmp_path, ctx, preview=True)
    assert not report.success
    assert "+    return a + b" in report.patch_diff
    # Verify disk was not modified
    assert failing_file.read_text() == "def add(a, b):\n    return a - b\n"
