"""Unit tests for ValdoZ pack system, inheritance, conflicts, and .valdozrc overrides."""

import pytest
from pathlib import Path
from valdoz.packs import (
    PackCheckDefinition,
    PackConflictError,
    PackManifest,
    merge_pack_checks,
    resolve_active_packs,
)


def test_resolve_builtin_packs():
    packs = resolve_active_packs(["web-app", "api"])
    pack_ids = [p.id for p in packs]
    # Base pack must always be first
    assert pack_ids[0] == "base"
    assert "web-app" in pack_ids
    assert "api" in pack_ids


def test_pack_conflict_detection():
    # Pack A defines check 'custom-check'
    pack_a = PackManifest(
        id="pack-a",
        checks=[PackCheckDefinition(id="custom-check", severity="blocking")],
    )
    # Pack B defines check 'custom-check' without replaces -> Conflict!
    pack_b = PackManifest(
        id="pack-b",
        checks=[PackCheckDefinition(id="custom-check", severity="blocking")],
    )

    with pytest.raises(PackConflictError, match="Pack conflict: Check 'custom-check' declared in both"):
        merge_pack_checks([pack_a, pack_b])


def test_pack_explicit_replaces_override():
    pack_base = PackManifest(
        id="base",
        checks=[PackCheckDefinition(id="liveness", severity="warning")],
    )
    pack_custom = PackManifest(
        id="custom",
        checks=[PackCheckDefinition(id="strict-liveness", replaces="liveness", severity="blocking")],
    )

    merged = merge_pack_checks([pack_base, pack_custom])
    check_ids = [c.id for c in merged]
    assert "liveness" not in check_ids
    assert "strict-liveness" in check_ids


def test_valdozrc_precedence_overrides():
    pack = PackManifest(
        id="web-app",
        checks=[
            PackCheckDefinition(id="check-one", severity="blocking"),
            PackCheckDefinition(id="check-two", severity="blocking"),
        ],
    )

    valdozrc = {
        "scar_policy": {
            "disabled": ["check-one"],
            "warning": ["check-two"],
        }
    }

    merged = merge_pack_checks([pack], valdozrc=valdozrc)
    # check-one is disabled
    assert not any(c.id == "check-one" for c in merged)
    # check-two demoted to warning
    check_two = next(c for c in merged if c.id == "check-two")
    assert check_two.severity == "warning"
