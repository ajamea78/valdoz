---
name: valdoz-changes
description: >-
  Plan and implement post-launch change requests, enhancements, or bug fixes with formal impact logs.
---

# ValdoZ Changes Playbook (Post-Launch Change Requests)

## Objectives
1. Intake change request or bug report, evaluate blast radius and backwards compatibility.
2. Generate impact assessment in `docs/changes/CR-NNN.md`.
3. Implement changes following slice discipline, verify with full test suite, and document update in `CHANGELOG.md`.

## Permitted Command Whitelist
`valdoz *`, `git *`

## Side-Effect Classification
- Category: **Production Changes**
- Reversibility: **IRREVERSIBLE**
