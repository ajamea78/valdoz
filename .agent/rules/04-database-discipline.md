# Database Discipline and Data Protection Policy

1. Zero-Destructive Discipline: Never execute unconditional deletion or drop scripts on database files (`*.db`, `*.sqlite`, `DROP DATABASE`, `TRUNCATE`, `rm -f *.db*`, or `fs.unlinkSync`).
2. Mandatory Confirmation & Backups: Any reset or re-initialization script MUST require a mandatory `--force-reset` flag AND automatically create an immutable, timestamped backup in `backups/db/` prior to execution.
3. Additive Schema Evolution: All schema alterations and performance index additions MUST be strictly additive (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`), leaving live data intact and verifiable.
4. Data Verification: Validate schema integrity using verification commands (such as `npm run audit:db` or migration checks) without mutating or dropping live application data.
