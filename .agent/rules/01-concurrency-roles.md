# Agent Roles and File Domains

## Builder Role
- Permitted write domains: `src/`, `tests/`, build configs, `.valdoz/slices/`
- Prohibited write domains: `docs/`, `CHANGELOG.md`

## Scribe Role
- Permitted write domains: `docs/`, `.valdoz/decisions.jsonl`, `.valdoz/research.jsonl`, `CHANGELOG.md`
- Read-only access: `src/`, `tests/`
