---
name: valdoz-import
description: >-
  Safely import, audit, and integrate any GitHub repo, UI component library, or template into the workspace.
---

# ValdoZ Import Playbook (GitHub Repo & Addon Integration)

Use this playbook to safely import third-party GitHub repositories, UI design kits, starter templates, or community modules into your project.

## Objectives
1. **Clone & Inspect:** Clone the specified GitHub repository to a temporary inspection workspace.
2. **Security & Safety Audit:**
   - Scan for malicious install scripts, prompt injections, and hidden network telemetry.
   - Scan for license compliance (flag restrictive GPL/AGPL copyleft when proprietary/MIT/Apache is required).
   - Check secret leaks and dependency hygiene.
3. **Safe Extraction & Integration:** Extract only the necessary UI components, stylesheets, or code modules into your project's folders.
4. **Wiring & Dependency Configuration:** Install required runtime packages and update build configurations.
5. **Provenance Logging:** Record the source repository URL, commit hash, license, and purpose into `.valdoz/decisions.jsonl`.

## Permitted Command Whitelist
`valdoz *`, `git clone`, `git status`, package manager install commands.

## Side-Effect Classification
- Category: **Files & Dependencies**
- Reversibility: **Reversible**
