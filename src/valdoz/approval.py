"""ValdoZ Approval Engine.

Enforces interactive-only, human approval of phases.
Refuses script or automated execution. Computes deliverable SHA-256 hashes
and write-protects state.json.
"""

from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from valdoz.phases import (
    PHASE_NAMES,
    append_approvals_log,
    get_required_deliverables,
)
from valdoz.state import (
    compute_deliverables_hash,
    compute_file_sha256,
    get_state_path,
    load_state,
    save_state,
    set_write_protection,
)


class ApprovalError(Exception):
    pass


class NonInteractiveApprovalError(ApprovalError):
    pass


class MissingDeliverableError(ApprovalError):
    pass


class TimeLockViolationError(ApprovalError):
    pass


class QuorumNotMetError(ApprovalError):
    pass


def get_user_keystore_path() -> Path:
    """Returns the out-of-workspace master key path in user's OS config directory."""
    config_dir = Path.home() / ".config" / "valdoz" / "keys"
    return config_dir / "approval.key"


def get_approval_secret(project_root: Optional[Path] = None) -> bytes:
    """Returns the cryptographic secret key for signing human approval tokens.

    Priority order:
    1. VALDOZ_APPROVAL_SECRET environment variable
    2. Out-of-workspace user key: ~/.config/valdoz/keys/approval.key
    3. In-workspace legacy fallback: <project_root>/.valdoz/.secret (deprecated)
    """
    env_sec = os.environ.get("VALDOZ_APPROVAL_SECRET")
    if env_sec:
        return env_sec.encode("utf-8")

    # 1. Out-of-workspace keystore
    user_key = get_user_keystore_path()
    if user_key.exists():
        try:
            return user_key.read_bytes()
        except Exception:
            pass

    # 2. In-workspace legacy key fallback (with migration warning if readable)
    root = project_root
    if not root:
        from valdoz.state import find_project_root
        root = find_project_root()

    sec_file = root / ".valdoz" / ".secret"
    if sec_file.exists():
        try:
            return sec_file.read_bytes()
        except Exception:
            pass

    # 3. Generate new 32-byte secret in out-of-workspace keystore
    new_sec = secrets.token_bytes(32)
    try:
        user_key.parent.mkdir(parents=True, exist_ok=True)
        # Directory 0o700 (user-only traversal), key file 0o600
        os.chmod(user_key.parent, 0o700)  # nosemgrep # nosec
        user_key.write_bytes(new_sec)
        os.chmod(user_key, 0o600)  # nosemgrep # nosec
        return new_sec
    except Exception:
        # Fallback to in-workspace if home directory is read-only
        sec_file.parent.mkdir(parents=True, exist_ok=True)
        sec_file.write_bytes(new_sec)
        os.chmod(sec_file, 0o600)
        return new_sec


def get_consumed_nonces_path(project_root: Optional[Path] = None) -> Path:
    """Returns path to the consumed nonce ledger."""
    root = project_root
    if not root:
        from valdoz.state import find_project_root
        root = find_project_root()
    return root / ".valdoz" / "consumed_nonces.json"


def is_nonce_consumed(nonce: str, project_root: Optional[Path] = None) -> bool:
    """Checks whether a token nonce has already been consumed (replay prevention)."""
    p = get_consumed_nonces_path(project_root)
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return nonce in data
    except Exception:
        return False


def burn_nonce(nonce: str, action: str, target: str, project_root: Optional[Path] = None) -> None:
    """Burns an approval token nonce to prevent replay attacks, pruning entries older than 15m."""
    p = get_consumed_nonces_path(project_root)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    data = {}
    if p.exists():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            # Auto-prune entries older than 15 minutes (900 seconds)
            data = {k: v for k, v in raw.items() if (now_ts - v.get("ts", 0)) < 900}
        except Exception:
            data = {}

    data[nonce] = {"action": action, "target": str(target), "ts": now_ts}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generate_human_token(
    action: str,
    target: str,
    project_root: Optional[Path] = None,
    deliverables_hash: Optional[str] = None,
) -> str:
    """Generates an HMAC-SHA256 signed approval token with a 5-minute TTL and unique nonce.

    If deliverables_hash is provided, generates a valdoz-v2 token bound to the deliverables hash.
    Otherwise, generates a valdoz-v1 token.
    """
    secret = get_approval_secret(project_root)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    nonce = secrets.token_hex(8)

    if deliverables_hash:
        msg = f"{action}:{target}:{deliverables_hash}:{now_ts}:{nonce}".encode("utf-8")
        sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
        return f"valdoz-v2.{action}.{target}.{deliverables_hash}.{now_ts}.{nonce}.{sig}"

    msg = f"{action}:{target}:{now_ts}:{nonce}".encode("utf-8")
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return f"valdoz-v1.{action}.{target}.{now_ts}.{nonce}.{sig}"


def generate_human_token_v2(
    action: str,
    target: str,
    deliverables_hash: str,
    project_root: Optional[Path] = None,
) -> str:
    """Explicitly generates a valdoz-v2 token bound to deliverable composite hash."""
    return generate_human_token(
        action,
        target,
        project_root=project_root,
        deliverables_hash=deliverables_hash,
    )


def verify_human_token(
    token: str,
    action: str,
    target: str,
    deliverables_hash: Optional[str] = None,
    max_age_seconds: int = 300,
    project_root: Optional[Path] = None,
    burn: bool = False,
) -> bool:
    """Cryptographically verifies that an approval token is authentic, matching, unexpired, and unburned."""
    if not token:
        return False

    # Check v2 cryptographic format: valdoz-v2.<action>.<target>.<deliv_hash>.<timestamp>.<nonce>.<sig>
    if token.startswith("valdoz-v2."):
        parts = token.split(".")
        if len(parts) != 7:
            return False
        _, tok_action, tok_target, tok_deliv_hash, tok_ts_str, tok_nonce, tok_sig = parts
        if tok_action != action or tok_target != str(target):
            return False

        # If deliverables_hash was provided, verify exact composite hash match (TOCTOU protection)
        if deliverables_hash is not None and tok_deliv_hash != deliverables_hash:
            return False

        # Check nonce replay burn
        if is_nonce_consumed(tok_nonce, project_root):
            return False

        try:
            tok_ts = int(tok_ts_str)
        except ValueError:
            return False

        # TTL validation (default 5 minutes)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if tok_ts > now_ts + 60 or (now_ts - tok_ts) > max_age_seconds:
            return False

        # Verify 256-bit HMAC signature
        secret = get_approval_secret(project_root)
        msg = f"{action}:{target}:{tok_deliv_hash}:{tok_ts}:{tok_nonce}".encode("utf-8")
        expected_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
        is_valid = hmac.compare_digest(tok_sig, expected_sig)

        if not is_valid and project_root is not None:
            fallback_secret = get_approval_secret(None)
            fallback_expected = hmac.new(fallback_secret, msg, hashlib.sha256).hexdigest()
            is_valid = hmac.compare_digest(tok_sig, fallback_expected)

        if is_valid and burn:
            burn_nonce(tok_nonce, action, target, project_root)

        return is_valid

    # Check v1 cryptographic format: valdoz-v1.<action>.<target>.<timestamp>.<nonce>.<sig>
    if token.startswith("valdoz-v1."):
        parts = token.split(".")
        if len(parts) != 6:
            return False
        _, tok_action, tok_target, tok_ts_str, tok_nonce, tok_sig = parts
        if tok_action != action or tok_target != str(target):
            return False

        # Check nonce replay burn
        if is_nonce_consumed(tok_nonce, project_root):
            return False

        try:
            tok_ts = int(tok_ts_str)
        except ValueError:
            return False

        # TTL validation (default 5 minutes)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if tok_ts > now_ts + 60 or (now_ts - tok_ts) > max_age_seconds:
            return False

        # Verify 256-bit HMAC signature
        secret = get_approval_secret(project_root)
        msg = f"{action}:{target}:{tok_ts}:{tok_nonce}".encode("utf-8")
        expected_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
        is_valid = hmac.compare_digest(tok_sig, expected_sig)

        if not is_valid and project_root is not None:
            fallback_secret = get_approval_secret(None)
            fallback_expected = hmac.new(fallback_secret, msg, hashlib.sha256).hexdigest()
            is_valid = hmac.compare_digest(tok_sig, fallback_expected)

        if is_valid and burn:
            burn_nonce(tok_nonce, action, target, project_root)

        return is_valid

    return False


def approve_phase(
    project_root: Path,
    phase_num: Optional[int] = None,
    approver_name: Optional[str] = None,
    enforce_tty: bool = True,
    confirmation_input: Optional[str] = None,
    human_token: Optional[str] = None,
    human_tokens: Optional[List[str]] = None,
    emergency_bypass: bool = False,
) -> Dict[str, str]:
    """Interactively approves a project phase.

    Supports two human approval channels:
      1. Interactive Terminal (TTY): sys.stdin.isatty() == True
      2. Antigravity In-Chat Bridge: human_token validated via explicit human action

    Enforces governance policies:
      - TOCTOU Defense: Deliverables composite hash bound into approval verification
      - Quorum: M-of-N human approvals for high-stakes phases
      - Time-Locks: Minimum dwell time per phase before approval
      - Replay Prevention: Single-use nonce burn
    """
    state = load_state(project_root)
    target_num = phase_num if phase_num is not None else state.current_phase
    phase_key = str(target_num)

    if phase_key not in state.phases:
        raise ApprovalError(f"Invalid phase number: {target_num}")

    phase_state = state.phases[phase_key]
    phase_name = PHASE_NAMES.get(target_num, f"Phase {target_num}")

    # 0. Early authentication check: If not interactive TTY and no human tokens submitted, fail immediately
    submitted_tokens: List[str] = []
    if human_token:
        submitted_tokens.append(human_token)
    if human_tokens:
        submitted_tokens.extend(human_tokens)

    if enforce_tty and not sys.stdin.isatty() and not submitted_tokens:
        raise NonInteractiveApprovalError(
            "Security Violation: Phase approval requires explicit human authorization.\n"
            "Must be approved via an interactive terminal or an authorized Antigravity in-chat approval action.\n"
            "AI agents and automated scripts are strictly prohibited from approving work."
        )

    # 1. Deliverables verification & Composite Hash computation (Pre-requisite for v2 token verification)
    required_files = get_required_deliverables(target_num)
    missing: List[str] = []
    deliverable_hashes: Dict[str, str] = {}

    for rel_path in required_files:
        file_path = project_root / rel_path
        if not file_path.exists():
            missing.append(rel_path)
        else:
            file_hash = compute_file_sha256(file_path)
            if file_hash:
                deliverable_hashes[rel_path] = file_hash

    if missing:
        raise MissingDeliverableError(
            f"Cannot approve Phase {target_num} ({phase_name}): missing required deliverables:\n"
            + "\n".join(f" - {f}" for f in missing)
        )

    composite_hash = compute_deliverables_hash(deliverable_hashes)

    # 2. Validate human approval tokens against target phase and composite hash
    valid_tokens = [
        tok for tok in set(submitted_tokens)
        if verify_human_token(
            tok,
            "phase",
            str(target_num),
            deliverables_hash=composite_hash,
            project_root=project_root,
        )
    ]
    has_valid_human_token = len(valid_tokens) > 0

    if enforce_tty and not sys.stdin.isatty() and not has_valid_human_token:
        raise NonInteractiveApprovalError(
            "Security Violation: Phase approval requires explicit human authorization.\n"
            "Must be approved via an interactive terminal or an authorized Antigravity in-chat approval action.\n"
            "AI agents and automated scripts are strictly prohibited from approving work."
        )

    # 3. Governance check: Load .valdozrc.json if present
    from valdoz.packs import load_valdozrc
    valdozrc = load_valdozrc(project_root)
    gov_cfg = valdozrc.get("governance", {})

    # Quorum verification (M-of-N)
    quorum_cfg = gov_cfg.get("quorum", {})
    required_quorum = quorum_cfg.get(str(target_num), quorum_cfg.get("default", 1))
    if required_quorum > 1:
        if len(valid_tokens) < required_quorum:
            raise QuorumNotMetError(
                f"Quorum failure: Phase {target_num} requires {required_quorum} distinct human approvals, "
                f"but received {len(valid_tokens)} valid token(s)."
            )

    # Time-lock verification
    timelock_cfg = gov_cfg.get("time_locks", {})
    min_minutes = timelock_cfg.get(str(target_num), timelock_cfg.get("default", 0))
    if min_minutes > 0 and not emergency_bypass:
        if phase_state.entered_at:
            try:
                entered_dt = datetime.fromisoformat(phase_state.entered_at)
                elapsed_sec = (datetime.now(timezone.utc) - entered_dt).total_seconds()
                if elapsed_sec < min_minutes * 60:
                    remaining_sec = int(min_minutes * 60 - elapsed_sec)
                    raise TimeLockViolationError(
                        f"Time-lock active: Phase {target_num} requires at least {min_minutes}m before approval "
                        f"({int(elapsed_sec // 60)}m elapsed, {remaining_sec}s remaining). "
                        f"Pass emergency_bypass=True to override."
                    )
            except ValueError:
                pass

    # Verify confirmation input if provided
    expected_name = phase_name.lower().replace(" ", "-")
    if confirmation_input is not None:
        typed = confirmation_input.strip().lower().replace(" ", "-")
        if typed != expected_name and typed != str(target_num):
            raise ApprovalError(
                f"Approval aborted: confirmation string '{confirmation_input}' did not match phase '{expected_name}'."
            )

    # 4. Burn nonces of all consumed tokens to prevent replay
    for tok in valid_tokens:
        parts = tok.split(".")
        nonce = parts[5] if tok.startswith("valdoz-v2.") else parts[4]
        burn_nonce(nonce, "phase", str(target_num), project_root=project_root)

    approver = approver_name or getpass.getuser()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Update phase state
    phase_state.status = "approved"
    phase_state.approved_by = approver
    phase_state.approved_at = now_iso
    phase_state.approval_hash = composite_hash
    phase_state.deliverable_hashes = deliverable_hashes
    if valid_tokens:
        phase_state.approvals = [
            {
                "token_nonce": tok.split(".")[5] if tok.startswith("valdoz-v2.") else tok.split(".")[4],
                "approved_at": now_iso,
            }
            for tok in valid_tokens
        ]

    # Save state and apply read-only write protection (chmod 444)
    save_state(project_root, state, write_protect=True)

    append_approvals_log(
        project_root,
        f"Phase {target_num} ({phase_name}) approved by {approver} at {now_iso}. "
        f"Composite hash: {composite_hash[:16]}... "
        f"Deliverables hashed: {len(deliverable_hashes)}.",
    )

    try:
        from valdoz.webhooks import emit_webhook_event
        emit_webhook_event(
            project_root,
            "phase.approved",
            {
                "phase": target_num,
                "phase_name": phase_name,
                "approver": approver,
                "composite_hash": composite_hash,
            },
        )
    except Exception:
        pass

    return deliverable_hashes
