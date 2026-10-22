import json
import pytest
from pathlib import Path
from valdoz.mcp_server import dispatch_tool, VALDOZ_TOOLS
from valdoz.state import ValdozState, save_state

def test_mcp_tools_list():
    names = [t["name"] for t in VALDOZ_TOOLS]
    assert "valdoz_get_status" in names
    assert "valdoz_run_audit" in names
    assert "valdoz_check_gates" in names
    assert "valdoz_slice_ops" in names
    assert "valdoz_request_human_approval" in names
    assert "valdoz_approve_with_human_token" in names

def test_mcp_dispatch_status_and_audit(tmp_path: Path):
    state = ValdozState(project_name="mcp-test", language="en", current_phase=0)
    save_state(tmp_path, state)

    # Status tool
    status = dispatch_tool("valdoz_get_status", {}, tmp_path)
    assert status["project_name"] == "mcp-test"
    assert status["current_phase"] == 0

    # Audit tool
    audit = dispatch_tool("valdoz_run_audit", {"fix": False}, tmp_path)
    assert "passed" in audit
    assert "results" in audit

def test_mcp_human_approval_workflow(tmp_path: Path):
    state = ValdozState(project_name="mcp-test", language="en", current_phase=1)
    save_state(tmp_path, state)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "01-intake.md").write_text("# Intake Brief\nVerified")

    # Request approval token
    req = dispatch_tool("valdoz_request_human_approval", {"phase_num": 1}, tmp_path)
    assert req["phase_num"] == 1
    token = req["human_token"]
    assert token.startswith("valdoz-human-phase-1-")

    # Call approval with token
    appr = dispatch_tool("valdoz_approve_with_human_token", {
        "phase_num": 1,
        "human_token": token,
    }, tmp_path)
    assert appr["status"] == "approved"
    assert "docs/01-intake.md" in appr["deliverable_hashes"]
