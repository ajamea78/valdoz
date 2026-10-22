# The Complete ValdoZ Protocol v3.0 User Guide

> **A practical, step-by-step handbook for human tech leads and Google Antigravity pair programming.**

---

## 1. What is ValdoZ? (The 30-Second Mental Model)

Autonomous AI coding agents like **Google Antigravity** are fast, but left unconstrained they sprint past key decisions:
- They assume requirements instead of asking.
- They invent packages, APIs, or URLs that don't exist.
- They mark tasks "done" without running real tests.
- They can bypass safety gates by running arbitrary terminal commands.

**ValdoZ Protocol** is the discipline harness. It acts as an experienced Tech Lead standing next to the agent:
1. **Phase-Gated Delivery**: The agent cannot jump ahead. Work progresses through 10 ordered phases (Intake $\rightarrow$ Requirements $\rightarrow$ Stack $\rightarrow$ Architecture $\rightarrow$ Setup $\rightarrow$ Build Slices $\rightarrow$ Verify $\rightarrow$ Deploy $\rightarrow$ Handover).
2. **Evidence Over Claims**: "Done" means actual commands ran, tests passed, and deliverables exist with no placeholders (`TODO`, `TBD`).
3. **Human Gatekeeper**: At the end of every phase, the agent stops cold. Only **you** (an interactive human terminal) can approve work. The agent cannot approve its own code.
4. **Tamper-Proof State**: Approved deliverables are cryptographically hashed (SHA-256) and `state.json` is write-protected (`chmod 444`). If files are silently edited later, gates fail immediately.

---

## 2. Quick Setup (2-Minute Onboarding)

### Installation
ValdoZ is installed via `uv`:
```bash
# In your terminal:
curl -Lsf https://astral.sh/uv/install.sh | sh
uv tool install valdoz-protocol@3.0.0

# Verify installation:
valdoz --version
```

### Initializing a Project
Navigate to your project repository:
```bash
cd /path/to/your-project

# Initialize ValdoZ (English deliverables)
valdoz project init

# Or for Arabic client-facing deliverables:
valdoz project init --lang ar
```

This creates:
- `.valdoz/state.json`: The write-protected state machine.
- `docs/`: Deliverable templates (`01-intake.md` through `09-handover.md`).

### Sync Antigravity Runtimes & Install Hooks
```bash
# 1. Generate Antigravity rules and skill playbooks (.agent/skills/):
valdoz sync-runtimes

# 2. Install the Git pre-commit hook (enforces role boundaries and checks):
valdoz hook install

# 3. Optional: Generate GitHub Actions CI verification:
valdoz ci generate
```

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

## 4. The 10 Project Phases (Cheat Sheet)

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

## 7. Universal Hygiene & Auditing

At any time, you can run a full code audit across your project:
```bash
valdoz audit
```
ValdoZ automatically checks:
- **Secrets Scan**: Scans for hardcoded AWS keys, OpenAI keys, private keys, and `.env` files.
- **Lockfile Check**: Verifies that `package-lock.json`, `uv.lock`, etc. are committed and dependencies are pinned.
- **Undeclared Imports**: Scans Python and JavaScript files to verify that all imported modules are declared in your package manifests (`pyproject.toml`, `package.json`).

---

## 8. Emergency Recovery & Troubleshooting

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

## 9. Complete CLI Command Reference

| Command | Description |
|---|---|
| `valdoz --version` | Display ValdoZ version. |
| `valdoz project init [--lang ar]` | Initialize `.valdoz/` state and deliverable templates. |
| `valdoz sync-runtimes [--dry-run]` | Generate Antigravity rules and skill playbooks. |
| `valdoz hook install` | Install Git pre-commit hook enforcing role domains. |
| `valdoz ci generate` | Generate GitHub Actions CI verification workflow. |
| `valdoz session start --role <builder\|scribe>` | Acquire active agent session role lock. |
| `valdoz session end --role <role>` | Release active session role lock. |
| `valdoz session status` | Show currently active agent sessions. |
| `valdoz session clear` | Clear stale session locks. |
| `valdoz phase status` | View current phase, required deliverables, and whitelist. |
| `valdoz phase next` | Advance to the next phase after approval. |
| `valdoz phase approve` | Human-only interactive TTY approval of deliverables. |
| `valdoz phase reopen <N>` | Reopen a past phase and void downstream approvals. |
| `valdoz gate check [--ci] [--dry-run]` | Run deliverable, heading, placeholder, and citation checks. |
| `valdoz slice start <id>` | Open a Phase 6 build slice. |
| `valdoz slice done <id>` | Check 3 slice gate conditions and mark gated. |
| `valdoz slice approve <id>` | Human-only interactive approval of a build slice. |
| `valdoz slice status` | List all slices and their states. |
| `valdoz decision add -q <q> -c <choice> -r <why>` | Append to `decisions.jsonl` and update `decisions.md`. |
| `valdoz research log -u <url> -c <claim>` | Pre-log fetch intent (Gap 4 security defense). |
| `valdoz research fetch <url>` | Safely fetch and boundary-wrap external web content. |
| `valdoz research add -u <url> -c <claim>` | Log verified research citation. |
| `valdoz audit [--strict] [--no-network]` | Run secrets, lockfile, and undeclared import scans. |
| `valdoz pack list` | List available and active stack packs. |
| `valdoz pack add <pack_id>` | Enable a stack pack (e.g., `web-app`, `api`, `website`). |
| `valdoz state repair` | Reconstruct `state.json` from git history. |
| `valdoz doctor` | Run environment diagnostics and Python drift checks. |
