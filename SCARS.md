# VALDOZ PROTOCOL — GLOBAL IMMUNITY LEDGER (v3.1.0)
<!-- valdoz_version: 3.1.0 -->

Tags:
- `[enforced]`: Automatically verified by `valdoz audit` or `valdoz gate check`. Blocking on failure.
- `[heuristic]`: Checked by audit but can produce false positives (warning by default).
- `[on-demand]`: Checked by running a dedicated command (e.g. `valdoz visual-diff`).
- `[advisory]`: Best practice guideline without automated check; must be verified during human review.

---

## 1. Core Protocol Immunity Ledger

1. **SCAR-CORE-001** (formerly SCAR-015) `[enforced]`: Approvals logs (`.valdoz/approvals.log`) must maintain an unbroken cryptographic hash chain linking each entry to its predecessor to prevent retroactive log editing or truncation.
2. **SCAR-CORE-002** (formerly SCAR-013) `[enforced]`: Cryptographic approval tokens must strictly enforce full 256-bit HMAC signatures with unique nonce and 5-minute TTL; unauthenticated or timestamp-only fallbacks are strictly prohibited.
3. **SCAR-CORE-003** (formerly SCAR-014) `[enforced]`: Phase 6 slice completion gates (`valdoz slice done`) must execute real automated test suites with regression detection before advancing a slice to `gated`.
4. **SCAR-CORE-004** (formerly SCAR-016) `[enforced]`: Central state records (`state.json`) approval hashes must cross-verify against the cryptographic audit trail ledger (`approvals.log`).
5. **SCAR-CORE-005** (formerly SCAR-007) `[enforced]`: Process liveness must be verified via recorded PID tracking and explicit signal checking, never via blind system-wide `pkill`.
6. **SCAR-CORE-006** (formerly SCAR-012) `[on-demand]`: Visual regression threshold enforcement against committed baselines (`valdoz visual-diff`) must fail gracefully with actionable guidance if optional visual dependencies are missing.
7. **SCAR-CORE-007** `[enforced]`: Role boundaries (Builder writing code/tests vs. Scribe writing docs/decisions) must be enforced by both local Git hooks and server-side CI gates.
8. **SCAR-CORE-008** `[enforced]`: Cryptographic audit logs must be anchored to an immutable external reference (Git tag or release anchor) to prevent end-to-end ledger recreation.

---

## 2. Web Application & Frontend Pack Ledger (`web-app`)

9. **SCAR-WEB-001** (formerly SCAR-001) `[enforced]`: Never create `public/design-preview.html`. Serve previews strictly via dynamic router endpoints.
10. **SCAR-WEB-002** (formerly SCAR-002) `[heuristic]`: Build completely independent component files for user flow directions (e.g., `Direction*.tsx` must be full implementations, not superficial hero swaps).
11. **SCAR-WEB-003** (formerly SCAR-003) `[enforced]`: Lock UI switcher controls to bottom-right (`fixed bottom-5 right-5 z-[9999]`) to avoid viewport collision.
12. **SCAR-WEB-004** (formerly SCAR-004) `[enforced]`: Verify `vercel.json` framework configuration matches declared dependencies in `package.json`.
13. **SCAR-WEB-005** (formerly SCAR-005) `[enforced]`: Tailwind content glob patterns must cover all source directories; compiled CSS must exceed the minimum size floor.
14. **SCAR-WEB-006** (formerly SCAR-006) `[heuristic]`: Client-side `useSearchParams` must sit under a Suspense boundary; dynamic timestamps (`new Date()`) must be gated behind mounted state to avoid SSR hydration mismatch.
15. **SCAR-WEB-007** (formerly SCAR-011) `[enforced]`: Deployment outputs must reference permanent branch or preview domains, never ephemeral hash-only URLs.

---

## 3. Desktop & System Integration Pack Ledger (`desktop`)

16. **SCAR-SYS-001** (formerly SCAR-008) `[advisory]`: Manage desktop environments using declarative tools (such as `xfconf-query`), never direct desktop XML file mutation.
17. **SCAR-SYS-002** (formerly SCAR-009) `[enforced]`: Require a successful HTTP/socket liveness probe before claiming deployment or startup success.
18. **SCAR-SYS-003** (formerly SCAR-010) `[advisory]`: Verify Python syntax and dependency locks within the dedicated project virtual environment.
