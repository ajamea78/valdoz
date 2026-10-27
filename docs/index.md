# ValdoZ Protocol v3.1.1

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
5. **TOCTOU Defense & Deliverables-Bound Approval Tokens (`valdoz-v2`)**: Human approval tokens bind the exact SHA-256 composite hash of deliverables into the HMAC-SHA256 signature, eliminating post-token file modification races.
6. **Out-of-Workspace Keystore Resolution**: Keys reside outside the workspace in `~/.config/valdoz/keys/approval.key` (or `VALDOZ_APPROVAL_SECRET`), isolating credentials from in-workspace agent execution.
7. **Single-Use Nonce Burn & Replay Defense**: Consumed approval tokens are registered in `.valdoz/consumed_nonces.json` with 15-minute pruning, preventing token replay attacks within TTL windows.
8. **RFC 8785 Canonical JSON Audit Log Hash Chaining**: Append-only hash-chained ledger (`.valdoz/approvals.log`) formats all entries into strict canonical JSON, ensuring non-repudiation and detecting retroactive log modifications.
9. **State Repair Laundering Defense**: `valdoz state repair` refuses to restore approved status without unbroken cryptographic ledger verification and un-tampered deliverable hashes.
10. **LLM Secret Scrubbing Pipeline**: Automated redaction of API keys, PATs, bearer headers, and private keys from failure logs before sending diagnostic prompts to AI self-healing endpoints.
11. **Pack Supply-Chain Integrity & Prompt Injection Defenses**: Scans imported agent skills and rules for adversarial prompt injections (override directives, jailbreaks, hidden comments) and verifies file SHA-256 integrity maps.
12. **Universal Security Audit & AST SAST**: Built-in scanner (`valdoz audit`) runs Semgrep AST analysis, real-time package hallucination & slopsquatting checks, copyleft compliance, and external audit trail anchoring (`valdoz anchor`).
13. **Autonomous Self-Healing**: Automated diagnosis, code patching, and gate re-verification for local development and CI/CD pipelines with strict security quarantine.
14. **Continuous Deployment Protection**: Built-in Git `pre-push` hooks block accidental pushes to production branches until Phase 8 (Deploy) is human-approved.
15. **Project-Scoped Credential Vaults & Multi-Account Isolation**: Each repository maintains its own isolated credential store (`.valdoz/.git-credentials`, `chmod 600`), stopping token collisions and identity leaks across personal, work, and client GitHub accounts.

---

## Quick Navigation

- 📖 **[Complete User Guide](USER_GUIDE.md)**: The end-to-end operational manual, Builder & Scribe roles, Phase 6 slices, and cheat sheets.
- 🛡️ **[Threat Model & Security Architecture](THREAT_MODEL.md)**: Formal analysis of Adversary A1 (rogue agent), Adversary A2 (cloud insider), and Adversary A3 (supply-chain attacker).
- 🔄 **[Migration Guide](MIGRATION.md)**: Upgrading existing ValdoZ repositories from v2.x/v3.0 to v3.1.1.
- 💡 **[Commercial & Strategy Playbook](marketing/PITCH_AND_MARKETING.md)**: Value proposition, agency delivery model, and monetization pathways.

---

## 3-Step Quick Start

### 1. Install ValdoZ
```bash
# Install uv (if not already installed):
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install tagged release directly:
uv tool install git+https://github.com/ajamea78/valdoz.git@v3.1.1

# (Or install from local source):
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
