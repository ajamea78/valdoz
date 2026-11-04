---
name: valdoz-setup
description: >-
  Initialize project structure, linters, test runner, Docker, hosting configs, and CI/CD pipelines.
---

# ValdoZ Setup Playbook (Project Tooling & CI/CD)

## Objectives
1. Initialize repository directory layout and package manifests (`pyproject.toml`, `package.json`, etc.).
2. Set up code linters, formatters, typecheckers, and test runner.
3. Configure deployment and container definitions (`Dockerfile`, `docker-compose.yml`, `fly.toml`, `vercel.json`).
4. Create `.env.example` with required secret placeholders.
5. Create CI pipeline workflow file (`.github/workflows/ci.yml`). Ensure baseline empty test suite passes.

## Permitted Command Whitelist
`valdoz *`, `git *`, `npm *`, `pnpm *`, `uv *`, `pip *`, `cargo *`

## Side-Effect Classification
- Category: **Config & Tooling**
- Reversibility: **Reversible**
