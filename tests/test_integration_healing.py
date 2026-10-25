import pytest
from pathlib import Path
from valdoz.integration import generate_ci_workflow, install_ci_workflow

def test_generate_ci_workflow_standard():
    wf = generate_ci_workflow(self_healing=False)
    assert "name: ValdoZ Gate Verification" in wf
    assert "valdoz-gate:" in wf
    assert "self-heal:" not in wf

def test_generate_ci_workflow_self_healing():
    wf = generate_ci_workflow(self_healing=True)
    assert "name: ValdoZ Gate Verification" in wf
    assert "valdoz-gate:" in wf
    assert "self-heal:" in wf
    assert "if: failure()" in wf
    assert "create-pull-request" in wf
    assert "VALDOZ_AI_API_KEY" in wf
    assert "valdoz heal" in wf

def test_install_ci_workflow_with_self_healing(tmp_path: Path):
    path = install_ci_workflow(tmp_path, self_healing=True)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "self-heal:" in content
