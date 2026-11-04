---
name: valdoz-build
description: >-
  Implement features slice-by-slice with test-driven discipline, typechecks, and zero broken builds.
---

# ValdoZ Build Playbook (Slice Implementation)

## Objectives
1. Implement features incrementally in isolated, tested slices.
2. For each slice, create `docs/slices/NN-name.md`, write automated tests first (TDD), implement the code, run typechecks and test suite.
3. Mark slice completion with `valdoz slice done`.

## Permitted Command Whitelist
`valdoz *`, `git status`, `git diff`, test runners, linters, build tools.

## Side-Effect Classification
- Category: **Commits & Branches**
- Reversibility: **Reversible**
