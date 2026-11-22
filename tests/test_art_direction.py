"""Unit tests for Art Direction (Phase 4.5), DESIGN.md Token Registry, and Anti-Slop Juror Gate."""

import pytest
from pathlib import Path

from valdoz.phases import PHASE_DELIVERABLES, PHASE_NAMES
from valdoz.gates import REQUIRED_HEADINGS, run_phase_gate_checks
from valdoz.checks import scan_anti_slop_juror
from valdoz.packs import BUILTIN_PACKS
from valdoz.slices import start_slice, done_slice, SliceGateConditionError
from valdoz.sync import sync_all_runtimes, get_core_agent_rules
from valdoz.state import ValdozState, save_state


@pytest.fixture
def temp_project(tmp_path: Path):
    state = ValdozState(project_name="art-direction-test", current_phase=4, packs=["base", "web-app"])
    save_state(tmp_path, state)
    return tmp_path


def test_phase_4_includes_art_direction_and_design_md():
    delivs = PHASE_DELIVERABLES[4]
    assert "docs/04-architecture.md" in delivs
    assert "docs/04-plan.md" in delivs
    assert "docs/04-art-direction.md" in delivs
    assert "DESIGN.md" in delivs
    assert "Art Direction" in PHASE_NAMES[4]


def test_required_headings_has_art_direction():
    assert "04-art-direction.md" in REQUIRED_HEADINGS
    en_headings = REQUIRED_HEADINGS["04-art-direction.md"]["en"]
    assert "Metaphor & Subject Inventory" in en_headings
    assert "Typographic System" in en_headings
    assert "Atmosphere & Surface Rules" in en_headings
    assert "Hero Artifact Blueprint" in en_headings

    ar_headings = REQUIRED_HEADINGS["04-art-direction.md"]["ar"]
    assert "المجاز ومستودع الموضوع" in ar_headings


def test_phase_4_gate_passes_with_all_deliverables(temp_project: Path):
    docs = temp_project / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    # 1. Architecture
    (docs / "04-architecture.md").write_text("""# Architecture
## Data Model
Specs here.
## API Contracts
Specs here.
## Authentication
Specs here.
## Integration Points
Specs here.
""")

    # 2. Plan
    (docs / "04-plan.md").write_text("""# Plan
## Milestones
Milestone 1.
## Slice Breakdown
Slice 1.
## Dependencies
Dep 1.
""")

    # 3. Art Direction (Phase 4.5)
    (docs / "04-art-direction.md").write_text("""# Art Direction
## Metaphor & Subject Inventory
1. Spatial coordinate grid
2. Capital velocity tracker
3. Hairline brass dials
4. Terminal amber readout
5. Vault door seals
6. Slate foundation blocks
7. Monolithic timestamp headers
8. Kinetic settlement pulses

## Typographic System
Display: Syne 800
UI: Inter 500
Data: JetBrains Mono 400

## Atmosphere & Surface Rules
Canvas: #0B0F17
Surfaces: 1px hairline border with rgba(255,255,255,0.08)
No random pastel badges or 3-identical-card slop.

## Hero Artifact Blueprint
Interactive kinetic visualizer with real-time settlement telemetry.
""")

    # 4. DESIGN.md
    (temp_project / "DESIGN.md").write_text("""# Design Tokens
```css
:root {
  --canvas: #0b0f17;
  --surface: #121824;
  --border: rgba(255, 255, 255, 0.08);
  --accent: #d97706;
}
```
""")

    report = run_phase_gate_checks(temp_project, phase_num=4)
    assert report.passed is True, f"Gate checks failed: {[c.message for c in report.checks if not c.passed]}"


def test_phase_4_gate_fails_when_art_direction_missing(temp_project: Path):
    docs = temp_project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "04-architecture.md").write_text("# Architecture\n## Data Model\nx\n## API Contracts\nx\n## Authentication\nx\n## Integration Points\nx\n")
    (docs / "04-plan.md").write_text("# Plan\n## Milestones\nx\n## Slice Breakdown\nx\n## Dependencies\nx\n")

    report = run_phase_gate_checks(temp_project, phase_num=4)
    assert report.passed is False
    missing_messages = [c.message for c in report.checks if not c.passed]
    assert any("04-art-direction.md" in m or "DESIGN.md" in m for m in missing_messages)


def test_scan_anti_slop_juror_passes_clean_code(temp_project: Path):
    src = temp_project / "src" / "components"
    src.mkdir(parents=True, exist_ok=True)
    component = src / "HeroCard.tsx"
    component.write_text("""
import React from 'react';

export const HeroCard = ({ metric, label }: { metric: number; label: string }) => {
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] p-6 rounded-lg">
      <div className="text-2xl font-mono tabular-nums text-white">
        ${metric.toLocaleString()}
      </div>
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <button className="px-4 py-2 bg-[var(--accent)] text-white rounded active:scale-[0.98] transition-transform">
        Execute
      </button>
    </div>
  );
};
""")
    res = scan_anti_slop_juror(temp_project)
    assert res.passed is True
    assert "Anti-Slop Juror Rubric" in res.name or "Anti-Slop" in res.name


def test_scan_anti_slop_juror_flags_unstyled_tailwind_colors(temp_project: Path):
    src = temp_project / "src" / "components"
    src.mkdir(parents=True, exist_ok=True)
    component = src / "BadCard.tsx"
    component.write_text("""
export const BadCard = () => (
  <div className="bg-blue-500 text-gray-400 p-4">
    Generic slop card
  </div>
);
""")
    res = scan_anti_slop_juror(temp_project)
    assert res.passed is False
    assert "default unstyled Tailwind" in res.message or "palette" in res.message


def test_scan_anti_slop_juror_flags_missing_tabular_nums(temp_project: Path):
    src = temp_project / "src" / "components"
    src.mkdir(parents=True, exist_ok=True)
    component = src / "MetricsCard.tsx"
    component.write_text("""
export const MetricsCard = () => (
  <div className="bg-[var(--surface)] p-4">
    <div className="text-3xl font-bold">
      $1,234,567.89
    </div>
  </div>
);
""")
    res = scan_anti_slop_juror(temp_project)
    assert res.passed is False
    assert "tabular-nums" in res.message or "tabular" in res.message


def test_scan_anti_slop_juror_flags_button_without_active_scale(temp_project: Path):
    src = temp_project / "src" / "components"
    src.mkdir(parents=True, exist_ok=True)
    component = src / "DeadButton.tsx"
    component.write_text("""
export const DeadButton = () => (
  <button className="px-4 py-2 bg-[var(--surface)] hover:bg-[var(--surface-hover)]">
    Click Me
  </button>
);
""")
    res = scan_anti_slop_juror(temp_project)
    assert res.passed is False
    assert "active:scale-" in res.message or "physical interaction" in res.message


def test_builtin_packs_include_anti_slop():
    web_pack = BUILTIN_PACKS["web-app"]
    check_ids = [c.id for c in web_pack.checks]
    assert "anti-slop-gate" in check_ids


def test_sync_generates_directive_14_and_art_direction_rule(temp_project: Path):
    rules = get_core_agent_rules()
    assert "14. Art Direction & Anti-Slop Aesthetic Discipline" in rules
    assert "docs/04-art-direction.md" in rules
    assert "DESIGN.md" in rules
    assert "active:scale-[0.98]" in rules

    outputs = sync_all_runtimes(temp_project, dry_run=False)
    rule_file = temp_project / ".agent" / "rules" / "05-art-direction.md"
    assert rule_file.exists()
    content = rule_file.read_text(encoding="utf-8")
    assert "Phase 4.5: Art Direction" in content
    assert "Anti-Slop Juror Rubric" in content
