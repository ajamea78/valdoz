"""Unit tests for ValdoZ Gate Engine: placeholders, headings, citations, and phase gates."""

import pytest
from pathlib import Path
from valdoz.gates import (
    run_phase_gate_checks,
    scan_placeholders,
    validate_deliverable_headings,
    check_research_citations,
)
from valdoz.logs import pre_log_research_intent
from valdoz.state import ValdozState, save_state


@pytest.fixture
def temp_project(tmp_path: Path):
    state = ValdozState(project_name="gate-test", language="en", current_phase=1)
    save_state(tmp_path, state)
    return tmp_path


def test_placeholder_scanner(tmp_path: Path):
    clean_file = tmp_path / "clean.md"
    clean_file.write_text("# Title\n\nClean verified content here.\n")
    assert len(scan_placeholders(clean_file)) == 0

    dirty_file = tmp_path / "dirty.md"
    dirty_file.write_text("# Title\n\nTODO: write section.\nLorem ipsum dolor sit amet.\n")
    findings = scan_placeholders(dirty_file)
    assert len(findings) == 2
    assert any("TODO" in f for f in findings)
    assert any("Lorem Ipsum" in f for f in findings)


def test_heading_validation_english(tmp_path: Path):
    intake_file = tmp_path / "01-intake.md"
    intake_file.write_text("""# Project Intake
## Client Brief
Quoted verbatim.
## Assumptions
Key assumptions.
## Risks
Identified risks.
## Stakeholders
Team members.
""")
    valid, missing = validate_deliverable_headings(intake_file, lang="en")
    assert valid is True
    assert len(missing) == 0

    # Incomplete file
    bad_file = tmp_path / "01-intake.md"
    bad_file.write_text("# Project Intake\n## Client Brief\nOnly brief.\n")
    valid, missing = validate_deliverable_headings(bad_file, lang="en")
    assert valid is False
    assert "Assumptions" in missing
    assert "Risks" in missing


def test_heading_validation_arabic(tmp_path: Path):
    ar_file = tmp_path / "01-intake.md"
    ar_file.write_text("""# موجز المشروع
## موجز العميل
النص الأصلي من العميل.
## الافتراضات
الافتراضات التقنية.
## المخاطر
المخاطر المتوقعة.
## أصحاب المصلحة
أعضاء الفريق والعميل.
""")
    valid, missing = validate_deliverable_headings(ar_file, lang="ar")
    assert valid is True
    assert len(missing) == 0


def test_research_citations_cross_check(temp_project: Path):
    doc = temp_project / "docs" / "01-intake.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Brief\nReference: https://api.stripe.com/v1/charges for payments.\n")

    # 1. Initially unlogged -> fails
    ok, unlogged = check_research_citations(temp_project, doc)
    assert ok is False
    assert "https://api.stripe.com/v1/charges" in unlogged

    # 2. Pre-log in research subsystem -> passes
    pre_log_research_intent(
        temp_project,
        url="https://api.stripe.com/v1/charges",
        claim="Stripe payment API",
        phase=1,
    )
    ok, unlogged = check_research_citations(temp_project, doc)
    assert ok is True
    assert len(unlogged) == 0


def test_phase_gate_check_runner_pass_and_fail(temp_project: Path):
    intake_doc = temp_project / "docs" / "01-intake.md"
    intake_doc.parent.mkdir(parents=True, exist_ok=True)

    # 1. Missing headings and placeholders -> Gate fails
    intake_doc.write_text("# Intake\nTODO: write everything.\n")
    report = run_phase_gate_checks(temp_project, phase_num=1)
    assert report.passed is False

    # 2. Valid complete deliverable -> Gate passes
    intake_doc.write_text("""# Intake
## Client Brief
Verbatim client brief.
## Assumptions
No legacy migration.
## Risks
External API rate limits.
## Stakeholders
Engineering lead and client product manager.
""")
    report = run_phase_gate_checks(temp_project, phase_num=1)
    assert report.passed is True
