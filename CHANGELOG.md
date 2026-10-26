# Changelog

All notable changes to the ValdoZ Protocol delivery discipline engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
