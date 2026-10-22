"""ValdoZ Protocol CLI Application.

Main entry point for command-line interactions.
"""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from valdoz import __version__
from valdoz.approval import (
    ApprovalError,
    MissingDeliverableError,
    NonInteractiveApprovalError,
    approve_phase,
)
from valdoz.logs import (
    add_decision,
    add_research,
    check_research_staleness,
    load_decisions,
    load_research,
    pre_log_research_intent,
    sanitize_and_wrap_content,
)
from valdoz.phases import (
    PHASE_NAMES,
    PhaseTransitionError,
    ReopenConfirmationError,
    advance_phase,
    get_phase_whitelist,
    get_required_deliverables,
    get_side_effect_info,
    reopen_phase,
)
from valdoz.repair import repair_state
from valdoz.session import (
    SessionLockError,
    acquire_session,
    clear_sessions,
    get_active_sessions,
    release_session,
)
from valdoz.state import (
    StateError,
    ValdozState,
    get_state_path,
    is_write_protected,
    load_state,
    save_state,
    verify_phase_integrity,
)

console = Console()
app = typer.Typer(
    name="valdoz",
    help="ValdoZ Protocol v3.0 — Antigravity Delivery Discipline Engine",
    no_args_is_help=True,
)
phase_app = typer.Typer(name="phase", help="Phase state machine commands", no_args_is_help=True)
session_app = typer.Typer(name="session", help="Multi-role session locks", no_args_is_help=True)
project_app = typer.Typer(name="project", help="Project lifecycle commands", no_args_is_help=True)
decision_app = typer.Typer(name="decision", help="Decision log commands", no_args_is_help=True)
research_app = typer.Typer(name="research", help="Research subsystem commands", no_args_is_help=True)
state_app = typer.Typer(name="state", help="State inspection and repair", no_args_is_help=True)
gate_app = typer.Typer(name="gate", help="Gate verification engine", no_args_is_help=True)
slice_app = typer.Typer(name="slice", help="Phase 6 slice governance", no_args_is_help=True)
pack_app = typer.Typer(name="pack", help="Stack and project-type packs", no_args_is_help=True)
hook_app = typer.Typer(name="hook", help="Git hook management", no_args_is_help=True)
ci_app = typer.Typer(name="ci", help="CI workflow management", no_args_is_help=True)

app.add_typer(phase_app)
app.add_typer(session_app)
app.add_typer(project_app)
app.add_typer(decision_app)
app.add_typer(research_app)
app.add_typer(state_app)
app.add_typer(gate_app)
app.add_typer(slice_app)
app.add_typer(pack_app)
app.add_typer(hook_app)
app.add_typer(ci_app)


def find_project_root() -> Path:
    """Finds repository root by searching upward for .valdoz or .git."""
    curr = Path.cwd().resolve()
    for parent in [curr, *curr.parents]:
        if (parent / ".valdoz").exists() or (parent / ".git").exists():
            return parent
    return curr


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show ValdoZ version"),
):
    if version:
        console.print(f"[bold cyan]ValdoZ Protocol[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit()


# ── Project Commands ────────────────────────────────────────────────────────
@project_app.command("init")
def project_init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    lang: str = typer.Option("en", "--lang", "-l", help="Language for client deliverables: en or ar"),
):
    """Initializes ValdoZ project state in the current repository."""
    root = find_project_root()
    valdoz_dir = root / ".valdoz"
    state_file = get_state_path(root)

    if state_file.exists():
        console.print(f"[yellow]Project is already initialized at {root}[/yellow]")
        raise typer.Exit(0)

    proj_name = name or root.name
    lang = lang.lower().strip()
    if lang not in ("en", "ar"):
        console.print("[red]Invalid language. Must be 'en' or 'ar'.[/red]")
        raise typer.Exit(1)

    # Pre-flight Terminal Safety Notice
    console.print(
        Panel.fit(
            "[bold yellow]Antigravity Review Policy Pre-Flight Verification[/bold yellow]\n"
            "Ensure Antigravity Review Policy is set to require human approval for commands.\n"
            "Production deployment and dangerous terminal tools are restricted.",
            title="Safety Check",
        )
    )

    state = ValdozState(
        project_name=proj_name,
        language=lang,
        current_phase=0,
        packs=["base"],
    )
    valdoz_dir.mkdir(parents=True, exist_ok=True)
    save_state(root, state)

    console.print(f"[bold green]ValdoZ v{__version__} initialized for project '{proj_name}' ({lang})[/bold green]")
    console.print(f"State file: [cyan]{state_file}[/cyan]")


# ── Session Commands ────────────────────────────────────────────────────────
@session_app.command("start")
def session_start(
    role: str = typer.Option(..., "--role", "-r", help="Role: builder or scribe"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", "-a", help="Agent identifier"),
):
    """Starts an agent session with a role lock (builder or scribe)."""
    root = find_project_root()
    try:
        sess = acquire_session(root, role=role, agent_id=agent_id)
        console.print(f"[green]Acquired session lock for role [bold]{role}[/bold][/green] (PID {sess.pid}, Agent '{sess.agent_id}')")
    except SessionLockError as e:
        console.print(f"[bold red]Lock Rejected:[/bold red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@session_app.command("end")
def session_end(
    role: str = typer.Option(..., "--role", "-r", help="Role to release: builder or scribe"),
):
    """Releases an active session lock."""
    root = find_project_root()
    released = release_session(root, role)
    if released:
        console.print(f"[green]Session lock for role '{role}' released.[/green]")
    else:
        console.print(f"[yellow]No active session lock found for role '{role}'.[/yellow]")


@session_app.command("clear")
def session_clear(
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Role to clear or all"),
):
    """Clears session locks (administrative recovery)."""
    root = find_project_root()
    clear_sessions(root, role)
    console.print("[green]Session locks cleared.[/green]")


@session_app.command("status")
def session_status():
    """Shows active session locks."""
    root = find_project_root()
    active = get_active_sessions(root)
    if not active:
        console.print("[dim]No active agent sessions.[/dim]")
        return

    table = Table(title="Active ValdoZ Sessions")
    table.add_column("Role", style="bold cyan")
    table.add_column("Agent ID", style="magenta")
    table.add_column("PID", style="yellow")
    table.add_column("Started At", style="green")

    for role, sess in active.items():
        table.add_row(role, sess.agent_id, str(sess.pid), sess.started_at)

    console.print(table)


# ── Phase Commands ──────────────────────────────────────────────────────────
@phase_app.command("status")
def phase_status():
    """Displays current phase, deliverables, whitelist, and integrity."""
    root = find_project_root()
    try:
        state = load_state(root)
    except StateError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    curr_num = state.current_phase
    curr_phase = state.phases[str(curr_num)]
    protected = is_write_protected(get_state_path(root))

    table = Table(title=f"Project: {state.project_name} (Phase {curr_num}: {curr_phase.name})")
    table.add_column("Phase #", justify="center")
    table.add_column("Phase Name", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Approved By")
    table.add_column("Integrity", justify="center")

    for p_num in sorted(PHASE_NAMES.keys()):
        p_state = state.phases[str(p_num)]
        status_color = {
            "approved": "green",
            "in_progress": "yellow",
            "pending": "dim",
            "pending_reapproval": "red",
        }.get(p_state.status, "white")

        integrity = "-"
        if p_state.status == "approved":
            is_valid, _ = verify_phase_integrity(root, p_num)
            integrity = "[green]VALID[/green]" if is_valid else "[bold red]TAMPERED[/bold red]"

        table.add_row(
            str(p_num),
            p_state.name,
            f"[{status_color}]{p_state.status}[/{status_color}]",
            p_state.approved_by or "-",
            integrity,
        )

    console.print(table)
    console.print(f"\nState write-protection: [bold {'green' if protected else 'yellow'}]{'LOCKED (read-only)' if protected else 'UNLOCKED'}[/]")

    deliverables = get_required_deliverables(curr_num)
    console.print(f"\n[bold]Required Deliverables for Phase {curr_num}:[/bold]")
    if deliverables:
        for d in deliverables:
            exists = (root / d).exists()
            console.print(f"  [{'green' if exists else 'red'}]{'✓' if exists else '✗'}[/] {d}")
    else:
        console.print("  [dim]No fixed deliverables specified (dynamic).[/dim]")

    whitelist = get_phase_whitelist(curr_num)
    console.print(f"\n[bold]Command Whitelist for Phase {curr_num}:[/bold]")
    console.print("  " + ", ".join(f"`{cmd}`" for cmd in whitelist))


@phase_app.command("next")
def phase_next():
    """Advances to the next phase after human approval."""
    root = find_project_root()
    try:
        new_num = advance_phase(root)
        name = PHASE_NAMES[new_num]
        console.print(f"[bold green]Successfully advanced to Phase {new_num}: {name}[/bold green]")
    except PhaseTransitionError as e:
        console.print(f"[bold red]Cannot Advance:[/bold red] {e}")
        raise typer.Exit(1)


@phase_app.command("approve")
def phase_approve(
    phase: Optional[int] = typer.Option(None, "--phase", "-p", help="Phase number to approve"),
):
    """Interactively approves phase deliverables (Human-Only, Interactive TTY)."""
    root = find_project_root()
    try:
        state = load_state(root)
    except StateError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    target_num = phase if phase is not None else state.current_phase
    phase_name = PHASE_NAMES.get(target_num, f"Phase {target_num}")

    console.print(f"\n[bold yellow]Human Gate Approval — Phase {target_num}: {phase_name}[/bold yellow]")
    console.print("This command requires human review of all deliverables and terminal confirmation.\n")

    expected_input = phase_name.lower().replace(" ", "-")
    user_input = typer.prompt(f"Type phase name '{expected_input}' to approve")

    try:
        hashes = approve_phase(
            project_root=root,
            phase_num=target_num,
            confirmation_input=user_input,
            enforce_tty=True,
        )
        console.print(f"[bold green]Phase {target_num} ({phase_name}) successfully approved![/bold green]")
        console.print(f"Hashed {len(hashes)} deliverable(s). state.json write-protected.")
    except NonInteractiveApprovalError as e:
        console.print(f"[bold red]Security Error:[/bold red] {e}")
        raise typer.Exit(1)
    except MissingDeliverableError as e:
        console.print(f"[bold red]Deliverable Error:[/bold red] {e}")
        raise typer.Exit(1)
    except ApprovalError as e:
        console.print(f"[bold red]Approval Failed:[/bold red] {e}")
        raise typer.Exit(1)


@phase_app.command("reopen")
def phase_reopen(
    phase_num: int = typer.Argument(..., help="Phase number to reopen"),
    confirm_project: Optional[str] = typer.Option(None, "--confirm-project", help="Confirm project name for irreversible phases"),
):
    """Reopens a past phase: voids approval hashes and cascades pending_reapproval."""
    root = find_project_root()
    try:
        state = load_state(root)
    except StateError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    side_effect = get_side_effect_info(phase_num)
    name = PHASE_NAMES.get(phase_num, f"Phase {phase_num}")

    console.print(f"\n[bold yellow]Reopening Phase {phase_num}: {name}[/bold yellow]")
    console.print(f"Side-Effect Class: [bold]{side_effect.category}[/bold] ({'Reversible' if side_effect.reversible else '[red]IRREVERSIBLE[/red]'})")
    console.print(f"{side_effect.description}\n")

    confirmation = confirm_project
    if not side_effect.reversible and not confirmation:
        confirmation = typer.prompt(f"Type project name '{state.project_name}' to confirm reopening irreversible phase")

    try:
        reopen_phase(root, target_phase=phase_num, confirm_project_name=confirmation)
        console.print(f"[bold green]Phase {phase_num} reopened successfully.[/bold green] Downstream phases marked pending re-approval.")
    except ReopenConfirmationError as e:
        console.print(f"[bold red]Confirmation Failed:[/bold red] {e}")
        raise typer.Exit(1)
    except PhaseTransitionError as e:
        console.print(f"[bold red]Reopen Failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── Decision Commands ───────────────────────────────────────────────────────
@decision_app.command("add")
def decision_add(
    question: str = typer.Option(..., "--question", "-q", help="The architectural or design question"),
    choice: str = typer.Option(..., "--choice", "-c", help="The chosen option"),
    rationale: str = typer.Option(..., "--rationale", "-r", help="Reasoning and trade-offs"),
    phase: Optional[int] = typer.Option(None, "--phase", "-p", help="Phase number"),
):
    """Appends an architectural decision to decisions.jsonl and regenerates decisions.md."""
    root = find_project_root()
    entry = add_decision(
        project_root=root,
        question=question,
        choice=choice,
        rationale=rationale,
        phase=phase,
    )
    console.print(f"[bold green]Recorded {entry.id}:[/bold green] '{entry.choice}' in Phase {entry.phase}")
    console.print(f"Updated: [cyan]{root / '.valdoz' / 'decisions.md'}[/cyan]")


# ── Research Commands ───────────────────────────────────────────────────────
@research_app.command("log")
def research_log(
    url: str = typer.Option(..., "--url", "-u", help="URL about to be fetched"),
    claim: str = typer.Option(..., "--claim", "-c", help="Expected claim or finding topic"),
    phase: Optional[int] = typer.Option(None, "--phase", "-p", help="Phase number"),
):
    """Pre-logs fetch intent before accessing external web content (Gap 4 defense)."""
    root = find_project_root()
    entry = pre_log_research_intent(root, url=url, claim=claim, phase=phase)
    console.print(f"[bold green]Pre-logged intent {entry.id}:[/bold green] '{entry.url}' (Pending Fetch)")


@research_app.command("fetch")
def research_fetch(
    url: str = typer.Argument(..., help="URL to safely fetch and sanitize"),
):
    """Safely fetches external content and wraps it with untrusted boundary delimiters."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ValdoZ-SanitizedFetcher/3.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
        wrapped = sanitize_and_wrap_content(raw_text, source_url=url)
        console.print(wrapped)
    except Exception as e:
        console.print(f"[bold red]Fetch Failed:[/bold red] {e}")
        raise typer.Exit(1)


@research_app.command("add")
def research_add_cmd(
    url: str = typer.Option(..., "--url", "-u", help="Source URL"),
    claim: str = typer.Option(..., "--claim", "-c", help="Verified finding or claim"),
    source_type: str = typer.Option("official_docs", "--source-type", "-s", help="official_docs, repository, blog, spec"),
    confidence: str = typer.Option("high", "--confidence", help="high, medium, low"),
    valid_days: int = typer.Option(90, "--valid-days", "-d", help="Validity period before warning"),
    phase: Optional[int] = typer.Option(None, "--phase", "-p", help="Phase number"),
):
    """Appends verified research finding to research.jsonl and regenerates research.md."""
    root = find_project_root()
    entry = add_research(
        project_root=root,
        url=url,
        claim=claim,
        source_type=source_type,
        confidence=confidence,
        valid_for_days=valid_days,
        phase=phase,
    )
    console.print(f"[bold green]Logged finding {entry.id}:[/bold green] '{entry.claim[:60]}...'")
    console.print(f"Updated: [cyan]{root / '.valdoz' / 'research.md'}[/cyan]")


# ── State Commands ──────────────────────────────────────────────────────────
@state_app.command("repair")
def state_repair_cmd():
    """Reconstructs state.json from git history and existing deliverable files."""
    root = find_project_root()
    console.print("[yellow]Initiating state reconstruction from git history and repository deliverables...[/yellow]")
    try:
        reconstructed, logs = repair_state(root)
        for msg in logs:
            console.print(f"  • {msg}")
        console.print(f"[bold green]State repaired successfully![/bold green] Current Phase: {reconstructed.current_phase} ({PHASE_NAMES[reconstructed.current_phase]})")
    except Exception as e:
        console.print(f"[bold red]State repair failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── Sync Runtimes Command ───────────────────────────────────────────────────
@app.command("sync-runtimes")
def sync_runtimes_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview generated files without writing"),
):
    """Generates Antigravity rules, playbooks, and managed blocks with 12,000 char cap check."""
    root = find_project_root()
    from valdoz.sync import sync_all_runtimes, CharLimitExceededError

    console.print(f"[bold cyan]Synchronizing Antigravity runtime files{' (Dry Run)' if dry_run else ''}...[/bold cyan]")
    try:
        results = sync_all_runtimes(root, dry_run=dry_run)
        table = Table(title="Generated Runtime Customizations")
        table.add_column("File Path", style="cyan")
        table.add_column("Size (chars)", justify="right")
        table.add_column("Status", style="green")

        for rel_path, content in sorted(results.items()):
            table.add_row(rel_path, f"{len(content):,}", "OK (within 12k cap)")

        console.print(table)
        console.print(f"[bold green]Successfully synchronized {len(results)} runtime configuration files.[/bold green]")
    except CharLimitExceededError as e:
        console.print(f"[bold red]Size Limit Exceeded:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Sync Failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── Gate Commands ───────────────────────────────────────────────────────────
@gate_app.command("check")
def gate_check(
    phase: Optional[int] = typer.Option(None, "--phase", "-p", help="Phase number to check"),
    ci: bool = typer.Option(False, "--ci", help="CI verification mode"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run preview"),
):
    """Runs deliverable, placeholder, heading, and research citation gate checks."""
    root = find_project_root()
    from valdoz.gates import run_phase_gate_checks

    report = run_phase_gate_checks(root, phase_num=phase, ci_mode=ci)
    table = Table(title=f"Gate Check: Phase {report.phase} ({report.phase_name})")
    table.add_column("Check ID", style="cyan")
    table.add_column("Description")
    table.add_column("Severity", justify="center")
    table.add_column("Result", justify="center")
    table.add_column("Message")

    for c in report.checks:
        res_str = "[bold green]PASS[/bold green]" if c.passed else (
            "[bold red]FAIL[/bold red]" if c.severity == "blocking" else "[yellow]WARN[/yellow]"
        )
        sev_color = "red" if c.severity == "blocking" else "yellow"
        table.add_row(
            c.id,
            c.name,
            f"[{sev_color}]{c.severity}[/{sev_color}]",
            res_str,
            c.message,
        )

    console.print(table)
    if report.passed:
        console.print(f"\n[bold green]✓ Phase {report.phase} Gate Passed![/bold green] Ready for human approval.")
    else:
        console.print(f"\n[bold red]✗ Phase {report.phase} Gate Failed![/bold red] Resolve blocking failures above.")
        raise typer.Exit(1)


# ── Slice Commands ──────────────────────────────────────────────────────────
@slice_app.command("start")
def slice_start_cmd(
    slice_id: str = typer.Argument(..., help="Slice identifier (e.g., 01-user-auth)"),
):
    """Starts a Phase 6 build slice after checking spec and previous slice approval."""
    root = find_project_root()
    from valdoz.slices import start_slice, SliceError
    try:
        s = start_slice(root, slice_id)
        console.print(f"[bold green]Slice '{s.slice_id}' started![/bold green] Base commit: [cyan]{s.base_commit[:8]}[/cyan]")
    except SliceError as e:
        console.print(f"[bold red]Cannot Start Slice:[/bold red] {e}")
        raise typer.Exit(1)


@slice_app.command("done")
def slice_done_cmd(
    slice_id: str = typer.Argument(..., help="Slice identifier"),
    cov_delta: float = typer.Option(0.0, "--cov-delta", help="Test coverage delta percentage"),
):
    """Closes a slice with test evidence, evaluating the Three Slice Gate Conditions."""
    root = find_project_root()
    from valdoz.slices import done_slice, SliceError, SliceGateConditionError
    try:
        s = done_slice(root, slice_id, coverage_delta=cov_delta)
        console.print(f"[bold green]Slice '{s.slice_id}' completed successfully![/bold green] Status: [cyan]gated[/cyan].")
        console.print("Three Slice Gate Conditions verified: pre-existing tests pass, new tests pass, coverage maintained.")
    except SliceGateConditionError as e:
        console.print(f"[bold red]Slice Gate Condition Failure:[/bold red] {e}")
        raise typer.Exit(1)
    except SliceError as e:
        console.print(f"[bold red]Slice Error:[/bold red] {e}")
        raise typer.Exit(1)


@slice_app.command("approve")
def slice_approve_cmd(
    slice_id: str = typer.Argument(..., help="Slice identifier to approve"),
):
    """Interactively approves a gated slice (Human-Only, Interactive TTY)."""
    root = find_project_root()
    from valdoz.slices import approve_slice, SliceError

    console.print(f"\n[bold yellow]Human Gate Approval — Slice: {slice_id}[/bold yellow]")
    confirm = typer.prompt(f"Type '{slice_id}' to approve slice")
    try:
        s = approve_slice(root, slice_id, confirmation_input=confirm, enforce_tty=True)
        console.print(f"[bold green]Slice '{s.slice_id}' successfully approved![/bold green] State write-protected.")
    except NonInteractiveApprovalError as e:
        console.print(f"[bold red]Security Error:[/bold red] {e}")
        raise typer.Exit(1)
    except SliceError as e:
        console.print(f"[bold red]Approval Failed:[/bold red] {e}")
        raise typer.Exit(1)


@slice_app.command("status")
def slice_status_cmd():
    """Lists all Phase 6 slices and their states."""
    root = find_project_root()
    from valdoz.slices import list_slices
    slices = list_slices(root)
    if not slices:
        console.print("[dim]No slices found in .valdoz/slices/.[/dim]")
        return

    table = Table(title="Phase 6 Build Slices")
    table.add_column("Slice ID", style="bold cyan")
    table.add_column("Status", justify="center")
    table.add_column("Approved By")
    table.add_column("Approved At")

    for s in slices:
        color = {"approved": "green", "gated": "yellow", "open": "cyan"}.get(s.status, "white")
        table.add_row(
            s.slice_id,
            f"[{color}]{s.status}[/{color}]",
            s.approved_by or "-",
            s.approved_at or "-",
        )
    console.print(table)


# ── Audit Command ───────────────────────────────────────────────────────────
@app.command("audit")
def audit_cmd(
    strict: bool = typer.Option(False, "--strict", help="Fail if any warning check fails"),
    no_network: bool = typer.Option(True, "--no-network", help="Disable checks requiring external network"),
):
    """Runs universal automated checks (secrets, lockfiles, undeclared imports)."""
    root = find_project_root()
    from valdoz.checks import run_valdoz_audit

    report = run_valdoz_audit(root, strict=strict, no_network=no_network)
    table = Table(title="ValdoZ Universal Audit")
    table.add_column("Check ID", style="cyan")
    table.add_column("Description")
    table.add_column("Severity", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Result", justify="center")
    table.add_column("Message")

    for c in report.checks:
        res_str = (
            "[dim]SKIPPED[/dim]" if c.status == "skipped"
            else ("[bold green]PASS[/bold green]" if c.passed
                  else ("[bold red]FAIL[/bold red]" if c.severity == "blocking" else "[yellow]WARN[/yellow]"))
        )
        sev_color = "red" if c.severity == "blocking" else "yellow"
        table.add_row(
            c.id,
            c.name,
            f"[{sev_color}]{c.severity}[/{sev_color}]",
            c.status,
            res_str,
            c.message,
        )

    console.print(table)
    if report.passed:
        console.print("\n[bold green]✓ ValdoZ Audit Passed![/bold green]")
    else:
        console.print("\n[bold red]✗ ValdoZ Audit Failed![/bold red] Resolve blocking issues above.")
        raise typer.Exit(1)


# ── Pack Commands ───────────────────────────────────────────────────────────
@pack_app.command("list")
def pack_list_cmd():
    """Lists available built-in packs and active project packs."""
    root = find_project_root()
    from valdoz.packs import BUILTIN_PACKS
    try:
        state = load_state(root)
        active_ids = set(state.packs)
    except Exception:
        active_ids = {"base"}

    table = Table(title="Available Stack & Project Packs")
    table.add_column("Pack ID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Version", justify="center")
    table.add_column("Active", justify="center")
    table.add_column("Description")

    for pid, p in BUILTIN_PACKS.items():
        is_active = pid in active_ids
        table.add_row(
            pid,
            p.name,
            p.version,
            "[bold green]YES[/bold green]" if is_active else "[dim]NO[/dim]",
            p.description,
        )
    console.print(table)


@pack_app.command("add")
def pack_add_cmd(
    pack_id: str = typer.Argument(..., help="Pack identifier to enable (e.g., web-app, api, website)"),
):
    """Enables a stack pack for the current project."""
    root = find_project_root()
    from valdoz.packs import BUILTIN_PACKS, PackError
    try:
        state = load_state(root)
    except StateError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    pid = pack_id.lower().strip()
    if pid not in BUILTIN_PACKS:
        console.print(f"[bold red]Unknown pack:[/bold red] '{pid}'. Run 'valdoz pack list' to view available packs.")
        raise typer.Exit(1)

    if pid in state.packs:
        console.print(f"[yellow]Pack '{pid}' is already enabled.[/yellow]")
        return

    state.packs.append(pid)
    save_state(root, state)
    console.print(f"[bold green]Enabled pack '{pid}' ({BUILTIN_PACKS[pid].name})![/bold green]")


# ── Hook Commands ───────────────────────────────────────────────────────────
@hook_app.command("install")
def hook_install_cmd():
    """Installs the ValdoZ pre-commit hook into .git/hooks/pre-commit."""
    root = find_project_root()
    from valdoz.integration import install_git_hook
    try:
        hook_path = install_git_hook(root)
        console.print(f"[bold green]Pre-commit hook installed successfully at:[/bold green] [cyan]{hook_path}[/cyan]")
        console.print("Enforces: role domain separation (builder vs scribe), gate checks, and audit.")
    except Exception as e:
        console.print(f"[bold red]Hook installation failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── CI Commands ─────────────────────────────────────────────────────────────
@ci_app.command("generate")
def ci_generate_cmd():
    """Generates the GitHub Actions CI workflow template at .github/workflows/valdoz.yml."""
    root = find_project_root()
    from valdoz.integration import install_ci_workflow
    try:
        wf_path = install_ci_workflow(root)
        console.print(f"[bold green]GitHub Actions CI workflow generated at:[/bold green] [cyan]{wf_path}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]CI generation failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── Doctor Command ──────────────────────────────────────────────────────────
@app.command("doctor")
def doctor():
    """Runs health check on ValdoZ configuration, environment, and Python drift."""
    root = find_project_root()
    state_file = get_state_path(root)

    console.print(f"[bold cyan]ValdoZ Doctor v{__version__}[/bold cyan]")
    console.print(f"Project root: {root}")

    # Check Python version drift
    py_ver = sys.version.split()[0]
    console.print(f"Python interpreter: {sys.executable} (v{py_ver})")
    installed_py_file = root / ".valdoz" / "python_version.txt"
    if installed_py_file.exists():
        installed_py = installed_py_file.read_text().strip()
        if installed_py != py_ver:
            console.print(
                f"  [bold yellow]! Python Version Drift Detected:[/bold yellow] "
                f"Project initialized with Python {installed_py}, currently running on {py_ver}."
            )
        else:
            console.print("  [green]✓[/green] Python version matches project initialization.")
    else:
        # Record current version
        if (root / ".valdoz").exists():
            installed_py_file.write_text(py_ver, encoding="utf-8")

    # Check state file
    if state_file.exists():
        console.print("  [green]✓[/green] state.json exists")
        protected = is_write_protected(state_file)
        console.print(f"  [{'green' if protected else 'yellow'}]{'✓' if protected else '!'}[/] Write protection: {'Active (read-only)' if protected else 'Not active'}")
    else:
        console.print("  [yellow]![/yellow] state.json not found (Run 'valdoz project init')")

    # Check sessions
    active = get_active_sessions(root)
    console.print(f"  [green]✓[/green] Active agent sessions: {len(active)}")

    # Check staleness
    stale = check_research_staleness(root)
    if stale:
        console.print(f"  [bold yellow]! Stale research items detected: {len(stale)}[/bold yellow]")
        for s in stale:
            console.print(f"    - {s['id']}: '{s['claim']}' is {s['age_days']} days old (limit: {s['valid_for_days']}d)")
    else:
        console.print("  [green]✓[/green] Research citations up to date.")
