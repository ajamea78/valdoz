"""ValdoZ Stdio Model Context Protocol (MCP) Server.

Enables native, in-Antigravity discovery and tool execution without
terminal switching.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from valdoz.checks import run_valdoz_audit
from valdoz.gates import run_phase_gate_checks
from valdoz.phases import PHASE_COMMAND_WHITELISTS, PHASE_NAMES, get_required_deliverables
from valdoz.slices import (
    approve_slice,
    done_slice,
    list_slices,
    load_slice,
    start_slice,
)
from valdoz.state import find_project_root, load_state


# ── MCP Tool Definitions ───────────────────────────────────────────────────

VALDOZ_TOOLS = [
    {
        "name": "valdoz_get_status",
        "description": "Get current ValdoZ protocol status, active phase, required deliverables, and whitelist.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "valdoz_run_audit",
        "description": "Run universal code hygiene audit across the repo (secrets, lockfiles, imports, semgrep SAST) and optionally auto-remediate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fix": {
                    "type": "boolean",
                    "description": "Automatically remediate detected issues (e.g. .env protection, lockfile generation).",
                    "default": False,
                },
                "strict": {
                    "type": "boolean",
                    "description": "Treat warnings as blocking failures.",
                    "default": False,
                },
                "semgrep": {
                    "type": "boolean",
                    "description": "Run Semgrep deterministic AST Static Application Security Testing (SAST).",
                    "default": False,
                },
                "verify_packages": {
                    "type": "boolean",
                    "description": "Query PyPI/npm live registries to detect AI-hallucinated and slopsquatted dependencies.",
                    "default": False,
                },
                "licenses": {
                    "type": "boolean",
                    "description": "Audit dependency licenses and check copyleft compliance.",
                    "default": False,
                },
                "contract": {
                    "type": "boolean",
                    "description": "Validate OpenAPI contract spec and detect route/schema drift.",
                    "default": False,
                },
                "containers": {
                    "type": "boolean",
                    "description": "Audit Dockerfile and container compose infrastructure security hardening.",
                    "default": False,
                },
            },
        },
    },
    {
        "name": "valdoz_check_gates",
        "description": "Verify deliverables, required headings, and absence of placeholders for current phase.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "phase_num": {
                    "type": "integer",
                    "description": "Phase number to check (defaults to active phase).",
                },
            },
        },
    },
    {
        "name": "valdoz_slice_ops",
        "description": "Manage Phase 6 TDD build slices (list, start, done, approve).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "start", "done", "approve"],
                    "description": "Action to perform on the slice.",
                },
                "slice_id": {
                    "type": "string",
                    "description": "Slice identifier, e.g. '01-auth'.",
                },
                "human_token": {
                    "type": "string",
                    "description": "Required when action is 'approve': human confirmation token from in-chat modal.",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "valdoz_request_human_approval",
        "description": "Generate an approval payload with required deliverable verification and an in-chat human confirmation token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "phase_num": {
                    "type": "integer",
                    "description": "Phase number to request approval for.",
                },
            },
        },
    },
    {
        "name": "valdoz_approve_with_human_token",
        "description": "Approve a phase using an explicit human confirmation token generated from user interaction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "phase_num": {
                    "type": "integer",
                    "description": "Phase number to approve.",
                },
                "human_token": {
                    "type": "string",
                    "description": "Human verification token.",
                },
                "confirmation": {
                    "type": "string",
                    "description": "Confirmation string typed/selected by human.",
                },
            },
            "required": ["phase_num", "human_token"],
        },
    },
    {
        "name": "valdoz_heal",
        "description": "Autonomous AI diagnosis and remediation for failed gates, audits, or Phase 6 slices.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["gate", "audit", "slice", "ci"],
                    "description": "Failure type to heal.",
                },
                "slice_id": {
                    "type": "string",
                    "description": "Slice identifier if healing a slice (e.g., '01-auth').",
                },
                "retries": {
                    "type": "integer",
                    "description": "Max remediation attempts.",
                    "default": 3,
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "valdoz_auth_status",
        "description": "Inspect project-scoped credential vault health, permissions, git helper isolation, and masked tokens.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "valdoz_auth_setup",
        "description": "Configure an isolated, project-scoped Git credential store in .valdoz/.git-credentials.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "GitHub/Git username for this project.",
                },
                "token": {
                    "type": "string",
                    "description": "Personal Access Token for this project.",
                },
                "host": {
                    "type": "string",
                    "description": "Git host, default 'github.com'.",
                    "default": "github.com",
                },
            },
            "required": ["username", "token"],
        },
    },
]


# ── MCP Tool Implementations ───────────────────────────────────────────────

def handle_get_status(root: Path) -> Dict[str, Any]:
    state = load_state(root)
    curr = state.current_phase
    phase_state = state.phases.get(str(curr))
    deliverables = get_required_deliverables(curr)

    deliv_status = []
    for d in deliverables:
        exists = (root / d).exists()
        deliv_status.append({"path": d, "exists": exists})

    return {
        "project_name": state.project_name,
        "language": state.language,
        "current_phase": curr,
        "phase_name": PHASE_NAMES.get(curr, "Unknown"),
        "status": phase_state.status if phase_state else "unknown",
        "deliverables": deliv_status,
        "whitelist": PHASE_COMMAND_WHITELISTS.get(curr, []),
        "packs": state.packs,
    }


def handle_run_audit(
    root: Path,
    fix: bool = False,
    strict: bool = False,
    semgrep: bool = False,
    verify_packages: bool = False,
    licenses: bool = False,
    contract: bool = False,
    containers: bool = False,
) -> Dict[str, Any]:
    report = run_valdoz_audit(
        root,
        fix=fix,
        strict=strict,
        semgrep=semgrep,
        verify_packages=verify_packages,
        licenses=licenses,
        contract=contract,
        containers=containers,
    )
    blocking_cnt = sum(1 for c in report.checks if c.severity == "blocking" and not c.passed)
    warning_cnt = sum(1 for c in report.checks if c.severity == "warning" and not c.passed)
    return {
        "passed": report.passed,
        "blocking_count": blocking_cnt,
        "warning_count": warning_cnt,
        "fixes_applied": report.fixes_applied,
        "results": [
            {
                "id": c.id,
                "passed": c.passed,
                "message": c.message,
                "severity": c.severity,
            }
            for c in report.checks
        ],
    }


def handle_check_gates(root: Path, phase_num: Optional[int] = None) -> Dict[str, Any]:
    report = run_phase_gate_checks(root, phase_num=phase_num)
    return {
        "passed": report.passed,
        "phase_num": report.phase,
        "results": [
            {
                "id": c.id,
                "passed": c.passed,
                "message": c.message,
                "severity": c.severity,
            }
            for c in report.checks
        ],
    }


def handle_slice_ops(
    root: Path,
    action: str,
    slice_id: Optional[str] = None,
    human_token: Optional[str] = None,
) -> Dict[str, Any]:
    if action == "list":
        slices = list_slices(root)
        return {
            "slices": [
                {
                    "slice_id": s.slice_id,
                    "status": s.status,
                    "spec_path": s.spec_path,
                    "tests_passed": s.tests_passed,
                }
                for s in slices
            ]
        }
    if not slice_id:
        return {"error": "slice_id is required for action: " + action}

    if action == "start":
        res = start_slice(root, slice_id)
        return {"message": f"Slice {slice_id} started.", "status": res.status}
    elif action == "done":
        res = done_slice(root, slice_id)
        return {"message": f"Slice {slice_id} completed and gated.", "status": res.status}
    elif action == "approve":
        if not human_token:
            return {"error": "human_token is required to approve slice."}
        res = approve_slice(root, slice_id, human_token=human_token, enforce_tty=False)
        return {"message": f"Slice {slice_id} approved.", "status": res.status}

    return {"error": f"Unknown action: {action}"}


def handle_request_human_approval(root: Path, phase_num: Optional[int] = None) -> Dict[str, Any]:
    from valdoz.approval import generate_human_token

    state = load_state(root)
    target = phase_num if phase_num is not None else state.current_phase
    phase_name = PHASE_NAMES.get(target, f"Phase {target}")
    token = generate_human_token("phase", str(target), project_root=root)

    return {
        "phase_num": target,
        "phase_name": phase_name,
        "human_token": token,
        "instructions": (
            f"To approve Phase {target} ({phase_name}), prompt the human user with an interactive "
            f"confirmation in Antigravity chat, then call 'valdoz_approve_with_human_token'."
        ),
    }


def handle_approve_with_token(
    root: Path,
    phase_num: int,
    human_token: str,
    confirmation: Optional[str] = None,
) -> Dict[str, Any]:
    from valdoz.approval import approve_phase

    hashes = approve_phase(
        root,
        phase_num=phase_num,
        enforce_tty=False,
        human_token=human_token,
        confirmation_input=confirmation,
    )
    return {
        "status": "approved",
        "phase_num": phase_num,
        "deliverable_hashes": hashes,
    }


def handle_heal_tool(
    root: Path,
    target: str,
    slice_id: Optional[str] = None,
    retries: int = 3,
) -> Dict[str, Any]:
    from valdoz.healing import collect_failure_context, run_healing_loop
    error_output = ""
    if target not in ("gate", "audit", "slice", "ci"):
        return {"status": "error", "error": f"Invalid target '{target}'. Must be 'gate', 'audit', 'slice', or 'ci'."}

    if target == "audit":
        from valdoz.checks import run_valdoz_audit
        rep = run_valdoz_audit(root, strict=True)
        if rep.passed:
            return {"status": "skipped", "message": "Audit is already passing."}
        error_output = "\n".join(f"[{c.id}] {c.name}: {c.message}" for c in rep.checks if not c.passed)
    elif target == "gate":
        from valdoz.gates import run_phase_gate_checks
        rep = run_phase_gate_checks(root)
        if rep.passed:
            return {"status": "skipped", "message": "Gate is already passing."}
        error_output = "\n".join(f"[{c.id}] {c.name}: {c.message}" for c in rep.checks if not c.passed)
    elif target == "slice":
        if not slice_id:
            return {"status": "error", "error": "slice_id is required when healing a slice."}
        error_output = f"Slice {slice_id} verification failed."
    elif target == "ci":
        ci_log = root / ".valdoz" / "ci-logs" / "failure.txt"
        if ci_log.exists():
            error_output = ci_log.read_text(encoding="utf-8", errors="replace")
        else:
            from valdoz.checks import run_valdoz_audit
            from valdoz.gates import run_phase_gate_checks
            audit_rep = run_valdoz_audit(root, strict=True)
            gate_rep = run_phase_gate_checks(root)
            errors = []
            if not audit_rep.passed:
                errors.extend(f"[Audit] [{c.id}] {c.name}: {c.message}" for c in audit_rep.checks if not c.passed)
            if not gate_rep.passed:
                errors.extend(f"[Gate] [{c.id}] {c.name}: {c.message}" for c in gate_rep.checks if not c.passed)
            if not errors:
                return {"status": "skipped", "message": "CI checks are already passing."}
            error_output = "\n".join(errors)

    ctx = collect_failure_context(
        root,
        failure_type="audit" if target == "audit" else ("ci" if target == "ci" else f"{target}_check"),
        error_output=error_output,
        slice_id=slice_id,
    )
    report = run_healing_loop(root, ctx, max_retries=retries)
    return {
        "success": report.success,
        "attempts": report.attempt_count,
        "root_cause": report.root_cause,
        "applied_files": report.applied_files,
        "summary": report.human_review_summary,
    }


# ── MCP Dispatcher ─────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, arguments: Dict[str, Any], root: Path) -> Dict[str, Any]:
    if tool_name == "valdoz_get_status":
        return handle_get_status(root)
    elif tool_name == "valdoz_run_audit":
        return handle_run_audit(
            root,
            fix=arguments.get("fix", False),
            strict=arguments.get("strict", False),
            semgrep=arguments.get("semgrep", False),
            verify_packages=arguments.get("verify_packages", False),
            licenses=arguments.get("licenses", False),
            contract=arguments.get("contract", False),
            containers=arguments.get("containers", False),
        )
    elif tool_name == "valdoz_check_gates":
        return handle_check_gates(root, phase_num=arguments.get("phase_num"))
    elif tool_name == "valdoz_slice_ops":
        return handle_slice_ops(
            root,
            action=arguments.get("action", "list"),
            slice_id=arguments.get("slice_id"),
            human_token=arguments.get("human_token"),
        )
    elif tool_name == "valdoz_request_human_approval":
        return handle_request_human_approval(root, phase_num=arguments.get("phase_num"))
    elif tool_name == "valdoz_approve_with_human_token":
        return handle_approve_with_token(
            root,
            phase_num=arguments["phase_num"],
            human_token=arguments["human_token"],
            confirmation=arguments.get("confirmation"),
        )
    elif tool_name == "valdoz_heal":
        return handle_heal_tool(
            root,
            target=arguments.get("target", "gate"),
            slice_id=arguments.get("slice_id"),
            retries=arguments.get("retries", 3),
        )
    elif tool_name == "valdoz_auth_status":
        from valdoz.auth import get_project_vault_status
        return get_project_vault_status(root)
    elif tool_name == "valdoz_auth_setup":
        from valdoz.auth import setup_project_vault
        username = arguments["username"]
        token = arguments["token"]
        host = arguments.get("host", "github.com")
        vault_path = setup_project_vault(root, username=username, token=token, host=host)
        return {
            "status": "success",
            "message": f"Project credential vault configured at {vault_path}",
            "vault_path": str(vault_path),
        }
    return {"error": f"Unknown tool: {tool_name}"}


def run_stdio_server(project_root: Optional[Path] = None):
    """Runs standard stdio MCP protocol loop."""
    root = project_root or find_project_root()

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "valdoz-mcp", "version": "3.0.0"},
                },
            }
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": VALDOZ_TOOLS},
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                res = dispatch_tool(tool_name, tool_args, root)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                    },
                }
            except Exception as e:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Error: {e}"}],
                    },
                }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
