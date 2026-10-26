# ValdoZ Protocol v3.0

> **Antigravity Delivery Discipline Engine**  
> Turning autonomous AI coding assistants into disciplined, accountable delivery partners.

---

## Documentation

- 📖 **[Complete User Guide](docs/USER_GUIDE.md)**: A practical, easy-to-read manual covering the operating loop, Builder & Scribe roles, Phase 6 slices, and cheat sheets.
- 🔄 **[Migration Guide (v2.x to v3.0)](docs/MIGRATION.md)**: Upgrading existing ValdoZ repositories to v3.0.
- 📋 **[Implementation Plan](docs/ValdoZ%20v3.0%20—%20Revised%20Implementation%20Plan.md)**: Full architecture and design decisions.

---

## Quick Start (3 Steps)

### 1. Install ValdoZ
```bash
# Install uv (if not already installed):
curl -Lsf https://astral.sh/uv/install.sh | sh

# Install from local source (inside cloned repository):
uv tool install --editable . --force

# Register with Google Antigravity MCP:
valdoz mcp register
```

### 2. Initialize in your Repository
```bash
cd /path/to/your-project
valdoz project init              # Scans maturity & auto-places phase (or --lang ar)
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

- **Phase Gate Model**: Work progresses in sequence through 10 life-cycle phases (Intake, Requirements, Stack Decision, Architecture, Setup, Build Slices, Verify, Deploy, Handover).
- **Builder / Scribe Concurrency**: Multi-agent sessions are partitioned by file domains. Builders write code and tests; Scribes write specifications and logs.
- **Phase 6 Build Slices**: Work is broken into small, reviewable slices (`valdoz slice start / done / approve`) evaluated against the Three Slice Gate Conditions.
- **Adversarial Content Defenses**: Mandatory pre-fetch intent logging (`valdoz research log`) and boundary wrapping (`valdoz research fetch`).
- **Write-Protected State & Hash-Chained Audit Trail**: Deliverables are SHA-256 hashed on approval, `state.json` is locked (`chmod 444`), and all approvals form a cryptographic hash chain. Tampering is detected immediately.
- **Enterprise Governance & Quorums**: M-of-N human approval quorums for high-stakes phases, review dwell time-locks, and AI behavioral budgets.
- **Executive Reporting**: Generate executive narratives and handover audit reports on-demand (`valdoz explain`).
- **State Repair**: Reconstruct `state.json` from git history at any time with `valdoz state repair`.

---

## License

MIT
