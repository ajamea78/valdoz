"""ValdoZ v2.1.1 fixture tests: one failing and one passing case per enforced SCAR.

Run:
  ~/.valdoz/venv/bin/pip install pytest
  ~/.valdoz/venv/bin/python -m pytest test_valdoz.py -v

Set VALDOZ_MAIN to test a different main.py.
"""
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

MAIN = Path(os.environ.get("VALDOZ_MAIN", Path.home() / ".valdoz/cli/main.py"))
if not MAIN.exists():
    pytest.skip(f"Legacy v2 CLI not found at {MAIN}", allow_module_level=True)
spec = importlib.util.spec_from_file_location("valdoz_main", MAIN)
vz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vz)
runner = CliRunner()


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    """Run every test in an empty repo dir with an isolated ~/.valdoz."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    monkeypatch.setattr(vz, "HOME", tmp_path / "home")
    return repo


def write(path: str, text: str = "") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def scars_hit(cfg=None) -> set:
    report = vz.run_all_scars(cfg, network=False)
    return {v.scar for v in report.violations}


def cfg_with_url(url: str):
    return vz.ValdozConfig(branches={"main": vz.BranchConfig(branch_name="main", permanent_url=url)})


# ── Config ──────────────────────────────────────────────────────────────────
def test_config_keeps_urls_and_strips_full_line_comments():
    write(".valdozrc.json", '// comment\n{"branches": {"main": {"branch_name": "main", '
                            '"permanent_url": "https://x.app"}}}\n')
    cfg, err = vz.load_config()
    assert err is None
    assert cfg.branches["main"].permanent_url == "https://x.app"


def test_bad_config_fails_strict_audit():
    write(".valdozrc.json", "{ not json")
    result = runner.invoke(vz.app, ["audit", "--strict", "--no-network"])
    assert result.exit_code == 1
    assert "CONFIG" in result.output


def test_missing_config_is_not_an_error():
    assert vz.load_config() == (None, None)


# ── SCAR-001 ────────────────────────────────────────────────────────────────
def test_001_fails_on_static_preview():
    write("public/design-preview.html", "<html/>")
    assert "SCAR-001" in scars_hit()


def test_001_passes_when_absent():
    assert "SCAR-001" not in scars_hit()


# ── SCAR-002 / 003 ──────────────────────────────────────────────────────────
PILL = '<div className="fixed bottom-5 right-5 z-[9999]" />'


def test_003_fails_without_pill():
    write("src/DirectionA.tsx", "\n".join(["const x = 1;"] * 100))
    assert "SCAR-003" in scars_hit()


def test_003_passes_with_tokens_in_any_order_and_shared_file():
    write("src/DirectionA.tsx", "\n".join(["const x = 1;"] * 100))
    write("src/Switcher.tsx", '<div className="z-[9999] right-5 fixed rounded bottom-5" />')
    assert "SCAR-003" not in scars_hit()


def test_002_flags_tiny_direction_files():
    write("src/DirectionA.tsx", PILL)
    assert "SCAR-002" in scars_hit()


# ── SCAR-004 ────────────────────────────────────────────────────────────────
def test_004_fails_on_framework_mismatch():
    write("package.json", json.dumps({"dependencies": {"next": "15.0.0"}}))
    write("vercel.json", json.dumps({"framework": "vite"}))
    assert "SCAR-004" in scars_hit()


def test_004_passes_on_match():
    write("package.json", json.dumps({"dependencies": {"next": "15.0.0"}}))
    write("vercel.json", json.dumps({"framework": "nextjs"}))
    assert "SCAR-004" not in scars_hit()


# ── SCAR-005 ────────────────────────────────────────────────────────────────
def test_005_fails_when_app_dir_uncovered():
    write("tailwind.config.js", "module.exports = { content: ['./src/**/*.{ts,tsx}'] }")
    write("src/a.tsx", "x")
    write("app/page.tsx", "x")
    assert "SCAR-005" in scars_hit()


def test_005_passes_when_app_dir_covered():
    write("tailwind.config.js", "module.exports = { content: ['./app/**/*.{ts,tsx}'] }")
    write("app/page.tsx", "x")
    assert "SCAR-005" not in scars_hit()


def test_005_fails_on_tiny_compiled_css():
    write(".next/static/css/app.css", "a{}")
    assert "SCAR-005" in scars_hit()


# ── SCAR-006 ────────────────────────────────────────────────────────────────
def test_006_fails_without_any_suspense():
    write("src/Search.tsx", "useSearchParams()")
    assert "SCAR-006" in scars_hit()


def test_006_passes_when_parent_page_provides_suspense():
    write("src/Search.tsx", "useSearchParams()")
    write("src/page.tsx", "import Search from './Search'; <Suspense><Search /></Suspense>")
    assert "SCAR-006" not in scars_hit()


def test_006_is_warning_only_by_default():
    write("src/Search.tsx", "useSearchParams()")
    report = vz.run_all_scars(None, network=False)
    errors, warnings = vz.apply_policy(report, vz.ScarPolicy())
    assert not errors and warnings


# ── SCAR-007 ────────────────────────────────────────────────────────────────
def test_007_live_process_is_alive():
    vz.ProcessManager.track("dev", os.getpid())
    assert vz.ProcessManager.is_alive("dev")
    assert "SCAR-007" not in scars_hit()


def test_007_dead_process_is_flagged():
    p = subprocess.Popen(["true"])
    p.wait()
    vz.ProcessManager.track("dev", p.pid)
    assert not vz.ProcessManager.is_alive("dev")
    assert "SCAR-007" in scars_hit()


def test_007_permission_error_means_alive(monkeypatch):
    vz.ProcessManager.track("dev", 4242)
    monkeypatch.setattr(vz.os, "kill", lambda *a: (_ for _ in ()).throw(PermissionError()))
    assert vz.ProcessManager.is_alive("dev")


def test_007_records_are_per_project(tmp_path, monkeypatch):
    vz.ProcessManager.track("dev", os.getpid())
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    assert not vz.ProcessManager.is_alive("dev")


# ── SCAR-011 ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("url,expected", [
    ("https://myapp-a1b2c3d4e-team.vercel.app", True),    # real preview hash
    ("https://myapp-git-main-team.vercel.app", False),    # permanent branch URL
    ("https://my-directory-site.vercel.app", False),      # ordinary words
    ("https://community-dashboard.example.com", False),   # not a vercel host
])
def test_011_preview_detection(url, expected):
    assert ("SCAR-011" in scars_hit(cfg_with_url(url))) is expected


# ── Policy / audit output ───────────────────────────────────────────────────
def test_disabled_scar_is_reported_as_skipped():
    write("public/design-preview.html", "<html/>")
    report = vz.run_all_scars(None, network=False)
    errors, _ = vz.apply_policy(report, vz.ScarPolicy(disabled=["SCAR-001"]))
    assert not errors
    assert report.skipped["SCAR-001"] == "disabled by policy"


def test_audit_states_what_ran_and_what_did_not():
    out = runner.invoke(vz.app, ["audit", "--no-network"]).output
    assert "Ran:" in out and "Not covered by audit" in out


# ── init hook ───────────────────────────────────────────────────────────────
def test_init_preserves_existing_hook_and_is_idempotent():
    subprocess.run(["git", "init", "-q"], check=True)
    hook = Path(".git/hooks/pre-commit")
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\necho husky\n")
    hook.chmod(0o755)
    assert runner.invoke(vz.app, ["init"]).exit_code == 0
    assert Path(".git/hooks/pre-commit.pre-valdoz").read_text().count("husky") == 1
    assert vz.HOOK_MARKER in hook.read_text()
    assert runner.invoke(vz.app, ["init"]).exit_code == 0  # second run must not clobber the backup
    assert "husky" in Path(".git/hooks/pre-commit.pre-valdoz").read_text()


def test_sync_runtimes_block_updates_in_place():
    write(str(vz.HOME / "SCARS.md"), "# SCARS v1\n1. rule one\n")
    write("CLAUDE.md", "# mine\n")

    r1 = runner.invoke(vz.app, ["sync-runtimes", "-t", "claude"])
    assert r1.exit_code == 0, r1.output
    first = Path("CLAUDE.md").read_text()
    assert first.startswith("# mine") and "VALDOZ:BEGIN" in first
    assert "rule one" in first

    # Same source: no change, no duplicate block.
    runner.invoke(vz.app, ["sync-runtimes", "-t", "claude"])
    assert Path("CLAUDE.md").read_text() == first

    # Changed source: block is replaced in place, user content kept.
    write(str(vz.HOME / "SCARS.md"), "# SCARS v2\n1. rule two\n")
    runner.invoke(vz.app, ["sync-runtimes", "-t", "claude"])
    updated = Path("CLAUDE.md").read_text()
    assert "rule two" in updated and "rule one" not in updated
    assert updated.count("VALDOZ:BEGIN") == 1
    assert updated.startswith("# mine")


    # ── SCAR-009 (network patched out) ──────────────────────────────────────────
def hits_009(monkeypatch, result):
    monkeypatch.setattr(vz, "probe", lambda url, timeout: result)
    report = vz.run_all_scars(cfg_with_url("https://x.app"), network=True)
    return report, {v.scar for v in report.violations}


def test_009_passes_on_200(monkeypatch):
    report, hit = hits_009(monkeypatch, (200, None))
    assert "SCAR-009" not in hit and "SCAR-009" in report.ran


def test_009_fails_on_5xx(monkeypatch):
    assert "SCAR-009" in hits_009(monkeypatch, (503, None))[1]


def test_009_fails_on_network_error(monkeypatch):
    assert "SCAR-009" in hits_009(monkeypatch, (None, "timed out"))[1]


def test_009_protected_preview_is_a_note_not_a_failure(monkeypatch):
    report, hit = hits_009(monkeypatch, (401, None))
    assert "SCAR-009" not in hit
    assert any("gated" in n for n in report.notes)


def test_009_skipped_with_no_network():
    report = vz.run_all_scars(cfg_with_url("https://x.app"), network=False)
    assert report.skipped["SCAR-009"] == "--no-network"


def test_probe_falls_back_to_get_when_head_is_405(monkeypatch):
    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout):
        if req.get_method() == "HEAD":
            raise vz.urllib.error.HTTPError(req.full_url, 405, "no HEAD", {}, None)
        return Resp()

    monkeypatch.setattr(vz.urllib.request, "urlopen", fake_urlopen)
    assert vz.probe("https://x.app", 1) == (200, None)