"""ValdoZ Autonomous Self-Healing Engine.

Inspired by modern AI-driven CI/CD remediation workflows:
- Collects failure context (error traces, failing files, git diff, slice specs)
- Formulates structured diagnostic prompts for AI root-cause analysis
- Generates and applies minimal unified diffs or file patches
- Re-verifies against ValdoZ gate conditions and slice test requirements
- Produces a transparent HealingReport for human review and sign-off
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from valdoz.sdk_bridge import FreeLLMAPIConfig, generate_freellmapi_config

MAX_PATCH_FILE_BYTES = 512_000  # 500 KB per file cap to prevent disk-exhaustion DoS
FORBIDDEN_AI_HOSTS = {"169.254.169.254", "metadata.google.internal", "metadata"}

# ── Redaction Patterns for LLM Scrubbing Pipeline ───────────────────────────
REDACTION_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z0-9_-]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9_-]+ PRIVATE KEY-----", re.MULTILINE), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\b(gh[pousr]_[0-9a-zA-Z]{36,}|github_pat_[0-9a-zA-Z_]{50,})\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,}|sk-ant-[a-zA-Z0-9_\-]{20,})\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"\bvaldoz-v[12]\.[a-zA-Z0-9_\-\.]+\b"), "[REDACTED_VALDOZ_TOKEN]"),
    (re.compile(r"(?i)\b(bearer\s+)([a-zA-Z0-9_\-\.]{15,})\b"), r"\1[REDACTED_BEARER_TOKEN]"),
    (re.compile(r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)\b((?:password|secret|api_key|access_token|private_key)\s*[:=]\s*['\"]?)([^'\s\"&]{8,})(['\"]?)"), r"\1[REDACTED_CREDENTIAL]\3"),
]


def redact_secrets_in_text(raw_text: str) -> Tuple[str, int]:
    """Redacts API keys, credentials, private keys, and auth tokens from raw text.

    Scrubs sensitive strings before sending diagnostics to external LLM endpoints.
    Returns:
        (sanitized_text, count_of_redacted_secrets)
    """
    if not raw_text:
        return "", 0

    sanitized = raw_text
    total_redacted = 0

    for pat, replacement in REDACTION_PATTERNS:
        matches = len(pat.findall(sanitized))
        if matches > 0:
            total_redacted += matches
            sanitized = pat.sub(replacement, sanitized)

    return sanitized, total_redacted


class HealingContext(BaseModel):
    failure_type: str  # "slice_gate", "audit", "gate_check", "ci"
    error_trace: str
    failing_files: List[str] = Field(default_factory=list)
    git_diff: str = ""
    slice_id: Optional[str] = None
    slice_spec: Optional[str] = None
    phase_num: Optional[int] = None
    attempt: int = 1


class HealingReport(BaseModel):
    success: bool
    attempt_count: int
    root_cause: str
    patch_diff: str
    verification_passed: bool
    applied_files: List[str] = Field(default_factory=list)
    human_review_summary: str


def collect_failure_context(
    project_root: Path,
    failure_type: str,
    error_output: str,
    slice_id: Optional[str] = None,
    phase_num: Optional[int] = None,
) -> HealingContext:
    """Gathers git diff, slice spec, and affected files to construct healing context."""
    # 1. Unstaged / recent git diff
    diff_text = ""
    try:
        proc = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        diff_text = proc.stdout.strip()
    except Exception:
        diff_text = ""

    # 2. Slice spec if slice_id provided
    slice_spec_content = None
    if slice_id:
        spec_file = project_root / "docs" / "slices" / f"{slice_id}.md"
        if spec_file.exists():
            slice_spec_content = spec_file.read_text(encoding="utf-8", errors="replace")

    # 3. Identify failing files from trace
    failing_files: List[str] = []
    root_resolved = project_root.resolve()
    # Pattern for file paths in common test/traceback outputs (absolute or relative)
    matches = re.findall(r"(?:/?(?:[\w\.-]+/)+[\w\.-]+\.(?:py|js|ts|jsx|tsx|json|md))", error_output)
    for m in set(matches):
        p = Path(m)
        if p.is_absolute():
            if p.exists() and p.is_file():
                try:
                    rel = p.resolve().relative_to(root_resolved)
                    failing_files.append(rel.as_posix())
                except ValueError:
                    pass
        else:
            cand = (project_root / m.lstrip("/")).resolve()
            try:
                rel = cand.relative_to(root_resolved)
                if cand.exists() and cand.is_file():
                    failing_files.append(rel.as_posix())
            except ValueError:
                pass

    return HealingContext(
        failure_type=failure_type,
        error_trace=error_output,
        failing_files=sorted(failing_files),
        git_diff=diff_text[:6000],  # cap to preserve context window
        slice_id=slice_id,
        slice_spec=slice_spec_content,
        phase_num=phase_num,
    )


def build_diagnosis_prompt(ctx: HealingContext) -> str:
    """Builds a precise system prompt for the AI root-cause analysis and patch generator.

    Automatically scrubs sensitive credentials, API keys, private keys, and auth tokens
    from error traces, git diffs, and slice specs to prevent data exfiltration.
    """
    clean_error, _ = redact_secrets_in_text(ctx.error_trace)
    clean_diff, _ = redact_secrets_in_text(ctx.git_diff or "")

    prompt = f"""You are the ValdoZ Protocol Autonomous Self-Healing Engine.
A build, test, or gate check has failed. Analyze the failure trace, identify the exact root cause, and provide a minimal, working code fix.

FAILURE CONTEXT:
- Failure Type: {ctx.failure_type}
- Target Slice/Phase: {ctx.slice_id or ctx.phase_num or 'Repository-wide'}
- Implicated Files: {', '.join(ctx.failing_files) or 'None explicitly identified'}

ERROR TRACE / FAILURE LOG:
```
{clean_error}
```

RECENT GIT DIFF:
```
{clean_diff or 'No uncommitted diff'}
```
"""
    if ctx.slice_spec:
        clean_spec, _ = redact_secrets_in_text(ctx.slice_spec[:2000])
        prompt += f"""
SLICE SPECIFICATION:
```markdown
{clean_spec}
```
"""

    prompt += """
RESPONSE INSTRUCTIONS:
1. Explain the ROOT CAUSE concisely (1-3 sentences).
2. Provide the exact file replacements or patches. Output the code fix enclosed in standard file blocks:
FILE: path/to/file.ext
```
<complete updated file content or targeted replacement>
```
Do not include hypothetical explanations. Provide working, verified solutions only.
"""
    return prompt


def parse_ai_patch_response(response_text: str) -> Dict[str, str]:
    """Parses FILE: <path> followed by code block from the LLM response."""
    file_patches: Dict[str, str] = {}
    pattern = re.compile(r"FILE:\s*([^\n\r]+)\s*```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(response_text):
        rel_path = match.group(1).strip()
        code = match.group(2)
        file_patches[rel_path] = code
    return file_patches


def apply_patch(project_root: Path, file_patches: Dict[str, str]) -> List[str]:
    """Applies file patches to disk after strict sanitization, syntax validation, and quarantine checks."""
    applied = []
    root_resolved = project_root.resolve()

    FORBIDDEN_PREFIXES = (
        ".git/", ".git",
        ".valdoz/", ".valdoz",
        ".github/", ".github",
        ".env",
        "pyproject.toml", "package.json", "package-lock.json",
        "uv.lock", "poetry.lock", "Pipfile.lock", "Cargo.lock",
    )

    for rel_path, content in file_patches.items():
        if "\0" in rel_path or "\0" in content:
            continue

        clean_rel = Path(rel_path).as_posix().lstrip("/")

        # Security Quarantine: block writes to git, valdoz internals, CI, and package manifests
        if any(clean_rel.startswith(p) or clean_rel == p for p in FORBIDDEN_PREFIXES):
            continue

        # Cap individual patch size
        if len(content.encode("utf-8")) > MAX_PATCH_FILE_BYTES:
            continue

        # Syntax check for Python patches: reject invalid syntax
        if clean_rel.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError:
                continue

        dest = (root_resolved / clean_rel).resolve()
        try:
            dest.relative_to(root_resolved)
        except ValueError:
            # Traversal attempt outside project root - ignore
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        applied.append(dest.relative_to(root_resolved).as_posix())
    return applied


def mock_or_call_ai(prompt: str, model_config: Optional[Dict[str, Any]] = None) -> str:
    """Dispatches to configured LLM endpoint or environment API.
    
    If VALDOZ_HEAL_MOCK_RESPONSE is set in environment, returns that directly (for deterministic unit tests).
    """
    mock_resp = os.environ.get("VALDOZ_HEAL_MOCK_RESPONSE")
    if mock_resp:
        return mock_resp

    # Check for direct FreeLLMAPI / OpenAI-compatible endpoint
    api_key = os.environ.get("VALDOZ_AI_API_KEY")
    base_url = os.environ.get("VALDOZ_AI_BASE_URL", "http://localhost:8000/v1")
    model_name = os.environ.get("VALDOZ_HEAL_MODEL", "gemini-2.5-flash")

    if api_key:
        try:
            import urllib.parse
            import urllib.request
            parsed = urllib.parse.urlparse(base_url)
            if parsed.scheme not in ("http", "https"):
                return f"Root Cause: Invalid AI base URL scheme '{parsed.scheme}'. Only http and https are permitted."

            hostname = (parsed.hostname or "").lower()
            if hostname in FORBIDDEN_AI_HOSTS or hostname.startswith("169.254."):
                return f"Root Cause: Security rejection: AI base URL cannot target cloud metadata or link-local endpoints ('{hostname}')."

            req_data = json.dumps({
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are the ValdoZ Protocol AI self-healing diagnostic assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url.rstrip('/')}/chat/completions",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 # nosemgrep
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Root Cause: Automated diagnosis failed to connect to AI provider ({e})."

    return (
        "Root Cause: AI remediation endpoint not configured. Set VALDOZ_AI_API_KEY or configure local FreeLLMAPI.\n"
        "Manual intervention required."
    )


def verify_after_patch(project_root: Path, ctx: HealingContext) -> bool:
    """Re-runs the corresponding verification based on failure type."""
    if ctx.failure_type == "audit":
        from valdoz.checks import run_valdoz_audit
        rep = run_valdoz_audit(project_root, strict=True)
        return rep.passed
    elif ctx.failure_type in ("gate", "gate_check"):
        from valdoz.gates import run_phase_gate_checks
        rep = run_phase_gate_checks(project_root, phase_num=ctx.phase_num)
        return rep.passed
    elif ctx.failure_type == "ci":
        from valdoz.checks import run_valdoz_audit
        from valdoz.gates import run_phase_gate_checks
        audit_rep = run_valdoz_audit(project_root, strict=True)
        if not audit_rep.passed:
            return False
        gate_rep = run_phase_gate_checks(project_root, phase_num=ctx.phase_num)
        return gate_rep.passed
    elif ctx.failure_type in ("slice_gate", "slice_test"):
        # Run local test suite (e.g. pytest or npm test)
        try:
            has_pyproject = (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists()
            has_package_json = (project_root / "package.json").exists()
            tests_dir = project_root / "tests"

            if has_pyproject:
                res = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q"],
                    cwd=project_root,
                    capture_output=True,
                    check=False,
                )
                return res.returncode == 0
            elif has_package_json:
                res = subprocess.run(
                    ["npm", "test"],
                    cwd=project_root,
                    capture_output=True,
                    check=False,
                )
                return res.returncode == 0
            elif tests_dir.exists() and tests_dir.is_dir():
                py_files = list(tests_dir.glob("**/*.py"))
                if py_files:
                    res = subprocess.run(
                        [sys.executable, "-m", "pytest", "-q"],
                        cwd=project_root,
                        capture_output=True,
                        check=False,
                    )
                    return res.returncode == 0
                else:
                    res = subprocess.run(
                        ["npm", "test"],
                        cwd=project_root,
                        capture_output=True,
                        check=False,
                    )
                    return res.returncode == 0
        except Exception:
            return False
    return True


def generate_patch_diff(project_root: Path, file_patches: Dict[str, str]) -> str:
    """Computes unified diff between disk files and proposed AI patches without modifying disk."""
    import difflib
    diff_lines: List[str] = []
    root_resolved = project_root.resolve()

    for rel_path, new_content in file_patches.items():
        clean_rel = Path(rel_path).as_posix().lstrip("/")
        dest = (root_resolved / clean_rel).resolve()
        is_new = not (dest.exists() and dest.is_file())
        old_content = ""
        if not is_new:
            try:
                old_content = dest.read_text(encoding="utf-8", errors="replace")
            except Exception:
                old_content = ""

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        fromfile = "/dev/null" if is_new else f"a/{clean_rel}"
        tofile = f"b/{clean_rel}"
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=fromfile,
            tofile=tofile,
        ))
        if diff:
            diff_lines.extend(diff)

    return "".join(diff_lines)


def run_healing_loop(
    project_root: Path,
    ctx: HealingContext,
    max_retries: int = 3,
    model_config: Optional[Dict[str, Any]] = None,
    preview: bool = False,
    preview_callback: Optional[Any] = None,
) -> HealingReport:
    """Executes the autonomous diagnosis, patch, and re-verification loop.

    Args:
        project_root: Repository root directory.
        ctx: Failure context containing traces and failing files.
        max_retries: Maximum diagnosis and patch iterations.
        model_config: Optional custom model configuration.
        preview: When True, computes and returns proposed diff without modifying disk.
        preview_callback: Optional callable(diff: str, patches: dict) -> bool for confirmation.
    """
    attempts = 0
    success = False
    applied_files: List[str] = []
    root_cause = ""
    patch_diff = ""

    while attempts < max_retries and not success:
        attempts += 1
        ctx.attempt = attempts

        if attempts > 1:
            backoff_seconds = 2 ** (attempts - 1)
            time.sleep(backoff_seconds)

        prompt = build_diagnosis_prompt(ctx)
        ai_resp = mock_or_call_ai(prompt, model_config)

        # Extract root cause summary
        cause_match = re.search(r"Root Cause:\s*(.+?)(?=\n\n|FILE:|$)", ai_resp, re.DOTALL | re.IGNORECASE)
        root_cause = cause_match.group(1).strip() if cause_match else ai_resp[:200]

        # Parse patch
        patches = parse_ai_patch_response(ai_resp)
        if patches:
            patch_diff = generate_patch_diff(project_root, patches)

            if preview:
                return HealingReport(
                    success=False,
                    attempt_count=attempts,
                    root_cause=root_cause,
                    patch_diff=patch_diff,
                    verification_passed=False,
                    applied_files=[],
                    human_review_summary=f"Diff preview generated for {len(patches)} file(s). No changes written to disk.",
                )

            if preview_callback and not preview_callback(patch_diff, patches):
                return HealingReport(
                    success=False,
                    attempt_count=attempts,
                    root_cause=root_cause,
                    patch_diff=patch_diff,
                    verification_passed=False,
                    applied_files=[],
                    human_review_summary="Patch application cancelled by user.",
                )

            applied = apply_patch(project_root, patches)
            applied_files.extend(applied)

            # Re-verify
            passed = verify_after_patch(project_root, ctx)
            if passed:
                success = True
                break

    applied_files_unique = sorted(set(applied_files))
    summary = (
        f"Self-Healing {'SUCCESSFUL' if success else 'EXHAUSTED'} after {attempts} attempt(s).\n"
        f"Root Cause: {root_cause}\n"
        f"Modified Files: {', '.join(applied_files_unique) or 'None'}"
    )

    return HealingReport(
        success=success,
        attempt_count=attempts,
        root_cause=root_cause,
        patch_diff=patch_diff,
        verification_passed=success,
        applied_files=applied_files_unique,
        human_review_summary=summary,
    )
