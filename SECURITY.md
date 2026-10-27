# Security Policy

ValdoZ Protocol provides cryptographic delivery discipline and governance guardrails for AI pair-programming and autonomous agent workflows. We take the security of this project and the codebases it governs seriously.

---

## Supported Versions

| Version | Supported          | Security Fixes |
| ------- | ------------------ | -------------- |
| 3.1.x   | :white_check_mark: | Active         |
| 3.0.x   | :white_check_mark: | Critical only  |
| < 3.0   | :x:                | End of life    |

---

## Core Security Assurances & Principles

ValdoZ provides deterministic, automated security guarantees:
- **Immutable Audit Trail**: Append-only audit logs with SHA-256 cryptographic hash-chaining linking every approval entry.
- **Human Approval Authority**: Strictly enforced interactive TTY validation and HMAC-SHA256 tokens with 5-minute TTL. Autonomous agents are prohibited from approving phases or build slices.
- **Package Hallucination Protection**: Proactive verification against PyPI and npm registries to prevent AI slopsquatting attacks.
- **Copyleft Isolation**: Automated license compliance checking protecting proprietary and permissive codebases from viral license contamination.
- **Container Hardening**: Hadolint AST linting blocking root execution, floating tags, and container socket exposure.
- **Credential Isolation**: Project-scoped Git credential vaults isolating credentials and preventing host credential leaks.

---

## Reporting a Vulnerability

If you discover a security vulnerability or potential bypass in ValdoZ Protocol:
1. **Do not open a public issue.**
2. Send a detailed vulnerability report via GitHub Private Vulnerability Reporting at:
   `https://github.com/ajamea78/valdoz/security/advisories/new`
   or email the security maintainer directly.
3. Include:
   - Type of vulnerability (e.g. hash chain bypass, token forgery, SSRF, prompt injection)
   - Steps to reproduce or proof of concept
   - Potential impact
4. We will acknowledge receipt within 48 hours and work with you on a coordinated disclosure timeline.
