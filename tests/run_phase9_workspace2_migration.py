#!/usr/bin/env python3
"""Verify the real additive Workspace 1 to 2 migration and rollback safety."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "product/.podo/scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from migration_store import apply_migration, plan_migration  # noqa: E402
from run_phase6_product_update import apply, package, synthetic_product  # noqa: E402
from run_phase7_planning import release_tree  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-workspace2-") as temporary:
        base = Path(temporary)
        old_product = synthetic_product(base, "0.6.0", [1])
        old_package, old_metadata = package(base, old_product, "6")
        target_product = synthetic_product(base, "0.7.0", [2])
        releases, _ = release_tree(base, target_product, "7")

        workspace = base / "workspace"
        installed = apply(old_package, old_metadata, workspace)
        if installed.returncode:
            raise AssertionError(installed.stdout + installed.stderr)
        shutil.rmtree(workspace / "people")
        shutil.rmtree(workspace / "research")
        state = workspace / "state/preserved.md"
        state.write_text("# Preserved\n\nUpdated: 2026-07-20\n\nSYNTHETIC_SENTINEL\n", encoding="utf-8")
        state_before = state.read_bytes()

        before = os.environ.copy()
        os.environ.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_DIR": str(releases)})
        try:
            plan = plan_migration(workspace, "0.7.0")
            if plan["affected_paths"] != ["people", "research"]:
                raise AssertionError(str(plan))
            if (workspace / "people").exists() or (workspace / "research").exists():
                raise AssertionError("planning changed user data")
            receipt = apply_migration(workspace, plan["plan_id"])
        finally:
            os.environ.clear()
            os.environ.update(before)
        if receipt["outcome"] != "committed":
            raise AssertionError(str(receipt))
        for relative in ("people", "research/papers", "research/topics", "research/projects"):
            if not (workspace / relative).is_dir():
                raise AssertionError(f"missing migrated directory: {relative}")
        if state.read_bytes() != state_before:
            raise AssertionError("additive migration changed existing State")
        if (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip() != "2":
            raise AssertionError("Workspace version was not applied last")
        backup = workspace / ".podo-backups" / plan["backup_id"]
        if not (backup / "backup.json").is_file():
            raise AssertionError("migration backup is missing")
        print("PASS real Workspace 1→2 plan, backup and additive People/Research migration")


if __name__ == "__main__":
    main()
