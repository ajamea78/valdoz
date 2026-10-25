---
name: valdoz-phase-1-intake
description: >-
  Use this playbook when operating in Phase 1 (Intake) of a ValdoZ project.
---

# Phase 1: Intake Playbook

## Objectives
Read the client's brief thoroughly. Quote the brief verbatim in `docs/01-intake.md`. Extract open questions, risks, assumptions, and key stakeholders. Ask questions one at a time.

## Permitted Command Whitelist
`valdoz *`, `git status`, `git diff`

## Required Deliverables
- `docs/01-intake.md`

## Side-Effect Classification
- Category: **Files only**
- Reversibility: **Reversible**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
