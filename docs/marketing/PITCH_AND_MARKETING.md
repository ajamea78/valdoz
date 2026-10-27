# ValdoZ Protocol v3.1.1 — Marketing & Pitch Playbook

> **The Autonomous Delivery Harness for Google Antigravity & Pair-Programming Agents.**
> *Discipline. Evidence. Cryptographic Integrity. Real Engineering.*

---

## Executive Summary (The 30-Second Elevator Pitch)

Autonomous AI coding agents can write code at superhuman speeds, but left unconstrained they sprint past architecture, invent phantom libraries, declare tasks "done" without executing tests, and overwrite critical files.

**ValdoZ Protocol** is the open-source engineering harness that acts as a virtual Principal Architect beside your agent. It constrains agent execution into **11 strictly ordered phases** (Phase 0: Init + 10 delivery phases), requires **executable test evidence** before any task can advance, write-protects approved code with **SHA-256 cryptographic hashes**, enforces **builder vs. scribe domain isolation**, and guarantees that **only an interactive human can approve deliverables** via deliverable-bound HMAC tokens (`valdoz-v2`) or a physical TTY.

With native support for the official **Google Antigravity SDK**, the **`wshobson/agents` marketplace**, **zero-cost testing via FreeLLMAPI**, **deterministic Semgrep AST SAST**, **live package hallucination verification**, and **autonomous self-healing**, ValdoZ turns stochastic LLM agents into predictable, enterprise-grade software delivery teams.

---

## The Problem: The 7 Fatal Traps of Autonomous Coding

| The Fatal Trap | What Agents Do Today | How ValdoZ Solves It |
|---|---|---|
| **1. The "Phantom Done" Illusion** | Agent writes code, hallucinates that it passed a test in a subshell, and says *"All done! Everything works."* | **Automated Phase & Slice Gates**: ValdoZ checks actual test execution logs, exit codes, and coverage deltas before allowing progression. |
| **2. Architectural Creep** | In Step 45, the agent decides to rewrite the database schema or swap the framework without permission. | **Read-Only Deliverable Freezing**: Approved architectural documents are set to `chmod 444` and hashed with SHA-256. Silent edits trigger immediate tamper alarms. |
| **3. Multi-Agent Chaos** | Concurrent subagents edit the same files at the same time, producing merge conflicts and phantom bugs. | **Builder vs. Scribe Locks**: Strict domain boundaries enforced by `.valdoz/session.lock` and Git pre-commit hooks. |
| **4. Self-Approval & Replay Bypass** | Autonomous scripts write mock tests that always assert `True` or replay old approval tokens. | **Deliverables-Bound `valdoz-v2` Tokens & Nonce Burn**: Tokens bind the exact SHA-256 hash of deliverables. Consumed nonces are burned immediately. |
| **5. AI Package Hallucination** | LLM imports non-existent libraries or typo-squatted malicious packages from npm/PyPI. | **Registry Verification**: `valdoz audit --verify-packages` verifies every declared dependency against live official registries. |
| **6. Secret Exfiltration in Diagnostics** | LLM leaks committed API keys, PATs, or JWTs when dumping crash traces into external prompt endpoints. | **Automated Secret Scrubber**: Redacts AWS, OpenAI, Gemini, GitHub PATs, and private keys before AI diagnostic analysis. |
| **7. Token Exhaustion & Cost Drain** | Long agent evaluation loops rack up hundreds of dollars on commercial API endpoints. | **FreeLLMAPI Zero-Cost Proxy**: Built-in adapter for 358 free LLM endpoints to test multi-step agent flows for \$0. |

---

## Target Audience: Who is ValdoZ Built For?

### 1. Engineering Managers & CTOs
- **The Challenge**: You want to adopt AI coding tools across your team, but you cannot afford security vulnerabilities, undeclared packages, or unvetted architecture.
- **The ValdoZ Advantage**: Complete compliance, automated universal audits (`valdoz audit` scans secrets, lockfiles, Semgrep AST SAST, package hallucination, and copyleft licenses), and cryptographic audit trails for every phase.

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

### 🏛️ 1. The 11-Phase Deterministic Delivery Machine
Projects follow an immutable lifecycle:
1. **Phase 0: Init** — Repository setup and language selection.
2. **Phase 1: Intake** — Client discovery and problem framing.
3. **Phase 2: Requirements** — User stories and non-negotiables.
4. **Phase 3: Stack Decision** — Framework selection and trade-off matrix.
5. **Phase 4: Architecture & Plan** — System diagrams, slice manifests, and API schemas.
6. **Phase 5: Project Setup** — Tooling, linting, and CI skeleton.
7. **Phase 6: Build Slices** — TDD vertical slices with automated test runner execution.
8. **Phase 7: Verify** — Universal audit, end-to-end integration, performance check.
9. **Phase 8: Deploy** — Infrastructure provisioning, staging, and production release with safety locks.
10. **Phase 9: Handover** — Documentation, credentials guide, and client acceptance.
*(Phase 10: Change Requests manages post-launch changes without breaking history).*

### 🛡️ 2. Cryptographic Tamper Evidence & `chmod 444`
Once you approve a deliverable:
- ValdoZ calculates deterministic SHA-256 hashes of all deliverable files.
- Deliverables and `state.json` are flipped to read-only (`chmod 444`).
- Any silent modifications by an overzealous agent immediately trip `valdoz gate check` with a `TamperError`.

### 🔐 3. Second-Order Security Hardening (v3.1.1)
- **Deliverables-Bound `valdoz-v2` Tokens**: Approval signatures bind the exact composite hash of deliverables (`HMAC-SHA256(secret, action || target || hash || ts || nonce)`).
- **Out-of-Workspace Keystore**: Signing secrets are resolved from `~/.config/valdoz/keys/approval.key` (or `VALDOZ_APPROVAL_SECRET`), completely isolating credentials from in-workspace agent execution.
- **Single-Use Nonce Burn**: Consumed token nonces are recorded in `.valdoz/consumed_nonces.json` with 15-minute pruning to prevent token replay attacks.
- **RFC 8785 Canonical JSON Audit Log**: Immutable append-only audit trail (`.valdoz/approvals.log`) formats all entries into strict canonical JSON, anchored to Git tags (`valdoz anchor`) to prevent history rewriting.

### 🔍 4. Universal Security Audit & AST SAST Engine
- Deterministic AST vulnerability scanning via **Semgrep** (`valdoz audit --semgrep`).
- Real-time **Package Hallucination & Slopsquatting** scanner validating declared packages against PyPI and npm registries (`valdoz audit --verify-packages`).
- Automated **Copyleft & Viral License Scanner** (`valdoz audit --licenses`).
- Hardcoded secrets and unpinned lockfile detection.

### 🩺 5. Autonomous Self-Healing Engine
- Ingests test failures, compiler errors, or gate violations and formulates structured diagnostic prompts.
- Cleanses logs of credentials via the **LLM Secret Scrubber**.
- Generates targeted unified diffs, applies patches within a 512 KB safety boundary, and re-runs test suites to confirm recovery.

### 🔄 6. Phase 6 TDD Build Slices
Instead of letting an agent write an entire app at once:
- Slices advance through 4 verifiable states: `open` $\rightarrow$ `built` $\rightarrow$ `gated` $\rightarrow$ `approved`.
- ValdoZ enforces the **Three Slice Gate Conditions**:
  1. Pre-existing tests pass without regression.
  2. New tests for the current slice pass.
  3. Overall test coverage does not drop.

### 🔌 7. Extensible Stack Packs & Marketplace Bridge
- Out of the box: `base`, `web-app`, `api`, and `website` stack packs.
- Sub-resource SHA-256 integrity map generation for all imported skills and rules.
- Automated scanner for adversarial prompt injections (override directives, jailbreaks, hidden comments).
- Direct 1-command import from `wshobson/agents`:
  ```bash
  valdoz pack import wshobson/agents:code-reviewer
  ```

### 🌍 8. Native English & Arabic Localization
- Client-facing deliverables are automatically generated with localized templates and heading verification in both languages (`--lang ar` or `--lang en`).
- RTL markdown structure and localized gate checks.

---

## Competitive Comparison

| Feature | ValdoZ Protocol v3.1.1 | Unconstrained AI Agents | Traditional CI/CD (GitHub Actions) |
|---|---|---|---|
| **Phase-Gated Execution** | ✅ Enforced 11 phases | ❌ Chaotic 1-shot prompts | ❌ Code-centric only (post-commit) |
| **Interactive Human Sign-Off** | ✅ TTY or `valdoz-v2` deliverable tokens | ❌ None (blind trust) | ⚠️ Manual PR reviews (often skipped) |
| **TOCTOU Attack Protection** | ✅ Deliverables composite hash binding | ❌ Vulnerable | ❌ None |
| **File Write-Protection** | ✅ OS-level `chmod 444` | ❌ Agent overwrites freely | ❌ Branch protection only |
| **Tamper-Evident Ledger** | ✅ Canonical JSON hash-chain + Git anchor | ❌ None | ❌ Git commit hashes only |
| **Role Separation** | ✅ Builder vs Scribe locks | ❌ Race conditions | ❌ N/A |
| **Package Hallucination Scan** | ✅ Real-time PyPI/npm verification | ❌ Severe hallucination risk | ❌ N/A |
| **Deterministic AST SAST** | ✅ Semgrep integration | ❌ Prompted review only | ⚠️ Heavy external pipeline |
| **Secret Scrubbing in AI Prompts**| ✅ Automatic regex sanitization | ❌ Leaks credentials to LLMs | ❌ N/A |
| **Self-Healing Diagnostics** | ✅ Automated diff generator + verify | ❌ Brittle trial-and-error | ❌ Static failure reports |
| **Marketplace Bridge** | ✅ `wshobson/agents` + packs + injection scan | ❌ Vendor locked | ❌ N/A |
| **Native Antigravity SDK** | ✅ Official Python SDK bridge | ❌ None | ❌ N/A |
| **Zero-Cost LLM Testing** | ✅ FreeLLMAPI integration | ❌ Commercial bills | ❌ N/A |

---

## 2-Minute Quickstart

```bash
# 1. Install ValdoZ globally via uv tool (direct from GitHub tag):
uv tool install git+https://github.com/ajamea78/valdoz.git@v3.1.1

# (Or install in editable mode from local clone):
uv tool install --editable . --force

# 2. Initialize in your project
cd my-project
valdoz project init --name "NextGen Portal"

# 3. Synchronize Antigravity playbooks & git hooks
valdoz sync-runtimes
valdoz hook install

# 4. Check where you are & run universal audit
valdoz phase status
valdoz audit --semgrep --verify-packages --licenses
```

---

## Frequently Asked Questions (FAQ)

**Q: Does ValdoZ slow down my development velocity?**  
*A: No. It accelerates your net velocity. Unconstrained agents move fast initially, then spend 80% of their time debugging phantom hallucinations, broken imports, and overwritten files. ValdoZ provides clean, linear forward progress without backtrack.*

**Q: Can an agent bypass the approval prompt?**  
*A: No. `valdoz phase approve` explicitly verifies standard input is connected to an interactive TTY device (`sys.stdin.isatty()`) or accepts an authentic `valdoz-v2` token signed with an out-of-workspace secret that the agent cannot access.*

**Q: Can I reopen a phase if requirements change?**  
*A: Yes. `valdoz phase reopen <N>` cleanly rolls back state, voids downstream approvals, and warns of cloud resource impacts if reopening deploy phases.*

**Q: What LLMs and runtimes does ValdoZ support?**  
*A: ValdoZ is designed for Google Antigravity (AGY), Claude Code, Gemini CLI, Cursor, and any runtime using Markdown skill standards or the Antigravity Python SDK.*

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
