---
name: valdoz-phase-9-handover
description: >-
  Use this playbook when operating in Phase 9 (Handover) of a ValdoZ project.
---

# Phase 9: Handover Playbook

## Objectives
Draft operational runbook, access transfer plan, known issues, and client sign-off in `docs/09-handover.md`.

## Permitted Command Whitelist
`valdoz *`, `git *`

## Required Deliverables
- `docs/09-handover.md`

## Side-Effect Classification
- Category: **Access Transfer**
- Reversibility: **IRREVERSIBLE**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
