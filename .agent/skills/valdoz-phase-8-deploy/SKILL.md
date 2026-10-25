---
name: valdoz-phase-8-deploy
description: >-
  Use this playbook when operating in Phase 8 (Deploy) of a ValdoZ project.
---

# Phase 8: Deploy Playbook

## Objectives
Prepare deployment environment, deployment procedures, live health checks, and rollback strategy in `docs/08-deploy.md`. CAUTION: Real-world side effects are IRREVERSIBLE.

## Permitted Command Whitelist
`valdoz *`, `git *`, `vercel *`, `fly *`, `aws *`, `docker *`

## Required Deliverables
- `docs/08-deploy.md`

## Side-Effect Classification
- Category: **Live Infrastructure**
- Reversibility: **IRREVERSIBLE**

## Operating Procedure
1. Check phase status: `valdoz phase status` (or use `valdoz_get_status` tool)
2. Formulate deliverables according to requirements.
3. Pre-log any research intent: `valdoz research log --url <url> --claim <claim>`
4. Present deliverables and summary of work to the human user in Antigravity chat.
5. In Antigravity: Never tell the user to switch to a terminal or shell. Request human approval directly in chat using `valdoz_request_human_approval` or by asking the user to confirm in conversation.
