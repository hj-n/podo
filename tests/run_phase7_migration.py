#!/usr/bin/env python3
"""Exercise exact approval, backup, staged migration, and failure rollback."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "product/.podo/scripts"))

from migration_store import MigrationError, apply_migration, plan_migration  # noqa: E402
from run_phase6_product_update import apply, package, product_snapshot, synthetic_product  # noqa: E402
from run_phase7_planning import add_migration, release_tree  # noqa: E402


FAILURE_POINTS = (
    "after-backup",
    "after-prepared",
    "after-product-AGENTS.md",
    "after-product-.codex",
    "after-product-.podo",
    "after-user-1",
    "after-workspace-version",
    "before-final-validation",
    "after-final-validation",
)


@contextmanager
def release_environment(releases: Path, *, fail_at: str | None = None):
    previous = os.environ.copy()
    os.environ.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_DIR": str(releases)})
    if fail_at is not None:
        os.environ.update(
            {
                "PODO_TEST_MIGRATION_FAILURES": "1",
                "PODO_TEST_MIGRATION_FAIL_AT": fail_at,
            }
        )
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


def add_custom_migration(product: Path, script: str) -> None:
    add_migration(product, 1, 2)
    (product / ".podo/migrations/1-to-2/migrate.py").write_text(script, encoding="utf-8")


def workspace_fixture(base: Path, name: str, old_package: Path, old_metadata: dict) -> Path:
    workspace = base / name
    installed = apply(old_package, old_metadata, workspace)
    if installed.returncode:
        raise AssertionError(installed.stdout + installed.stderr)
    state = workspace / "state/project.md"
    state.write_text(
        "# Synthetic Project\n\nUpdated: 2026-07-15\n\n## Current Context\n\nMIGRATION_ORIGINAL\n",
        encoding="utf-8",
    )
    state.chmod(0o600)
    config = workspace / "user_config.md"
    config.chmod(0o640)
    return workspace


def file_value(path: Path) -> tuple[str, int]:
    return hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode)


def full_snapshot(workspace: Path) -> dict:
    return {
        "product": product_snapshot(workspace),
        "workspace_version": file_value(workspace / "WORKSPACE_VERSION"),
        "config": file_value(workspace / "user_config.md"),
        "state": file_value(workspace / "state/project.md"),
    }


def version(workspace: Path) -> tuple[str, str]:
    return (
        (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip(),
        (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip(),
    )


def expect(code: str, function, *args) -> None:
    try:
        function(*args)
    except MigrationError as error:
        if error.code != code:
            raise AssertionError(f"expected {code}, got {error.code}: {error}") from error
    else:
        raise AssertionError(f"expected {code}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase7-migration-") as temporary:
        base = Path(temporary)
        old_product = synthetic_product(base, "0.9.0", [1])
        old_package, old_metadata = package(base, old_product, "1")

        target_product = synthetic_product(base, "1.0.0", [2])
        add_migration(target_product, 1, 2)
        releases, _target_metadata = release_tree(base, target_product, "2")

        workspace = workspace_fixture(base, "success", old_package, old_metadata)
        before_config = file_value(workspace / "user_config.md")
        before_state = file_value(workspace / "state/project.md")
        with release_environment(releases):
            plan = plan_migration(workspace, "1.0.0")
            receipt = apply_migration(workspace, plan["plan_id"])
        if receipt["outcome"] != "committed" or version(workspace) != ("1.0.0", "2"):
            raise AssertionError(str(receipt))
        state = workspace / "state/project.md"
        if "Format: 2" not in state.read_text(encoding="utf-8") or stat.S_IMODE(state.stat().st_mode) != before_state[1]:
            raise AssertionError(state.read_text(encoding="utf-8"))
        if file_value(workspace / "user_config.md") != before_config:
            raise AssertionError("migration changed unlisted user config")
        backup = workspace / ".podo-backups" / plan["backup_id"]
        backup_manifest = json.loads((backup / "backup.json").read_text(encoding="utf-8"))
        if backup_manifest["state"] != "complete" or backup_manifest["migration_outcome"] != "committed":
            raise AssertionError(str(backup_manifest))
        if (backup / "product/.podo/VERSION").read_text(encoding="utf-8").strip() != "0.9.0":
            raise AssertionError("backup does not contain previous product")
        if "Format: 2" in (backup / "user-data/state/project.md").read_text(encoding="utf-8"):
            raise AssertionError("backup does not contain original user data")
        print("PASS exact plan approval applies staged Workspace 1→2 with retained full backup")

        stale = workspace_fixture(base, "stale", old_package, old_metadata)
        with release_environment(releases):
            stale_plan = plan_migration(stale, "1.0.0")
            (stale / "state/project.md").write_text(
                (stale / "state/project.md").read_text(encoding="utf-8") + "\nSTALE_CHANGE\n",
                encoding="utf-8",
            )
            expect("E_MIGRATION_PLAN_STALE", apply_migration, stale, stale_plan["plan_id"])
        if (stale / ".podo-backups" / stale_plan["backup_id"]).exists() or version(stale) != ("0.9.0", "1"):
            raise AssertionError("stale plan wrote backup or changed versions")
        print("PASS stale affected evidence is rejected before backup")

        failing_product = synthetic_product(base, "1.0.1", [2])
        add_custom_migration(
            failing_product,
            "import argparse\np=argparse.ArgumentParser();p.add_argument('--workspace');p.parse_args()\nraise SystemExit(23)\n",
        )
        release_tree(base, failing_product, "3")
        entrypoint = workspace_fixture(base, "entrypoint-failure", old_package, old_metadata)
        before = full_snapshot(entrypoint)
        with release_environment(releases):
            failed_plan = plan_migration(entrypoint, "1.0.1")
            expect("E_MIGRATION_ENTRYPOINT", apply_migration, entrypoint, failed_plan["plan_id"])
        if full_snapshot(entrypoint) != before:
            raise AssertionError("entrypoint failure changed product or user data")
        failed_backup = entrypoint / ".podo-backups" / failed_plan["backup_id"] / "backup.json"
        if json.loads(failed_backup.read_text(encoding="utf-8"))["state"] != "complete":
            raise AssertionError("entrypoint failure did not retain complete backup")
        print("PASS staged entrypoint failure preserves current Workspace and complete backup")

        undeclared_product = synthetic_product(base, "1.0.2", [2])
        add_custom_migration(
            undeclared_product,
            """import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args()
s=a.workspace/'state/project.md';s.write_text(s.read_text().replace('Updated:','Format: 2\\n\\nUpdated:',1))
c=a.workspace/'user_config.md';c.write_text(c.read_text()+'\\nUNDECLARED\\n')
""",
        )
        release_tree(base, undeclared_product, "4")
        undeclared = workspace_fixture(base, "undeclared", old_package, old_metadata)
        before = full_snapshot(undeclared)
        with release_environment(releases):
            undeclared_plan = plan_migration(undeclared, "1.0.2")
            expect("E_MIGRATION_UNDECLARED_CHANGE", apply_migration, undeclared, undeclared_plan["plan_id"])
        if full_snapshot(undeclared) != before:
            raise AssertionError("undeclared staged change reached current Workspace")
        print("PASS undeclared staged user change is rejected before apply")

        for index, point in enumerate(FAILURE_POINTS, start=1):
            failed = workspace_fixture(base, f"failure-{index}", old_package, old_metadata)
            original = full_snapshot(failed)
            with release_environment(releases):
                failure_plan = plan_migration(failed, "1.0.0")
            with release_environment(releases, fail_at=point):
                expect("E_INJECTED_MIGRATION_FAILURE", apply_migration, failed, failure_plan["plan_id"])
            if full_snapshot(failed) != original or version(failed) != ("0.9.0", "1"):
                raise AssertionError(f"{point} did not restore original product and user data")
            transactions = list((failed / ".podo-work/migrations").glob("*")) if (failed / ".podo-work/migrations").exists() else []
            if transactions:
                raise AssertionError(f"{point} left handled transaction: {transactions}")
            if not (failed / ".podo-backups" / failure_plan["backup_id"] / "backup.json").is_file():
                raise AssertionError(f"{point} did not preserve backup")
        print("PASS every handled migration apply boundary restores exact previous product and user data")


if __name__ == "__main__":
    main()
