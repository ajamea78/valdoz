"""Unit tests for Directive 13: Zero-Destructive Database Discipline & Data Protection."""

import json
import pytest
from pathlib import Path

from valdoz.checks import scan_database_safety, run_valdoz_audit
from valdoz.packs import BUILTIN_PACKS
from valdoz.sync import sync_all_runtimes, get_core_agent_rules
from valdoz.state import ValdozState, save_state


@pytest.fixture
def temp_project(tmp_path: Path):
    state = ValdozState(project_name="db-safety-test", packs=["base"])
    save_state(tmp_path, state)
    return tmp_path


def test_builtin_base_pack_includes_db_safety_guard():
    base_pack = BUILTIN_PACKS["base"]
    check_ids = [c.id for c in base_pack.checks]
    assert "db-safety-guard" in check_ids


def test_core_agent_rules_includes_directive_13():
    rules = get_core_agent_rules()
    assert "13. Zero-Destructive Database Discipline & Data Protection" in rules
    assert "--force-reset" in rules
    assert "backups/db/" in rules


def test_clean_project_passes_database_safety(temp_project: Path):
    res = scan_database_safety(temp_project)
    assert res.passed is True
    assert res.id == "db-safety-guard"
    assert "adhere to zero-destructive discipline" in res.message


def test_unguarded_rm_db_in_script_fails(temp_project: Path):
    script_dir = temp_project / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    script = script_dir / "reset.sh"
    script.write_text("#!/bin/bash\nrm -f data.sqlite\n")

    res = scan_database_safety(temp_project)
    assert res.passed is False
    assert "scripts/reset.sh" in res.message


def test_unguarded_unlink_in_js_script_fails(temp_project: Path):
    script_dir = temp_project / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    script = script_dir / "init-db.js"
    script.write_text("""
const fs = require('fs');
fs.unlinkSync('./dev.db');
console.log('Database wiped');
""")

    res = scan_database_safety(temp_project)
    assert res.passed is False
    assert "scripts/init-db.js" in res.message
    assert "--force-reset" in res.message


def test_unguarded_drop_database_fails(temp_project: Path):
    script_dir = temp_project / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    sql_script = script_dir / "cleanup.sql"
    sql_script.write_text("DROP DATABASE production_db;\n")

    res = scan_database_safety(temp_project)
    assert res.passed is False
    assert "scripts/cleanup.sql" in res.message


def test_unguarded_package_json_db_wipe_fails(temp_project: Path):
    pkg_json = temp_project / "package.json"
    pkg_json.write_text(json.dumps({
        "name": "test-app",
        "scripts": {
            "db:wipe": "rm -f ./app.db && node seed.js"
        }
    }))

    res = scan_database_safety(temp_project)
    assert res.passed is False
    assert "package.json" in res.message


def test_guarded_init_db_script_passes(temp_project: Path):
    script_dir = temp_project / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    script = script_dir / "init-db.js"
    script.write_text("""
const fs = require('fs');
const path = require('path');

const dbPath = path.join(__dirname, '../data.db');
if (fs.existsSync(dbPath)) {
    if (!process.argv.includes('--force-reset')) {
        console.error('[VALDOZ SAFETY GATE BLOCKED]: An active database was found. Refusing to wipe without --force-reset flag.');
        process.exit(1);
    }
    // Automated timestamped backup prior to reset
    const backupDir = path.join(__dirname, '../backups/db');
    fs.mkdirSync(backupDir, { recursive: true });
    fs.copyFileSync(dbPath, path.join(backupDir, `backup-${Date.now()}.db`));
    fs.unlinkSync(dbPath);
}
""")

    res = scan_database_safety(temp_project)
    assert res.passed is True


def test_tests_directory_excluded_from_false_positives(temp_project: Path):
    test_dir = temp_project / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "test_models.py"
    test_file.write_text("""
import os
import pytest

def test_teardown():
    if os.path.exists('test.db'):
        os.remove('test.db')
""")

    res = scan_database_safety(temp_project)
    assert res.passed is True


def test_sync_generates_database_discipline_rule(temp_project: Path):
    outputs = sync_all_runtimes(temp_project, dry_run=False)
    db_rule = temp_project / ".agent" / "rules" / "04-database-discipline.md"
    assert db_rule.exists()
    content = db_rule.read_text(encoding="utf-8")
    assert "Zero-Destructive Discipline" in content
    assert "--force-reset" in content
    assert "backups/db/" in content

    # Check that AGENTS.md and GEMINI.md include Directive 13
    agents_md = (temp_project / "AGENTS.md").read_text(encoding="utf-8")
    gemini_md = (temp_project / "GEMINI.md").read_text(encoding="utf-8")
    core_md = (temp_project / ".agent" / "rules" / "00-core-discipline.md").read_text(encoding="utf-8")

    assert "13. Zero-Destructive Database Discipline & Data Protection" in agents_md
    assert "13. Zero-Destructive Database Discipline & Data Protection" in gemini_md
    assert "13. Zero-Destructive Database Discipline & Data Protection" in core_md
