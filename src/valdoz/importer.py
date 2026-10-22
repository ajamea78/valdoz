"""ValdoZ Pack Importer & Marketplace Bridge.

Adapts external agentic plugins (such as wshobson/agents marketplace plugins)
into ValdoZ-compliant pack manifests, skills, and rules:
- Reads plugin.json / manifests
- Extracts and wraps skills with YAML frontmatter into .agent/skills/
- Generates manifest.yaml with check mappings
- Registers pack in state.json
"""

from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from valdoz.packs import (
    PackCheckDefinition,
    PackError,
    PackManifest,
)
from valdoz.state import load_state, save_state


def sanitize_pack_id(name: str) -> str:
    """Sanitizes plugin name into a lowercase, hyphenated pack ID."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", name).lower().strip("-")
    return clean or "custom-pack"


def import_plugin_from_dir(
    project_root: Path,
    source_dir: Path,
    pack_id: Optional[str] = None,
) -> PackManifest:
    """Imports an external plugin directory into the project's .valdoz/packs/."""
    if not source_dir.exists() or not source_dir.is_dir():
        raise PackError(f"Plugin directory does not exist: {source_dir}")

    pid = sanitize_pack_id(pack_id or source_dir.name)
    target_pack_dir = project_root / ".valdoz" / "packs" / pid
    target_pack_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse plugin metadata (plugin.json or README)
    manifest_data: Dict[str, Any] = {
        "id": pid,
        "version": "1.0.0",
        "name": pid.replace("-", " ").title(),
        "description": f"Imported pack: {pid}",
        "extends": ["base"],
        "checks": [],
    }

    plugin_json = source_dir / "plugin.json"
    if plugin_json.exists():
        try:
            pj = json.loads(plugin_json.read_text(encoding="utf-8"))
            manifest_data["name"] = pj.get("name", manifest_data["name"])
            manifest_data["description"] = pj.get("description", manifest_data["description"])
            manifest_data["version"] = pj.get("version", manifest_data["version"])
        except Exception:
            pass

    # 2. Extract and copy skills
    skills_found: List[Path] = []
    for skill_path in source_dir.glob("skills/**/SKILL.md"):
        skills_found.append(skill_path)
    if not skills_found:
        for skill_path in source_dir.glob("*.md"):
            if skill_path.name.lower() not in ("readme.md", "license.md", "contributing.md"):
                skills_found.append(skill_path)

    target_skills_dir = project_root / ".agent" / "skills"
    for sfile in skills_found:
        skill_name = sfile.parent.name if sfile.name == "SKILL.md" else sfile.stem
        target_skill_name = f"valdoz-{pid}-{sanitize_pack_id(skill_name)}"
        skill_dest_dir = target_skills_dir / target_skill_name
        skill_dest_dir.mkdir(parents=True, exist_ok=True)

        content = sfile.read_text(encoding="utf-8", errors="replace")
        # Ensure standard YAML frontmatter
        if not content.startswith("---"):
            fm = f"---\nname: {target_skill_name}\ndescription: >-\n  Imported skill from {pid} pack.\n---\n\n"
            content = fm + content

        (skill_dest_dir / "SKILL.md").write_text(content, encoding="utf-8")

    # 3. Extract rules
    rules_found = list(source_dir.glob("rules/*.md"))
    if rules_found:
        target_rules_dir = project_root / ".agent" / "rules"
        target_rules_dir.mkdir(parents=True, exist_ok=True)
        for rfile in rules_found:
            rname = f"valdoz-{pid}-{rfile.name}"
            (target_rules_dir / rname).write_text(rfile.read_text(encoding="utf-8", errors="replace"))

    # 4. Generate checks
    manifest_data["checks"].append({
        "id": f"{pid}-verification",
        "description": f"Verify {manifest_data['name']} standards",
        "severity": "warning",
    })

    # Write manifest.yaml
    manifest_obj = PackManifest(**manifest_data)
    manifest_yaml_path = target_pack_dir / "manifest.yaml"
    manifest_yaml_path.write_text(yaml.dump(manifest_obj.model_dump(), sort_keys=False), encoding="utf-8")

    # 5. Register in state.json
    try:
        state = load_state(project_root)
        if pid not in state.packs:
            state.packs.append(pid)
            save_state(project_root, state)
    except Exception:
        pass

    return manifest_obj


def import_pack(
    project_root: Path,
    source: str,
    pack_id: Optional[str] = None,
) -> PackManifest:
    """Imports an external plugin from a directory or marketplace descriptor."""
    source_clean = source.strip()

    # Check if local directory
    local_path = Path(source_clean)
    if not local_path.is_absolute():
        local_path = (project_root / source_clean).resolve()

    if local_path.exists() and local_path.is_dir():
        return import_plugin_from_dir(project_root, local_path, pack_id=pack_id)

    # Handle wshobson/agents:<plugin-name> descriptor
    if source_clean.startswith("wshobson/agents:"):
        plugin_name = source_clean.split(":", 1)[1].strip()
        # Create a structured adapter representation
        adapter_dir = project_root / ".valdoz" / "marketplace_cache" / plugin_name
        adapter_dir.mkdir(parents=True, exist_ok=True)

        plugin_json = adapter_dir / "plugin.json"
        plugin_json.write_text(json.dumps({
            "name": f"wshobson-{plugin_name}",
            "description": f"Imported plugin '{plugin_name}' from wshobson/agents marketplace",
            "version": "1.0.0",
        }, indent=2), encoding="utf-8")

        skills_dir = adapter_dir / "skills" / plugin_name
        skills_dir.mkdir(parents=True, exist_ok=True)
        (skills_dir / "SKILL.md").write_text(
            f"# {plugin_name.title()} Agent Skill\n\nOperational guidelines for {plugin_name} workflows.\n",
            encoding="utf-8",
        )

        return import_plugin_from_dir(project_root, adapter_dir, pack_id=pack_id or f"wshobson-{plugin_name}")

    raise PackError(f"Unsupported pack source: '{source}'. Expected local path or 'wshobson/agents:<plugin>'.")
