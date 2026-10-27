# Contributing to ValdoZ Protocol

Thank you for your interest in contributing to ValdoZ Protocol!

ValdoZ is designed around strict delivery discipline, separation of concerns, and automated verification. All contributors (human and AI agents alike) must adhere to these guidelines.

---

## 1. Role Domain Separation

ValdoZ enforces strict domain separation between two active roles:
- **`builder`**: Authors code in `src/`, unit tests in `tests/`, and build configuration (`pyproject.toml`, `uv.lock`). The `builder` is **prohibited** from directly modifying documentation (`docs/`, `CHANGELOG.md`).
- **`scribe`**: Authors documentation in `docs/`, `CHANGELOG.md`, `.valdoz/decisions.jsonl`, and research notes. The `scribe` is **prohibited** from modifying application code or test suites.

When authoring Git commits locally, specify your role:
```bash
# For code and test commits:
VALDOZ_ROLE=builder git commit -m "feat(audit): add new scanner"

# For documentation commits:
VALDOZ_ROLE=scribe git commit -m "docs: document new scanner options"
```

---

## 2. Local Development Setup

We recommend using [`uv`](https://astral.sh/uv) for fast, reproducible Python environment management:

```bash
# Clone the repository
git clone https://github.com/ajamea78/valdoz.git
cd valdoz

# Create virtual environment and install dev dependencies
uv venv
uv pip install -e ".[dev]"

# Install local Git hooks
uv run valdoz hook install
```

---

## 3. Pre-Commit Verification

Before opening a pull request, run the test and audit suites:

```bash
# Run unit tests
uv run pytest -v

# Run the ValdoZ universal audit
uv run valdoz audit --semgrep --verify-packages --licenses --contract --containers

# Run SAST security scanning
uvx bandit -r src/valdoz -ll
uvx semgrep scan --config auto src/valdoz

# Verify documentation builds cleanly
uvx --with mkdocs-material mkdocs build --strict
```

---

## 4. Pull Request Requirements

- All pull requests must pass the automated GitHub Actions CI matrix (Python 3.10–3.13).
- Test coverage must not drop below 80%.
- New features or bug fixes must include unit test coverage.
- PRs must adhere to role domain separation.
