"""Unit tests for ValdoZ Pack Importer and wshobson/agents marketplace bridge."""

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from valdoz.cli import app
from valdoz.importer import (
    import_pack,
    import_plugin_from_dir,
    sanitize_pack_id,
)
from valdoz.packs import PackError, resolve_active_packs
from valdoz.state import ValdozState, load_state, save_state

runner = CliRunner()


@pytest.fixture
def project_env(tmp_path: Path, monkeypatch):
    """Sets up an initialized ValdoZ project in a temporary directory."""
    monkeypatch.chdir(tmp_path)
    state = ValdozState(project_name="test-importer-proj", language="en")
    save_state(tmp_path, state)
    return tmp_path


def test_sanitize_pack_id():
    assert sanitize_pack_id("Claude Code Plugin") == "claude-code-plugin"
    assert sanitize_pack_id("my_cool_pack!@#") == "my-cool-pack"
    assert sanitize_pack_id("---") == "custom-pack"


def test_import_plugin_from_directory(project_env: Path):
    # Setup mock plugin directory
    plugin_src = project_env / "source_plugins" / "my-test-plugin"
    plugin_src.mkdir(parents=True)
    (plugin_src / "plugin.json").write_text(
        json.dumps({
            "name": "My Super Plugin",
            "description": "Provides specialized testing and deployment",
            "version": "1.2.0",
        }),
        encoding="utf-8",
    )

    # Add a skill
    skill_dir = plugin_src / "skills" / "deployer"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Deployer\nDeploy actions.\n", encoding="utf-8")

    # Add a rule
    rule_dir = plugin_src / "rules"
    rule_dir.mkdir(parents=True)
    (rule_dir / "deploy-safety.md").write_text("# Safety\nNever deploy on Fridays.\n", encoding="utf-8")

    manifest = import_plugin_from_dir(project_env, plugin_src)

    assert manifest.id == "my-test-plugin"
    assert manifest.name == "My Super Plugin"
    assert manifest.version == "1.2.0"

    # Verify manifest was written
    manifest_file = project_env / ".valdoz" / "packs" / "my-test-plugin" / "manifest.yaml"
    assert manifest_file.exists()

    # Verify skill was copied and wrapped with frontmatter
    skill_file = project_env / ".agent" / "skills" / "valdoz-my-test-plugin-deployer" / "SKILL.md"
    assert skill_file.exists()
    content = skill_file.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "valdoz-my-test-plugin-deployer" in content

    # Verify rule was copied
    rule_file = project_env / ".agent" / "rules" / "valdoz-my-test-plugin-deploy-safety.md"
    assert rule_file.exists()

    # Verify registered in state.json
    state = load_state(project_env)
    assert "my-test-plugin" in state.packs

    # Verify pack resolution includes the custom pack
    resolved = resolve_active_packs(state.packs, custom_packs_dir=project_env / ".valdoz" / "packs")
    resolved_ids = [p.id for p in resolved]
    assert "base" in resolved_ids
    assert "my-test-plugin" in resolved_ids


def test_import_wshobson_agents_syntax(project_env: Path):
    manifest = import_pack(project_env, source="wshobson/agents:code-reviewer")
    assert manifest.id == "wshobson-code-reviewer"

    # Verify manifest exists
    assert (project_env / ".valdoz" / "packs" / "wshobson-code-reviewer" / "manifest.yaml").exists()

    # Verify skill generated
    skill_path = project_env / ".agent" / "skills" / "valdoz-wshobson-code-reviewer-code-reviewer" / "SKILL.md"
    assert skill_path.exists()

    state = load_state(project_env)
    assert "wshobson-code-reviewer" in state.packs


def test_import_invalid_source_raises(project_env: Path):
    with pytest.raises(PackError, match="Unsupported pack source"):
        import_pack(project_env, source="non_existent_folder_xyz")


def test_cli_pack_import_and_list(project_env: Path):
    # Setup mock plugin folder
    plugin_dir = project_env / "external_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({"name": "External Tool", "version": "0.5.0"}))
    (plugin_dir / "skills").mkdir()
    (plugin_dir / "skills" / "SKILL.md").write_text("Instruction text")

    res_import = runner.invoke(app, ["pack", "import", str(plugin_dir), "--id", "ext-tool"])
    assert res_import.exit_code == 0
    assert "Successfully imported pack" in res_import.output
    assert "ext-tool" in res_import.output

    res_list = runner.invoke(app, ["pack", "list"])
    assert res_list.exit_code == 0
    assert "ext-tool" in res_list.output
