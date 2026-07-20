#!/usr/bin/env python3
"""Verify the real additive Workspace 1 to 2 migration and rollback safety."""

from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "product/.podo/scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from run_phase6_product_update import apply, package, synthetic_product  # noqa: E402
from run_phase7_planning import release_tree  # noqa: E402


def cli(workspace: Path, releases: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_DIR": str(releases)})
    return subprocess.run(
        [str(workspace / ".podo/bin/podo"), *args],
        cwd=workspace,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-workspace2-") as temporary:
        base = Path(temporary)
        old_product = synthetic_product(base, "0.6.0", [1])
        legacy_store = old_product / ".podo/scripts/migration_store.py"
        legacy_text = legacy_store.read_text(encoding="utf-8")
        legacy_text = legacy_text.replace(
            '{"user_config.md", "events", "deltas", "state", "people", "research"}',
            '{"user_config.md", "events", "deltas", "state"}',
        ).replace(
            '("user_config.md", "events", "deltas", "state", "people", "research")',
            '("user_config.md", "events", "deltas", "state")',
        )
        legacy_store.write_text(legacy_text, encoding="utf-8")
        old_package, old_metadata = package(base, old_product, "6")

        bridge_product = synthetic_product(base, "0.6.1", [1])
        releases, _ = release_tree(base, bridge_product, "5")
        target_product = synthetic_product(base, "0.7.0", [2])
        release_tree(base, target_product, "7")

        workspace = base / "workspace"
        installed = apply(old_package, old_metadata, workspace)
        if installed.returncode:
            raise AssertionError(installed.stdout + installed.stderr)
        shutil.rmtree(workspace / "people")
        shutil.rmtree(workspace / "research")
        state = workspace / "state/preserved.md"
        state.write_text(
            "# Preserved\n\nUpdated: 2026-07-20\n\nSYNTHETIC_SENTINEL\n\n"
            "Legacy: ../deltas/2026/07/legacy-reference.md\n",
            encoding="utf-8",
        )
        state_before = state.read_bytes()

        legacy_plan = cli(workspace, releases, "migrate", "--version", "0.7.0", "--json")
        if legacy_plan.returncode == 0 or "E_MIGRATION_IMPACT" not in legacy_plan.stderr:
            raise AssertionError(legacy_plan.stdout + legacy_plan.stderr)
        if (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip() != "0.6.0":
            raise AssertionError("legacy planning failure changed the product")

        bridged = cli(workspace, releases, "update", "--version", "0.6.1")
        if bridged.returncode or "UPDATED" not in bridged.stdout:
            raise AssertionError(bridged.stdout + bridged.stderr)
        if (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip() != "1":
            raise AssertionError("bridge update changed the Workspace version")

        planned = cli(workspace, releases, "migrate", "--version", "0.7.0", "--json")
        if planned.returncode:
            raise AssertionError(planned.stdout + planned.stderr)
        plan = json.loads(planned.stdout)
        if plan["affected_paths"] != ["people", "research"]:
            raise AssertionError(str(plan))
        if (workspace / "people").exists() or (workspace / "research").exists():
            raise AssertionError("planning changed user data")
        applied = cli(workspace, releases, "migrate", "--apply", plan["plan_id"], "--json")
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        receipt = json.loads(applied.stdout)
        if receipt["outcome"] != "committed":
            raise AssertionError(str(receipt))
        for relative in ("people", "research/papers", "research/topics", "research/projects"):
            if not (workspace / relative).is_dir():
                raise AssertionError(f"missing migrated directory: {relative}")
        if state.read_bytes() != state_before:
            raise AssertionError("additive migration changed existing State")
        if (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip() != "2":
            raise AssertionError("Workspace version was not applied last")
        doctor = cli(workspace, releases, "doctor", "--json")
        codes = {finding["code"] for finding in json.loads(doctor.stdout)["findings"]}
        if "PODO_D121_PLAIN_REFERENCE" not in codes:
            raise AssertionError(doctor.stdout)
        backup = workspace / ".podo-backups" / plan["backup_id"]
        if not (backup / "backup.json").is_file():
            raise AssertionError("migration backup is missing")
        print("PASS legacy 0.6.0 bridge update, real Workspace 1→2 plan, backup and additive migration")


if __name__ == "__main__":
    main()
