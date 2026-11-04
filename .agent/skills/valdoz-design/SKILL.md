---
name: valdoz-design
description: >-
  Redesign website/app UI/UX, overhaul visual styling, modern responsive layouts, design systems, and screen generation.
---

# ValdoZ Design Playbook (UI/UX & Aesthetics Overhaul)

Use this playbook whenever you want to redesign an existing app or website, polish visual styling, create responsive layouts, or build a cohesive design system.

## Objectives
1. **Catalog & Skill Check:** Read `.valdoz/repos.yaml` for curated design skills (e.g., `Nutlope/hallmark` to prevent generic AI-slop UI, `pbakaus/impeccable` for visual annotations, and `tt-a1i/archify` for architecture/flow diagrams).
2. **Visual & UX Audit:** Evaluate current markup, CSS/Tailwind configs, typography scale, spacing rhythms, mobile responsiveness, and accessibility contrast.
3. **Design Direction & Palettes:** Propose 2-3 modern aesthetic themes (e.g., sleek minimal SaaS, dark mode, high-contrast dashboard) with concrete color tokens and font pairings.
4. **Mockups & Screen Generation:** Integrate with screen generators (Stitch MCP for layout generation, Canva for brand graphics, Generative UI for live previews).
5. **Design Tokens & Component Kit:** Structure reusable UI components (buttons, cards, navigation, forms, modals) or import verified GitHub UI kits via `/valdoz-import`.
6. **Implementation & Preview:** Update styles and components in tested design slices. Verify visually on dev server before merging.

## Permitted Command Whitelist
`valdoz *`, `git status`, `git diff`, `npm run dev`, `pnpm dev`, `vite`, `python -m http.server`

## Side-Effect Classification
- Category: **Files only / Styling**
- Reversibility: **Reversible**

## Operating Procedure
1. Check `.valdoz/repos.yaml` for design skills and UI templates.
2. Inspect existing UI structure and styling configs (`tailwind.config.*`, CSS files, component templates).
3. Present visual proposals and mockups to the user in chat.
4. Once approved, implement styling changes in isolated slices.
5. Verify responsiveness and contrast. Present before-and-after walkthrough to the user.
