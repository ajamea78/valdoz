# Changelog

All notable changes to the ValdoZ Protocol delivery discipline engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.4.0] - 2026-11-11

### Added
- **Enacted Directive 13: Zero-Destructive Database Discipline & Data Protection**:
  - Added Directive 13 across `src/valdoz/sync.py`, `AGENTS.md`, `GEMINI.md`, and `.agent/rules/00-core-discipline.md`:
    - Prohibits unconditional deletion or drop scripts on database files (`*.db`, `*.sqlite`, `DROP DATABASE`, `TRUNCATE`, `rm -f *.db*`, or `fs.unlinkSync`).
    - Mandates `--force-reset` command-line flag requirement on all database reset, initialization, and seed scripts.
    - Mandates automatic creation of immutable, timestamped backups in `backups/db/` prior to executing any destructive wipe.
    - Mandates strictly additive schema evolutions (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`), leaving live data intact and verifiable.
- **Dedicated Modular Rule (`.agent/rules/04-database-discipline.md`)**:
  - Scaffolds standalone database discipline and data protection policy file during `valdoz sync-runtimes`.
- **Database Safety Audit Check (`db-safety-guard`) in Base Pack (`src/valdoz/checks.py`, `src/valdoz/packs.py`)**:
  - Registered `db-safety-guard` in the default `base` pack.
  - Automatically scans `package.json` scripts, shell scripts (`.sh`, `.bash`), JavaScript/TypeScript files, Python files, and SQL migration files.
  - Detects unguarded database removals, unlinks, or database drops lacking `--force-reset` gates and backup routines, mechanically blocking phase advancement or slice completion.
- **Playbook & Skill Enhancements**:
  - Updated `valdoz-architect`: Enforces additive schema designs, migration safety, and backup directories.
  - Updated `valdoz-setup`: Mandates automated safety gates on scaffolded `init-db` and `reset-db` scripts.
  - Updated `valdoz-build`: Enforces backward-compatible, additive database changes during feature slices.
- **Documentation**:
  - Added full documentation for Directive 13 and `db-safety-guard` audit check in `docs/USER_GUIDE.md`.

## [3.3.0] - 2026-11-06

### Added
- **Full-Spectrum Non-Bypassable Verification Engine (`src/valdoz/verification.py`)**:
  - Implemented multi-package workspace discovery that automatically traverses root and nested subprojects (e.g. `staff-interface/`, `customer-portal/`, `client/`, `server/`).
  - Executes authoritative root `npm run verify` if present; otherwise runs the 4-pillar verification matrix across every workspace:
    1. **Lint Phase**: `npm run lint`, `ruff check`, `cargo clippy`.
    2. **Typecheck Phase**: `npm run typecheck`, `npx tsc --noEmit`, `mypy`.
    3. **Test Phase**: `npm test`, `pytest`, `cargo test`.
    4. **Build Phase**: `npm run build`, `cargo build`.
  - Added `valdoz verify` CLI command with Rich status matrices, execution times, and captured failure panels.
  - Added `valdoz_verify_project` native MCP server tool for automated agent verification calls.
- **Hardened Directive 9 in Core Directives (`AGENTS.md`, `GEMINI.md`, `00-core-discipline.md`)**:
  - Upgraded Directive 9 to **Full-Spectrum Non-Bypassable Verification**:
    - Mandates running all 4 pillars across both root and all workspace subprojects before declaring any task "done" or requesting approval.
    - Explicitly codified the "Bundler Pass $\neq$ Code Works" rule: production bundlers (`vite build`) transpile syntax but do not catch undeclared variables; linters (`npm run lint`, ESLint `no-undef`) must run explicitly.
- **UI & Perceptual Stability Directive (Directive 9 & Playbooks)**:
  - Updated Directive 9 across `AGENTS.md`, `GEMINI.md`, and `.agent/rules/00-core-discipline.md` with explicit **UI & Perceptual Guard**: automated passes verify code logic but cannot detect visual layout shifts (CLS), unmounting layout shells, or mounting flickers.
  - Banished the "Early-Return Skeleton Trap" (`if (loading) return <Skeleton />`) across `valdoz-design`, `valdoz-build`, and `valdoz-verify`: mandates persistent layout frames (headers, navigation, actions remain mounted) and confines skeletons strictly to inner data containers.
  - Mandated cache-first / SWR state persistence across page transitions so tab switching does not trigger flashing loading states.
  - Added frontend perceptual verification checklist to `valdoz-verify` and `valdoz-design` playbooks.
- **Slice Gate Hardening (`src/valdoz/slices.py`)**:
  - `run_slice_test_suite` now invokes full-spectrum workspace verification.
  - Subproject lint failures (such as undeclared JSX identifiers like `isDir2`) automatically block slice advancement to `gated`.
- **Monorepo Verification Integrity Audit Check (`src/valdoz/checks.py`, `src/valdoz/packs.py`)**:
  - Added `monorepo-verification-integrity` to the Base Pack.
  - Verifies that multi-package repositories define a unified root `verify` script and that all subprojects have active linters configured.
- **External Catalog Reference Additions (`.valdoz/repos.yaml`)**:
  - Added industry-standard verification references: `vercel/turborepo` (monorepo pipelines), `biomejs/biome` and `oxc-project/oxc` (instant AST semantic linting), `microsoft/playwright` (headless UI smoke testing to prevent blank screens), and `paul-gauthier/aider` (pre-commit verification loops).

## [3.2.0] - 2026-11-04

### Security Hardening & Bug Fixes
- **Atomic State Persistence & Round-Trip Validation (`src/valdoz/state.py`)**:
  - Implemented atomic file writes via `.json.tmp` and `os.replace` to prevent corruption if process exits mid-save.
  - Added schema round-trip deserialization guard before flushing state changes to disk.
- **Unified Broad Secret Scanner & Multi-File Coverage (`src/valdoz/checks.py`)**:
  - Broadened GitHub token detection regex to catch fine-grained PATs (`github_pat_`), app tokens (`ghs_`, `ghu_`), and variable-length tokens.
  - Added support for `.toml`, `.sh`, `.cfg`, and `.ini` files in secrets scan.
  - Added `.valdoz` directory to directory exclusion list to isolate credential vault verification from source tree scanning.
- **Approval Keystore Isolation & Fallback Opt-In (`src/valdoz/approval.py`)**:
  - Parameterized global keystore fallback via `allow_global_fallback` (defaulting to `False`) to prevent cross-project token reuse.
- **Adversarial Prompt Injection Hardening (`src/valdoz/importer.py`)**:
  - Integrated Unicode NFKD normalization, zero-width space removal (`[\u200B-\u200D\uFEFF\u00AD\u2060]`), and Cyrillic/Greek homoglyph transliteration to defeat evasion attacks.
- **State Repair Legacy Hash Warning (`src/valdoz/repair.py`)**:
  - Added explicit notice logging when restoring phases recorded with legacy short hashes.

### Added
- **Autonomous Conversational Governance (Rule 12)**:
  - Once a project initializes ValdoZ, the agent automatically manages and structures all natural conversation requests under ValdoZ protocol discipline.
  - The user no longer needs to prefix prompts with `/valdoz` or call slash commands for routine work:
    - Visual/UI requests automatically route to `/valdoz-design`.
    - Features, enhancements, and fixes automatically route to test-driven slices (`/valdoz-build`).
    - Architecture, database, and stack requests route to `/valdoz-architect`.
    - Quality and audit checks route to `/valdoz-verify` and `/valdoz-audit`.
    - Deployments route to `/valdoz-deploy` with mandatory in-chat human sign-off.
- **Machine-Wide Skill Synchronization & Legacy Purge**:
  - Fully populated `~/.gemini/config/skills/` with the complete streamlined ValdoZ command suite.
  - Automatically scanned and purged obsolete `valdoz-phase-*` directories across all existing projects on the machine (`GoCar Auto`, `MeemEvents`, `Smart Directory`, `Dania`, `Dental Management System`, `AI News Dashboard`).
- **Streamlined Intent-Driven Slash Command Suite**:
  - Replaced legacy numbered phase playbooks (`valdoz-phase-X-...`) in Antigravity chat with human-friendly, task-oriented slash commands.
  - Added `/valdoz-guide`: End-to-end guru companion guiding delivery from raw concept to live deployment with best practices for web, mobile, and APIs.
  - Added `/valdoz-concept`: Unified product intake and requirements discovery (Phases 1 & 2).
  - Added `/valdoz-design`: First-class UI/UX redesign and styling overhaul skill integrating with screen generators (Stitch MCP / Canva) and component kits.
  - Added `/valdoz-architect`: Unified tech stack selection, hosting infrastructure strategy (Vercel, Cloud Run, AWS, Supabase), and API/DB schema architecture (Phases 3 & 4).
  - Added `/valdoz-import`: Third-party GitHub repository and UI component importer with security scanning, license verification, and provenance logging.
  - Added `/valdoz-setup`: Tooling, Docker, container configurations, and CI/CD pipeline scaffolding (Phase 5).
  - Added `/valdoz-build`: Test-driven feature slice implementation (Phase 6).
  - Added `/valdoz-verify`: Automated test suites, Semgrep SAST, secrets detection, and quality gate audits (Phase 7).
  - Added `/valdoz-deploy`: Safe cloud staging and production deployment with DNS and rollback strategies (Phase 8).
  - Added `/valdoz-handover`: Operational runbooks, credential handover, and client sign-off (Phase 9).
  - Added `/valdoz-changes`: Post-handover change request impact assessments and tracking (Phase 10).
- **Runtime Sync Engine Upgrade (`src/valdoz/sync.py`)**:
  - Automated generation of streamlined `.agent/skills/valdoz-*/SKILL.md` with standard YAML frontmatter.
  - Automated cleanup of obsolete legacy `valdoz-phase-*` directories during synchronization.
- **Documentation**:
  - Added full reference for the streamlined slash command suite in `docs/USER_GUIDE.md`.

## [3.1.2] - 2026-10-27

### Security Hardening & Bug Fixes
- **Static Type Safety & Analysis Remediations**:
  - Resolved 58 mypy type errors across `cli.py`, `checks.py`, `importer.py`, `healing.py`, and `mcp_server.py`.
  - Added automated mypy type verification step to GitHub Actions CI (`.github/workflows/test.yml`).
  - Documented compliance boundaries in `docs/THREAT_MODEL.md` formalizing why SaaS-layer regulations (GDPR/HIPAA/PCI DSS) do not apply to the on-premise CLI binary.
- **Automated Documentation Enforcement (Rule 11 & `doc-sync`)**:
  - Implemented `scan_doc_sync()` audit check in `src/valdoz/checks.py` and registered it in the `base` pack to mechanically block un-synchronized code releases.
  - Added Rule 11 ("Atomic Documentation Reflex") across core runtime configurations (`sync.py`, `AGENTS.md`, `GEMINI.md`, `.agent/rules/03-doc-sync.md`), mandating automatic transition to the `scribe` role in the same session to record functional deltas.
  - Added automated scaffolding of baseline `CHANGELOG.md` in `valdoz audit --fix` and `valdoz project init`.
- **MCP Error Guarding & Request Limits**:
  - Replaced unguarded dictionary accesses on required arguments (`phase_num`, `human_token`, `username`, `token`) with safe lookups and explicit validation errors.
  - Added a strict 1 MB per-line size limit to the MCP stdio protocol loop to prevent memory exhaustion DoS.
  - Masked the credential store path returned by `valdoz_auth_setup` to relative `.valdoz/.git-credentials` to prevent internal filesystem disclosure.
- **RFC 8785 UTF-8 Preservation**: Changed `canonical_json_bytes()` to `ensure_ascii=False`, preserving unescaped raw UTF-8 Arabic project names and text while maintaining cryptographic determinism.
- **Diff Secrets Scrubbing**: Integrated `redact_secrets_in_text()` into `generate_semantic_diff_summary()` to prevent logging unredacted credentials to `.valdoz/history/semantic_diffs.jsonl`.
- **Unified Diff Formatting for New Files**: Fixed `generate_patch_diff()` to produce standard `@@ -0,0 +1,N @@` hunk headers and `/dev/null` sources for newly created files.
- **Path Traversal Defense in Failure Context**: Normalized candidate error trace paths with `.resolve()` and verified relative containment within `project_root`, rejecting traversal attempts (e.g. `../../../../etc/passwd.md`).
- **Pack Supply-Chain Verification**: Connected `scan_prompt_injection_patterns()` and `verify_pack_integrity()` into `resolve_active_packs()`, preventing untrusted packs from loading if prompt injections or corrupted integrity maps are present.
- **Dual-Metric Behavioral Budgets**: Expanded `check_behavioral_budget()` to independently validate both `file_writes` and `tool_calls`, and lowered the Phase 6 default file writes budget from 250 to 100.
- **Self-Healing LLM Throttling**: Added exponential backoff (`2 ** (attempt - 1)` seconds) between retry attempts in `run_healing_loop()`.
- **Webhook Error Sanitization**: Sanitized webhook failure messages to prevent leaking internal socket or filesystem details.

## [3.1.1] - 2026-10-27

### Second-Order Security Hardening (Adversary A1 & A3 Defenses)
- **Deliverables-Bound Approval Tokens (`valdoz-v2`)**: Embedded deterministic SHA-256 composite hash of deliverables into token signature (`SHA256(action || target || deliverables_hash || ts || nonce)`), eliminating Time-of-Check to Time-of-Use (TOCTOU) file alteration races.
- **Out-of-Workspace Keystore Resolution**: Master secret resolution prioritizes `VALDOZ_APPROVAL_SECRET` and user OS configuration directory (`~/.config/valdoz/keys/approval.key` with `0700`/`0600` permissions), isolating credentials outside the workspace boundary to defend against in-workspace code execution.
- **Single-Use Nonce Burn & Replay Defense**: Consumed approval token nonces are recorded in `.valdoz/consumed_nonces.json` with automatic 15-minute pruning, preventing token replay attacks within TTL windows.
- **RFC 8785 Canonical JSON Audit Log Hash Chaining**: Formatted all `.valdoz/approvals.log` hash-chain payloads into strict canonical JSON (deterministic lexicographical sorting, compact delimiters) to eliminate delimiter collision attacks.
- **State Repair Laundering Defense**: Strengthened `valdoz state repair` to require unbroken cryptographic ledger proofs and assert that disk deliverables match recorded approval hashes before restoring `approved` phase states.
- **LLM Secret Scrubbing Pipeline**: Automated redaction of API keys (OpenAI, Anthropic, Gemini, AWS), personal access tokens (GitHub), private keys, Bearer headers, and ValdoZ tokens before sending error traces, diffs, or specifications to AI self-healing diagnostic prompts.
- **Pack & Skill Supply-Chain Integrity**: Added automated prompt injection scanners detecting instruction overrides, jailbreaks, hidden comments, and shell pipes in imported agent skills. Generated SHA-256 integrity maps in `manifest.yaml` and verified with `verify_pack_integrity`.

## [3.1.0] - 2026-10-26

### Security Hardening
- **Cryptographic Approval Tokens**: Removed legacy predictable `valdoz-human-*` fallback. Approval tokens require HMAC-SHA256 signatures with nonce, timestamp, and 5-minute TTL.
- **Full 256-bit HMAC**: Upgraded verification digest comparison from truncated 64-bit (`[:16]`) to full 256-bit SHA-256 digest with constant-time equality checks.
- **SSRF & Metadata Protection**:
  - `healing.py`: Blocked external AI requests targeting cloud metadata IPs (`169.254.169.254`, `metadata.google.internal`) and forbidden hosts. Added null-byte stripping, AST parsing validation for Python code, and patch size cap (512 KB).
  - `research fetch`: Added strict response size cap (1 MB), Content-Type enforcement (text/json/xml/scripts only), and forbidden host checking for cloud metadata and loopback destinations.
- **Audit Log Integrity Enforcement**: Added top-level blocking check `audit-log-integrity` to `valdoz gate check`, verifying the cryptographic hash chain on every single phase gate evaluation.
- **Brownfield Fast-Forward Warning**: Flagged pre-approved phases from project auto-scan as `"auto-scanner (unverified)"`, added prominent banner notice, and introduced `--require-human-signoff` flag.

### Features & Governance
- **Cryptographic Audit Trail**: Hash-chained append-only ledger (`.valdoz/approvals.log`) linking each approval to the SHA-256 hash of the prior entry.
- **M-of-N Approval Quorum**: Supported multi-signature approval requiring multiple distinct human approvers for critical deployment phases.
- **Time-Locked Phases**: Enforced minimum dwell times to ensure deliberate human review and prevent rapid rubber-stamping.
- **Real Test Runner in Slice Gate**: `done_slice` automatically invokes project test runners (`pytest`, `npm test`, etc.) to verify test execution before advancing slices.
- **AI Agent Oversight**:
  - Behavioral budgets per phase with tool call tracking and anomaly warnings.
  - Semantic diff summaries logged for every applied patch.
  - `--auto-heal-preview` flag to review diffs before applying self-healing code changes.
- **Audit & Packaging**:
  - `state.json` tamper-detection and cross-checking included in `verify_phase_integrity()`.
  - Added `mypy` static type checking to optional dev dependencies and CI SAST workflows.
  - Defined explicit public Python API and `__all__` in `valdoz.__init__`.
  - Committed `uv.lock` dependency lockfile for zero-trust reproducible builds.

---

## [3.0.0] - 2026-10-24

### Added
- **10-Phase Waterfall-Agile Lifecycle Engine**: Automated intake, requirements, stack decision, architecture, project setup, slice build, verification, deployment, handover, and change requests.
- **Role Boundary Separation**: Explicit concurrency lock system enforcing `builder` vs `scribe` write boundaries.
- **Interactive Antigravity In-Chat Approval Bridge**: Nonce-based cryptographic approval bridge allowing one-click gate authorization natively in Antigravity chat.
- **Self-Healing Engine**: Autonomous diagnosis and remediation for failed phase gates, slice test regressions, and CI test pipelines.
- **Live HTML Dashboard**: Standalone visual portal with real-time SSE stream for monitoring phase status, slice progress, and deliverable integrity.
- **Multi-Runtime Sync Engine**: Auto-synchronization across `.valdoz`, `.agent/skills`, Cursor `.cursorrules`, GitHub Copilot instructions, and Claude desktop configurations.
- **Institutional Memory (SCARS)**: Persistent failure ledger cataloging historical regressions and prevention strategies.
- **Bilingual Arabic/English Support**: Automated heading and deliverable structure validation in both Arabic and English.
