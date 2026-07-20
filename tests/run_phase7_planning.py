#!/usr/bin/env python3
"""Exercise verified migration discovery and read-only impact planning."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "product/.podo/scripts"))

from migration_store import MigrationError, impact_path, migration_chain, plan_migration, validate_descriptor  # noqa: E402
from run_phase6_product_update import apply, package, synthetic_product  # noqa: E402


MIGRATE_SCRIPT = '''#!/usr/bin/env python3
import argparse
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument("--workspace", required=True, type=Path)
args = parser.parse_args()
path = args.workspace / "state/project.md"
text = path.read_text(encoding="utf-8")
path.write_text(text.replace("Updated:", "Format: 2\\n\\nUpdated:", 1), encoding="utf-8")
'''


def add_migration(product: Path, start: int, end: int, *, affected: list[str] | None = None) -> None:
    directory = product / f".podo/migrations/{start}-to-{end}"
    directory.mkdir(exist_ok=True)
    descriptor = {
        "migration_contract_version": 1,
        "from_workspace_version": start,
        "to_workspace_version": end,
        "description": f"Synthetic Workspace {start} to {end}",
        "changes": ["Adds a synthetic format marker to project State."],
        "affected_paths": affected or ["state/project.md"],
        "entrypoint": "migrate.py",
    }
    (directory / "migration.json").write_text(
        json.dumps(descriptor, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (directory / "migrate.py").write_text(MIGRATE_SCRIPT, encoding="utf-8")


def release_tree(base: Path, product: Path, digit: str) -> tuple[Path, dict]:
    _package, metadata = package(base, product, digit)
    releases = base / "releases"
    releases.mkdir(exist_ok=True)
    shutil.copytree(base / f"assets-{product.name}", releases / metadata["tag"])
    return releases, metadata


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect(code: str, function, *args) -> None:
    try:
        function(*args)
    except MigrationError as error:
        if error.code != code:
            raise AssertionError(f"expected {code}, got {error.code}: {error}") from error
    else:
        raise AssertionError(f"expected {code}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase7-planning-") as temporary:
        base = Path(temporary)
        old_product = synthetic_product(base, "0.9.0", [1])
        old_package, old_metadata = package(base, old_product, "1")
        target_product = synthetic_product(base, "1.0.0", [2])
        add_migration(target_product, 1, 2)
        releases, target_metadata = release_tree(base, target_product, "2")

        workspace = base / "workspace"
        installed = apply(old_package, old_metadata, workspace)
        if installed.returncode:
            raise AssertionError(installed.stdout + installed.stderr)
        state = workspace / "state/project.md"
        state.write_text(
            "# Synthetic Project\n\nUpdated: 2026-07-15\n\n## Current Context\n\nPLANNING_SENTINEL\n",
            encoding="utf-8",
        )
        state.chmod(0o600)
        before = {
            "product": sha(workspace / ".podo/install-manifest.json"),
            "workspace": sha(workspace / "WORKSPACE_VERSION"),
            "state": sha(state),
            "config": sha(workspace / "user_config.md"),
        }
        env_before = os.environ.copy()
        os.environ.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_DIR": str(releases)})
        try:
            plan = plan_migration(workspace, "1.0.0")
            repeated = plan_migration(workspace, "1.0.0")
        finally:
            os.environ.clear()
            os.environ.update(env_before)
        if plan != repeated:
            raise AssertionError("same evidence did not produce the same migration plan")
        if plan["target_release"]["archive_sha256"] != target_metadata["archive_sha256"]:
            raise AssertionError(str(plan))
        if plan["affected_paths"] != ["state/project.md"] or plan["from_workspace_version"] != 1 or plan["to_workspace_version"] != 2:
            raise AssertionError(str(plan))
        if plan["chain"][0]["description"] != "Synthetic Workspace 1 to 2":
            raise AssertionError(str(plan))
        after = {
            "product": sha(workspace / ".podo/install-manifest.json"),
            "workspace": sha(workspace / "WORKSPACE_VERSION"),
            "state": sha(state),
            "config": sha(workspace / "user_config.md"),
        }
        if before != after:
            raise AssertionError("planning changed permanent product or user data")
        plans = list((workspace / ".podo-work/migration-plans").glob("*.json"))
        if len(plans) != 1 or json.loads(plans[0].read_text(encoding="utf-8")) != plan:
            raise AssertionError(str(plans))
        print("PASS verified target package produces one exact, idempotent, non-applying impact plan")

        expect("E_MIGRATION_PATH", migration_chain, [], 1, [2])
        ambiguous = [
            {"from_workspace_version": 1, "to_workspace_version": 2},
            {"from_workspace_version": 1, "to_workspace_version": 3},
        ]
        expect("E_MIGRATION_AMBIGUOUS", migration_chain, ambiguous, 1, [2, 3])
        for unsafe in ("WORKSPACE_VERSION", ".podo/VERSION", "../state/project.md", "/tmp/project.md", "state/../events/x"):
            expect("E_MIGRATION_IMPACT", impact_path, unsafe)
        print("PASS missing, ambiguous and unsafe impact graphs fail before plan creation")

        invalid = base / "1-to-2"
        invalid.mkdir()
        (invalid / "migration.json").write_text(
            json.dumps(
                {
                    "migration_contract_version": 1,
                    "from_workspace_version": 2,
                    "to_workspace_version": 1,
                    "description": "wrong direction",
                    "changes": ["invalid"],
                    "affected_paths": ["state/project.md"],
                    "entrypoint": "migrate.py",
                }
            ),
            encoding="utf-8",
        )
        (invalid / "migrate.py").write_text("pass\n", encoding="utf-8")
        expect("E_MIGRATION_DESCRIPTOR", validate_descriptor, invalid)
        print("PASS descriptor directory and declared versions must match")


if __name__ == "__main__":
    main()
