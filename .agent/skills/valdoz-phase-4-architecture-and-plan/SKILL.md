---
name: valdoz-phase-4-architecture-and-plan
description: >-
  Use this playbook when operating in Phase 4 (Architecture and Plan) of a ValdoZ project.
---

# Phase 4: Architecture and Plan Playbook

## Objectives
Design system architecture, data models, API contracts, integration points, and the slice roadmap in `docs/04-architecture.md` and `docs/04-plan.md`.

## Permitted Command Whitelist
`valdoz *`, `git status`, `git diff`

## Required Deliverables
- `docs/04-architecture.md`
- `docs/04-plan.md`

## Side-Effect Classification
- Category: **Files only**
- Reversibility: **Reversible**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
