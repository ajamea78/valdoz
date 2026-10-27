# Changelog

All notable changes to the ValdoZ Protocol delivery discipline engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.2] - 2026-10-27

### Security Hardening & Bug Fixes
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
