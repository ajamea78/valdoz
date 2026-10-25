---
name: valdoz-phase-7-verify
description: >-
  Use this playbook when operating in Phase 7 (Verify) of a ValdoZ project.
---

# Phase 7: Verify Playbook

## Objectives
Execute full verification: unit tests, integration tests, accessibility check, security checklist, and acceptance walkthrough in `docs/07-verification.md`.

## Permitted Command Whitelist
`valdoz *`, `git *`, `pytest *`, `npm test`, `npm run lint`

## Required Deliverables
- `docs/07-verification.md`

## Side-Effect Classification
- Category: **Test Artifacts**
- Reversibility: **Reversible**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
