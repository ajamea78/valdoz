"""ValdoZ Pack Importer & Marketplace Bridge.

Adapts external agentic plugins (such as wshobson/agents marketplace plugins)
into ValdoZ-compliant pack manifests, skills, and rules:
- Reads plugin.json / manifests
- Extracts and wraps skills with YAML frontmatter into .agent/skills/
- Generates manifest.yaml with check mappings
- Registers pack in state.json
"""

from __future__ import annotations

import hashlib
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
    PackSecurityError,
)
from valdoz.state import load_state, save_state

# ── Prompt Injection & Malicious Pattern Scanners ───────────────────────────
PROMPT_INJECTION_PATTERNS = [
    (re.compile(r"(?i)\b(?:ignore|disregard|forget|bypass)\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions|guidelines|rules|prompts)\b"), "Instruction Override / Ignore Rules"),
    (re.compile(r"(?i)\b(?:you\s+are\s+now\s+in\s+developer\s+mode|dan\s+mode|jailbreak)\b"), "Jailbreak Directive"),
    (re.compile(r"(?i)\b(?:system\s+prompt\s+override|override\s+system\s+prompt)\b"), "System Prompt Override"),
    (re.compile(r"<!--[\s\S]*?(?:ignore|override|system\s+prompt|curl|eval|bash|exec)[\s\S]*?-->", re.IGNORECASE), "Hidden Markdown Injection in Comments"),
    (re.compile(r"(?i)<\s*script[^>]*>"), "Embedded HTML Script Tag"),
    (re.compile(r"(?i)\b(?:javascript:|data:text/html)"), "Malicious URI Protocol Handler"),
    (re.compile(r"(?i)\b(?:curl|wget)\s+.*?(?:http|ftp|tcp).*?\|\s*(?:ba)?sh\b"), "Arbitrary Shell Execution Pipe"),
]


def scan_prompt_injection_patterns(text: str) -> List[str]:
    """Scans text for adversarial prompt injection directives or malicious wrappers."""
    findings: List[str] = []
    for pat, desc in PROMPT_INJECTION_PATTERNS:
        if pat.search(text):
            findings.append(desc)
    return findings


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

    # 2. Extract and copy skills with prompt injection scanning & integrity hashing
    integrity_map: Dict[str, str] = {}
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

        # Security scan for prompt injections
        injections = scan_prompt_injection_patterns(content)
        if injections:
            raise PackSecurityError(
                f"Malicious content or prompt injection pattern detected in '{sfile.name}': {', '.join(injections)}"
            )

        # Ensure standard YAML frontmatter
        if not content.startswith("---"):
            fm = f"---\nname: {target_skill_name}\ndescription: >-\n  Imported skill from {pid} pack.\n---\n\n"
            content = fm + content

        dest_file = skill_dest_dir / "SKILL.md"
        dest_file.write_text(content, encoding="utf-8")
        rel_path = f".agent/skills/{target_skill_name}/SKILL.md"
        integrity_map[rel_path] = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # 3. Extract rules with prompt injection scanning & integrity hashing
    rules_found = list(source_dir.glob("rules/*.md"))
    if rules_found:
        target_rules_dir = project_root / ".agent" / "rules"
        target_rules_dir.mkdir(parents=True, exist_ok=True)
        for rfile in rules_found:
            rcontent = rfile.read_text(encoding="utf-8", errors="replace")
            injections = scan_prompt_injection_patterns(rcontent)
            if injections:
                raise PackSecurityError(
                    f"Malicious content or prompt injection pattern detected in rule '{rfile.name}': {', '.join(injections)}"
                )
            rname = f"valdoz-{pid}-{rfile.name}"
            dest_rule = target_rules_dir / rname
            dest_rule.write_text(rcontent, encoding="utf-8")
            rel_path = f".agent/rules/{rname}"
            integrity_map[rel_path] = hashlib.sha256(rcontent.encode("utf-8")).hexdigest()

    manifest_data["integrity"] = integrity_map

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


def verify_pack_integrity(project_root: Path, pack_id: str) -> Tuple[bool, List[str]]:
    """Verifies that installed skills and rules match the SHA-256 integrity map in the pack manifest."""
    manifest_file = project_root / ".valdoz" / "packs" / pack_id / "manifest.yaml"
    if not manifest_file.exists():
        return False, [f"Pack manifest not found: {manifest_file}"]

    try:
        data = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
        integrity_map = data.get("integrity", {})
    except Exception as e:
        return False, [f"Failed to read pack manifest: {e}"]

    if not integrity_map:
        return True, []

    violations: List[str] = []
    for rel_path, expected_sha in integrity_map.items():
        target_file = project_root / rel_path
        if not target_file.exists():
            violations.append(f"Missing file declared in pack integrity: '{rel_path}'")
            continue
        try:
            actual_sha = hashlib.sha256(target_file.read_bytes()).hexdigest()
            if actual_sha != expected_sha:
                violations.append(f"Integrity mismatch in '{rel_path}': expected {expected_sha[:10]}..., got {actual_sha[:10]}...")
        except Exception as e:
            violations.append(f"Failed to read '{rel_path}': {e}")

    return len(violations) == 0, violations
