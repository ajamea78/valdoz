# ValdoZ Protocol v3.1

> **Antigravity Delivery Discipline Engine**  
> Turning autonomous AI coding assistants into disciplined, accountable delivery partners.

[![CI Test Suite](https://github.com/ajamea78/valdoz/actions/workflows/test.yml/badge.svg)](https://github.com/ajamea78/valdoz/actions/workflows/test.yml)
[![Security Audit & SAST](https://github.com/ajamea78/valdoz/actions/workflows/security-audit.yml/badge.svg)](https://github.com/ajamea78/valdoz/actions/workflows/security-audit.yml)
[![Deploy Documentation](https://github.com/ajamea78/valdoz/actions/workflows/docs.yml/badge.svg)](https://github.com/ajamea78/valdoz/actions/workflows/docs.yml)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/ajamea78/valdoz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Documentation

- 📖 **[Complete User Guide](docs/USER_GUIDE.md)**: A practical, easy-to-read manual covering the operating loop, Builder & Scribe roles, Phase 6 slices, and cheat sheets.
- 🛡️ **[Threat Model & Security Architecture](docs/THREAT_MODEL.md)**: Adversary model, cryptographic roots of trust, defense-in-depth matrix, and speed bump definitions.
- 🔄 **[Migration Guide (v2.x to v3.1)](docs/MIGRATION.md)**: Upgrading existing ValdoZ repositories to v3.1.
- 📋 **[Implementation Plan](docs/ValdoZ%20v3.0%20—%20Revised%20Implementation%20Plan.md)**: Full architecture and design decisions.

---

## Quick Start (3 Steps)

### 1. Install ValdoZ
```bash
# Install uv (if not already installed):
curl -LsSf https://astral.sh/uv/install.sh | sh

# Option A: Install tagged release directly from GitHub:
uv tool install git+https://github.com/ajamea78/valdoz.git@v3.1.0

# Option B: Install from local cloned source:
uv tool install --editable . --force

# Register with Google Antigravity MCP:
valdoz mcp register
```

### 2. Initialize in your Repository
```bash
cd /path/to/your-project
valdoz project init              # Scans maturity & auto-places phase (or --lang ar, --require-human-signoff)
valdoz sync-runtimes             # Generate Antigravity rules & skills
valdoz hook install              # Enforce role locks & CD push protection
```

### 3. Daily Operating Loop
```bash
# Start an agent session
valdoz session start --role builder

# Check where you are
valdoz phase status

# Run gate verification
valdoz gate check

# Approve work (Human-Only, Interactive TTY)
valdoz phase approve

# Advance to next phase
valdoz phase next
```

---

## Key Capabilities

- **Phase Gate Model**: Work progresses in sequence through 11 total phases: Phase 0 (Init) plus 10 structured delivery phases (1. Intake, 2. Requirements, 3. Stack Decision, 4. Architecture & Plan, 5. Project Setup, 6. Build Slices, 7. Verify, 8. Deploy, 9. Handover, 10. Change Requests).
- **Builder / Scribe Concurrency**: Multi-agent sessions are partitioned by file domains. Builders write code and tests; Scribes write specifications and logs.
- **Phase 6 Build Slices**: Work is broken into small, reviewable slices (`valdoz slice start / done / approve`) evaluated against the Three Slice Gate Conditions.
- **Adversarial Content Defenses**: Mandatory pre-fetch intent logging (`valdoz research log`) and boundary wrapping (`valdoz research fetch`) with ANSI escape and control character sanitization.
- **Write-Protected State & Hash-Chained Audit Trail**: Deliverables are SHA-256 hashed on approval, `state.json` is locked (`chmod 444`), and all approvals form a cryptographic hash chain anchored externally via Git tags (`valdoz-anchor-*`). Tampering is detected immediately.
- **Enterprise Governance & Quorums**: M-of-N human approval quorums for high-stakes phases, review dwell time-locks, and AI behavioral budgets.
- **Universal Multi-Scanner Audit**: Built-in AST vulnerability scanning (Semgrep), AI package hallucination & slopsquatting detection, license compliance & copyleft isolation, OpenAPI contract drift, and container hardening.
- **Executive Reporting**: Generate executive narratives and handover audit reports on-demand (`valdoz explain`).
- **State Repair**: Reconstruct `state.json` from git history at any time with `valdoz state repair`.

---

## License

Distributed under the [MIT License](LICENSE). See `LICENSE` for more information.
