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

app.add_typer(phase_app)
app.add_typer(session_app)
app.add_typer(project_app)
app.add_typer(decision_app)
app.add_typer(research_app)
app.add_typer(state_app)


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
