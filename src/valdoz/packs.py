"""ValdoZ Pack Engine.

Manages stack and project-type packs:
- Pack manifest schema (manifest.yaml)
- Inheritance and conflict detection (PackConflictError)
- Check severity rules (blocking vs warning)
- Precedence hierarchy (.valdozrc.json > pack manifests > base defaults)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml


class PackCheckDefinition(BaseModel):
    id: str
    description: str = ""
    severity: str = "blocking"  # blocking or warning
    replaces: Optional[str] = None
    disabled: bool = False


class PackManifest(BaseModel):
    id: str
    version: str = "1.0.0"
    name: str = ""
    description: str = ""
    extends: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    checks: List[PackCheckDefinition] = Field(default_factory=list)
    questions: List[Dict[str, Any]] = Field(default_factory=list)


class PackError(Exception):
    pass


class PackConflictError(PackError):
    pass


# ── Built-in Pack Definitions ───────────────────────────────────────────────
BUILTIN_PACKS: Dict[str, PackManifest] = {
    "base": PackManifest(
        id="base",
        version="1.0.0",
        name="Base Discipline Pack",
        description="Fundamental repository hygiene, secrets scanning, and lockfile verification.",
        checks=[
            PackCheckDefinition(id="secrets-scan", description="Scan for hardcoded API keys and secrets", severity="blocking"),
            PackCheckDefinition(id="lockfile-check", description="Verify lockfile presence and dependency pinning", severity="blocking"),
            PackCheckDefinition(id="placeholder-scan", description="Scan for TODO, TBD, and lorem placeholders", severity="blocking"),
        ],
    ),
    "web-app": PackManifest(
        id="web-app",
        version="1.0.0",
        name="Web Application Pack",
        description="Frontend and backend application with authentication and database.",
        extends=["base"],
        checks=[
            PackCheckDefinition(id="undeclared-imports", description="Verify all imports exist in package manifest", severity="blocking"),
            PackCheckDefinition(id="build-check", description="Run project build script if present", severity="blocking"),
            PackCheckDefinition(id="test-check", description="Run project test runner", severity="blocking"),
            PackCheckDefinition(id="liveness-probe", description="Verify deployment preview URLs if available", severity="warning"),
        ],
    ),
    "website": PackManifest(
        id="website",
        version="1.0.0",
        name="Content & Marketing Website Pack",
        description="Marketing and content websites, SEO basics, performance budget, accessibility.",
        extends=["base"],
        checks=[
            PackCheckDefinition(id="seo-meta-check", description="Check for HTML title and meta tags", severity="warning"),
            PackCheckDefinition(id="accessibility-check", description="Check image alt tags and basic a11y", severity="warning"),
            PackCheckDefinition(id="bundle-budget", description="Verify bundle size budget", severity="warning"),
        ],
    ),
    "api": PackManifest(
        id="api",
        version="1.0.0",
        name="Backend & REST/GraphQL API Pack",
        description="Contracts-first APIs, schema validation, rate limiting, and migrations.",
        extends=["base"],
        checks=[
            PackCheckDefinition(id="api-contract-check", description="Check for OpenAPI/Swagger contract spec", severity="blocking"),
            PackCheckDefinition(id="migration-check", description="Verify database migrations exist", severity="warning"),
            PackCheckDefinition(id="undeclared-imports", description="Verify backend imports exist in manifest", severity="blocking"),
        ],
    ),
}


def load_valdozrc(project_root: Path) -> Dict[str, Any]:
    """Loads project-level .valdozrc.json configuration if present."""
    rc_path = project_root / ".valdozrc.json"
    if not rc_path.exists():
        return {}
    try:
        text = re.sub(r"^\s*//.*$", "", rc_path.read_text(encoding="utf-8"), flags=re.MULTILINE)
        return json.loads(text)
    except Exception:
        return {}


def resolve_active_packs(
    declared_pack_ids: List[str],
    custom_packs_dir: Optional[Path] = None,
) -> List[PackManifest]:
    """Resolves and orders active pack manifests. Base pack always precedes declared packs."""
    resolved_order = ["base"]
    for pid in declared_pack_ids:
        if pid not in resolved_order:
            resolved_order.append(pid)

    packs: List[PackManifest] = []
    for pid in resolved_order:
        if pid in BUILTIN_PACKS:
            packs.append(BUILTIN_PACKS[pid])
        elif custom_packs_dir:
            custom_manifest = custom_packs_dir / pid / "manifest.yaml"
            if custom_manifest.exists():
                data = yaml.safe_load(custom_manifest.read_text(encoding="utf-8"))
                packs.append(PackManifest(**data))
            else:
                raise PackError(f"Pack manifest '{pid}' not found.")
        else:
            raise PackError(f"Unknown pack ID: '{pid}'")
    return packs


def merge_pack_checks(
    active_packs: List[PackManifest],
    valdozrc: Optional[Dict[str, Any]] = None,
) -> List[PackCheckDefinition]:
    """Merges checks across active packs applying conflict detection and .valdozrc.json overrides.

    Precedence:
    1. .valdozrc.json (highest: can demote blocking -> warning, or disable)
    2. Pack manifests in declared order (with replaces: <check-id>)
    3. Base pack defaults
    """
    merged: Dict[str, Tuple[PackCheckDefinition, str]] = {}  # check_id -> (check, pack_id)

    for pack in active_packs:
        # Check pack conflicts list
        for conflict_id in pack.conflicts:
            if any(p.id == conflict_id for p in active_packs):
                raise PackConflictError(f"Pack conflict: '{pack.id}' conflicts with active pack '{conflict_id}'.")

        for check in pack.checks:
            cid = check.id

            # If check explicitly replaces an existing check
            if check.replaces:
                if check.replaces in merged:
                    del merged[check.replaces]
                merged[cid] = (check, pack.id)
                continue

            # Check if this exact check ID was already defined by a previous pack
            if cid in merged:
                existing_check, existing_pack = merged[cid]
                # If it's the exact same pack or base inheritance with identical definition, allow
                if existing_pack == pack.id or existing_check.id == check.id:
                    # Same check ID across distinct packs without replaces is a conflict!
                    if existing_pack != pack.id and existing_pack != "base":
                        raise PackConflictError(
                            f"Pack conflict: Check '{cid}' declared in both '{existing_pack}' and '{pack.id}' "
                            f"without an explicit 'replaces: {cid}' override."
                        )
                    # Override/merge with newer pack definition
                    merged[cid] = (check, pack.id)
                else:
                    raise PackConflictError(
                        f"Pack check ID collision for '{cid}' between '{existing_pack}' and '{pack.id}'."
                    )
            else:
                merged[cid] = (check, pack.id)

    # Apply project-level .valdozrc.json overrides
    final_checks: List[PackCheckDefinition] = []
    scar_policy = (valdozrc or {}).get("scar_policy", {})
    disabled_list = set(scar_policy.get("disabled", []))
    warning_list = set(scar_policy.get("warning", []))

    for cid, (chk, _) in merged.items():
        # Check if disabled in .valdozrc.json
        if cid in disabled_list:
            chk.disabled = True
        # Check if demoted to warning in .valdozrc.json
        elif cid in warning_list and chk.severity == "blocking":
            chk.severity = "warning"

        if not chk.disabled:
            final_checks.append(chk)

    return final_checks
