# ValdoZ Protocol v3.0

> **Antigravity Delivery Discipline Engine**  
> Turning autonomous AI coding assistants into disciplined, accountable delivery partners.

---

## What is ValdoZ?

Autonomous AI coding agents like **Google Antigravity** are fast, but left unconstrained they sprint past key decisions:
- They assume requirements instead of asking.
- They invent packages, APIs, or URLs that don't exist.
- They mark tasks "done" without running real tests.
- They can bypass safety gates by running arbitrary terminal commands.

**ValdoZ Protocol** is the discipline harness. It acts as an experienced Tech Lead standing next to the agent:
1. **11-Phase Lifecycle Delivery**: The agent cannot jump ahead. Work progresses in sequence from Phase 0 (Init) through Phase 10 (Changes).
2. **Evidence Over Claims**: "Done" means actual commands ran, tests passed, and deliverables exist with no placeholders (`TODO`, `TBD`).
3. **Human Gatekeeper**: At the end of every phase, the agent stops cold. Only an interactive human can approve work. The agent cannot approve its own code.
4. **Tamper-Proof State**: Approved deliverables are cryptographically hashed (SHA-256) and `state.json` is write-protected (`chmod 444`).
5. **Autonomous Self-Healing**: Automated diagnosis, code patching, and gate re-verification for local development and CI/CD pipelines.
6. **Continuous Deployment Protection**: Built-in Git `pre-push` hooks block accidental pushes to production branches until Phase 8 (Deploy) is human-approved.

---

## Quick Navigation

- 📖 **[Complete User Guide](USER_GUIDE.md)**: The end-to-end operational manual, Builder & Scribe roles, Phase 6 slices, and cheat sheets.
- 🔄 **[Migration Guide](MIGRATION.md)**: Upgrading existing ValdoZ repositories from v2.x to v3.0.
- 💡 **[Commercial & Strategy Playbook](marketing/PITCH_AND_MARKETING.md)**: Value proposition, agency delivery model, and monetization pathways.

---

## 3-Step Quick Start

### 1. Install ValdoZ
```bash
# Install uv (if not already installed):
curl -LsSf https://astral.sh/uv/install.sh | sh

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

# Approve work (Human-Only, Interactive TTY or Antigravity Bridge)
valdoz phase approve

# Advance to next phase
valdoz phase next
```
