#!/usr/bin/env python3
"""Exercise canonical migration CLI, update separation, and diagnosis."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
from run_phase6_product_update import package, synthetic_product  # noqa: E402
from run_phase7_migration import full_snapshot, release_environment, version, workspace_fixture  # noqa: E402
from run_phase7_planning import add_migration, release_tree  # noqa: E402


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def cli(workspace: Path, releases: Path, *args: str):
    env = os.environ.copy()
    env.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_DIR": str(releases)})
    return run([str(workspace / ".podo/bin/podo"), *args], cwd=workspace, env=env)


def json_output(result: subprocess.CompletedProcess[str]) -> dict:
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase7-cli-") as temporary:
        base = Path(temporary)
        old_product = synthetic_product(base, "0.9.0", [1])
        old_package, old_metadata = package(base, old_product, "1")
        target_product = synthetic_product(base, "1.0.0", [2])
        add_migration(target_product, 1, 2)
        releases, _target_metadata = release_tree(base, target_product, "2")

        separated = workspace_fixture(base, "update-separated", old_package, old_metadata)
        before = full_snapshot(separated)
        rejected = cli(separated, releases, "update", "--version", "1.0.0")
        if rejected.returncode == 0 or "E_WORKSPACE_INCOMPATIBLE" not in rejected.stderr:
            raise AssertionError(rejected.stdout + rejected.stderr)
        if full_snapshot(separated) != before or list((separated / ".podo-work/migration-plans").glob("*")):
            raise AssertionError("normal update created migration state")
        print("PASS normal product update does not plan or apply an incompatible migration")

        workspace = workspace_fixture(base, "cli-roundtrip", old_package, old_metadata)
        plan = json_output(cli(workspace, releases, "migrate", "--version", "1.0.0", "--json"))
        if plan["kind"] != "migration" or version(workspace) != ("0.9.0", "1"):
            raise AssertionError(str(plan))
        migrated = json_output(cli(workspace, releases, "migrate", "--apply", plan["plan_id"], "--json"))
        if migrated["outcome"] != "committed" or version(workspace) != ("1.0.0", "2"):
            raise AssertionError(str(migrated))
        rollback = json_output(
            cli(workspace, releases, "migrate", "rollback", "--backup", plan["backup_id"], "--json")
        )
        if rollback["kind"] != "rollback" or version(workspace) != ("1.0.0", "2"):
            raise AssertionError(str(rollback))
        restored = json_output(cli(workspace, releases, "migrate", "--apply", rollback["plan_id"], "--json"))
        if restored["outcome"] != "rollback-committed" or version(workspace) != ("0.9.0", "1"):
            raise AssertionError(str(restored))
        print("PASS canonical CLI requires separate exact migration and full rollback plans")

        diagnosed = workspace_fixture(base, "diagnosis", old_package, old_metadata)
        transaction = diagnosed / f".podo-work/migrations/migration-{'a' * 24}"
        transaction.mkdir(parents=True)
        (transaction / "journal.json").write_text(
            json.dumps(
                {
                    "migration_journal_version": 1,
                    "plan_id": transaction.name,
                    "backup_id": f"{transaction.name}-before-workspace-v2",
                    "state": "applying",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        doctor = cli(diagnosed, releases, "doctor", "--json")
        if doctor.returncode == 0:
            raise AssertionError(doctor.stdout)
        diagnosis = json.loads(doctor.stdout)
        codes = {finding["code"] for finding in diagnosis["findings"]}
        if "PODO_D320_MIGRATION_INCOMPLETE" not in codes:
            raise AssertionError(doctor.stdout)
        inbox = json_output(cli(diagnosed, releases, "inbox", "--json"))
        if inbox["migration_recovery_required"] != [transaction.name]:
            raise AssertionError(str(inbox))
        inbox_codes = {finding["code"] for finding in inbox["recovery_diagnosis"]["findings"]}
        if "PODO_D320_MIGRATION_INCOMPLETE" not in inbox_codes:
            raise AssertionError(str(inbox))
        blocked_update = cli(diagnosed, releases, "update", "--version", "1.0.0")
        if blocked_update.returncode == 0 or "E_MIGRATION_RECOVERY_REQUIRED" not in blocked_update.stderr:
            raise AssertionError(blocked_update.stdout + blocked_update.stderr)
        print("PASS doctor and task startup surface unfinished migration separately")


if __name__ == "__main__":
    main()
