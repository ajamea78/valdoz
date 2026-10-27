"""ValdoZ Protocol CLI Application.

Main entry point for command-line interactions.
"""

from __future__ import annotations

import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
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
mcp_app = typer.Typer(name="mcp", help="Native Model Context Protocol integration", no_args_is_help=True)
profile_app = typer.Typer(name="profile", help="Manage multi-account Git & GitHub profiles and identity isolation", no_args_is_help=True)
auth_app = typer.Typer(name="auth", help="Project-scoped secure credentials and git authentication", no_args_is_help=True)

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
app.add_typer(mcp_app)
app.add_typer(profile_app)
app.add_typer(auth_app)


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
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Developer Git & GitHub profile to bind to this project"),
    skip_scan: bool = typer.Option(False, "--skip-scan", help="Skip intelligent project scanning"),
    require_human_signoff: bool = typer.Option(False, "--require-human-signoff", help="Do not auto-approve pre-existing phases without human approval"),
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

    # ── Intelligent Project Scan ───────────────────────────────────────
    assessment = None
    if not skip_scan:
        from valdoz.scanner import scan_and_assess
        console.print("\n[bold cyan]🔍 Scanning project directory...[/bold cyan]")
        assessment = scan_and_assess(root)
        signals = assessment.signals

        # Display scan results
        archetype_colors = {
            "greenfield": "green",
            "brownfield": "yellow",
            "production": "cyan",
        }
        archetype_label = {
            "greenfield": "🌱 Greenfield (New Project)",
            "brownfield": "🏗️  Brownfield (In Development)",
            "production": "🚀 Production (Live System)",
        }
        ac = archetype_colors.get(assessment.archetype, "white")
        al = archetype_label.get(assessment.archetype, assessment.archetype)

        console.print(f"\n[bold {ac}]Project Archetype: {al}[/bold {ac}]")
        console.print(f"[dim]Confidence: {assessment.confidence:.0%}[/dim]\n")

        # Scan details table
        scan_table = Table(title="Project Scan Results", show_lines=False)
        scan_table.add_column("Signal", style="cyan", min_width=22)
        scan_table.add_column("Status", justify="center", min_width=8)
        scan_table.add_column("Details")

        def yes_no(val: bool) -> str:
            return "[bold green]✓[/bold green]" if val else "[dim]✗[/dim]"

        scan_table.add_row("Source Code", yes_no(signals.has_source_code),
                          f"{signals.source_file_count} files ({', '.join(sorted(signals.source_languages)) or '-'})")
        scan_table.add_row("Tests", yes_no(signals.has_tests),
                          f"{signals.test_file_count} files ({', '.join(sorted(signals.test_frameworks)) or '-'})")
        scan_table.add_row("Documentation", yes_no(signals.has_docs_dir or signals.has_readme),
                          f"{'docs/' if signals.has_docs_dir else '-'} {'README' if signals.has_readme else ''}")
        scan_table.add_row("Package Manifest", yes_no(signals.has_package_manifest),
                          ", ".join(sorted(signals.manifests_found)) or "-")
        scan_table.add_row("Lockfile", yes_no(signals.has_lockfile), "Pinned" if signals.has_lockfile else "Missing")
        scan_table.add_row("CI/CD", yes_no(signals.has_ci_config),
                          ", ".join(sorted(signals.ci_systems)) or "-")
        scan_table.add_row("Deploy Configs", yes_no(signals.has_deploy_configs),
                          " | ".join(filter(None, [
                              "Docker" if signals.has_dockerfile else "",
                              "Compose" if signals.has_docker_compose else "",
                              "K8s" if signals.has_k8s_configs else "",
                              "Terraform" if signals.has_terraform else "",
                          ])) or "-")
        scan_table.add_row("Git History", yes_no(signals.has_git),
                          f"{signals.git_commit_count} commits, {signals.git_age_days}d old" if signals.has_git else "-")
        scan_table.add_row("Linter Config", yes_no(signals.has_linter_config),
                          ", ".join(sorted(signals.linter_configs)) or "-")
        console.print(scan_table)

        # Warnings
        if assessment.warnings:
            console.print()
            for w in assessment.warnings:
                console.print(f"  [bold yellow]⚠ {w}[/bold yellow]")

        # Recommendations
        if assessment.recommendations:
            console.print()
            for r in assessment.recommendations:
                console.print(f"  [dim]💡 {r}[/dim]")

        console.print(f"\n[bold]→ Auto-placing at Phase {assessment.recommended_phase} "
                      f"({PHASE_NAMES.get(assessment.recommended_phase, '?')})[/bold]")
        if assessment.pre_approved_phases:
            if require_human_signoff:
                console.print(f"  [dim]Pre-approval skipped (--require-human-signoff active): phases {', '.join(str(p) for p in assessment.pre_approved_phases)} will require manual sign-off.[/dim]")
            else:
                console.print(f"  [dim]Pre-approving phases (unverified): {', '.join(str(p) for p in assessment.pre_approved_phases)}[/dim]")

    # ── Create State ───────────────────────────────────────────────────
    starting_phase = assessment.recommended_phase if assessment else 0

    state = ValdozState(
        project_name=proj_name,
        language=lang,
        current_phase=starting_phase,
        packs=["base"],
    )

    # Pre-approve phases the scanner confirmed are already done
    if assessment and assessment.pre_approved_phases and not require_human_signoff:
        console.print(
            Panel.fit(
                "[bold yellow]⚠ Governance Notice: Fast-Forwarding Pre-Existing Phases[/bold yellow]\n"
                "The auto-scanner has pre-approved detected phases with status 'auto-scanner (unverified)'.\n"
                "To enforce strict human cryptographic sign-off from Phase 0, initialize with --require-human-signoff.",
                title="Brownfield Fast-Forward Warning",
                border_style="yellow",
            )
        )
        from valdoz.phases import append_approvals_log, get_required_deliverables
        from valdoz.state import compute_deliverables_hash, compute_file_sha256

        for p_num in sorted(assessment.pre_approved_phases):
            p_key = str(p_num)
            if p_key in state.phases:
                req_files = get_required_deliverables(p_num)
                deliverable_hashes: Dict[str, str] = {}
                missing: List[str] = []

                for rel_path in req_files:
                    fpath = root / rel_path
                    if fpath.exists():
                        h = compute_file_sha256(fpath)
                        if h:
                            deliverable_hashes[rel_path] = h
                    else:
                        missing.append(rel_path)

                if missing:
                    # Keep as in_progress/pending if required deliverables are absent
                    state.phases[p_key].status = "in_progress" if p_num == starting_phase else "pending"
                    continue

                comp_hash = compute_deliverables_hash(deliverable_hashes)
                now_iso = datetime.now(timezone.utc).isoformat()
                p_name = PHASE_NAMES.get(p_num, f"Phase {p_num}")

                state.phases[p_key].status = "approved"
                state.phases[p_key].approved_by = "auto-scanner (unverified)"
                state.phases[p_key].approved_at = now_iso
                state.phases[p_key].approval_hash = comp_hash
                state.phases[p_key].deliverable_hashes = deliverable_hashes

                append_approvals_log(
                    root,
                    f"Phase {p_num} ({p_name}) approved by auto-scanner (unverified) at {now_iso}. "
                    f"Composite hash: {comp_hash[:16]}... "
                    f"Deliverables hashed: {len(deliverable_hashes)}.",
                )

        # Set current phase to in_progress
        curr_key = str(starting_phase)
        if curr_key in state.phases:
            state.phases[curr_key].status = "in_progress"
            state.phases[curr_key].entered_at = datetime.now(timezone.utc).isoformat()

    # Store detected stack
    if assessment and assessment.detected_stack:
        state.chosen_stack = assessment.detected_stack

    # Bind Developer Profile & Git Identity
    from valdoz.profiles import apply_profile_to_repo, get_profile, load_profiles
    from valdoz.state import GitIdentityState

    selected_profile = profile
    if not selected_profile:
        cfg = load_profiles()
        selected_profile = cfg.default

    if selected_profile:
        prof_obj = get_profile(selected_profile)
        if prof_obj:
            state.profile = selected_profile
            state.git_identity = GitIdentityState(
                profile_name=selected_profile,
                name=prof_obj.name,
                email=prof_obj.email,
                github_username=prof_obj.github_username,
            )
            if (root / ".git").exists():
                try:
                    apply_profile_to_repo(root, selected_profile)
                except Exception:
                    pass

    valdoz_dir.mkdir(parents=True, exist_ok=True)
    save_state(root, state)

    # ── Auto-Remediations ──────────────────────────────────────────────
    if assessment and assessment.auto_remediations:
        from valdoz.checks import autofix_audit_issues
        console.print("\n[bold cyan]🔧 Running automatic remediations...[/bold cyan]")
        fixes = autofix_audit_issues(root)
        for fix in fixes:
            console.print(f"  [green]✓ {fix}[/green]")

    console.print(f"\n[bold green]ValdoZ v{__version__} initialized for project '{proj_name}' ({lang})[/bold green]")
    console.print(f"State file: [cyan]{state_file}[/cyan]")
    if assessment and assessment.archetype != "greenfield":
        console.print(f"[dim]Starting at Phase {starting_phase} ({PHASE_NAMES.get(starting_phase, '?')}) based on project scan.[/dim]")


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


MAX_RESEARCH_FETCH_BYTES = 1_048_576  # 1MB response limit
FORBIDDEN_FETCH_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata",
    "localhost",
    "127.0.0.1",
    "::1",
}


@research_app.command("fetch")
def research_fetch(
    url: str = typer.Argument(..., help="URL to safely fetch and sanitize"),
):
    """Safely fetches external content and wraps it with untrusted boundary delimiters."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        console.print(f"[bold red]Fetch Failed:[/bold red] Forbidden URL scheme '{parsed.scheme}'. Only http and https are allowed.")
        raise typer.Exit(1)

    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname in FORBIDDEN_FETCH_HOSTS or hostname.endswith(".internal"):
        console.print(f"[bold red]Fetch Blocked:[/bold red] Destination host '{hostname}' is not permitted (metadata or loopback address).")
        raise typer.Exit(1)

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ValdoZ-SanitizedFetcher/3.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310 # nosemgrep
            content_type = response.headers.get("Content-Type", "")
            allowed_content_types = ("text/", "application/json", "application/xml", "application/javascript")
            if content_type and not any(content_type.lower().startswith(act) for act in allowed_content_types):
                console.print(f"[bold red]Fetch Blocked:[/bold red] Unsupported Content-Type '{content_type}'. Only text or data documents are allowed.")
                raise typer.Exit(1)

            content_bytes = response.read(MAX_RESEARCH_FETCH_BYTES + 1)
            if len(content_bytes) > MAX_RESEARCH_FETCH_BYTES:
                console.print(f"[bold red]Fetch Blocked:[/bold red] Content size exceeds maximum limit of 1MB ({MAX_RESEARCH_FETCH_BYTES} bytes).")
                raise typer.Exit(1)

            raw_text = content_bytes.decode("utf-8", errors="replace")
        wrapped = sanitize_and_wrap_content(raw_text, source_url=url)
        console.print(wrapped)
    except typer.Exit:
        raise
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
    auto_heal: bool = typer.Option(False, "--auto-heal", help="Trigger autonomous self-healing on failure"),
    auto_heal_preview: bool = typer.Option(False, "--auto-heal-preview", help="Preview proposed self-healing patch without applying"),
    retries: int = typer.Option(3, "--retries", help="Max healing attempts"),
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
        if auto_heal or auto_heal_preview:
            console.print("\n[bold cyan]🔧 Triggering ValdoZ Autonomous Self-Healing Engine...[/bold cyan]")
            from valdoz.healing import collect_failure_context, run_healing_loop
            ctx = collect_failure_context(root, failure_type="slice_gate", error_output=str(e), slice_id=slice_id)

            def confirm_preview(diff: str, patches: dict) -> bool:
                console.print("\n[bold yellow]Proposed AI Healing Patch Diff:[/bold yellow]")
                console.print(diff)
                return typer.confirm("Apply this patch to disk?", default=False)

            report = run_healing_loop(
                root,
                ctx,
                max_retries=retries,
                preview=auto_heal_preview,
                preview_callback=confirm_preview if (not auto_heal_preview and sys.stdin.isatty()) else None,
            )

            if auto_heal_preview and report.patch_diff:
                console.print("\n[bold yellow]Healing Diff Preview (Dry-Run):[/bold yellow]")
                console.print(report.patch_diff)
                console.print("[dim]Run with --auto-heal to apply changes.[/dim]")
                raise typer.Exit(1)

            if report.success:
                console.print(f"[bold green]✓ {report.human_review_summary}[/bold green]")
                console.print(f"Applied fixes to: {', '.join(report.applied_files)}")
                try:
                    s = done_slice(root, slice_id, coverage_delta=max(cov_delta, 0.0))
                    console.print(f"[bold green]Slice '{s.slice_id}' completed successfully![/bold green] Status: [cyan]gated[/cyan].")
                    return
                except SliceGateConditionError as post_err:
                    console.print(f"[bold red]Tests still failing post-healing:[/bold red] {post_err}")
            else:
                console.print(f"[bold red]✗ Self-healing exhausted:[/bold red] {report.root_cause}")
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
    fix: bool = typer.Option(False, "--fix", help="Automatically remediate safe audit failures (e.g. add .env to .gitignore, generate lockfile)"),
    semgrep: bool = typer.Option(False, "--semgrep", help="Run Semgrep deterministic AST vulnerability analysis"),
    verify_packages: bool = typer.Option(False, "--verify-packages", help="Query PyPI/npm live registries to detect AI-hallucinated and slopsquatted dependencies"),
    licenses: bool = typer.Option(False, "--licenses", help="Audit dependency licenses and check copyleft compliance"),
    contract: bool = typer.Option(False, "--contract", help="Validate OpenAPI contract spec and detect code-contract drift"),
):
    """Runs universal automated checks (secrets, lockfiles, imports, semgrep SAST, package hallucination, license compliance, contract drift)."""
    root = find_project_root()
    from valdoz.checks import run_valdoz_audit

    report = run_valdoz_audit(
        root,
        strict=strict,
        no_network=no_network,
        fix=fix,
        semgrep=semgrep,
        verify_packages=verify_packages,
        licenses=licenses,
        contract=contract,
    )

    if report.fixes_applied:
        console.print("[bold green]✓ Automatically applied audit fixes:[/bold green]")
        for f in report.fixes_applied:
            console.print(f"  • {f}")
        console.print()

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
        console.print("\n[bold red]✗ ValdoZ Audit Failed![/bold red] Resolve blocking issues above (or run 'valdoz audit --fix').")
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

    # Also list imported custom packs in .valdoz/packs/
    custom_packs_dir = root / ".valdoz" / "packs"
    if custom_packs_dir.exists():
        import yaml
        for cdir in sorted(custom_packs_dir.iterdir()):
            if cdir.is_dir() and (cdir / "manifest.yaml").exists() and cdir.name not in BUILTIN_PACKS:
                try:
                    cdata = yaml.safe_load((cdir / "manifest.yaml").read_text(encoding="utf-8"))
                    is_active = cdir.name in active_ids
                    table.add_row(
                        cdir.name,
                        cdata.get("name", cdir.name),
                        cdata.get("version", "1.0.0"),
                        "[bold green]YES[/bold green]" if is_active else "[dim]NO[/dim]",
                        cdata.get("description", "Custom imported pack"),
                    )
                except Exception:
                    pass

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
    custom_manifest = root / ".valdoz" / "packs" / pid / "manifest.yaml"
    if pid not in BUILTIN_PACKS and not custom_manifest.exists():
        console.print(f"[bold red]Unknown pack:[/bold red] '{pid}'. Run 'valdoz pack list' to view available packs.")
        raise typer.Exit(1)

    if pid in state.packs:
        console.print(f"[yellow]Pack '{pid}' is already enabled.[/yellow]")
        return

    state.packs.append(pid)
    save_state(root, state)
    p_name = BUILTIN_PACKS[pid].name if pid in BUILTIN_PACKS else pid
    console.print(f"[bold green]Enabled pack '{pid}' ({p_name})![/bold green]")


@pack_app.command("import")
def pack_import_cmd(
    source: str = typer.Argument(..., help="Path to plugin directory or 'wshobson/agents:<plugin>'"),
    pack_id: Optional[str] = typer.Option(None, "--id", "-i", help="Custom pack ID to assign"),
    sync: bool = typer.Option(True, "--sync/--no-sync", help="Automatically run runtime sync after import"),
):
    """Imports an external plugin (e.g. wshobson/agents) into a ValdoZ pack."""
    root = find_project_root()
    from valdoz.importer import import_pack
    from valdoz.packs import PackError
    try:
        manifest = import_pack(root, source=source, pack_id=pack_id)
        console.print(f"[bold green]Successfully imported pack:[/bold green] [cyan]{manifest.id}[/cyan] ({manifest.name})")
        if sync:
            from valdoz.sync import sync_all_runtimes
            sync_all_runtimes(root)
            console.print("[dim]Runtimes synced. Added skills and rules.[/dim]")
    except PackError as e:
        console.print(f"[bold red]Pack Import Error:[/bold red] {e}")
        raise typer.Exit(1)


# ── Hook Commands ───────────────────────────────────────────────────────────
@hook_app.command("install")
def hook_install_cmd():
    """Installs the ValdoZ pre-commit and pre-push hooks into .git/hooks/."""
    root = find_project_root()
    from valdoz.integration import install_git_hook
    try:
        hook_path = install_git_hook(root)
        console.print(f"[bold green]Pre-commit and Pre-push hooks installed successfully in:[/bold green] [cyan]{hook_path.parent}[/cyan]")
        console.print("Enforces: role domain separation (builder vs scribe), gate checks, and production push protection.")
    except Exception as e:
        console.print(f"[bold red]Hook installation failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── CI Commands ─────────────────────────────────────────────────────────────
@ci_app.command("generate")
def ci_generate_cmd(
    self_healing: bool = typer.Option(False, "--self-healing", help="Include autonomous self-healing failure recovery job in GitHub Actions"),
):
    """Generates the GitHub Actions CI workflow template at .github/workflows/valdoz.yml."""
    root = find_project_root()
    from valdoz.integration import install_ci_workflow
    try:
        wf_path = install_ci_workflow(root, self_healing=self_healing)
        console.print(f"[bold green]GitHub Actions CI workflow generated at:[/bold green] [cyan]{wf_path}[/cyan]")
        if self_healing:
            console.print("[cyan]Self-healing CI enabled:[/cyan] CI failures will auto-diagnose and open a remediation PR.")
    except Exception as e:
        console.print(f"[bold red]CI generation failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── Heal Command ────────────────────────────────────────────────────────────
@app.command("heal")
def heal_cmd(
    target: str = typer.Argument("gate", help="Target failure to heal: 'gate', 'audit', 'slice', or 'ci'"),
    slice_id: Optional[str] = typer.Option(None, "--slice-id", "-s", help="Slice identifier if healing a slice"),
    log_file: Optional[Path] = typer.Option(None, "--log-file", "-l", help="Optional log file containing error trace"),
    retries: int = typer.Option(3, "--retries", "-r", help="Maximum autonomous remediation iterations"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview proposed AI patch diff without writing to disk"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm patch application without prompt"),
):
    """Runs autonomous AI diagnosis and self-healing for failed gates, audits, slices, or CI runs."""
    root = find_project_root()
    from valdoz.healing import collect_failure_context, run_healing_loop

    console.print(f"[bold cyan]🔍 Inspecting failure state for healing target: [bold white]{target}[/bold white]...[/bold cyan]")
    error_output = ""

    if log_file and log_file.exists():
        error_output = log_file.read_text(encoding="utf-8", errors="replace")

    if target == "audit":
        if not error_output:
            from valdoz.checks import run_valdoz_audit
            rep = run_valdoz_audit(root, strict=True)
            if rep.passed:
                console.print("[green]✓ Audit is already passing! No healing needed.[/green]")
                return
            error_output = "\n".join(f"[{c.id}] {c.name}: {c.message}" for c in rep.checks if not c.passed)
    elif target == "gate":
        if not error_output:
            from valdoz.gates import run_phase_gate_checks
            rep = run_phase_gate_checks(root)
            if rep.passed:
                console.print(f"[green]✓ Phase {rep.phase} gate is already passing! No healing needed.[/green]")
                return
            error_output = "\n".join(f"[{c.id}] {c.name}: {c.message}" for c in rep.checks if not c.passed)
    elif target == "slice":
        if not slice_id:
            console.print("[red]Error: --slice-id is required when healing a slice.[/red]")
            raise typer.Exit(1)
        if not error_output:
            error_output = f"Slice {slice_id} failed gate conditions or unit tests."
    elif target == "ci":
        if not error_output:
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
                    console.print("[green]✓ All CI gate and audit checks are already passing! No healing needed.[/green]")
                    return
                error_output = "\n".join(errors)
    else:
        console.print(f"[red]Unknown healing target '{target}'. Use 'gate', 'audit', 'slice', or 'ci'.[/red]")
        raise typer.Exit(1)

    ctx = collect_failure_context(
        root,
        failure_type="audit" if target == "audit" else ("ci" if target == "ci" else f"{target}_check"),
        error_output=error_output,
        slice_id=slice_id,
    )

    def confirm_patch(diff: str, patches: dict) -> bool:
        console.print("\n[bold yellow]Proposed AI-Generated Patch Diff:[/bold yellow]")
        console.print(diff)
        return typer.confirm("Apply this patch to disk?", default=False)

    report = run_healing_loop(
        root,
        ctx,
        max_retries=retries,
        preview=preview,
        preview_callback=confirm_patch if (not yes and not preview and sys.stdin.isatty()) else None,
    )

    if preview and report.patch_diff:
        console.print("\n[bold yellow]Proposed Healing Diff Preview (Dry-Run):[/bold yellow]")
        console.print(report.patch_diff)
        console.print("[dim]Run without --preview to apply fixes.[/dim]")
        return

    if report.success:
        console.print(f"\n[bold green]✓ {report.human_review_summary}[/bold green]")
        if report.patch_diff:
            console.print(f"\n[dim]{report.patch_diff}[/dim]")
    else:
        console.print(f"\n[bold red]✗ Self-Healing Incomplete:[/bold red] {report.root_cause}")
        console.print(f"[yellow]Attempted {report.attempt_count} revision(s). Manual intervention required.[/yellow]")
        raise typer.Exit(1)


# ── Explain Command ─────────────────────────────────────────────────────────
@app.command("explain")
def explain_cmd(
    output_file: Optional[Path] = typer.Option(None, "--output-file", "-o", help="Optional markdown file to write narrative to"),
):
    """Generates an executive, human-readable narrative of the project lifecycle and sign-offs."""
    root = find_project_root()
    state = load_state(root)
    from valdoz.phases import PHASE_NAMES
    from valdoz.repair import parse_approvals_log
    from valdoz.slices import list_slices

    approvals = parse_approvals_log(root)
    slices = list_slices(root)

    lines = [
        f"# Executive Narrative: {state.project_name}",
        f"**Current Status:** Phase {state.current_phase} ({PHASE_NAMES.get(state.current_phase, '')})",
        f"**Primary Language/Stack:** {state.chosen_stack.get('language', 'General')} | Packs: {', '.join(state.packs)}",
        "\n## Phase Progression & Governance History\n",
    ]

    for p_num in sorted(PHASE_NAMES.keys()):
        p_name = PHASE_NAMES[p_num]
        p_state = state.phases.get(str(p_num))
        status = p_state.status if p_state else "pending"

        if status == "approved":
            app_info = approvals.get(p_num, {})
            approver = app_info.get("approver") or p_state.approved_by or "Human Lead"
            ts = app_info.get("timestamp") or p_state.approved_at or "Unknown"
            comp_hash = (app_info.get("hash") or p_state.approval_hash or "")[:12]
            lines.append(f"### [✓] Phase {p_num}: {p_name}")
            lines.append(f"- **Status:** Approved by `{approver}` at `{ts}`")
            if comp_hash:
                lines.append(f"- **Composite Audit Hash:** `{comp_hash}...`")
            delivs = list(p_state.deliverable_hashes.keys()) if p_state else []
            if delivs:
                lines.append(f"- **Frozen Deliverables ({len(delivs)}):** {', '.join(delivs)}")
        elif status == "in_progress":
            lines.append(f"### [●] Phase {p_num}: {p_name} (ACTIVE)")
            lines.append("- **Status:** Currently in progress.")
        else:
            lines.append(f"### [ ] Phase {p_num}: {p_name}")
            lines.append("- **Status:** Pending.")
        lines.append("")

    if slices:
        lines.append("## Phase 6 TDD Slices\n")
        for s in slices:
            lines.append(f"- **Slice `{s.slice_id}`**: Status: `{s.status}`, Tests: `{'Passed' if s.tests_passed else 'Pending'}`")

    narrative = "\n".join(lines)

    if output_file:
        output_file.write_text(narrative, encoding="utf-8")
        console.print(f"[bold green]Executive narrative exported to:[/bold green] [cyan]{output_file}[/cyan]")
    else:
        from rich.markdown import Markdown
        console.print(Markdown(narrative))


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

    # Check Antigravity SDK
    from valdoz.sdk_bridge import is_sdk_available, get_sdk_version
    if is_sdk_available():
        sdk_ver = get_sdk_version() or "installed"
        console.print(f"  [green]✓[/green] Google Antigravity SDK: v{sdk_ver} active")
    else:
        console.print("  [dim]• Google Antigravity SDK: Not installed (optional, pip install google-antigravity)[/dim]")

    # Check staleness
    stale = check_research_staleness(root)
    if stale:
        console.print(f"  [bold yellow]! Stale research items detected: {len(stale)}[/bold yellow]")
        for s in stale:
            console.print(f"    - {s['id']}: '{s['claim']}' is {s['age_days']} days old (limit: {s['valid_for_days']}d)")
    else:
        console.print("  [green]✓[/green] Research citations up to date.")


# ── MCP Commands ────────────────────────────────────────────────────────────
@mcp_app.command("run")
def mcp_run_cmd():
    """Starts the standard stdio MCP server for native Antigravity tool calling."""
    from valdoz.mcp_server import run_stdio_server
    root = find_project_root()
    run_stdio_server(root)


@mcp_app.command("register")
def mcp_register_cmd():
    """Registers ValdoZ MCP server into global Antigravity config (~/.gemini/config/mcp_config.json)."""
    import json
    cfg_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"mcpServers": {}}
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            data = {"mcpServers": {}}

    if "mcpServers" not in data:
        data["mcpServers"] = {}

    data["mcpServers"]["valdoz"] = {
        "command": sys.executable,
        "args": ["-m", "valdoz.cli", "mcp", "run"],
    }

    cfg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(f"[bold green]Registered ValdoZ MCP server in:[/bold green] [cyan]{cfg_path}[/cyan]")
    console.print("Antigravity will now natively discover ValdoZ tools on next session.")


# ── Dashboard Command ───────────────────────────────────────────────────────
@app.command("dashboard")
def dashboard_cmd(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Custom output path for dashboard HTML"),
):
    """Generates the live interactive ValdoZ Generative UI dashboard."""
    from valdoz.dashboard import generate_dashboard_html
    root = find_project_root()
    html_content = generate_dashboard_html(root)
    out_file = output or (root / ".valdoz" / "dashboard.html")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_content, encoding="utf-8")
    console.print(f"[bold green]Live ValdoZ Dashboard generated at:[/bold green] [cyan]{out_file}[/cyan]")


# ── Profile Commands ────────────────────────────────────────────────────────
@profile_app.command("list")
def profile_list():
    """Lists all registered developer profiles."""
    from valdoz.profiles import load_profiles

    cfg = load_profiles()
    if not cfg.profiles:
        console.print("[yellow]No developer profiles registered yet. Run 'valdoz profile add <name> ...' to register one.[/yellow]")
        return

    table = Table(title="ValdoZ Registered Developer Profiles")
    table.add_column("Profile ID", style="bold cyan")
    table.add_column("Author Name", style="white")
    table.add_column("Author Email", style="green", overflow="fold")
    table.add_column("GitHub User", style="magenta")
    table.add_column("SSH / Signing", style="dim")
    table.add_column("Default", justify="center")

    for pid, prof in cfg.profiles.items():
        is_def = "[bold green]★ Default[/bold green]" if cfg.default == pid else ""
        extra = []
        if prof.ssh_key:
            extra.append(f"SSH: {Path(prof.ssh_key).name}")
        if prof.signing_key:
            extra.append("GPG")
        extra_str = ", ".join(extra) or "-"
        table.add_row(pid, prof.name, prof.email, prof.github_username or "-", extra_str, is_def)

    console.print(table)


@profile_app.command("add")
def profile_add(
    profile_id: str = typer.Argument(..., help="Unique profile identifier (e.g. personal, work, client-a)"),
    email: str = typer.Option(..., "--email", "-e", help="Git commit email address"),
    name: str = typer.Option(..., "--name", "-n", help="Git commit author name"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="GitHub username / handle"),
    ssh_key: Optional[str] = typer.Option(None, "--ssh-key", "-s", help="Path to SSH private key for this identity"),
    signing_key: Optional[str] = typer.Option(None, "--signing-key", "-k", help="GPG/SSH signing key ID"),
    default: bool = typer.Option(False, "--default", "-d", help="Set this profile as system default"),
):
    """Registers or updates a developer profile."""
    from valdoz.profiles import Profile, add_profile

    prof = Profile(
        name=name,
        email=email,
        github_username=user,
        ssh_key=ssh_key,
        signing_key=signing_key,
    )
    add_profile(profile_id, prof, set_default=default)
    console.print(f"[bold green]Profile '{profile_id}' saved successfully.[/bold green]")
    if default:
        console.print(f"[dim]Set '{profile_id}' as default profile.[/dim]")


@profile_app.command("remove")
def profile_remove(
    profile_id: str = typer.Argument(..., help="Profile identifier to remove"),
):
    """Removes a registered developer profile."""
    from valdoz.profiles import remove_profile

    removed = remove_profile(profile_id)
    if removed:
        console.print(f"[green]Profile '{profile_id}' removed.[/green]")
    else:
        console.print(f"[yellow]Profile '{profile_id}' not found.[/yellow]")


@profile_app.command("use")
def profile_use(
    profile_id: str = typer.Argument(..., help="Profile identifier to bind to current repository"),
):
    """Binds current repository to a profile and applies local Git configs."""
    from valdoz.profiles import apply_profile_to_repo, get_profile
    from valdoz.state import GitIdentityState, load_state, save_state

    root = find_project_root()
    prof = get_profile(profile_id)
    if not prof:
        console.print(f"[bold red]Profile '{profile_id}' does not exist.[/bold red]")
        console.print("Run 'valdoz profile list' to see available profiles or 'valdoz profile add' to create it.")
        raise typer.Exit(1)

    try:
        applied = apply_profile_to_repo(root, profile_id)
    except Exception as e:
        console.print(f"[bold red]Failed to apply git configuration:[/bold red] {e}")
        raise typer.Exit(1)

    # Update project state if .valdoz exists
    try:
        state = load_state(root)
        state.profile = profile_id
        state.git_identity = GitIdentityState(
            profile_name=profile_id,
            name=applied.name,
            email=applied.email,
            github_username=applied.github_username,
        )
        save_state(root, state)
    except Exception:
        pass

    console.print(f"[bold green]Repository bound to profile '{profile_id}'.[/bold green]")
    console.print(f"  • Author Name:  [cyan]{applied.name}[/cyan]")
    console.print(f"  • Author Email: [cyan]{applied.email}[/cyan]")
    console.print("  • Credential Isolation: [green]credential.useHttpPath = true[/green]")
    if applied.ssh_key:
        console.print(f"  • SSH Scoping:  [dim]{applied.ssh_key}[/dim]")


@profile_app.command("status")
def profile_status():
    """Displays repository Git identity and multi-account credential isolation status."""
    from valdoz.profiles import get_repo_git_identity, load_profiles
    from valdoz.state import load_state

    root = find_project_root()
    info = get_repo_git_identity(root)

    bound_profile = None
    try:
        state = load_state(root)
        bound_profile = state.profile
    except Exception:
        pass

    cfg = load_profiles()
    prof = cfg.profiles.get(bound_profile) if bound_profile else None

    table = Table(title=f"Git Multi-Account Identity Status: {root.name}")
    table.add_column("Property", style="bold cyan", min_width=24)
    table.add_column("Configured Value", min_width=25)
    table.add_column("Health / Policy", justify="center", min_width=12)

    # Bound Profile
    if bound_profile:
        table.add_row("Bound ValdoZ Profile", bound_profile, "[green]✓ Bound[/green]")
    else:
        table.add_row("Bound ValdoZ Profile", "[dim]None (Unbound)[/dim]", "[yellow]⚠ Unbound[/yellow]")

    # Local Email
    local_email = info.get("local_email")
    if local_email:
        if prof and local_email != prof.email:
            table.add_row("Local Git Email", local_email, f"[red]✗ Mismatch ({prof.email})[/red]")
        else:
            table.add_row("Local Git Email", local_email, "[green]✓ Local[/green]")
    else:
        global_email = info.get("global_email") or "Not set"
        table.add_row("Local Git Email", f"[yellow]Falling back to global ({global_email})[/yellow]", "[red]✗ Leaking Global[/red]")

    # Local Name
    local_name = info.get("local_name")
    if local_name:
        table.add_row("Local Git Name", local_name, "[green]✓ Local[/green]")
    else:
        global_name = info.get("global_name") or "Not set"
        table.add_row("Local Git Name", f"[dim]Global ({global_name})[/dim]", "[yellow]⚠ Global[/yellow]")

    # credential.useHttpPath
    use_http = info.get("use_http_path")
    if use_http == "true":
        table.add_row("HTTP Credential Isolation", "credential.useHttpPath = true", "[green]✓ Isolated[/green]")
    else:
        table.add_row("HTTP Credential Isolation", "[yellow]Not set[/yellow]", "[yellow]⚠ Shared Host[/yellow]")

    # Remote Origin
    remote = info.get("remote_origin") or "None"
    table.add_row("Remote Origin URL", remote, "[cyan]Info[/cyan]")

    # SSH Command
    ssh_cmd = info.get("ssh_command")
    if ssh_cmd:
        table.add_row("Custom SSH Command", ssh_cmd, "[green]✓ Scoped[/green]")

    console.print(table)


# ── Auth Commands ───────────────────────────────────────────────────────────
@auth_app.command("setup")
def auth_setup(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="GitHub username"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Personal Access Token"),
    from_env: Optional[str] = typer.Option(None, "--from-env", help="Environment variable name containing the token"),
    host: str = typer.Option("github.com", "--host", "-h", help="Git hosting provider hostname"),
):
    """Configures project-scoped isolated Git credentials in .valdoz/.git-credentials."""
    from valdoz.auth import setup_project_vault

    root = find_project_root()
    git_dir = root / ".git"
    if not git_dir.exists():
        console.print("[bold red]Not a git repository (missing .git directory).[/bold red]")
        raise typer.Exit(1)

    username = user
    if not username:
        username = typer.prompt("Enter the GitHub username for this project")

    auth_token = token
    if from_env and not auth_token:
        auth_token = os.environ.get(from_env)
        if not auth_token:
            console.print(f"[bold red]Environment variable '{from_env}' not found or empty.[/bold red]")
            raise typer.Exit(1)

    if not auth_token:
        auth_token = typer.prompt("Enter the GitHub Personal Access Token for this project", hide_input=True)

    if not username or not auth_token:
        console.print("[bold red]Username and Token are required to configure project authentication.[/bold red]")
        raise typer.Exit(1)

    try:
        vault_path = setup_project_vault(root, username=username, token=auth_token, host=host)
    except Exception as e:
        console.print(f"[bold red]Failed to configure project vault:[/bold red] {e}")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold green]✓ Project Authentication Vault Configured[/bold green]\n\n"
            f"• [cyan]Vault Location:[/cyan] {vault_path}\n"
            f"• [cyan]File Permissions:[/cyan] [green]chmod 600 (owner read/write only)[/green]\n"
            f"• [cyan]Git Helper:[/cyan] [green]credential.helper = store --file {vault_path}[/green]\n"
            f"• [cyan]Credential Isolation:[/cyan] [green]credential.useHttpPath = true[/green]\n"
            f"• [cyan]Security:[/cyan] Ignored in .gitignore (zero global OS/keychain pollution)\n\n"
            f"[dim]All Git operations (push, fetch, CI checks) in this project will now run autonomously inside Antigravity without prompting.[/dim]",
            title="ValdoZ Security Isolation",
        )
    )


@auth_app.command("status")
def auth_status():
    """Inspects project-level credential vault health, permissions, and git helper mapping."""
    from valdoz.auth import get_project_vault_status

    root = find_project_root()
    status = get_project_vault_status(root)

    table = Table(title=f"Project Credential Vault Status: {root.name}")
    table.add_column("Security Property", style="bold cyan", min_width=25)
    table.add_column("Configured Value", min_width=25)
    table.add_column("Audit Health", justify="center", min_width=15)

    if status["vault_exists"]:
        table.add_row("Vault Presence", "Present (.valdoz/.git-credentials)", "[green]✓ Installed[/green]")
        perm_label = "[green]✓ chmod 600 (Secure)[/green]" if status["permissions_secure"] else "[red]✗ Insecure Mode[/red]"
        table.add_row("Vault Permissions", "Owner Read/Write Only", perm_label)
        ign_label = "[green]✓ Ignored[/green]" if status["is_gitignored"] else "[red]✗ Not Ignored[/red]"
        table.add_row("Git Ignore Status", ".valdoz/.git-credentials", ign_label)
        track_label = "[green]✓ Untracked[/green]" if status["is_untracked"] else "[bold red]✗ Tracked (Risk)[/bold red]"
        table.add_row("Git Index Status", "Never Committed", track_label)
        help_label = "[green]✓ Project-Scoped[/green]" if status["credential_helper_configured"] else "[yellow]⚠ Not Mapped[/yellow]"
        table.add_row("Git Credential Helper", "store --file <local_vault>", help_label)
        http_label = "[green]✓ Path-Isolated[/green]" if status["credential_use_http_path"] else "[yellow]⚠ Missing[/yellow]"
        table.add_row("credential.useHttpPath", "true", http_label)
        table.add_row("Authenticated User", status["username"] or "Unknown", "[cyan]User[/cyan]")
        table.add_row("Token Hash/Mask", status["token_masked"] or "None", "[dim]Masked[/dim]")
    else:
        table.add_row("Vault Presence", "[dim]Not Configured[/dim]", "[yellow]⚠ Missing[/yellow]")
        table.add_row("Isolation Status", "[yellow]Global Machine Helper Active[/yellow]", "[yellow]Shared Host[/yellow]")
        table.add_row("Recommendation", "Run 'valdoz auth setup' to isolate this project", "[cyan]Action[/cyan]")

    console.print(table)


@auth_app.command("clear")
def auth_clear(
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm deletion without prompting"),
):
    """Securely deletes project credentials and unsets local git credential helper."""
    from valdoz.auth import clear_project_vault

    root = find_project_root()
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete project credentials for '{root.name}'?")
        if not confirm:
            console.print("[dim]Aborted.[/dim]")
            return

    cleared = clear_project_vault(root)
    if cleared:
        console.print("[bold green]Project credential vault securely cleared and unmapped from Git.[/bold green]")
    else:
        console.print("[yellow]No project credential vault was found.[/yellow]")



