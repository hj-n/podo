#!/usr/bin/env python3
"""Validate the Phase 7 migration contract without changing Workspace format 1."""

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
    assert value["user_impact"]["allowed_roots"] == ["user_config.md", "events", "deltas", "state"]
    assert value["transaction"]["product_roots"] == ["AGENTS.md", ".codex", ".podo"]
    assert value["transaction"]["workspace_version_applied_last"] is True
    assert value["backup"]["automatic_deletion_allowed"] is False

    version = (PODO / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    versions = json.loads((PODO / "contracts/versions.json").read_text(encoding="utf-8"))
    assert versions["compatible"][version] == [1]
    actual_migrations = [path for path in (PODO / "migrations").iterdir() if path.is_dir()]
    assert actual_migrations == [], "development product must not introduce a real Workspace 2 format"
    print("PASS Phase 7 contracts keep migration approval separate and current Workspace format at 1")


if __name__ == "__main__":
    main()
