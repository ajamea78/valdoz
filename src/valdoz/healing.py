"""ValdoZ Autonomous Self-Healing Engine.

Inspired by modern AI-driven CI/CD remediation workflows:
- Collects failure context (error traces, failing files, git diff, slice specs)
- Formulates structured diagnostic prompts for AI root-cause analysis
- Generates and applies minimal unified diffs or file patches
- Re-verifies against ValdoZ gate conditions and slice test requirements
- Produces a transparent HealingReport for human review and sign-off
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from valdoz.sdk_bridge import FreeLLMAPIConfig, generate_freellmapi_config


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
    # Pattern for file paths in common test/traceback outputs (absolute or relative)
    matches = re.findall(r"(?:/?(?:[\w\.-]+/)+[\w\.-]+\.(?:py|js|ts|jsx|tsx|json|md))", error_output)
    for m in set(matches):
        p = Path(m)
        if p.is_absolute() and p.exists():
            try:
                rel = p.relative_to(project_root)
                failing_files.append(rel.as_posix())
            except ValueError:
                pass
        else:
            rel_p = project_root / m.lstrip("/")
            if rel_p.exists() and rel_p.is_file():
                failing_files.append(m.lstrip("/"))

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
    """Builds a precise system prompt for the AI root-cause analysis and patch generator."""
    prompt = f"""You are the ValdoZ Protocol Autonomous Self-Healing Engine.
A build, test, or gate check has failed. Analyze the failure trace, identify the exact root cause, and provide a minimal, working code fix.

FAILURE CONTEXT:
- Failure Type: {ctx.failure_type}
- Target Slice/Phase: {ctx.slice_id or ctx.phase_num or 'Repository-wide'}
- Implicated Files: {', '.join(ctx.failing_files) or 'None explicitly identified'}

ERROR TRACE / FAILURE LOG:
```
{ctx.error_trace}
```

RECENT GIT DIFF:
```
{ctx.git_diff or 'No uncommitted diff'}
```
"""
    if ctx.slice_spec:
        prompt += f"""
SLICE SPECIFICATION:
```markdown
{ctx.slice_spec[:2000]}
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
    """Applies file patches to disk and returns the list of modified paths."""
    applied = []
    for rel_path, content in file_patches.items():
        # Prevent directory traversal attacks
        clean_rel = Path(rel_path).as_posix().lstrip("/").replace("../", "")
        dest = project_root / clean_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        applied.append(clean_rel)
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
            import urllib.request
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
            with urllib.request.urlopen(req, timeout=30) as resp:
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
    elif ctx.failure_type == "gate_check":
        from valdoz.gates import run_phase_gate_checks
        rep = run_phase_gate_checks(project_root, phase_num=ctx.phase_num)
        return rep.passed
    elif ctx.failure_type in ("slice_gate", "slice_test"):
        # Run local test suite (e.g. pytest or npm test)
        try:
            # Check pytest
            if (project_root / "pyproject.toml").exists() or (project_root / "tests").exists():
                res = subprocess.run(
                    ["pytest", "-q"],
                    cwd=project_root,
                    capture_output=True,
                    check=False,
                )
                return res.returncode == 0
            # Check npm test
            elif (project_root / "package.json").exists():
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


def run_healing_loop(
    project_root: Path,
    ctx: HealingContext,
    max_retries: int = 3,
    model_config: Optional[Dict[str, Any]] = None,
) -> HealingReport:
    """Executes the autonomous diagnosis, patch, and re-verification loop."""
    attempts = 0
    success = False
    applied_files: List[str] = []
    root_cause = ""
    patch_diff = ""

    while attempts < max_retries and not success:
        attempts += 1
        ctx.attempt = attempts

        prompt = build_diagnosis_prompt(ctx)
        ai_resp = mock_or_call_ai(prompt, model_config)

        # Extract root cause summary
        cause_match = re.search(r"Root Cause:\s*(.+?)(?=\n\n|FILE:|$)", ai_resp, re.DOTALL | re.IGNORECASE)
        root_cause = cause_match.group(1).strip() if cause_match else ai_resp[:200]

        # Parse and apply patch
        patches = parse_ai_patch_response(ai_resp)
        if patches:
            applied = apply_patch(project_root, patches)
            applied_files.extend(applied)

            # Capture patch diff
            try:
                proc = subprocess.run(
                    ["git", "diff", *applied],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                patch_diff = proc.stdout.strip()
            except Exception:
                patch_diff = "\n".join(f"Updated {f}" for f in applied)

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
