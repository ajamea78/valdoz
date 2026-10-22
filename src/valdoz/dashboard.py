"""ValdoZ Live Generative UI Dashboard Generator.

Creates a self-contained, theme-aware interactive dashboard using
Antigravity's approved Tailwind design system and CSS custom properties.
"""

from __future__ import annotations

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

    # Build phase items JSON
    phase_data = []
    for i in range(11):
        name = PHASE_NAMES.get(i, f"Phase {i}")
        p_state = state.phases.get(str(i))
        status = p_state.status if p_state else "not_started"
        deliverables = PHASE_DELIVERABLES.get(i, [])
        deliv_info = []
        for d in deliverables:
            deliv_info.append({
                "path": d,
                "exists": (root / d).exists(),
            })
        phase_data.append({
            "number": i,
            "name": name,
            "status": status,
            "is_current": (i == curr_phase),
            "deliverables": deliv_info,
            "whitelist": PHASE_COMMAND_WHITELISTS.get(i, []),
        })

    slice_data = [
        {
            "id": s.slice_id,
            "status": s.status,
            "tests_passed": s.tests_passed,
            "coverage_delta": s.coverage_delta,
        }
        for s in slices
    ]

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
          <span class="text-xs text-[var(--muted-foreground)]">v3.0.0</span>
        </div>
        <p class="text-xs text-[var(--muted-foreground)] mt-1">Project: <span class="font-mono text-white">{state.project_name}</span> &bull; Client Lang: <span class="uppercase font-mono">{state.language}</span></p>
      </div>
      <div class="text-right">
        <span class="text-xs text-[var(--muted-foreground)]">Current Focus</span>
        <div class="text-lg font-bold text-white">Phase {curr_phase}: {PHASE_NAMES.get(curr_phase, 'Unknown')}</div>
      </div>
    </div>

    <!-- Stepper Grid -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
      {"".join(f'''
      <div class="p-3 rounded-lg border text-xs flex flex-col justify-between {
          "border-[var(--primary)] bg-[var(--primary)]/10 ring-1 ring-[var(--primary)]" if p["is_current"]
          else "border-emerald-500/40 bg-emerald-950/20" if p["status"] == "approved"
          else "border-[var(--border)] bg-[var(--card)] opacity-60"
      }">
        <div class="flex items-center justify-between mb-1">
          <span class="font-mono font-bold text-xs {'text-[var(--primary)]' if p['is_current'] else 'text-emerald-400' if p['status'] == 'approved' else 'text-[var(--muted-foreground)]'}">P{p['number']}</span>
          <span class="text-[11px] uppercase tracking-wider">{
              '● ACTIVE' if p['is_current']
              else '✓ DONE' if p['status'] == 'approved'
              else 'WAITING'
          }</span>
        </div>
        <div class="font-semibold truncate text-white">{p['name']}</div>
      </div>
      ''' for p in phase_data)}
    </div>

    <!-- Current Phase Details Card -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-white tracking-wide uppercase">Active Phase Deliverables</h3>
        <span class="text-xs px-2.5 py-1 rounded-full font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">Phase {curr_phase} Checklist</span>
      </div>

      <div class="divide-y divide-[var(--border)]">
        {"".join(f'''
        <div class="py-2.5 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2">
            <span class="font-mono text-sm">{ "✓" if d["exists"] else "✗" }</span>
            <span class="font-mono { "text-white" if d["exists"] else "text-[var(--muted-foreground)]" }">{d["path"]}</span>
          </div>
          <span class="px-2 py-0.5 rounded text-[11px] {
              "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" if d["exists"]
              else "bg-amber-500/10 text-amber-400 border border-amber-500/20"
          }">{ "READY" if d["exists"] else "MISSING" }</span>
        </div>
        ''' for d in phase_data[curr_phase]["deliverables"]) or '<div class="text-xs text-[var(--muted-foreground)] py-2">No static deliverable requirements for this phase.</div>'}
      </div>
    </div>

    <!-- Phase 6 Slices (if any) -->
    {f'''
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 space-y-3">
      <h3 class="text-sm font-semibold text-white tracking-wide uppercase">Phase 6 Build Slices</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        {"".join(f"""
        <div class="p-3 rounded-lg border border-[var(--border)] bg-zinc-900/40 text-xs space-y-1">
          <div class="flex items-center justify-between font-mono">
            <span class="font-bold text-white">{s["id"]}</span>
            <span class="uppercase text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">{s["status"]}</span>
          </div>
          <div class="text-[11px] text-[var(--muted-foreground)]">Tests: {'✓ Passing' if s['tests_passed'] else '✗ Not Run'}</div>
        </div>
        """ for s in slice_data) or '<div class="text-xs text-[var(--muted-foreground)] col-span-3">No slices registered yet.</div>'}
      </div>
    </div>
    ''' if curr_phase == 6 or slice_data else ''}

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
