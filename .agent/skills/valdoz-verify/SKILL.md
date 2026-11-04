---
name: valdoz-verify
description: >-
  Execute comprehensive verification: unit/integration tests, security SAST scans, secret leak checks, and gate audits.
---

# ValdoZ Verify Playbook (Quality & Security Verification)

## Objectives
1. Execute full test suite (unit, integration, end-to-end) with test coverage thresholds.
2. Run automated SAST scan (Semgrep), secrets detection, and lockfile integrity verification.
3. Verify accessibility (WCAG), performance, and API contract drift.
4. Compile verification report in `docs/07-verification.md`.

## Permitted Command Whitelist
`valdoz *`, `valdoz audit`, test runners, linters.

## Required Deliverables
- `docs/07-verification.md`

## Side-Effect Classification
- Category: **Test Artifacts**
- Reversibility: **Reversible**
