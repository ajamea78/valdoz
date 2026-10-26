# VALDOZ PROTOCOL — GLOBAL IMMUNITY LEDGER (v2.1.1)
<!-- valdoz_version: 2.1.1 -->
Tags: [enforced] checked by `valdoz audit`; [heuristic] checked by audit but can
false-positive (warning by default); [on-demand] checked by running a separate
command; [advisory] no automated check, follow manually.

1. **SCAR-001** [enforced]: Never create public/design-preview.html. Serve via router.
2. **SCAR-002** [heuristic]: Build completely independent component files for directions (Direction*.tsx should not be tiny hero swaps).
3. **SCAR-003** [enforced]: Lock switcher pill to bottom-right (fixed bottom-5 right-5 z-[9999]).
4. **SCAR-004** [enforced]: Verify vercel.json framework matches package.json.
5. **SCAR-005** [enforced]: Tailwind content globs cover source dirs; compiled CSS above the size floor.
6. **SCAR-006** [heuristic]: useSearchParams should sit under a Suspense boundary; new Date() behind mounted state.
7. **SCAR-007** [enforced]: Process liveness checked via PID records, not blind pkill.
8. **SCAR-008** [advisory]: Use xfconf-query, never direct desktop XML edits.
9. **SCAR-009** [enforced]: Require a successful liveness probe before claiming deploy success.
10. **SCAR-010** [advisory]: Verify Python syntax and dependency lock via the project venv.
11. **SCAR-011** [enforced]: Output permanent branch domains only (no preview-hash URLs).
12. **SCAR-012** [on-demand]: Enforce visual regression threshold against a committed baseline (`valdoz visual-diff`).
13. **SCAR-013** [enforced]: Cryptographic approval tokens must strictly enforce full 256-bit HMAC signatures; never permit unauthenticated timestamp fallbacks.
14. **SCAR-014** [enforced]: Slice completion gates must execute real automated test suites before advancing to `gated`.
15. **SCAR-015** [enforced]: Approvals logs must maintain an immutable cryptographic hash chain to prevent retroactive log editing or truncation.
16. **SCAR-016** [enforced]: Central state file (`state.json`) approval records must cross-verify against the cryptographic audit ledger.
