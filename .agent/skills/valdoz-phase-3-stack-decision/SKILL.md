---
name: valdoz-phase-3-stack-decision
description: >-
  Use this playbook when operating in Phase 3 (Stack Decision) of a ValdoZ project.
---

# Phase 3: Stack Decision Playbook

## Objectives
Compare technical options against the requirements. Provide 2-3 stack options with trade-offs and a recommendation. Record the chosen stack in `docs/03-stack-decision.md` and log decisions with `valdoz decision add`.

## Permitted Command Whitelist
`valdoz *`, `git status`, `git diff`

## Required Deliverables
- `docs/03-stack-decision.md`

## Side-Effect Classification
- Category: **Files only**
- Reversibility: **Reversible**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
