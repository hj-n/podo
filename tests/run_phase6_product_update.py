#!/usr/bin/env python3
"""Exercise three-root product update, rollback and failure recovery."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_release.py"
FAILURE_POINTS = (
    "after-prepared",
    "after-backup-AGENTS.md",
    "after-backup-.codex",
    "after-backup-.podo",
    "after-install-AGENTS.md",
    "after-install-.codex",
    "after-install-.podo",
    "before-final-validation",
    "after-final-validation",
)


def run(args: list[str], **kwargs):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def synthetic_product(base: Path, version: str, workspace_versions: list[int]) -> Path:
    product = base / f"product-{version}"
    shutil.copytree(
        ROOT / "product",
        product,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "install-manifest.json"),
    )
    (product / ".podo/VERSION").write_text(version + "\n", encoding="utf-8")
    versions_path = product / ".podo/contracts/versions.json"
    values = json.loads(versions_path.read_text(encoding="utf-8"))
    values["compatible"][version] = workspace_versions
    versions_path.write_text(json.dumps(values, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (product / ".podo/templates/workspace/WORKSPACE_VERSION").write_text(
        f"{workspace_versions[0]}\n", encoding="utf-8"
    )
    return product


def package(base: Path, product: Path, commit_digit: str) -> tuple[Path, dict]:
    assets = base / f"assets-{product.name}"
    built = run(
        [
            sys.executable,
            str(BUILDER),
            "--product",
            str(product),
            "--output",
            str(assets),
            "--source-commit",
            commit_digit * 40,
        ],
        cwd=ROOT,
    )
    if built.returncode:
        raise AssertionError(built.stdout + built.stderr)
    metadata = json.loads((assets / "release.json").read_text(encoding="utf-8"))
    extracted = base / f"extracted-{product.name}"
    with tarfile.open(assets / metadata["archive_asset"], "r:gz") as bundle:
        bundle.extractall(extracted, filter="data")
    return extracted / f"podo-{metadata['product_version']}", metadata


def apply(package_root: Path, metadata: dict, workspace: Path, *, update: bool = False, env=None):
    command = [
        sys.executable,
        str(package_root / "install.py"),
        "--workspace",
        str(workspace),
        "--source-kind",
        "local-release",
        "--source-repository",
        "hj-n/podo",
        "--source-tag",
        metadata["tag"],
        "--archive-sha256",
        metadata["archive_sha256"],
    ]
    if update:
        command.append("--update")
    return run(command, cwd=package_root, env=env)


def product_snapshot(workspace: Path) -> dict[str, tuple[str, int]]:
    values: dict[str, tuple[str, int]] = {}
    candidates = [workspace / "AGENTS.md"]
    for directory in (workspace / ".codex", workspace / ".podo"):
        candidates.extend(path for path in directory.rglob("*") if path.is_file())
    for path in sorted(candidates):
        relative = path.relative_to(workspace).as_posix()
        values[relative] = (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode))
    return values


def add_user_sentinels(workspace: Path) -> dict[str, tuple[str, int]]:
    values = {
        ".podo-work/user-sentinel.txt": b"WORK_SENTINEL\n",
        ".podo-backups/user-sentinel.txt": b"BACKUP_SENTINEL\n",
        "state/user-sentinel.md": b"# Sentinel\n\nUpdated: 2026-07-15\n\n## Current Context\n\nSTATE_SENTINEL\n",
    }
    result: dict[str, tuple[str, int]] = {}
    for relative, raw in values.items():
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o600)
        result[relative] = (hashlib.sha256(raw).hexdigest(), 0o600)
    for relative in ("user_config.md", "WORKSPACE_VERSION"):
        path = workspace / relative
        result[relative] = (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode))
    return result


def assert_user_sentinels(workspace: Path, expected: dict[str, tuple[str, int]]) -> None:
    for relative, value in expected.items():
        path = workspace / relative
        actual = (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode))
        if actual != value:
            raise AssertionError(f"user-owned path changed: {relative} {actual} != {value}")


def version(workspace: Path) -> str:
    return (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase6-product-update-") as temporary:
        base = Path(temporary)
        old_package, old_metadata = package(base, synthetic_product(base, "0.4.0", [1]), "1")
        new_package, new_metadata = package(base, synthetic_product(base, "0.4.1", [1]), "2")
        incompatible_package, incompatible_metadata = package(
            base, synthetic_product(base, "0.4.2", [2]), "3"
        )

        workspace = base / "normal"
        installed = apply(old_package, old_metadata, workspace)
        if installed.returncode:
            raise AssertionError(installed.stdout + installed.stderr)
        sentinels = add_user_sentinels(workspace)
        updated = apply(new_package, new_metadata, workspace, update=True)
        if updated.returncode or "UPDATED" not in updated.stdout or version(workspace) != "0.4.1":
            raise AssertionError(updated.stdout + updated.stderr)
        assert_user_sentinels(workspace, sentinels)
        manifest = json.loads((workspace / ".podo/install-manifest.json").read_text(encoding="utf-8"))
        if manifest["source"]["archive_sha256"] != new_metadata["archive_sha256"]:
            raise AssertionError(str(manifest))
        rolled_back = apply(old_package, old_metadata, workspace, update=True)
        if rolled_back.returncode or "ROLLED_BACK" not in rolled_back.stdout or version(workspace) != "0.4.0":
            raise AssertionError(rolled_back.stdout + rolled_back.stderr)
        assert_user_sentinels(workspace, sentinels)
        print("PASS compatible product update and exact-version rollback preserve user files")

        for index, point in enumerate(FAILURE_POINTS):
            failed_workspace = base / f"failure-{index}"
            initial = apply(old_package, old_metadata, failed_workspace)
            if initial.returncode:
                raise AssertionError(initial.stdout + initial.stderr)
            sentinels = add_user_sentinels(failed_workspace)
            before = product_snapshot(failed_workspace)
            env = os.environ.copy()
            env.update({"PODO_TEST_UPDATE_FAILURES": "1", "PODO_TEST_UPDATE_FAIL_AT": point})
            failed = apply(new_package, new_metadata, failed_workspace, update=True, env=env)
            if failed.returncode == 0 or "E_INJECTED_UPDATE_FAILURE" not in failed.stderr:
                raise AssertionError(f"{point}: {failed.stdout}{failed.stderr}")
            if product_snapshot(failed_workspace) != before or version(failed_workspace) != "0.4.0":
                raise AssertionError(f"{point} did not restore previous product")
            assert_user_sentinels(failed_workspace, sentinels)
            active = failed_workspace / ".podo-work/product-updates"
            if active.is_dir() and any(active.iterdir()):
                raise AssertionError(f"{point} left active product transaction")
        print("PASS every product replacement boundary rolls back to exact previous product")

        modified = base / "modified"
        if apply(old_package, old_metadata, modified).returncode:
            raise AssertionError("modified fixture install failed")
        path = modified / ".podo/policies/todo.md"
        path.write_text(path.read_text(encoding="utf-8") + "modified\n", encoding="utf-8")
        rejected = apply(new_package, new_metadata, modified, update=True)
        if rejected.returncode == 0 or "E_PRODUCT_MODIFIED" not in rejected.stderr or "modified" not in path.read_text(encoding="utf-8"):
            raise AssertionError(rejected.stdout + rejected.stderr)

        recovering = base / "recovering"
        if apply(old_package, old_metadata, recovering).returncode:
            raise AssertionError("recovery fixture install failed")
        (recovering / ".podo-work/transactions/context-synthetic").mkdir(parents=True)
        rejected = apply(new_package, new_metadata, recovering, update=True)
        if rejected.returncode == 0 or "E_CONTEXT_RECOVERY_REQUIRED" not in rejected.stderr:
            raise AssertionError(rejected.stdout + rejected.stderr)

        incompatible = base / "incompatible"
        if apply(old_package, old_metadata, incompatible).returncode:
            raise AssertionError("incompatible fixture install failed")
        rejected = apply(incompatible_package, incompatible_metadata, incompatible, update=True)
        if rejected.returncode == 0 or "E_WORKSPACE_INCOMPATIBLE" not in rejected.stderr or version(incompatible) != "0.4.0":
            raise AssertionError(rejected.stdout + rejected.stderr)
        print("PASS update preflight rejects drift, Context recovery and incompatible Workspace")


if __name__ == "__main__":
    main()
