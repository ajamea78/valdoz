# Documentation Synchronization Policy

1. Atomic Documentation Reflex: Never consider any update, bug fix, security patch, API change, or feature addition complete without reflecting it in `CHANGELOG.md` and relevant documentation (`docs/USER_GUIDE.md` or `README.md`).
2. Scribe Transition: After the `builder` role completes code and test verification, automatically switch to the `scribe` role to record the functional delta.
3. Changelog Maintenance: Keep `CHANGELOG.md` updated per Keep a Changelog standards under the active version header before requesting human approval or completing tasks.
