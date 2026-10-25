# ValdoZ Protocol: v2.x to v3.0 Migration Guide

This document describes how to migrate an existing repository governed by ValdoZ v2.1.1 to ValdoZ v3.0.

---

## What Changed in v3.0

1. **State Engine**:
   - `state.json` is write-protected (`chmod 444`) after phase approval.
   - Deliverables are SHA-256 hashed on approval. Any post-approval edits trigger tamper alerts.
   - `valdoz state repair` can reconstruct state from git history at any time.

2. **Multi-Role Concurrency (Builder & Scribe)**:
   - ValdoZ separates agent duties into two non-overlapping domains:
     - `builder`: writes code (`src/`), tests (`tests/`), and package manifests.
     - `scribe`: writes documentation (`docs/`), decisions, research logs, and changelogs.
   - Active roles are locked via `.valdoz/session.lock`.

3. **Phase 6 Slices**:
   - Work in Phase 6 progresses through 4 states: `open` $\rightarrow$ `built` $\rightarrow$ `gated` $\rightarrow$ `approved`.
   - Each slice requires a specification in `docs/slices/NN-name.md` with:
     - Summary
     - Acceptance Criteria
     - Test Plan
     - File Manifest
   - Slice completion requires satisfying the **Three Slice Gate Conditions**:
     1. Pre-existing tests pass.
     2. New tests pass.
     3. Test coverage is maintained.

4. **Adversarial Content Defenses**:
   - External web URLs must be pre-logged with `valdoz research log --url <url> --claim <claim>`.
   - External pages can be sanitized and safely boundary-wrapped with `valdoz research fetch <url>`.

5. **Universal Audit & Stack Packs**:
   - Legacy SCAR rules have transitioned into the modular pack system:
     - `base`: secrets scan, lockfile check, placeholder scan.
     - `web-app`: imports check, build check, test check, liveness probe.
     - `website`: SEO meta, accessibility, bundle budget.
     - `api`: OpenAPI contracts, migrations.

---

## Migration Steps

### Step 1: Install ValdoZ v3.0
```bash
# From local repository source:
uv tool install --editable . --force

# Or standard global install:
uv tool install . --force

# Or with pipx / virtualenv:
pipx install .
```

### Step 2: Initialize v3.0 State
In your project repository:
```bash
valdoz project init
# Or with Arabic client deliverables:
valdoz project init --lang ar
```

### Step 3: Synchronize Agent Runtimes
Generate the updated Antigravity rules and skills:
```bash
valdoz sync-runtimes
```

### Step 4: Install Git Pre-Commit Hook
Enforce role domain locks and gate checks locally:
```bash
valdoz hook install
```

### Step 5: Generate CI Workflow
```bash
valdoz ci generate
```

### Step 6: Verify Repository Health
Run an audit across your codebase:
```bash
valdoz audit
```
