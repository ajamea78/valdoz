"""ValdoZ AI Agent Oversight and Anomaly Detection Engine.

Provides behavioral budget limits, pre-patch semantic diff summaries,
and phase intent declaration tracking.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BUDGETS = {
    0: 15,   # Init
    1: 20,   # Intake
    2: 20,   # Requirements
    3: 20,   # Stack Decision
    4: 25,   # Architecture and Plan
    5: 80,   # Project Setup
    6: 100,  # Build slices (hardened default)
    7: 60,   # Verify
    8: 40,   # Deploy
    9: 30,   # Handover
    10: 100, # Changes
}

DEFAULT_TOOL_CALL_BUDGETS = {
    0: 30,
    1: 40,
    2: 40,
    3: 40,
    4: 50,
    5: 160,
    6: 200,
    7: 120,
    8: 80,
    9: 60,
    10: 200,
}


def get_telemetry_file(project_root: Path) -> Path:
    p = project_root / ".valdoz" / "sessions" / "telemetry.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_telemetry(project_root: Path) -> Dict[str, Any]:
    p = get_telemetry_file(project_root)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"phases": {}}


def save_telemetry(project_root: Path, data: Dict[str, Any]) -> None:
    p = get_telemetry_file(project_root)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def track_behavioral_action(
    project_root: Path,
    phase_num: int,
    action_type: str = "file_write",
    target: str = "",
) -> int:
    """Records an agent action against the phase behavioral budget and returns current count."""
    data = load_telemetry(project_root)
    p_key = str(phase_num)
    if p_key not in data["phases"]:
        data["phases"][p_key] = {"file_writes": 0, "tool_calls": 0, "actions": []}

    phase_data = data["phases"][p_key]
    if action_type == "file_write":
        phase_data["file_writes"] += 1
    else:
        phase_data["tool_calls"] += 1

    phase_data["actions"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": action_type,
        "target": target,
    })
    # Keep last 50 actions to preserve disk
    phase_data["actions"] = phase_data["actions"][-50:]
    save_telemetry(project_root, data)
    return phase_data.get(f"{action_type}s", 0)


def check_behavioral_budget(project_root: Path, phase_num: int) -> Tuple[bool, Optional[str]]:
    """Checks whether the agent has exceeded the allocated operation budget for the phase."""
    from valdoz.packs import load_valdozrc
    valdozrc = load_valdozrc(project_root)
    custom_budgets = valdozrc.get("oversight", {}).get("behavioral_budget", {})
    write_limit = custom_budgets.get(
        f"phase_{phase_num}_file_writes",
        custom_budgets.get(str(phase_num), DEFAULT_BUDGETS.get(phase_num, 100)),
    )
    tool_limit = custom_budgets.get(
        f"phase_{phase_num}_tool_calls",
        DEFAULT_TOOL_CALL_BUDGETS.get(phase_num, 200),
    )

    data = load_telemetry(project_root)
    p_key = str(phase_num)
    phase_stats = data.get("phases", {}).get(p_key, {})
    writes = phase_stats.get("file_writes", 0)
    tool_calls = phase_stats.get("tool_calls", 0)

    if writes > write_limit:
        return False, f"Behavioral budget exceeded in Phase {phase_num}: {writes} file writes executed (threshold: {write_limit})."
    if tool_calls > tool_limit:
        return False, f"Behavioral budget exceeded in Phase {phase_num}: {tool_calls} tool calls executed (threshold: {tool_limit})."
    return True, None


def generate_semantic_diff_summary(
    diff_text: str,
    project_root: Optional[Path] = None,
    model_config: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates a plain-English, bulleted summary of code modifications."""
    if not diff_text or not diff_text.strip():
        return "No changes detected in diff."

    prompt = (
        "Summarize the following code changes in 3-5 concise, technical bullet points:\n\n"
        f"```diff\n{diff_text[:4000]}\n```\n\n"
        "Output ONLY the bulleted points."
    )

    from valdoz.healing import mock_or_call_ai
    resp = mock_or_call_ai(prompt, model_config)

    # If mock or no LLM configured, produce a structured fallback from file headers
    if "AI remediation endpoint not configured" in resp or "Manual intervention required" in resp:
        files = re.findall(r"(?:---|\+\+\+)\s+[ab]/(.+)", diff_text)
        unique_files = sorted(set(files))
        if unique_files:
            summary = "\n".join(f"- Modified {f}" for f in unique_files)
        else:
            summary = "- Applied automated code patch."
    else:
        summary = resp.strip()

    # Log to history with secret redaction
    if project_root:
        from valdoz.healing import redact_secrets_in_text
        history_file = project_root / ".valdoz" / "history" / "semantic_diffs.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "diff_snippet": redact_secrets_in_text(diff_text[:1000]),
        }
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    return summary


def declare_phase_intent(project_root: Path, phase_num: int, intent_text: str) -> Path:
    """Writes an agent intent declaration before starting phase work."""
    intent_file = project_root / ".valdoz" / "intents" / f"phase-{phase_num}.md"
    intent_file.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    content = f"# Phase {phase_num} Intent Declaration\nDeclared at: {ts}\n\n{intent_text.strip()}\n"
    intent_file.write_text(content, encoding="utf-8")
    return intent_file


def validate_phase_intent(project_root: Path, phase_num: int) -> Tuple[bool, str]:
    """Verifies that an intent declaration exists and contains meaningful content."""
    intent_file = project_root / ".valdoz" / "intents" / f"phase-{phase_num}.md"
    if not intent_file.exists():
        return False, f"Missing intent declaration at .valdoz/intents/phase-{phase_num}.md"
    text = intent_file.read_text(encoding="utf-8").strip()
    if len(text.splitlines()) < 3 or len(text) < 30:
        return False, f"Intent declaration at .valdoz/intents/phase-{phase_num}.md is empty or incomplete."
    return True, "Intent declared and verified."
