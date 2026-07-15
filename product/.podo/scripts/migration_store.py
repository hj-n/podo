#!/usr/bin/env python3
"""Plan verified Workspace migrations without changing permanent user data."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from product_install import (
    InstallError,
    build_stage,
    current_product,
    scan_product,
    source_manifest,
    validate_release,
    validate_workspace,
)
from product_manager import ProductManagerError, prepare_release


MIGRATION_DIR_RE = re.compile(r"^([1-9]\d*)-to-([1-9]\d*)$")
ENTRYPOINT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.py$")
ALLOWED_ROOTS = {"user_config.md", "events", "deltas", "state"}
REQUIRED_DESCRIPTOR = {
    "migration_contract_version",
    "from_workspace_version",
    "to_workspace_version",
    "description",
    "changes",
    "affected_paths",
    "entrypoint",
}
PRODUCT_ROOTS = ("AGENTS.md", ".codex", ".podo")
USER_ROOTS = ("user_config.md", "events", "deltas", "state")
PLAN_ID_RE = re.compile(r"^(migration|rollback)-[a-f0-9]{24}$")
BACKUP_ID_RE = re.compile(r"^migration-[a-f0-9]{24}-before-workspace-v[1-9]\d*$")


class MigrationError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def fail(code: str, detail: str) -> None:
    raise MigrationError(code, detail)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(code, str(error))
    if not isinstance(value, dict):
        fail(code, "JSON root must be an object")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def migration_lock(root: Path):
    path = root / ".podo-work/migration-apply.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("E_MIGRATION_BUSY", "another migration or full rollback apply is running")
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def impact_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        fail("E_MIGRATION_IMPACT", f"invalid affected path: {raw!r}")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != raw or not path.parts:
        fail("E_MIGRATION_IMPACT", raw)
    if path.parts[0] not in ALLOWED_ROOTS:
        fail("E_MIGRATION_IMPACT", f"path is not user migration data: {raw}")
    if path.parts[0] == "user_config.md" and len(path.parts) != 1:
        fail("E_MIGRATION_IMPACT", raw)
    return raw


def validate_descriptor(directory: Path) -> dict[str, Any]:
    match = MIGRATION_DIR_RE.fullmatch(directory.name)
    if not match or directory.is_symlink() or not directory.is_dir():
        fail("E_MIGRATION_DESCRIPTOR", f"invalid migration directory: {directory.name}")
    value = load_json(directory / "migration.json", "E_MIGRATION_DESCRIPTOR")
    if not REQUIRED_DESCRIPTOR.issubset(value):
        fail("E_MIGRATION_DESCRIPTOR", f"missing fields in {directory.name}")
    start, end = int(match.group(1)), int(match.group(2))
    if (
        value.get("migration_contract_version") != 1
        or value.get("from_workspace_version") != start
        or value.get("to_workspace_version") != end
        or end <= start
    ):
        fail("E_MIGRATION_DESCRIPTOR", f"version mismatch in {directory.name}")
    if not isinstance(value.get("description"), str) or not value["description"].strip():
        fail("E_MIGRATION_DESCRIPTOR", f"description is missing in {directory.name}")
    changes = value.get("changes")
    affected = value.get("affected_paths")
    if not isinstance(changes, list) or not changes or any(not isinstance(item, str) or not item.strip() for item in changes):
        fail("E_MIGRATION_DESCRIPTOR", f"changes are invalid in {directory.name}")
    if not isinstance(affected, list) or not affected:
        fail("E_MIGRATION_DESCRIPTOR", f"affected paths are invalid in {directory.name}")
    affected_paths = sorted(set(impact_path(item) for item in affected))
    entrypoint = value.get("entrypoint")
    if not isinstance(entrypoint, str) or not ENTRYPOINT_RE.fullmatch(entrypoint):
        fail("E_MIGRATION_DESCRIPTOR", f"entrypoint is invalid in {directory.name}")
    entrypoint_path = directory / entrypoint
    if entrypoint_path.is_symlink() or not entrypoint_path.is_file():
        fail("E_MIGRATION_DESCRIPTOR", f"entrypoint is missing in {directory.name}")
    return {
        "id": directory.name,
        "from_workspace_version": start,
        "to_workspace_version": end,
        "description": value["description"].strip(),
        "changes": changes,
        "affected_paths": affected_paths,
        "entrypoint": entrypoint,
        "descriptor_sha256": sha256(directory / "migration.json"),
        "entrypoint_sha256": sha256(entrypoint_path),
    }


def migration_steps(package: Path) -> list[dict[str, Any]]:
    root = package / "product/.podo/migrations"
    if root.is_symlink() or not root.is_dir():
        fail("E_MIGRATION_GRAPH", "target product migration directory is missing")
    steps: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        if path.name == "README.md" or path.name.startswith("."):
            continue
        steps.append(validate_descriptor(path))
    return steps


def migration_chain(steps: list[dict[str, Any]], start: int, targets: list[int]) -> list[dict[str, Any]]:
    by_start: dict[int, list[dict[str, Any]]] = {}
    for step in steps:
        by_start.setdefault(step["from_workspace_version"], []).append(step)
    paths: list[list[dict[str, Any]]] = []

    def walk(version: int, chain: list[dict[str, Any]]) -> None:
        if version in targets:
            paths.append(chain)
        for step in by_start.get(version, []):
            walk(step["to_workspace_version"], [*chain, step])

    walk(start, [])
    nonempty = [path for path in paths if path]
    if not nonempty:
        fail("E_MIGRATION_PATH", f"no migration path from Workspace {start} to {targets}")
    if len(nonempty) != 1:
        fail("E_MIGRATION_AMBIGUOUS", f"multiple migration paths from Workspace {start}")
    return nonempty[0]


def path_evidence(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        fail("E_MIGRATION_SYMLINK", str(path))
    if not path.exists():
        return {"kind": "missing"}
    if path.is_file():
        return {"kind": "file", "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}", "sha256": sha256(path)}
    if not path.is_dir():
        fail("E_MIGRATION_PATH_TYPE", str(path))
    entries: dict[str, dict[str, str]] = {}
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            fail("E_MIGRATION_SYMLINK", str(item))
        relative = item.relative_to(path).as_posix()
        if item.is_dir():
            entries[relative] = {"kind": "directory", "mode": f"{stat.S_IMODE(item.stat().st_mode):04o}"}
        elif item.is_file():
            entries[relative] = {
                "kind": "file",
                "mode": f"{stat.S_IMODE(item.stat().st_mode):04o}",
                "sha256": sha256(item),
            }
        else:
            fail("E_MIGRATION_PATH_TYPE", str(item))
    return {"kind": "directory", "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}", "entries": entries}


def evidence(root: Path, affected_paths: list[str]) -> dict[str, dict[str, Any]]:
    return {relative: path_evidence(root / relative) for relative in affected_paths}


def reject_overlapping(paths: list[str]) -> None:
    for index, relative in enumerate(paths):
        for other in paths[index + 1 :]:
            if other.startswith(relative + "/") or relative.startswith(other + "/"):
                fail("E_MIGRATION_IMPACT", f"overlapping affected paths: {relative}, {other}")


def plan_migration(root: Path, version: str) -> dict[str, Any]:
    if not version:
        fail("E_MIGRATION_VERSION", "an exact target product version is required")
    try:
        current, workspace_version = current_product(root)
    except InstallError as error:
        fail(error.code, error.detail)
    unfinished = root / ".podo-work/migrations"
    if unfinished.is_dir() and any(path.is_dir() for path in unfinished.iterdir() if not path.name.startswith(".")):
        fail("E_MIGRATION_RECOVERY_REQUIRED", "unfinished migration exists")
    with tempfile.TemporaryDirectory(prefix="podo-migration-plan-") as temporary:
        try:
            selected, metadata, package, _actual = prepare_release(version, Path(temporary))
        except ProductManagerError as error:
            fail(error.code, error.detail)
        targets = metadata.get("workspace_versions")
        if not isinstance(targets, list) or any(not isinstance(value, int) for value in targets):
            fail("E_MIGRATION_TARGET", "target Workspace versions are invalid")
        if workspace_version in targets:
            fail("E_MIGRATION_NOT_REQUIRED", "target product supports the current Workspace; use podo update")
        chain = migration_chain(migration_steps(package), workspace_version, targets)
        affected_paths = sorted({path for step in chain for path in step["affected_paths"]})
        reject_overlapping(affected_paths)
        pinned = {
            "current_product_manifest_sha256": sha256(root / ".podo/install-manifest.json"),
            "affected_evidence": evidence(root, affected_paths),
            "workspace_version": workspace_version,
        }
        identity = {
            "version": selected["version"],
            "tag": metadata["tag"],
            "source_commit": metadata["source_commit"],
            "archive_sha256": metadata["archive_sha256"],
            "workspace_versions": metadata["workspace_versions"],
        }
        content = {
            "migration_plan_version": 1,
            "kind": "migration",
            "from_product_version": current["product_version"],
            "to_product_version": selected["version"],
            "from_workspace_version": workspace_version,
            "to_workspace_version": chain[-1]["to_workspace_version"],
            "target_release": identity,
            "chain": chain,
            "affected_paths": affected_paths,
            "backup_parent": ".podo-backups",
            "rollback": "Restores the previous product and every affected user path from the retained backup.",
            "pins": pinned,
        }
        canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        plan_id = "migration-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        backup_id = f"{plan_id}-before-workspace-v{content['to_workspace_version']}"
        plan = {**content, "plan_id": plan_id, "backup_id": backup_id}
        path = root / f".podo-work/migration-plans/{plan_id}.json"
        if path.exists():
            if load_json(path, "E_MIGRATION_PLAN") != plan:
                fail("E_MIGRATION_PLAN", "plan ID collision")
        else:
            atomic_json(path, plan)
        return plan


def load_plan(root: Path, plan_id: str) -> dict[str, Any]:
    if not PLAN_ID_RE.fullmatch(plan_id):
        fail("E_MIGRATION_PLAN_ID", "exact migration plan ID is required")
    plan = load_json(root / f".podo-work/migration-plans/{plan_id}.json", "E_MIGRATION_PLAN")
    if (
        plan.get("migration_plan_version") != 1
        or plan.get("kind") not in {"migration", "rollback"}
        or plan.get("plan_id") != plan_id
    ):
        fail("E_MIGRATION_PLAN", "plan identity is invalid")
    return plan


def verify_pins(root: Path, plan: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        current, workspace_version = current_product(root)
    except InstallError as error:
        fail(error.code, error.detail)
    pins = plan.get("pins")
    affected_paths = plan.get("affected_paths")
    if not isinstance(pins, dict) or not isinstance(affected_paths, list):
        fail("E_MIGRATION_PLAN", "plan pins are invalid")
    if (
        workspace_version != plan.get("from_workspace_version")
        or workspace_version != pins.get("workspace_version")
        or current.get("product_version") != plan.get("from_product_version")
    ):
        fail("E_MIGRATION_PLAN_STALE", "product or Workspace version changed after planning")
    manifest = root / ".podo/install-manifest.json"
    if sha256(manifest) != pins.get("current_product_manifest_sha256"):
        fail("E_MIGRATION_PLAN_STALE", "installed product manifest changed after planning")
    actual_evidence = evidence(root, affected_paths)
    if actual_evidence != pins.get("affected_evidence"):
        fail("E_MIGRATION_PLAN_STALE", "affected user data changed after planning")
    return current, workspace_version


def copy_path(source: Path, destination: Path) -> None:
    if source.is_symlink():
        fail("E_MIGRATION_SYMLINK", str(source))
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    elif source.is_dir():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, copy_function=shutil.copy2)
    elif source.exists():
        fail("E_MIGRATION_PATH_TYPE", str(source))


def remove_path(path: Path) -> None:
    if path.is_symlink():
        fail("E_MIGRATION_SYMLINK", str(path))
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()
    elif path.exists():
        fail("E_MIGRATION_PATH_TYPE", str(path))


def flattened_snapshot(root: Path) -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}
    for relative in USER_ROOTS:
        base = root / relative
        if base.is_symlink():
            fail("E_MIGRATION_SYMLINK", relative)
        if base.is_file():
            values[relative] = {
                "kind": "file",
                "mode": f"{stat.S_IMODE(base.stat().st_mode):04o}",
                "sha256": sha256(base),
            }
            continue
        if not base.is_dir():
            values[relative] = {"kind": "missing"}
            continue
        values[relative] = {"kind": "directory", "mode": f"{stat.S_IMODE(base.stat().st_mode):04o}"}
        for item in sorted(base.rglob("*")):
            if item.is_symlink():
                fail("E_MIGRATION_SYMLINK", str(item))
            key = item.relative_to(root).as_posix()
            if item.is_dir():
                values[key] = {"kind": "directory", "mode": f"{stat.S_IMODE(item.stat().st_mode):04o}"}
            elif item.is_file():
                values[key] = {
                    "kind": "file",
                    "mode": f"{stat.S_IMODE(item.stat().st_mode):04o}",
                    "sha256": sha256(item),
                }
            else:
                fail("E_MIGRATION_PATH_TYPE", str(item))
    return values


def allowed_change(relative: str, affected_paths: list[str]) -> bool:
    return any(relative == affected or relative.startswith(affected + "/") for affected in affected_paths)


def assert_declared_changes(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
    affected_paths: list[str],
) -> None:
    changed = sorted(
        relative
        for relative in set(before) | set(after)
        if before.get(relative) != after.get(relative)
    )
    undeclared = [relative for relative in changed if not allowed_change(relative, affected_paths)]
    if undeclared:
        fail("E_MIGRATION_UNDECLARED_CHANGE", ",".join(undeclared[:20]))


def copy_current_user_data(root: Path, stage: Path) -> None:
    for relative in USER_ROOTS:
        destination = stage / relative
        if destination.exists():
            remove_path(destination)
        copy_path(root / relative, destination)
    shutil.copy2(root / "WORKSPACE_VERSION", stage / "WORKSPACE_VERSION")


def create_backup(root: Path, plan: dict[str, Any], current_manifest: dict[str, Any]) -> Path:
    backup = root / ".podo-backups" / plan["backup_id"]
    manifest_path = backup / "backup.json"
    if backup.exists():
        existing = load_json(manifest_path, "E_MIGRATION_BACKUP")
        if existing.get("state") == "complete" and existing.get("plan_id") == plan["plan_id"]:
            return backup
        fail("E_MIGRATION_BACKUP", f"incomplete or unrelated backup exists: {plan['backup_id']}")
    backup.mkdir()
    manifest: dict[str, Any] = {
        "migration_backup_version": 1,
        "backup_id": plan["backup_id"],
        "plan_id": plan["plan_id"],
        "state": "building",
        "from_product_version": plan["from_product_version"],
        "from_workspace_version": plan["from_workspace_version"],
        "to_product_version": plan["to_product_version"],
        "to_workspace_version": plan["to_workspace_version"],
        "affected_paths": plan["affected_paths"],
        "original_evidence": plan["pins"]["affected_evidence"],
        "current_product_manifest": current_manifest,
        "created_at": now(),
    }
    atomic_json(manifest_path, manifest)
    try:
        for relative in PRODUCT_ROOTS:
            copy_path(root / relative, backup / "product" / relative)
        copy_path(root / "WORKSPACE_VERSION", backup / "user-data/WORKSPACE_VERSION")
        for relative in plan["affected_paths"]:
            copy_path(root / relative, backup / "user-data" / relative)
        if sha256(backup / "product/.podo/install-manifest.json") != plan["pins"]["current_product_manifest_sha256"]:
            fail("E_MIGRATION_BACKUP", "copied product manifest does not match the plan")
        copied = evidence(backup / "user-data", plan["affected_paths"])
        if copied != plan["pins"]["affected_evidence"]:
            fail("E_MIGRATION_BACKUP", "copied user data does not match the plan")
        manifest["state"] = "complete"
        manifest["completed_at"] = now()
        atomic_json(manifest_path, manifest)
    except Exception as error:
        manifest["state"] = "incomplete"
        manifest["failure"] = {"code": getattr(error, "code", "E_MIGRATION_BACKUP"), "detail": str(error), "at": now()}
        atomic_json(manifest_path, manifest)
        if isinstance(error, MigrationError):
            raise
        fail("E_MIGRATION_BACKUP", str(error))
    return backup


def verify_target_plan(package: Path, metadata: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    identity = {
        "version": metadata["product_version"],
        "tag": metadata["tag"],
        "source_commit": metadata["source_commit"],
        "archive_sha256": metadata["archive_sha256"],
        "workspace_versions": metadata["workspace_versions"],
    }
    if identity != plan.get("target_release"):
        fail("E_MIGRATION_TARGET_CHANGED", "target Release identity differs from the approved plan")
    chain = migration_chain(
        migration_steps(package),
        plan["from_workspace_version"],
        metadata["workspace_versions"],
    )
    if chain != plan.get("chain") or chain[-1]["to_workspace_version"] != plan.get("to_workspace_version"):
        fail("E_MIGRATION_TARGET_CHANGED", "migration chain differs from the approved plan")
    return chain


def prepare_staged_workspace(
    root: Path,
    package: Path,
    metadata: dict[str, Any],
    archive_sha256: str,
    plan: dict[str, Any],
    stage: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    release = validate_release(package)
    source = source_manifest(
        release,
        kind="local-release" if os.environ.get("PODO_TEST_RELEASES") == "1" else "github",
        repository=metadata["repository"],
        tag=metadata["tag"],
        archive_sha256=archive_sha256,
    )
    desired = build_stage(
        package,
        stage,
        source,
        release,
        plan["to_workspace_version"],
    )
    copy_current_user_data(root, stage)
    before = flattened_snapshot(stage)
    return desired, before


def execute_staged_migrations(
    package: Path,
    stage: Path,
    chain: list[dict[str, Any]],
    desired: dict[str, Any],
    before: dict[str, dict[str, str]],
    affected_paths: list[str],
) -> None:
    for step in chain:
        script = package / "product/.podo/migrations" / step["id"] / step["entrypoint"]
        result = subprocess.run(
            [sys.executable, str(script), "--workspace", str(stage)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
            env={**os.environ, "PODO_MIGRATION_STAGE": "1"},
        )
        if result.returncode:
            fail(
                "E_MIGRATION_ENTRYPOINT",
                (result.stderr or result.stdout or f"{step['id']} failed").strip(),
            )
        (stage / "WORKSPACE_VERSION").write_text(
            f"{step['to_workspace_version']}\n",
            encoding="utf-8",
        )
    after = flattened_snapshot(stage)
    assert_declared_changes(before, after, affected_paths)
    if scan_product(stage) != desired["product_files"]:
        fail("E_MIGRATION_PRODUCT_CHANGED", "migration entrypoint changed staged product files")
    try:
        validate_workspace(stage, "context-present")
    except InstallError as error:
        fail(error.code, error.detail)


def migration_inject(point: str) -> None:
    if os.environ.get("PODO_TEST_MIGRATION_FAILURES") == "1" and os.environ.get("PODO_TEST_MIGRATION_FAIL_AT") == point:
        fail("E_INJECTED_MIGRATION_FAILURE", point)


def restore_backup(root: Path, backup: Path, plan: dict[str, Any]) -> None:
    for relative in PRODUCT_ROOTS:
        destination = root / relative
        if destination.exists() or destination.is_symlink():
            remove_path(destination)
        copy_path(backup / "product" / relative, destination)
    for relative in plan["affected_paths"]:
        destination = root / relative
        if destination.exists() or destination.is_symlink():
            remove_path(destination)
        original = plan["pins"]["affected_evidence"][relative]
        if original.get("kind") != "missing":
            copy_path(backup / "user-data" / relative, destination)
    workspace_version = root / "WORKSPACE_VERSION"
    if workspace_version.exists() or workspace_version.is_symlink():
        remove_path(workspace_version)
    copy_path(backup / "user-data/WORKSPACE_VERSION", workspace_version)


def save_journal(path: Path, journal: dict[str, Any]) -> None:
    journal["updated_at"] = now()
    atomic_json(path / "journal.json", journal)


def apply_staged(
    root: Path,
    stage: Path,
    backup: Path,
    plan: dict[str, Any],
    desired: dict[str, Any],
) -> dict[str, Any]:
    transaction = root / ".podo-work/migrations" / plan["plan_id"]
    if transaction.exists() or transaction.is_symlink():
        fail("E_MIGRATION_RECOVERY_REQUIRED", plan["plan_id"])
    (transaction / "previous-product").mkdir(parents=True)
    (transaction / "previous-user").mkdir()
    journal: dict[str, Any] = {
        "migration_journal_version": 1,
        "plan_id": plan["plan_id"],
        "backup_id": plan["backup_id"],
        "state": "prepared",
        "product_installed": [],
        "user_installed": [],
        "workspace_version_installed": False,
        "created_at": now(),
        "updated_at": now(),
    }
    save_journal(transaction, journal)
    try:
        migration_inject("after-prepared")
        journal["state"] = "applying"
        save_journal(transaction, journal)
        for relative in PRODUCT_ROOTS:
            os.replace(root / relative, transaction / "previous-product" / relative)
            os.replace(stage / relative, root / relative)
            journal["product_installed"].append(relative)
            save_journal(transaction, journal)
            migration_inject(f"after-product-{relative}")
        for index, relative in enumerate(plan["affected_paths"], start=1):
            current = root / relative
            previous = transaction / "previous-user" / relative
            if current.exists():
                previous.parent.mkdir(parents=True, exist_ok=True)
                os.replace(current, previous)
            migrated = stage / relative
            if migrated.exists():
                current.parent.mkdir(parents=True, exist_ok=True)
                os.replace(migrated, current)
            journal["user_installed"].append(relative)
            save_journal(transaction, journal)
            migration_inject(f"after-user-{index}")
        os.replace(root / "WORKSPACE_VERSION", transaction / "previous-user/WORKSPACE_VERSION")
        os.replace(stage / "WORKSPACE_VERSION", root / "WORKSPACE_VERSION")
        journal["workspace_version_installed"] = True
        save_journal(transaction, journal)
        migration_inject("after-workspace-version")
        migration_inject("before-final-validation")
        try:
            validate_workspace(root, "context-present")
        except InstallError as error:
            fail(error.code, error.detail)
        if scan_product(root) != desired["product_files"]:
            fail("E_MIGRATION_PRODUCT_CHANGED", "applied target product differs from its manifest")
        migration_inject("after-final-validation")
        journal["state"] = "committed"
        journal["committed_at"] = now()
        save_journal(transaction, journal)
        backup_manifest = load_json(backup / "backup.json", "E_MIGRATION_BACKUP")
        backup_manifest["migration_outcome"] = "committed"
        backup_manifest["after_product_manifest_sha256"] = sha256(root / ".podo/install-manifest.json")
        backup_manifest["after_evidence"] = evidence(root, plan["affected_paths"])
        backup_manifest["committed_at"] = journal["committed_at"]
        atomic_json(backup / "backup.json", backup_manifest)
        receipt = {
            "migration_receipt_version": 1,
            "plan_id": plan["plan_id"],
            "backup_id": plan["backup_id"],
            "outcome": "committed",
            "from_product_version": plan["from_product_version"],
            "to_product_version": plan["to_product_version"],
            "from_workspace_version": plan["from_workspace_version"],
            "to_workspace_version": plan["to_workspace_version"],
            "affected_paths": plan["affected_paths"],
            "after_product_manifest_sha256": backup_manifest["after_product_manifest_sha256"],
            "after_evidence": backup_manifest["after_evidence"],
            "committed_at": journal["committed_at"],
        }
        atomic_json(root / f".podo-work/migration-receipts/{plan['plan_id']}.json", receipt)
        shutil.rmtree(transaction)
        return receipt
    except Exception as error:
        try:
            journal["state"] = "rolling-back"
            journal["failure"] = {
                "code": getattr(error, "code", "E_MIGRATION_APPLY"),
                "detail": str(error),
                "at": now(),
            }
            save_journal(transaction, journal)
            restore_backup(root, backup, plan)
            try:
                validate_workspace(root, "context-present")
            except InstallError as validation_error:
                fail(validation_error.code, validation_error.detail)
            journal["state"] = "rolled-back"
            journal["rolled_back_at"] = now()
            save_journal(transaction, journal)
            receipt = {
                "migration_receipt_version": 1,
                "plan_id": plan["plan_id"],
                "backup_id": plan["backup_id"],
                "outcome": "rolled-back",
                "failure": journal["failure"],
                "rolled_back_at": journal["rolled_back_at"],
            }
            atomic_json(root / f".podo-work/migration-receipts/{plan['plan_id']}-failure.json", receipt)
            shutil.rmtree(transaction)
        except Exception as rollback_error:
            fail("E_MIGRATION_ROLLBACK", f"{error}; restore failed: {rollback_error}")
        if isinstance(error, MigrationError):
            raise
        fail("E_MIGRATION_APPLY", str(error))


def _apply_migration(root: Path, plan_id: str) -> dict[str, Any]:
    plan = load_plan(root, plan_id)
    current, _workspace_version = verify_pins(root, plan)
    with tempfile.TemporaryDirectory(prefix="podo-migration-apply-", dir=root.parent) as temporary:
        directory = Path(temporary)
        try:
            _selected, metadata, package, archive_sha256 = prepare_release(
                plan["to_product_version"],
                directory,
            )
        except ProductManagerError as error:
            fail(error.code, error.detail)
        chain = verify_target_plan(package, metadata, plan)
        stage = directory / "staged-workspace"
        stage.mkdir()
        desired, before = prepare_staged_workspace(
            root,
            package,
            metadata,
            archive_sha256,
            plan,
            stage,
        )
        verify_pins(root, plan)
        backup = create_backup(root, plan, current)
        migration_inject("after-backup")
        execute_staged_migrations(
            package,
            stage,
            chain,
            desired,
            before,
            plan["affected_paths"],
        )
        verify_pins(root, plan)
        return apply_staged(root, stage, backup, plan, desired)


def apply_migration(root: Path, plan_id: str) -> dict[str, Any]:
    with migration_lock(root):
        return _apply_migration(root, plan_id)


def verify_source_backup(backup: Path, manifest: dict[str, Any]) -> None:
    if manifest.get("migration_backup_version") != 1 or manifest.get("state") != "complete":
        fail("E_MIGRATION_BACKUP", "backup is not complete")
    product_manifest = backup / "product/.podo/install-manifest.json"
    expected_manifest = manifest.get("current_product_manifest")
    if not isinstance(expected_manifest, dict):
        fail("E_MIGRATION_BACKUP", "previous product manifest evidence is missing")
    if sha256(product_manifest) != hashlib.sha256(
        (json.dumps(expected_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    ).hexdigest():
        fail("E_MIGRATION_BACKUP", "previous product manifest bytes changed")
    if scan_product(backup / "product") != expected_manifest.get("product_files"):
        fail("E_MIGRATION_BACKUP", "previous product files differ from backup manifest")
    affected = manifest.get("affected_paths")
    original = manifest.get("original_evidence")
    if not isinstance(affected, list) or not isinstance(original, dict):
        fail("E_MIGRATION_BACKUP", "previous user evidence is missing")
    if evidence(backup / "user-data", affected) != original:
        fail("E_MIGRATION_BACKUP", "previous user data differs from backup manifest")


def plan_rollback(root: Path, backup_id: str) -> dict[str, Any]:
    if not BACKUP_ID_RE.fullmatch(backup_id):
        fail("E_ROLLBACK_BACKUP_ID", "exact migration backup ID is required")
    backup = root / ".podo-backups" / backup_id
    manifest = load_json(backup / "backup.json", "E_MIGRATION_BACKUP")
    verify_source_backup(backup, manifest)
    if manifest.get("migration_outcome") != "committed":
        fail("E_ROLLBACK_BACKUP", "backup does not describe a committed migration")
    try:
        current, workspace_version = current_product(root)
    except InstallError as error:
        fail(error.code, error.detail)
    if (
        current.get("product_version") != manifest.get("to_product_version")
        or workspace_version != manifest.get("to_workspace_version")
        or sha256(root / ".podo/install-manifest.json") != manifest.get("after_product_manifest_sha256")
    ):
        fail("E_ROLLBACK_CURRENT_PRODUCT", "current product is not the committed migration target")
    affected_paths = manifest["affected_paths"]
    current_evidence = evidence(root, affected_paths)
    after_evidence = manifest.get("after_evidence")
    if not isinstance(after_evidence, dict):
        fail("E_ROLLBACK_BACKUP", "post-migration evidence is missing")
    changed_since_migration = sorted(
        relative
        for relative in affected_paths
        if current_evidence.get(relative) != after_evidence.get(relative)
    )
    content = {
        "migration_plan_version": 1,
        "kind": "rollback",
        "source_backup_id": backup_id,
        "source_backup_manifest_sha256": sha256(backup / "backup.json"),
        "from_product_version": current["product_version"],
        "to_product_version": manifest["from_product_version"],
        "from_workspace_version": workspace_version,
        "to_workspace_version": manifest["from_workspace_version"],
        "affected_paths": affected_paths,
        "changes_since_migration": changed_since_migration,
        "rollback": "Overwrites current affected paths and product with the retained pre-migration backup.",
        "pins": {
            "current_product_manifest_sha256": sha256(root / ".podo/install-manifest.json"),
            "affected_evidence": current_evidence,
            "workspace_version": workspace_version,
        },
    }
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    plan_id = "rollback-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    safety_backup_id = f"migration-{hashlib.sha256(plan_id.encode()).hexdigest()[:24]}-before-workspace-v{content['to_workspace_version']}"
    plan = {**content, "plan_id": plan_id, "backup_id": safety_backup_id}
    path = root / f".podo-work/migration-plans/{plan_id}.json"
    if path.exists():
        if load_json(path, "E_ROLLBACK_PLAN") != plan:
            fail("E_ROLLBACK_PLAN", "rollback plan ID collision")
    else:
        atomic_json(path, plan)
    return plan


def verify_rollback_pins(root: Path, plan: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        current, workspace_version = current_product(root)
    except InstallError as error:
        fail(error.code, error.detail)
    if (
        current.get("product_version") != plan.get("from_product_version")
        or workspace_version != plan.get("from_workspace_version")
        or workspace_version != plan.get("pins", {}).get("workspace_version")
        or sha256(root / ".podo/install-manifest.json") != plan.get("pins", {}).get("current_product_manifest_sha256")
        or evidence(root, plan.get("affected_paths", [])) != plan.get("pins", {}).get("affected_evidence")
    ):
        fail("E_ROLLBACK_PLAN_STALE", "current product or affected user data changed after rollback planning")
    source = root / ".podo-backups" / str(plan.get("source_backup_id"))
    if sha256(source / "backup.json") != plan.get("source_backup_manifest_sha256"):
        fail("E_ROLLBACK_PLAN_STALE", "source backup manifest changed after rollback planning")
    return current, workspace_version


def backup_plan_for_current(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "plan_id": plan["plan_id"],
        "backup_id": plan["backup_id"],
        "from_product_version": plan["from_product_version"],
        "to_product_version": plan["to_product_version"],
        "from_workspace_version": plan["from_workspace_version"],
        "to_workspace_version": plan["to_workspace_version"],
        "affected_paths": plan["affected_paths"],
        "pins": plan["pins"],
    }


def apply_rollback_paths(
    root: Path,
    source: Path,
    safety: Path,
    plan: dict[str, Any],
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    transaction = root / ".podo-work/migrations" / plan["plan_id"]
    if transaction.exists() or transaction.is_symlink():
        fail("E_MIGRATION_RECOVERY_REQUIRED", plan["plan_id"])
    transaction.mkdir(parents=True)
    journal: dict[str, Any] = {
        "migration_journal_version": 1,
        "plan_id": plan["plan_id"],
        "source_backup_id": plan["source_backup_id"],
        "safety_backup_id": plan["backup_id"],
        "state": "prepared",
        "created_at": now(),
        "updated_at": now(),
    }
    save_journal(transaction, journal)
    try:
        migration_inject("after-rollback-prepared")
        journal["state"] = "applying"
        save_journal(transaction, journal)
        for relative in PRODUCT_ROOTS:
            remove_path(root / relative)
            copy_path(source / "product" / relative, root / relative)
            migration_inject(f"after-rollback-product-{relative}")
        for index, relative in enumerate(plan["affected_paths"], start=1):
            destination = root / relative
            if destination.exists() or destination.is_symlink():
                remove_path(destination)
            if source_manifest["original_evidence"][relative].get("kind") != "missing":
                copy_path(source / "user-data" / relative, destination)
            migration_inject(f"after-rollback-user-{index}")
        remove_path(root / "WORKSPACE_VERSION")
        copy_path(source / "user-data/WORKSPACE_VERSION", root / "WORKSPACE_VERSION")
        migration_inject("after-rollback-workspace-version")
        migration_inject("before-rollback-final-validation")
        try:
            validate_workspace(root, "context-present")
        except InstallError as error:
            fail(error.code, error.detail)
        migration_inject("after-rollback-final-validation")
        journal["state"] = "committed"
        journal["committed_at"] = now()
        save_journal(transaction, journal)
        receipt = {
            "migration_receipt_version": 1,
            "plan_id": plan["plan_id"],
            "source_backup_id": plan["source_backup_id"],
            "safety_backup_id": plan["backup_id"],
            "outcome": "rollback-committed",
            "from_product_version": plan["from_product_version"],
            "to_product_version": plan["to_product_version"],
            "from_workspace_version": plan["from_workspace_version"],
            "to_workspace_version": plan["to_workspace_version"],
            "affected_paths": plan["affected_paths"],
            "committed_at": journal["committed_at"],
        }
        atomic_json(root / f".podo-work/migration-receipts/{plan['plan_id']}.json", receipt)
        shutil.rmtree(transaction)
        return receipt
    except Exception as error:
        try:
            journal["state"] = "rolling-back"
            journal["failure"] = {
                "code": getattr(error, "code", "E_ROLLBACK_APPLY"),
                "detail": str(error),
                "at": now(),
            }
            save_journal(transaction, journal)
            restore_backup(root, safety, backup_plan_for_current(plan))
            try:
                validate_workspace(root, "context-present")
            except InstallError as validation_error:
                fail(validation_error.code, validation_error.detail)
            journal["state"] = "rolled-back"
            journal["rolled_back_at"] = now()
            save_journal(transaction, journal)
            receipt = {
                "migration_receipt_version": 1,
                "plan_id": plan["plan_id"],
                "source_backup_id": plan["source_backup_id"],
                "safety_backup_id": plan["backup_id"],
                "outcome": "rollback-failed-restored",
                "failure": journal["failure"],
                "rolled_back_at": journal["rolled_back_at"],
            }
            atomic_json(root / f".podo-work/migration-receipts/{plan['plan_id']}-failure.json", receipt)
            shutil.rmtree(transaction)
        except Exception as rollback_error:
            fail("E_ROLLBACK_RESTORE", f"{error}; safety restore failed: {rollback_error}")
        if isinstance(error, MigrationError):
            raise
        fail("E_ROLLBACK_APPLY", str(error))


def _apply_rollback(root: Path, plan_id: str) -> dict[str, Any]:
    plan = load_plan(root, plan_id)
    if plan.get("kind") != "rollback":
        fail("E_ROLLBACK_PLAN", "plan is not a rollback plan")
    current, _workspace_version = verify_rollback_pins(root, plan)
    source = root / ".podo-backups" / plan["source_backup_id"]
    source_manifest = load_json(source / "backup.json", "E_MIGRATION_BACKUP")
    verify_source_backup(source, source_manifest)
    verify_rollback_pins(root, plan)
    safety_plan = backup_plan_for_current(plan)
    safety = create_backup(root, safety_plan, current)
    migration_inject("after-rollback-backup")
    verify_rollback_pins(root, plan)
    return apply_rollback_paths(root, source, safety, plan, source_manifest)


def apply_rollback(root: Path, plan_id: str) -> dict[str, Any]:
    with migration_lock(root):
        return _apply_rollback(root, plan_id)


def apply_plan(root: Path, plan_id: str) -> dict[str, Any]:
    plan = load_plan(root, plan_id)
    if plan["kind"] == "migration":
        return apply_migration(root, plan_id)
    return apply_rollback(root, plan_id)
