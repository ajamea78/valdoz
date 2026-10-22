# ValdoZ Protocol v3.0 — Marketing & Pitch Playbook

> **The Autonomous Delivery Harness for Google Antigravity & Pair-Programming Agents.**
> *Discipline. Evidence. Cryptographic Integrity. Real Engineering.*

---

## Executive Summary (The 30-Second Elevator Pitch)

Autonomous AI coding agents can write code at superhuman speeds, but left unconstrained they sprint past architecture, invent phantom libraries, declare tasks "done" without executing tests, and overwrite critical files.

**ValdoZ Protocol** is the open-source engineering harness that acts as a virtual Principal Architect beside your agent. It constrains agent execution into **10 strictly ordered phases**, requires **executable test evidence** before any task can advance, write-protects approved code with **SHA-256 cryptographic hashes**, enforces **builder vs. scribe domain isolation**, and guarantees that **only an interactive human in a real terminal can approve deliverables**.

With native support for the official **Google Antigravity SDK**, the **`wshobson/agents` marketplace**, and **zero-cost testing via FreeLLMAPI**, ValdoZ turns stochastic LLM agents into predictable, enterprise-grade software delivery teams.

---

## The Problem: The 5 Fatal Traps of Autonomous Coding

| The Fatal Trap | What Agents Do Today | How ValdoZ Solves It |
|---|---|---|
| **1. The "Phantom Done" Illusion** | Agent writes code, hallucinates that it passed a test in a subshell, and says *"All done! Everything works."* | **Automated Phase & Slice Gates**: ValdoZ checks actual test execution logs, exit codes, and coverage deltas before allowing progression. |
| **2. Architectural Creep** | In Step 45, the agent decides to rewrite the database schema or swap the framework without permission. | **Read-Only Deliverable Freezing**: Approved architectural documents are set to `chmod 444` and hashed with SHA-256. Silent edits trigger immediate tamper alarms. |
| **3. Multi-Agent Chaos** | Concurrent subagents edit the same files at the same time, producing merge conflicts and phantom bugs. | **Builder vs. Scribe Locks**: Strict domain boundaries enforced by `.valdoz/session.lock` and Git pre-commit hooks. |
| **4. Self-Approval Bypass** | Autonomous scripts write mock tests that always assert `True` and approve their own milestones. | **Interactive-Only TTY Approvals**: ValdoZ rejects scripts, redirects, and automated approvals. A real human must type the confirmation in a physical terminal. |
| **5. Token Exhaustion & Cost Drain** | Long agent evaluation loops rack up hundreds of dollars on commercial API endpoints. | **FreeLLMAPI Zero-Cost Proxy**: Built-in adapter for 358 free LLM endpoints to test multi-step agent flows for \$0. |

---

## Target Audience: Who is ValdoZ Built For?

### 1. Engineering Managers & CTOs
- **The Challenge**: You want to adopt AI coding tools across your team, but you cannot afford security vulnerabilities, undeclared packages, or unvetted architecture.
- **The ValdoZ Advantage**: Complete compliance, automated audits (`valdoz audit` scans secrets, lockfiles, and imports), and cryptographic audit trails for every phase.

### 2. Software Agencies & Client Service Boutiques
- **The Challenge**: Clients demand transparency, fixed-scope delivery, and confidence that deliverables meet exact specs.
- **The ValdoZ Advantage**: First-class support for English and Arabic (`--lang ar`) client-facing specs. You can share cryptographically verified Phase 1–9 deliverables with clients as proof of work.

### 3. AI Agent Builders & Researchers
- **The Challenge**: Building autonomous workflows that do not derail after step 10.
- **The ValdoZ Advantage**: Official `google-antigravity` Python SDK bridge with native tool definitions (`valdoz_gate_check`, `valdoz_slice_done`), plus instant access to 80+ agent plugins via the `wshobson/agents` marketplace bridge.

### 4. Solo Developers & Technical Founders
- **The Challenge**: You are building alone and need the discipline, code review, and rigor of a senior FAANG staff engineer.
- **The ValdoZ Advantage**: Test-Driven Development (TDD) build slices in Phase 6 ensure you never ship regressions.

---

## Core Feature Pillars

### 🏛️ 1. The 10-Phase Deterministic Delivery Machine
Projects follow an immutable lifecycle:
1. **Phase 0: Init** — Repository setup and language selection.
2. **Phase 1: Intake** — Client discovery and problem framing.
3. **Phase 2: Requirements** — User stories and non-negotiables.
4. **Phase 3: Stack Decision** — Framework selection and trade-off matrix.
5. **Phase 4: Architecture & Plan** — System diagrams, slice manifests, and API schemas.
6. **Phase 5: Project Setup** — Tooling, linting, and CI skeleton.
7. **Phase 6: Build Slices** — TDD vertical slices with test coverage verification.
8. **Phase 7: Verify** — Universal audit, end-to-end integration, performance check.
9. **Phase 8: Deploy** — Infrastructure provisioning, staging, and production release with safety locks.
10. **Phase 9: Handover** — Documentation, credentials guide, and client acceptance.
*(Phase 10: Change Requests manages post-launch changes without breaking history).*

### 🛡️ 2. Cryptographic Tamper Evidence & `chmod 444`
Once you approve a deliverable:
- ValdoZ calculates deterministic SHA-256 hashes of all deliverable files.
- Deliverables and `state.json` are flipped to read-only (`chmod 444`).
- Any silent modifications by an overzealous agent immediately trip `valdoz gate check` with a `TamperError`.

### 🔄 3. Phase 6 TDD Build Slices
Instead of letting an agent write an entire app at once:
- Slices advance through 4 verifiable states: `open` $\rightarrow$ `built` $\rightarrow$ `gated` $\rightarrow$ `approved`.
- ValdoZ enforces the **Three Slice Gate Conditions**:
  1. Pre-existing tests pass without regression.
  2. New tests for the current slice pass.
  3. Overall test coverage does not drop.

### 🔌 4. Extensible Stack Packs & Marketplace Bridge
- Out of the box: `base`, `web-app`, `api`, and `website` stack packs.
- Conflict detection and `.valdozrc.json` override precedence.
- Direct 1-command import from `wshobson/agents`:
  ```bash
  valdoz pack import wshobson/agents:code-reviewer
  ```

### 🌍 5. Native English & Arabic Localization
- Client-facing deliverables are automatically generated with localized templates and heading verification in both languages (`--lang ar` or `--lang en`).
- RTL markdown structure and localized gate checks.

---

## Competitive Comparison

| Feature | ValdoZ Protocol v3.0 | Unconstrained AI Agents | Traditional CI/CD (GitHub Actions) |
|---|---|---|---|
| **Phase-Gated Execution** | ✅ Enforced 10 phases | ❌ Chaotic 1-shot prompts | ❌ Code-centric only (post-commit) |
| **Interactive Human Sign-Off** | ✅ TTY-only (no script bypass) | ❌ None (blind trust) | ⚠️ Manual PR reviews (often skipped) |
| **File Write-Protection** | ✅ OS-level `chmod 444` | ❌ Agent overwrites freely | ❌ Branch protection only |
| **Tamper Detection** | ✅ SHA-256 state hashing | ❌ None | ❌ Git commit hashes only |
| **Role Separation** | ✅ Builder vs Scribe locks | ❌ Race conditions | ❌ N/A |
| **Marketplace Bridge** | ✅ `wshobson/agents` + packs | ❌ Vendor locked | ❌ N/A |
| **Native Antigravity SDK** | ✅ Official Python SDK bridge | ❌ None | ❌ N/A |
| **Zero-Cost LLM Testing** | ✅ FreeLLMAPI integration | ❌ Commercial bills | ❌ N/A |

---

## 2-Minute Quickstart

```bash
# 1. Install ValdoZ
uv tool install valdoz-protocol@3.0.0

# 2. Initialize in your project
cd my-project
valdoz project init --name "NextGen Portal"

# 3. Synchronize Antigravity playbooks & git hooks
valdoz sync-runtimes
valdoz hook install

# 4. Check where you are
valdoz phase status
```

---

## Frequently Asked Questions (FAQ)

**Q: Does ValdoZ slow down my development velocity?**  
*A: No. It accelerates your net velocity. Unconstrained agents move fast initially, then spend 80% of their time debugging phantom hallucinations, broken imports, and overwritten files. ValdoZ provides clean, linear forward progress without backtrack.*

**Q: Can an agent bypass the approval prompt?**  
*A: No. `valdoz phase approve` explicitly verifies standard input is connected to an interactive TTY device (`sys.stdin.isatty()`). Subshells, echo piping, and background cron scripts are rejected with `NonInteractiveApprovalError`.*

**Q: Can I reopen a phase if requirements change?**  
*A: Yes. `valdoz phase reopen <N>` cleanly rolls back state, voids downstream approvals, and warns of cloud resource impacts if reopening deploy phases.*

**Q: What LLMs and runtimes does ValdoZ support?**  
*A: ValdoZ is designed for Google Antigravity (AGY), Claude Code, Gemini CLI, Cursor, and any runtime using Markdown skill standards or the Antigravity Python SDK.*
