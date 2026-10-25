# The Complete ValdoZ Protocol v3.0 User Guide

> **A practical, step-by-step handbook for human tech leads and Google Antigravity pair programming.**

---

## Table of Contents
1. [What is ValdoZ? (The 30-Second Mental Model)](#1-what-is-valdoz-the-30-second-mental-model)
2. [Quick Setup & Intelligent Project Initialization](#2-quick-setup-intelligent-project-initialization)
3. [The Core Concept: Builder & Scribe Roles](#3-the-core-concept-builder-scribe-roles)
4. [The 11 Lifecycle Phases (Phase 0-10 Cheat Sheet)](#4-the-11-lifecycle-phases-phase-0-10-cheat-sheet)
5. [Daily Operating Loop: Step-by-Step](#5-daily-operating-loop-step-by-step)
6. [Phase 6: Mastering Build Slices](#6-phase-6-mastering-build-slices)
7. [Universal Hygiene & Automated Remediation](#7-universal-hygiene-automated-remediation)
8. [Stack Packs & Ecosystem Marketplace Plugins](#8-stack-packs-ecosystem-marketplace-plugins)
9. [100% In-Antigravity Native Management (Zero Terminal Switching)](#9-100-in-antigravity-native-management-zero-terminal-switching)
10. [Autonomous Self-Healing Engine (CI/CD & Local Gates)](#10-autonomous-self-healing-engine-cicd-local-gates)
11. [Emergency Recovery & Troubleshooting](#11-emergency-recovery-troubleshooting)
12. [Complete CLI Command Reference](#12-complete-cli-command-reference)

---

## 1. What is ValdoZ? (The 30-Second Mental Model)

Autonomous AI coding agents like **Google Antigravity** are fast, but left unconstrained they sprint past key decisions:
- They assume requirements instead of asking.
- They invent packages, APIs, or URLs that don't exist.
- They mark tasks "done" without running real tests.
- They can bypass safety gates by running arbitrary terminal commands.

**ValdoZ Protocol** is the discipline harness. It acts as an experienced Tech Lead standing next to the agent:
1. **Phase-Gated Delivery**: The agent cannot jump ahead. Work progresses through 11 ordered phases (Phase 0: Init $\rightarrow$ Intake $\rightarrow$ Requirements $\rightarrow$ Stack $\rightarrow$ Architecture $\rightarrow$ Setup $\rightarrow$ Build Slices $\rightarrow$ Verify $\rightarrow$ Deploy $\rightarrow$ Handover $\rightarrow$ Phase 10: Changes).
2. **Evidence Over Claims**: "Done" means actual commands ran, tests passed, and deliverables exist with no placeholders (`TODO`, `TBD`).
3. **Human Gatekeeper**: At the end of every phase, the agent stops cold. Only **you** (an interactive human terminal) can approve work. The agent cannot approve its own code.
4. **Tamper-Proof State**: Approved deliverables are cryptographically hashed (SHA-256) and `state.json` is write-protected (`chmod 444`). If files are silently edited later, gates fail immediately.

---

## 2. Quick Setup & Intelligent Project Initialization

### Installation

ValdoZ can be installed globally as an isolated CLI tool using **uv** (recommended), **pipx**, or standard **pip**.

#### Prerequisites: Install `uv` (if not already installed)
```bash
# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

#### Method 1: Local Source Installation (Recommended for Development)
From inside the `valdoz` repository directory:
```bash
cd /path/to/valdoz

# Install globally in editable mode (updates live as you edit source):
uv tool install --editable . --force

# Or standard global tool install:
uv tool install . --force
```

*Alternative with `pipx` or `pip`:*
```bash
# Using pipx:
pipx install .

# Or inside an active virtual environment:
pip install -e .
```

---

#### Method 2: From Remote Git Repository (Once Hosted on GitHub/GitLab)
```bash
# Install directly from git:
uv tool install git+https://github.com/<your-username>/valdoz.git --force
```

---

#### Method 3: From PyPI Registry (Once Published)
```bash
# Public PyPI package:
uv tool install valdoz-protocol

# Or with pipx:
pipx install valdoz-protocol
```

---

### Post-Installation & Antigravity Setup

1. **Verify CLI Installation**:
   ```bash
   valdoz --version
   # Output: ValdoZ Protocol version 3.0.0
   ```

2. **Register ValdoZ with Google Antigravity**:
   To enable native tool calling, automated auditing, and in-chat self-healing inside Antigravity:
   ```bash
   valdoz mcp register
   ```
   *This writes the MCP server configuration into `~/.gemini/config/mcp_config.json`.*

### Intelligent Project Initialization (`valdoz project init`)
ValdoZ is not a rigid one-size-fits-all checklist. It features an **Intelligent Project Scanner** that inspects your repository when initialized, detects its maturity archetype, and automatically routes you to the right starting phase:

```bash
cd /path/to/your-project

# Run intelligent initialization
valdoz project init
```

#### How the Scanner Categorizes Projects:
1. **🌱 Greenfield (Brand New Projects)**:
   - *Signals*: Empty or minimal directory, no prior source files or manifests.
   - *Action*: Starts cleanly at **Phase 0 (Init)**.

2. **🏗️ Brownfield (Active In-Development Projects)**:
   - *Signals*: Existing source files (`src/`), tests (`pytest`, `jest`), manifests (`package.json`, `pyproject.toml`), and lockfiles.
   - *Action*: Detects that setup, architecture, and stack decisions are already satisfied. Pre-approves earlier phases as `approved (by: auto-scanner)` and places the project directly into **Phase 6 (Build Slices)** or **Phase 7 (Verify)**.

3. **🚀 Production (Live Deployed Systems)**:
   - *Signals*: Mature git history (100+ commits), deployment infrastructure (`Dockerfile`, `docker-compose.yml`, `k8s/`, `terraform`), and active CI pipelines.
   - *Action*: Skips initial development ceremony and auto-places directly into **Phase 10 (Change Requests & Operations)**.

#### Automatic Remediation During Init:
During initialization, the scanner automatically identifies hygiene risks and triggers remediations on the fly:
- If an unignored `.env` file is found, it adds it to `.gitignore` to prevent credential leaks.
- If a manifest exists without a lockfile, it triggers lockfile generation.

#### CLI Options for Init:
```bash
# Initialize for Arabic client-facing deliverables:
valdoz project init --lang ar

# Explicitly name your project:
valdoz project init --name "my-saas-platform"

# Skip the intelligent scanner and force Phase 0:
valdoz project init --skip-scan
```

### Sync Antigravity Runtimes & Install Hooks
```bash
# 1. Generate Antigravity rules and skill playbooks (.agent/skills/):
valdoz sync-runtimes

# 2. Install Git hooks (enforces role boundaries, gate checks, and production push protection):
valdoz hook install

# 3. Optional: Generate GitHub Actions CI verification:
valdoz ci generate
```

#### Git Hooks Installed by `valdoz hook install`:
- **`pre-commit`**: Prevents role domain violations (`builder` editing docs or `scribe` editing code), runs fast audit, and verifies gate requirements before each commit.
- **`pre-push`**: Intercepts `git push` targeting `main`, `master`, `production`, or `release/*`. Because cloud platforms (Vercel, AWS, Fly, Netlify) automatically deploy pushes on these branches directly to Live, direct pushes are **blocked** unless the project is formally in Phase 8 (Deploy) and human-approved. Work must be pushed on slice/feature branches (`slice/<id>`).

---

## 3. The Core Concept: Builder & Scribe Roles

Antigravity 2.0 can run multiple subagents concurrently. To prevent race conditions and file collisions, ValdoZ divides work into two non-overlapping roles:

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│          BUILDER AGENT          │       │          SCRIBE AGENT           │
├─────────────────────────────────┤       ├─────────────────────────────────┤
│ Writes:                         │       │ Writes:                         │
│ • src/ (application code)       │       │ • docs/ (specifications)        │
│ • tests/ (test suites)          │       │ • decisions.jsonl & research    │
│ • package manifests             │       │ • CHANGELOG.md & PR notes       │
│ • .valdoz/slices/ (build state) │       │                                 │
│                                 │       │ Reads:                          │
│ Executes:                       │       │ • src/ (read-only inspection)   │
│ • build & test runners          │       │                                 │
└─────────────────────────────────┘       └─────────────────────────────────┘
```

### Starting an Agent Session
Before an agent starts working, it declares its role:
```bash
# If coding or running tests:
valdoz session start --role builder

# If writing specs, intake notes, or documentation:
valdoz session start --role scribe
```
ValdoZ locks `.valdoz/session.lock`. Two builders cannot conflict on the same repo, and git commits that violate role domains are blocked by the pre-commit hook.

---

## 4. The 11 Lifecycle Phases (Phase 0-10 Cheat Sheet)

| Phase | Name | What Happens | What You Deliver |
|---|---|---|---|
| **0** | **Init** | Repo setup, stack packs chosen | `.valdoz/state.json` |
| **1** | **Intake** | Client brief quoted verbatim, risks, assumptions | `docs/01-intake.md` |
| **2** | **Requirements** | Functional/non-functional specs, acceptance criteria | `docs/02-requirements.md` |
| **3** | **Stack Decision** | Compare 2–3 options, trade-offs, pinned versions | `docs/03-stack-decision.md` + decision log |
| **4** | **Architecture** | Data models, API contracts, auth, slice plan | `docs/04-architecture.md`, `docs/04-plan.md` |
| **5** | **Setup** | Tooling, linter, test runner, CI config, `.env.example` | Working empty repo, passing tests |
| **6** | **Build Slices** | Repeatable TDD slices: spec $\rightarrow$ tests $\rightarrow$ code | `docs/slices/NN-name.md`, code, tests |
| **7** | **Verify** | Full test suite, security checklist, accessibility | `docs/07-verification.md` |
| **8** | **Deploy** | Deployment steps, live health proof, rollback plan | `docs/08-deploy.md` (IRREVERSIBLE) |
| **9** | **Handover** | Runbook, access credentials transfer, client sign-off | `docs/09-handover.md` (IRREVERSIBLE) |
| **10** | **Changes** | Post-launch change requests | `docs/changes/CR-NNN.md` |

---

## 5. Daily Operating Loop: Step-by-Step

Whenever you or Antigravity work on a project, follow this simple 5-step loop:

### Step 1: Check Where You Are
Never guess the current phase. Run:
```bash
valdoz phase status
```
This displays:
- Active phase and its status (`in_progress`, `approved`, etc.)
- Required deliverable files (green `✓` if present, red `✗` if missing)
- Permitted command whitelist for that phase

### Step 2: Work on the Deliverable
Have Antigravity draft the deliverable in `docs/` according to the phase playbook.
- If Antigravity needs to research online:
  ```bash
  # Pre-log the URL first (defense against malicious injections):
  valdoz research log --url "https://api.stripe.com" --claim "OAuth token requirements"
  
  # Fetch sanitized content:
  valdoz research fetch "https://api.stripe.com"
  
  # Log verified findings:
  valdoz research add -u "https://api.stripe.com" -c "Stripe requires PKCE flow for native apps"
  ```
- If an architectural choice is made:
  ```bash
  valdoz decision add -q "PostgreSQL vs DynamoDB?" -c "PostgreSQL" -r "Relational transactions required"
  ```

### Step 3: Run the Gate Check
Before asking for approval, verify that all deliverable requirements pass:
```bash
valdoz gate check
```
The gate checks:
- Deliverable files exist
- All required headings are present (English or Arabic)
- No `TODO`, `TBD`, `lorem ipsum` remain
- All external URLs were pre-logged
- Prior approved deliverables were not tampered with

### Step 4: Human Interactive Approval
Once `valdoz gate check` passes, Antigravity **must stop and ask for your approval**.
You run:
```bash
valdoz phase approve
```
You will be prompted:
`Type phase name 'intake' to approve:`

On approval:
- ValdoZ computes SHA-256 hashes of the deliverables.
- `state.json` is write-protected (`chmod 444`).
- An immutable audit entry is written to `.valdoz/approvals.log`.

### Step 5: Advance to the Next Phase
```bash
valdoz phase next
```
ValdoZ prepares deliverable stubs for the next phase and sets it to `in_progress`.

---

## 6. Phase 6: Mastering Build Slices

Most coding happens in **Phase 6 (Build)**. Instead of letting an agent write an entire application at once, ValdoZ breaks the work into small, reviewed **slices** (e.g. `01-user-auth`, `02-billing`, `03-dashboard`).

Each slice moves through 4 states:
```
[open]  ───>  [built]  ───>  [gated]  ───>  [approved]
```

### The 4 Slice Steps

#### 1. Open a Slice
Write the slice specification in `docs/slices/01-auth.md` with 4 required sections:
- `## Summary`
- `## Acceptance Criteria`
- `## Test Plan`
- `## File Manifest`

Then run:
```bash
valdoz slice start 01-auth
```
*ValdoZ enforces: slice 01 must be approved before slice 02 can start.*

#### 2. Implement Tests & Code (TDD)
The builder agent writes tests in `tests/`, then implements the code in `src/`.

#### 3. Complete the Slice
When tests pass, run:
```bash
valdoz slice done 01-auth
```
ValdoZ verifies the **Three Slice Gate Conditions**:
1. Pre-existing tests before the slice still pass.
2. New tests added in the slice pass.
3. Test coverage has not dropped below baseline.

#### 4. Human Slice Approval
Review the git diff and approve:
```bash
valdoz slice approve 01-auth
```
*(Prompts for confirmation; locks `.valdoz/slices/01-auth.json` to read-only).*

Now you are ready to open slice `02-billing`!

---

## 7. Universal Hygiene & Automated Remediation

At any time, you can run a full code audit across your project:
```bash
valdoz audit
```
ValdoZ automatically checks:
- **Secrets Scan**: Scans for hardcoded AWS keys, OpenAI keys, private keys, and `.env` files (distinguishes safely gitignored local files from exposed files).
- **Lockfile Check**: Verifies that `package-lock.json`, `uv.lock`, etc. are committed and dependencies are pinned.
- **Undeclared Imports**: Scans Python and JavaScript files to verify that all imported modules are declared in your package manifests (`pyproject.toml`, `package.json`).

### Automated Issue Remediation (`valdoz audit --fix`)
Instead of just reporting audit failures, ValdoZ can automatically fix common hygiene issues for you:
```bash
valdoz audit --fix
```
What `--fix` automatically remediates:
- **Exposed `.env` files**: Automatically appends `.env` to `.gitignore` and untracks it from git cache if accidentally tracked (`git rm --cached .env`).
- **Missing lockfiles**: Automatically generates `package-lock.json` via `npm install --package-lock-only` (or `uv.lock` via `uv lock`) when a manifest is present.
- **Re-runs audit**: Confirms that fixes resolved the blocking issues.

---

## 8. Stack Packs & Ecosystem Marketplace Plugins

ValdoZ supports composable **Packs** that extend your project with stack-specific rules, skills, and automated audit checks.

### Enabling Built-in Packs
List available packs:
```bash
valdoz pack list
```
Enable a pack (e.g., `web-app`, `api`, `website`):
```bash
valdoz pack add web-app
```

### Importing Marketplace Plugins (`wshobson/agents` Bridge)
ValdoZ can directly adapt external agentic plugins (such as marketplace plugins from `wshobson/agents` or local plugin folders):
```bash
# Import a plugin directly from the wshobson/agents marketplace
valdoz pack import wshobson/agents:code-reviewer

# Or import from a local plugin directory
valdoz pack import ./my-custom-plugin --id custom-tools
```
When imported:
1. Skills are extracted, wrapped with valid YAML frontmatter, and placed in `.agent/skills/`.
2. Rules are copied to `.agent/rules/`.
3. A `manifest.yaml` is generated in `.valdoz/packs/<id>/` with audit checks.
4. The pack is activated in `state.json` and synchronized into Antigravity runtimes.

### Programmatic Google Antigravity SDK Agents
If you run automated Antigravity agents via the official Python SDK (`google-antigravity`), ValdoZ exposes native tool definitions for direct agent invocation:

```python
from google import antigravity
from valdoz.sdk_bridge import get_valdoz_native_tools

# Register ValdoZ enforcement tools (valdoz_gate_check, valdoz_slice_done, valdoz_research_log)
native_tools = get_valdoz_native_tools()
```

### Zero-Cost LLM Testing via FreeLLMAPI
During development and milestone testing, avoid racking up commercial API bills by routing agent requests through a local FreeLLMAPI proxy (providing 358 free endpoints):

```python
from valdoz.sdk_bridge import get_freellmapi_config

# Generates zero-persistence OpenAI-compatible client configuration
config = get_freellmapi_config(base_url="http://localhost:8000/v1")
```

---

## 9. 100% In-Antigravity Native Management (Zero Terminal Switching)

With ValdoZ Protocol v3.0, you **never need to switch back and forth between Antigravity and your shell terminal**. The entire protocol lifecycle can be commanded, monitored, and approved directly within the Antigravity conversation interface.

### Registering the ValdoZ MCP Server
Run once to integrate ValdoZ directly into Antigravity's Model Context Protocol (MCP) tool registry:
```bash
valdoz mcp register
```
This writes the tool configuration to `~/.gemini/config/mcp_config.json`. Antigravity now natively has access to:
- `valdoz_get_status`: Inspects active phase, deliverable checklist, and command whitelist.
- `valdoz_run_audit`: Runs code audits with optional `--fix` auto-remediation directly in chat.
- `valdoz_check_gates`: Verifies deliverable completeness and absence of placeholders.
- `valdoz_slice_ops`: Starts, completes, and tracks Phase 6 TDD build slices.
- `valdoz_request_human_approval`: Generates an in-chat interactive human gate prompt and issues a human token.
- `valdoz_approve_with_human_token`: Submits cryptographically verified human token to approve phases.
- `valdoz_heal`: Triggers autonomous AI diagnosis and remediation for failed gates, audits, slices, or CI.

### The In-Chat Human Approval Bridge
Historically, gates required an interactive terminal (`sys.stdin.isatty()`) to prevent automated AI self-approval. 

ValdoZ now features a **Human Non-Repudiation In-Chat Bridge**:
1. When Antigravity completes deliverables for a phase, it prompts you in the chat with a summary.
2. An interactive confirmation modal (`ask_question` or user decision) prompts you to confirm approval.
3. Upon your explicit selection, a secure cryptographic verification token is issued (`valdoz-human-phase-<N>-<timestamp>`), allowing the phase to be approved without leaving the conversation.
4. **Security Guarantee Preserved**: The AI agent cannot fabricate this token on its own; it requires explicit human interaction.

### Live Generative UI Dashboard
You can render a real-time, theme-aware visual dashboard directly in Antigravity chat:
```bash
valdoz dashboard
```
This renders:
- An interactive 10-phase progression breadcrumb stepper.
- Real-time status for all deliverables (green `✓` vs amber `MISSING`).
- Active role lock indicator (Builder vs Scribe).
- Phase 6 TDD slice execution tracker.

---

## 10. Autonomous Self-Healing Engine (CI/CD & Local Gates)

Inspired by the freeCodeCamp course *Build a Self-Healing CI/CD Pipeline with AI*, ValdoZ Protocol features an **autonomous diagnosis and remediation loop** for both local terminal operations and cloud CI/CD pipelines.

### Local Self-Healing (`valdoz heal`)
When a gate check, audit, or build slice fails, you can trigger the self-healing engine:
```bash
# Auto-heal gate check failures
valdoz heal gate

# Auto-heal audit failures
valdoz heal audit

# Auto-heal Phase 6 build slice failures
valdoz heal slice --slice-id 01-user-auth

# Auto-heal CI failure from diagnostic log file
valdoz heal ci --log-file .valdoz/ci-logs/failure.txt
```
During slice execution, you can also enable auto-healing automatically on failure:
```bash
valdoz slice done 01-user-auth --auto-heal
```

#### How the Healing Loop Works:
1. **Context Collection**: Extracts exact failure tracebacks, recent git diffs, implicated files, and slice specifications.
2. **AI Root-Cause Diagnosis**: Analyzes why the failure occurred and formulates a minimal patch.
3. **Targeted Code Application**: Applies the fix to the offending files.
4. **Mechanical Re-Verification**: Automatically re-runs gate conditions or test suites.
5. **Human Gate Intact**: Once passing, a `HealingReport` is generated for the human Tech Lead to review and approve before advancing.

---

### Self-Healing CI/CD Pipeline (`valdoz ci generate --self-healing`)
Generate a self-healing GitHub Actions workflow:
```bash
valdoz ci generate --self-healing
```
When generated with `--self-healing`, the workflow includes a dedicated `self-heal` job that executes automatically if `valdoz-gate` fails:
- Fetches the failure logs from the GitHub Actions run.
- Runs `valdoz audit --fix` and `valdoz heal ci --log-file .valdoz/ci-logs/failure.txt`.
- Automatically opens a **Pull Request** (`fix/valdoz-auto-heal-<run_id>`) containing the fix and root-cause analysis for team review!

---

## 11. Emergency Recovery & Troubleshooting

### If an Approved Phase Needs Changes (`reopen`)
If a discovery in Phase 6 requires modifying the Architecture from Phase 4:
```bash
valdoz phase reopen 4
```
- Voids approval hashes for Phase 4.
- Marks downstream phases (5 and 6) as `pending_reapproval`.
- If reopening **Phase 8 (Deploy)**, ValdoZ warns that live cloud resources cannot be undone, requires typing the project name to confirm, and automatically creates a Change Request stub in `docs/changes/CR-001-reopen-phase8.md`.

### If `state.json` is Corrupted or Accidentally Deleted
ValdoZ can reconstruct the entire project state from git history:
```bash
valdoz state repair
```
Reads commit history, existing documents, and `.valdoz/approvals.log` to restore `state.json` and re-applies write protection.

### If an Agent Session Crashes (Stuck Lock)
If an agent terminal crashed without calling `session end`:
```bash
valdoz session clear
```

### Health Checkup
```bash
valdoz doctor
```
Checks virtualenv status, Python version drift, state write protection, and staleness of cited research.

---

## 12. Complete CLI Command Reference

| Command | Description |
|---|---|
| `valdoz --version` | Display ValdoZ version. |
| `valdoz project init [--name <n>] [--lang ar] [--skip-scan]` | Intelligent init: scans project maturity, auto-places phase, applies fixes. |
| `valdoz mcp register` | Register ValdoZ MCP server into `~/.gemini/config/mcp_config.json`. |
| `valdoz mcp run` | Launch standard stdio Model Context Protocol (MCP) server. |
| `valdoz dashboard [--output <file>]` | Generate live Generative UI interactive dashboard HTML. |
| `valdoz heal [gate\|audit\|slice\|ci] [--slice-id <id>] [--log-file <path>]` | Run autonomous AI diagnosis and self-healing for failed gates/audits/slices/CI runs. |
| `valdoz sync-runtimes [--dry-run]` | Generate Antigravity rules and skill playbooks. |
| `valdoz hook install` | Install Git pre-commit and pre-push hooks (role separation + live push protection). |
| `valdoz ci generate [--self-healing]` | Generate GitHub Actions CI workflow (with optional self-healing PR recovery). |
| `valdoz session start --role <builder\|scribe>` | Acquire active agent session role lock. |
| `valdoz session end --role <role>` | Release active session role lock. |
| `valdoz session status` | Show currently active agent sessions. |
| `valdoz session clear` | Clear stale session locks. |
| `valdoz phase status` | View current phase, required deliverables, and whitelist. |
| `valdoz phase next` | Advance to the next phase after approval. |
| `valdoz phase approve` | Human-only interactive TTY or in-chat approval of deliverables. |
| `valdoz phase reopen <N>` | Reopen a past phase and void downstream approvals. |
| `valdoz gate check [--ci] [--dry-run]` | Run deliverable, heading, placeholder, and citation checks. |
| `valdoz slice start <id>` | Open a Phase 6 build slice. |
| `valdoz slice done <id> [--auto-heal]` | Check 3 slice gate conditions; optionally auto-heal failures. |
| `valdoz slice approve <id>` | Human-only interactive approval of a build slice. |
| `valdoz slice status` | List all slices and their states. |
| `valdoz decision add -q <q> -c <choice> -r <why>` | Append to `decisions.jsonl` and update `decisions.md`. |
| `valdoz research log -u <url> -c <claim>` | Pre-log fetch intent (Gap 4 security defense). |
| `valdoz research fetch <url>` | Safely fetch and boundary-wrap external web content. |
| `valdoz research add -u <url> -c <claim>` | Log verified research citation. |
| `valdoz audit [--fix] [--strict] [--no-network]` | Run code hygiene audit; `--fix` auto-remediates secrets & missing lockfiles. |
| `valdoz pack list` | List available and active stack packs. |
| `valdoz pack add <pack_id>` | Enable a stack pack (e.g., `web-app`, `api`, `website`). |
| `valdoz pack import <source> [--id <id>]` | Import plugin from local dir or `wshobson/agents:<plugin>`. |
| `valdoz state repair` | Reconstruct `state.json` from git history. |
| `valdoz doctor` | Run environment diagnostics and Python drift checks. |
