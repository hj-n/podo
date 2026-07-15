#!/usr/bin/env python3
"""Plan verified Workspace migrations without changing permanent user data."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any


from product_install import InstallError, current_product
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
