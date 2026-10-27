"""ValdoZ Live Generative UI Dashboard Generator.

Creates a self-contained, theme-aware interactive dashboard using
Antigravity's approved Tailwind design system and CSS custom properties.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Optional

from valdoz.phases import (
    PHASE_COMMAND_WHITELISTS,
    PHASE_DELIVERABLES,
    PHASE_NAMES,
)
from valdoz.slices import list_slices
from valdoz.state import find_project_root, load_state


def generate_dashboard_html(project_root: Optional[Path] = None) -> str:
    """Generates an interactive HTML dashboard reflecting live ValdoZ state."""
    root = project_root or find_project_root()
    state = load_state(root)
    curr_phase = state.current_phase
    slices = list_slices(root)

    # Build phase items
    phase_cards = []
    for i in range(11):
        name = PHASE_NAMES.get(i, f"Phase {i}")
        p_state = state.phases.get(str(i))
        status = p_state.status if p_state else "not_started"
        is_curr = (i == curr_phase)

        if is_curr:
            card_cls = "border-[var(--primary)] bg-[var(--primary)]/10 ring-1 ring-[var(--primary)]"
            num_color = "text-[var(--primary)]"
            badge = "● ACTIVE"
        elif status == "approved":
            card_cls = "border-emerald-500/40 bg-emerald-950/20"
            num_color = "text-emerald-400"
            badge = "✓ DONE"
        else:
            card_cls = "border-[var(--border)] bg-[var(--card)] opacity-60"
            num_color = "text-[var(--muted-foreground)]"
            badge = "WAITING"

        phase_cards.append(
            f'<div class="p-3 rounded-lg border text-xs flex flex-col justify-between {card_cls}">'
            f'<div class="flex items-center justify-between mb-1">'
            f'<span class="font-mono font-bold text-xs {num_color}">P{i}</span>'
            f'<span class="text-[11px] uppercase tracking-wider">{badge}</span>'
            f'</div>'
            f'<div class="font-semibold truncate text-white">{html.escape(name)}</div>'
            f'</div>'
        )

    # Build deliverables list for active phase
    active_deliverables = PHASE_DELIVERABLES.get(curr_phase, [])
    deliv_rows = []
    for d in active_deliverables:
        exists = (root / d).exists()
        icon = "✓" if exists else "✗"
        path_color = "text-white" if exists else "text-[var(--muted-foreground)]"
        badge_cls = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" if exists else "bg-amber-500/10 text-amber-400 border border-amber-500/20"
        badge_txt = "READY" if exists else "MISSING"

        deliv_rows.append(
            f'<div class="py-2.5 flex items-center justify-between text-xs">'
            f'<div class="flex items-center gap-2">'
            f'<span class="font-mono text-sm">{icon}</span>'
            f'<span class="font-mono {path_color}">{html.escape(d)}</span>'
            f'</div>'
            f'<span class="px-2 py-0.5 rounded text-[11px] {badge_cls}">{badge_txt}</span>'
            f'</div>'
        )

    deliv_content = "".join(deliv_rows) if deliv_rows else '<div class="text-xs text-[var(--muted-foreground)] py-2">No static deliverable requirements for this phase.</div>'

    # Build slices block
    slices_section = ""
    if curr_phase == 6 or slices:
        slice_cards = []
        for s in slices:
            test_lbl = "✓ Passing" if s.tests_passed else "✗ Not Run"
            slice_cards.append(
                f'<div class="p-3 rounded-lg border border-[var(--border)] bg-zinc-900/40 text-xs space-y-1">'
                f'<div class="flex items-center justify-between font-mono">'
                f'<span class="font-bold text-white">{html.escape(s.slice_id)}</span>'
                f'<span class="uppercase text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">{html.escape(s.status)}</span>'
                f'</div>'
                f'<div class="text-[11px] text-[var(--muted-foreground)]">Tests: {test_lbl}</div>'
                f'</div>'
            )
        slices_content = "".join(slice_cards) if slice_cards else '<div class="text-xs text-[var(--muted-foreground)] col-span-3">No slices registered yet.</div>'
        slices_section = (
            f'<div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 space-y-3">'
            f'<h3 class="text-sm font-semibold text-white tracking-wide uppercase">Phase 6 Build Slices</h3>'
            f'<div class="grid grid-cols-1 md:grid-cols-3 gap-3">{slices_content}</div>'
            f'</div>'
        )

    cards_html = "".join(phase_cards)
    phase_title = html.escape(PHASE_NAMES.get(curr_phase, "Unknown"))
    proj_name = html.escape(state.project_name)
    lang_name = html.escape(state.language).upper()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ValdoZ Protocol Live Dashboard</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --background: 240 10% 4%;
      --foreground: 0 0% 98%;
      --card: 240 10% 7%;
      --card-foreground: 0 0% 98%;
      --border: 240 4% 16%;
      --primary: 217 91% 60%;
      --primary-foreground: 0 0% 100%;
      --muted: 240 4% 16%;
      --muted-foreground: 240 5% 65%;
      --accent: 142 71% 45%;
    }}
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] p-6 font-sans min-h-screen">
  <div class="max-w-5xl mx-auto space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between border-b border-[var(--border)] pb-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="text-2xl font-black tracking-tight text-[var(--primary)]">VALDOZ</span>
          <span class="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">LIVE ENGINE</span>
          <span class="text-xs text-[var(--muted-foreground)]">v3.1.0</span>
        </div>
        <p class="text-xs text-[var(--muted-foreground)] mt-1">Project: <span class="font-mono text-white">{proj_name}</span> &bull; Client Lang: <span class="font-mono">{lang_name}</span></p>
      </div>
      <div class="text-right">
        <span class="text-xs text-[var(--muted-foreground)]">Current Focus</span>
        <div class="text-lg font-bold text-white">Phase {curr_phase}: {phase_title}</div>
      </div>
    </div>

    <!-- Stepper Grid -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
      {cards_html}
    </div>

    <!-- Current Phase Details Card -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-white tracking-wide uppercase">Active Phase Deliverables</h3>
        <span class="text-xs px-2.5 py-1 rounded-full font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">Phase {curr_phase} Checklist</span>
      </div>

      <div class="divide-y divide-[var(--border)]">
        {deliv_content}
      </div>
    </div>

    <!-- Phase 6 Slices -->
    {slices_section}

    <!-- Protocol Guidance -->
    <div class="p-4 rounded-xl border border-blue-500/20 bg-blue-950/20 text-xs text-blue-200 flex items-center justify-between">
      <div>
        <span class="font-bold">Antigravity Integrated Mode Active:</span> All gate checks, audits, and slice operations can be executed directly inside the conversation using ValdoZ MCP tools without terminal switching.
      </div>
    </div>

  </div>
</body>
</html>
"""
