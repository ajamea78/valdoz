---
name: valdoz-build
description: >-
  Implement features slice-by-slice with test-driven discipline, typechecks, and zero broken builds.
---

# ValdoZ Build Playbook (Slice Implementation)

## Objectives
1. Implement features incrementally in isolated, tested slices.
2. For each slice, create `docs/slices/NN-name.md`, write automated tests first (TDD), implement the code, run typechecks, linters, and test suite.
3. For frontend slices, enforce persistent layout frames (no full-page skeleton replacement) and cache-first state initialization to guarantee flicker-free navigation.
4. For database slices, enforce additive schema changes (Directive 13) leaving live application data intact.
5. Mark slice completion with `valdoz slice done` (executes non-bypassable full-spectrum verification across all packages).

## Permitted Command Whitelist
`valdoz *`, `valdoz verify`, `git status`, `git diff`, test runners, linters, build tools.

## Side-Effect Classification
- Category: **Commits & Branches**
- Reversibility: **Reversible**
