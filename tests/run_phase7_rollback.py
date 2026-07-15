#!/usr/bin/env python3
"""Exercise ordered multi-hop migration and separately approved full rollback."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "product/.podo/scripts"))

from migration_store import MigrationError, apply_migration, apply_rollback, plan_migration, plan_rollback  # noqa: E402
from run_phase6_product_update import package, synthetic_product  # noqa: E402
from run_phase7_migration import full_snapshot, release_environment, version, workspace_fixture  # noqa: E402
from run_phase7_planning import add_migration, release_tree  # noqa: E402


ROLLBACK_FAILURE_POINTS = (
    "after-rollback-backup",
    "after-rollback-prepared",
    "after-rollback-product-AGENTS.md",
    "after-rollback-product-.codex",
    "after-rollback-product-.podo",
    "after-rollback-user-1",
    "after-rollback-workspace-version",
    "before-rollback-final-validation",
    "after-rollback-final-validation",
)


def expect(code: str, function, *args) -> None:
    try:
        function(*args)
    except MigrationError as error:
        if error.code != code:
            raise AssertionError(f"expected {code}, got {error.code}: {error}") from error
    else:
        raise AssertionError(f"expected {code}")


def migrate(workspace: Path, releases: Path, target: str = "1.0.0") -> dict:
    with release_environment(releases):
        plan = plan_migration(workspace, target)
        apply_migration(workspace, plan["plan_id"])
    return plan


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase7-rollback-") as temporary:
        base = Path(temporary)
        old_product = synthetic_product(base, "0.9.0", [1])
        old_package, old_metadata = package(base, old_product, "1")

        target_product = synthetic_product(base, "1.0.0", [2])
        add_migration(target_product, 1, 2)
        releases, _metadata = release_tree(base, target_product, "2")

        multihop_product = synthetic_product(base, "2.0.0", [3])
        add_migration(multihop_product, 1, 2)
        add_migration(multihop_product, 2, 3)
        second = multihop_product / ".podo/migrations/2-to-3/migrate.py"
        second.write_text(
            """import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args()
s=a.workspace/'state/project.md';text=s.read_text()
if 'Format: 2' not in text: raise SystemExit('missing Workspace 2 marker')
s.write_text(text.replace('Format: 2','Format: 3',1))
""",
            encoding="utf-8",
        )
        release_tree(base, multihop_product, "3")
        multihop = workspace_fixture(base, "multihop", old_package, old_metadata)
        with release_environment(releases):
            multihop_plan = plan_migration(multihop, "2.0.0")
            if [step["id"] for step in multihop_plan["chain"]] != ["1-to-2", "2-to-3"]:
                raise AssertionError(str(multihop_plan["chain"]))
            apply_migration(multihop, multihop_plan["plan_id"])
        if version(multihop) != ("2.0.0", "3") or "Format: 3" not in (multihop / "state/project.md").read_text():
            raise AssertionError("ordered multi-hop migration did not reach Workspace 3")
        print("PASS unique Workspace 1→2→3 chain executes in order")

        workspace = workspace_fixture(base, "rollback-success", old_package, old_metadata)
        original = full_snapshot(workspace)
        migration_plan = migrate(workspace, releases)
        state = workspace / "state/project.md"
        state.write_text(state.read_text(encoding="utf-8") + "\nUSER_AFTER_MIGRATION\n", encoding="utf-8")
        with release_environment(releases):
            rollback_plan = plan_rollback(workspace, migration_plan["backup_id"])
        if rollback_plan["changes_since_migration"] != ["state/project.md"]:
            raise AssertionError(str(rollback_plan))
        before_rollback = full_snapshot(workspace)
        with release_environment(releases):
            receipt = apply_rollback(workspace, rollback_plan["plan_id"])
        if receipt["outcome"] != "rollback-committed" or version(workspace) != ("0.9.0", "1"):
            raise AssertionError(str(receipt))
        if full_snapshot(workspace) != original:
            raise AssertionError("full rollback did not restore exact pre-migration snapshot")
        source = workspace / ".podo-backups" / migration_plan["backup_id"]
        safety = workspace / ".podo-backups" / rollback_plan["backup_id"]
        if not source.is_dir() or not safety.is_dir():
            raise AssertionError("full rollback removed source or safety backup")
        safety_state = (safety / "user-data/state/project.md").read_text(encoding="utf-8")
        if "Format: 2" not in safety_state or "USER_AFTER_MIGRATION" not in safety_state:
            raise AssertionError("safety backup did not preserve rollback-start state")
        if before_rollback["state"] == original["state"]:
            raise AssertionError("rollback fixture did not contain post-migration user change")
        print("PASS separately planned full rollback restores old product/data and retains both backups")

        stale = workspace_fixture(base, "rollback-stale", old_package, old_metadata)
        stale_migration = migrate(stale, releases)
        with release_environment(releases):
            stale_plan = plan_rollback(stale, stale_migration["backup_id"])
        (stale / "state/project.md").write_text(
            (stale / "state/project.md").read_text(encoding="utf-8") + "\nAFTER_ROLLBACK_PLAN\n",
            encoding="utf-8",
        )
        with release_environment(releases):
            expect("E_ROLLBACK_PLAN_STALE", apply_rollback, stale, stale_plan["plan_id"])
        if (stale / ".podo-backups" / stale_plan["backup_id"]).exists() or version(stale) != ("1.0.0", "2"):
            raise AssertionError("stale rollback plan wrote safety backup or changed versions")
        print("PASS rollback plan becomes stale before safety backup")

        for index, point in enumerate(ROLLBACK_FAILURE_POINTS, start=1):
            failed = workspace_fixture(base, f"rollback-failure-{index}", old_package, old_metadata)
            failed_migration = migrate(failed, releases)
            with release_environment(releases):
                failed_plan = plan_rollback(failed, failed_migration["backup_id"])
            current = full_snapshot(failed)
            previous = os.environ.copy()
            os.environ.update(
                {
                    "PODO_TEST_RELEASES": "1",
                    "PODO_RELEASE_DIR": str(releases),
                    "PODO_TEST_MIGRATION_FAILURES": "1",
                    "PODO_TEST_MIGRATION_FAIL_AT": point,
                }
            )
            try:
                expect("E_INJECTED_MIGRATION_FAILURE", apply_rollback, failed, failed_plan["plan_id"])
            finally:
                os.environ.clear()
                os.environ.update(previous)
            if full_snapshot(failed) != current or version(failed) != ("1.0.0", "2"):
                raise AssertionError(f"{point} did not restore rollback-start product and user data")
            if not (failed / ".podo-backups" / failed_plan["backup_id"] / "backup.json").is_file():
                raise AssertionError(f"{point} did not retain rollback safety backup")
            transactions = list((failed / ".podo-work/migrations").glob("*")) if (failed / ".podo-work/migrations").exists() else []
            if transactions:
                raise AssertionError(f"{point} left handled rollback transaction: {transactions}")
        print("PASS every handled full rollback boundary restores exact rollback-start state")


if __name__ == "__main__":
    main()
