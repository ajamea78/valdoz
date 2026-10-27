"""ValdoZ Protocol Delivery Discipline & AI Governance Engine.

Provides cryptographic phase gating, human approval locks, hash-chained audit logging,
and autonomous delivery guardrails for AI pair programming sessions.
"""

from valdoz.approval import (
    ApprovalError,
    MissingDeliverableError,
    NonInteractiveApprovalError,
    approve_phase,
    generate_human_token,
    generate_human_token_v2,
    verify_human_token,
)
from valdoz.checks import run_valdoz_audit
from valdoz.gates import GateCheck, GateReport, run_phase_gate_checks
from valdoz.healing import redact_secrets_in_text
from valdoz.phases import (
    PHASE_NAMES,
    advance_phase,
    anchor_audit_log,
    reopen_phase,
    verify_audit_log_integrity,
    verify_external_anchor,
)
from valdoz.slices import approve_slice, done_slice, start_slice
from valdoz.state import (
    ValdozState,
    get_state_path,
    is_write_protected,
    load_state,
    save_state,
    verify_phase_integrity,
)

__version__ = "3.1.2"

__all__ = [
    "__version__",
    "ApprovalError",
    "GateCheck",
    "GateReport",
    "MissingDeliverableError",
    "NonInteractiveApprovalError",
    "PHASE_NAMES",
    "ValdozState",
    "advance_phase",
    "anchor_audit_log",
    "approve_phase",
    "approve_slice",
    "done_slice",
    "generate_human_token",
    "generate_human_token_v2",
    "get_state_path",
    "is_write_protected",
    "load_state",
    "redact_secrets_in_text",
    "reopen_phase",
    "run_phase_gate_checks",
    "run_valdoz_audit",
    "save_state",
    "start_slice",
    "verify_audit_log_integrity",
    "verify_external_anchor",
    "verify_human_token",
    "verify_phase_integrity",
]

