## Summary
<!-- Briefly describe the changes introduced in this pull request and the motivation behind them. -->

## Changes Introduced
- [ ] Code implementation (`src/`)
- [ ] Unit tests added / updated (`tests/`)
- [ ] Documentation updated (`docs/`, `CHANGELOG.md`)

## Pre-Submission Verification Checklist
- [ ] Ran `uv run pytest -v` (100% tests passing)
- [ ] Test coverage maintained ($\ge 80\%$)
- [ ] Ran `uv run valdoz audit --strict` (all blocking checks pass)
- [ ] Ran `uvx bandit -r src/valdoz -ll` (zero issues identified)
- [ ] Ran `uvx semgrep scan --config auto src/valdoz` (clean SAST analysis)
- [ ] Documentation and code commits adhere to Builder / Scribe role separation
