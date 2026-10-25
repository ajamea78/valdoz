---
name: valdoz-phase-10-change-requests
description: >-
  Use this playbook when operating in Phase 10 (Change Requests) of a ValdoZ project.
---

# Phase 10: Change Requests Playbook

## Objectives
Handle post-handover change requests with short intake, impact note, and approval in `docs/changes/CR-NNN.md`.

## Permitted Command Whitelist
`valdoz *`, `git *`

## Required Deliverables
- Dynamic deliverables

## Side-Effect Classification
- Category: **Production Changes**
- Reversibility: **IRREVERSIBLE**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
