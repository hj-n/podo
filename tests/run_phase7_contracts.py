#!/usr/bin/env python3
"""Validate the migration approval contract and the additive Workspace 2 descriptor."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PODO = ROOT / "product/.podo"
CONTRACT = PODO / "contracts/workspace_migrations.json"


def main() -> None:
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert value["contract_version"] == 1
    assert value["approval"] == {
        "apply_requires_exact_plan_id": True,
        "normal_product_update_is_not_migration_approval": True,
        "rollback_requires_separate_plan": True,
    }
    descriptor = value["descriptor"]
    assert descriptor["file"] == "migration.json"
    assert descriptor["entrypoint"] == "migrate.py"
    assert set(descriptor["required_fields"]) == {
        "migration_contract_version",
        "from_workspace_version",
        "to_workspace_version",
        "description",
        "changes",
        "affected_paths",
        "entrypoint",
    }
    assert value["user_impact"]["allowed_roots"] == [
        "user_config.md",
        "events",
        "deltas",
        "state",
        "people",
        "research",
    ]
    assert value["transaction"]["product_roots"] == ["AGENTS.md", ".codex", ".podo"]
    assert value["transaction"]["workspace_version_applied_last"] is True
    assert value["backup"]["automatic_deletion_allowed"] is False

    version = (PODO / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    versions = json.loads((PODO / "contracts/versions.json").read_text(encoding="utf-8"))
    assert versions["compatible"][version] == [2]
    actual_migrations = [path for path in (PODO / "migrations").iterdir() if path.is_dir()]
    assert [path.name for path in actual_migrations] == ["1-to-2"]
    migration = json.loads((actual_migrations[0] / "migration.json").read_text(encoding="utf-8"))
    assert migration["affected_paths"] == ["people", "research"]
    assert migration["from_workspace_version"] == 1 and migration["to_workspace_version"] == 2
    print("PASS migration approval remains separate and Workspace 2 only adds People and Research roots")


if __name__ == "__main__":
    main()
