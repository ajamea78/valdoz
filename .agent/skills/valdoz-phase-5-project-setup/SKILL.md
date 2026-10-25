---
name: valdoz-phase-5-project-setup
description: >-
  Use this playbook when operating in Phase 5 (Project Setup) of a ValdoZ project.
---

# Phase 5: Project Setup Playbook

## Objectives
Initialize the project repository structure, linter, formatter, test runner, `.env.example`, and CI workflow file. Ensure a baseline empty test suite passes.

## Permitted Command Whitelist
`valdoz *`, `git *`, `uv *`, `pip *`, `npm *`, `pytest *`, `python *`

## Required Deliverables
- `README.md`

## Side-Effect Classification
- Category: **Config & Tooling**
- Reversibility: **Reversible**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
