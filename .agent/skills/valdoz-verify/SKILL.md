---
name: valdoz-verify
description: >-
  Execute comprehensive verification: unit/integration tests, security SAST scans, secret leak checks, and gate audits.
---

# ValdoZ Verify Playbook (Quality & Security Verification)

## Objectives
1. **Security Standards & Skills:** Reference `.valdoz/repos.yaml` for security and verification tools (e.g. `vercel/turborepo` for monorepo tasks, `biomejs/biome` for instant AST semantic analysis, `microsoft/playwright` for headless smoke tests, `cloudflare/security-audit-skill` for vulnerability assessment).
2. **Full-Spectrum Verification:** Execute `valdoz verify` to run the 4 verification pillars across root and all workspace subprojects (linters, typechecks, tests, builds).
3. **Static Analysis & SAST:** Run automated SAST scan (Semgrep), secrets detection, and lockfile integrity verification.
4. **Compliance & Drift:** Verify accessibility (WCAG), performance, and API contract drift.
5. **UI & Perceptual Stability Verification:** For frontend tasks, automated passes do NOT guarantee visual smoothness. Verify that shells do not unmount on navigation, persistent frames eliminate layout shifts (no early skeleton returns), state initializes cache-first, and all JSX symbols are imported.
6. **Reporting:** Compile verification report in `docs/07-verification.md`.

## Permitted Command Whitelist
`valdoz *`, `valdoz verify`, `valdoz audit`, test runners, linters.

## Required Deliverables
- `docs/07-verification.md`

## Side-Effect Classification
- Category: **Test Artifacts**
- Reversibility: **Reversible**
