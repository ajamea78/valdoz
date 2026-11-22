# Art Direction & Anti-Slop Aesthetic Discipline Policy

1. Phase 4.5: Art Direction & Design Tokens: Before proceeding to Phase 5 or any Phase 6 implementation slice, every project must define `docs/04-art-direction.md` and `DESIGN.md`.
2. Required Aesthetic Specifications: `docs/04-art-direction.md` must codify: (a) Metaphor & Subject Inventory, (b) Typographic System (Display, Body, Monospace Data), (c) Atmosphere & Surface Rules (canvas texture, hairline borders, prohibited slop elements), and (d) Hero Artifact Blueprint.
3. Design Token Registry: `DESIGN.md` must register living CSS variables or design tokens for canvas, cards, borders, and accents.
4. Anti-Slop Juror Rubric: Frontend code slices are rejected if they rely on default unstyled Tailwind color palettes, lack tabular alignment (`tabular-nums`) for numeric metrics, use symmetric 3-card grids without asymmetric cadence, or feature buttons without physical micro-interaction states (`active:scale-[0.98]`).
