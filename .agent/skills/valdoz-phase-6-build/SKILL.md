---
name: valdoz-phase-6-build
description: >-
  Use this playbook when operating in Phase 6 (Build) of a ValdoZ project.
---

# Phase 6: Build Playbook

## Objectives
Implement the project in tested slices. For each slice, create `docs/slices/NN-name.md`, write tests first, implement code, and run `valdoz slice done`.

## Permitted Command Whitelist
`valdoz *`, `git *`, `uv *`, `pip *`, `npm *`, `pytest *`, `python *`

## Required Deliverables
- Dynamic deliverables

## Side-Effect Classification
- Category: **Commits & Branches**
- Reversibility: **Reversible**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
