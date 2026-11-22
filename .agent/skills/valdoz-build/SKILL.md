---
name: valdoz-build
description: >-
  Implement features slice-by-slice with test-driven discipline, typechecks, and zero broken builds.
---

# ValdoZ Build Playbook (Slice Implementation)

## Objectives
1. Implement features incrementally in isolated, mechanically tracked slices. Every code slice MUST be initialized with `valdoz slice start <slice-id>` before writing or modifying code.
2. For each slice, create `docs/slices/NN-name.md`, write automated tests first (TDD), implement the code, run typechecks, linters, and test suite.
3. For frontend slices, enforce the Anti-Slop Juror Rubric (use `DESIGN.md` tokens, `tabular-nums` on numbers, `active:scale-[0.98]` on buttons), maintain persistent layout frames, and enforce cache-first state initialization.
4. For database slices, enforce additive schema changes (Directive 13) leaving live application data intact.
5. Mark slice completion with `valdoz slice done <slice-id>` (executes non-bypassable full-spectrum verification across all packages and anti-slop audits).

## Permitted Command Whitelist
`valdoz *`, `valdoz verify`, `git status`, `git diff`, test runners, linters, build tools.

## Side-Effect Classification
- Category: **Commits & Branches**
- Reversibility: **Reversible**
