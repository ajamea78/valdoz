---
name: valdoz-architect
description: >-
  Choose tech stack, hosting providers (Vercel, AWS, Cloud Run, Supabase), database schemas, APIs, and system architecture.
---

# ValdoZ Architect Playbook (Tech Stack, Hosting & Architecture)

## Objectives
1. **Tech Stack Selection:** Compare 2-3 technology stacks against project requirements (frontend, backend, database, state management). Document decision in `docs/03-stack-decision.md`.
2. **Hosting & Cloud Infrastructure:** Define hosting targets upfront (Vercel, Cloudflare, Supabase, Fly.io, Cloud Run, AWS). Define cost budgets, serverless vs container strategy, environment variables, and CDN/DNS setup.
3. **System Architecture & Data Models:** Design system components, database schemas, API contracts (OpenAPI/REST/GraphQL), third-party integrations, and implementation slice roadmaps in `docs/04-architecture.md` and `docs/04-plan.md`.

## Permitted Command Whitelist
`valdoz *`, `git status`, `git diff`

## Required Deliverables
- `docs/03-stack-decision.md`
- `docs/04-architecture.md`
- `docs/04-plan.md`

## Side-Effect Classification
- Category: **Files only**
- Reversibility: **Reversible**

## Operating Procedure
1. Check phase status: `valdoz phase status`
2. Formulate tech stack, hosting blueprint, and system architecture.
3. Present deliverables and summary of architectural decisions in chat.
4. Request human approval directly in Antigravity chat.
