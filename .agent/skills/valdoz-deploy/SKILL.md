---
name: valdoz-deploy
description: >-
  Deploy and host application on staging or production cloud environments with DNS, SSL, and rollback strategy.
---

# ValdoZ Deploy Playbook (Staging & Production Deployment)

## Objectives
1. Prepare deployment runbook, environment secrets, and rollback strategy in `docs/08-deploy.md`.
2. Deploy to staging environment, run live smoke tests, and verify endpoints.
3. Request explicit human sign-off before deploying to live production cloud infrastructure.
4. Verify custom domain, DNS records, SSL certificates, and health monitoring.

## Permitted Command Whitelist
`valdoz *`, deployment CLIs (`vercel`, `fly`, `aws`, `gcloud`, `docker`), `git push` to production branches.

## Required Deliverables
- `docs/08-deploy.md`

## Side-Effect Classification
- Category: **Live Infrastructure**
- Reversibility: **IRREVERSIBLE** (Requires explicit human confirmation)
