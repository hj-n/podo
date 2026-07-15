#!/usr/bin/env python3
"""Install a verified Podo product package into a User Workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCT_ROOTS = ("AGENTS.md", ".codex", ".podo")
USER_FILES = ("WORKSPACE_VERSION", "user_config.md")
USER_DIRS = (".podo-work", ".podo-backups", "events", "deltas", "state")
MANIFEST_PATH = ".podo/install-manifest.json"
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
TOKEN_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


class InstallError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass
class CreatedPath:
    path: Path
    kind: str


def fail(code: str, detail: str) -> None:
    raise InstallError(code, detail)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(path: Path) -> dict[str, str]:
    return {"sha256": sha256(path), "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}"}


def write_text(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(code, str(error))
    if not isinstance(value, dict):
        fail(code, "JSON root must be an object")
    return value


def scan_product(root: Path) -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}
    candidates = [root / "AGENTS.md"]
    for directory in (root / ".codex", root / ".podo"):
        if directory.is_dir():
            candidates.extend(sorted(directory.rglob("*")))
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST_PATH or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            fail("E_SYMLINK", f"product path is a symlink: {relative}")
        if path.is_file():
            values[relative] = record(path)
    return dict(sorted(values.items()))


def render_user_config(template: Path) -> str:
    values = {
        "ASSISTANT_NAME": "포도",
        "ASSISTANT_PERSONALITY": "차분하고 명확하며 사용자의 결정을 존중함",
        "RESPONSE_STYLE": "핵심 결과를 먼저 말하고 필요한 다음 행동을 간결하게 설명함",
        "EXPLICIT_DEFAULTS": "- 날짜는 명확한 형식으로 기록한다.\n- 불확실한 선호는 사용자에게 확인한다.",
        "ALLOWED_EXTERNAL_SOURCES": "- 사용자가 명시적으로 허용하거나 요청한 자료만 사용한다.",
    }
    content = template.read_text(encoding="utf-8")
    required = set(TOKEN_RE.findall(content))
    if required - values.keys():
        fail("E_TEMPLATE", "user config template contains unknown values")
    for key in required:
        content = content.replace("{{" + key + "}}", values[key])
    if TOKEN_RE.search(content):
        fail("E_TEMPLATE", "user config contains unresolved values")
    return content


def validate_release(package_root: Path) -> dict[str, Any]:
    release = load_json(package_root / "release.json", "E_RELEASE_METADATA")
    version = str(release.get("product_version") or "")
    if not SEMVER_RE.fullmatch(version) or release.get("tag") != f"v{version}":
        fail("E_RELEASE_METADATA", "release version and tag do not match")
    product_version = (package_root / "product/.podo/VERSION").read_text(encoding="utf-8").strip()
    if product_version != version:
        fail("E_RELEASE_METADATA", "archive product version does not match release metadata")
    compatible = release.get("workspace_versions")
    if not isinstance(compatible, list) or not compatible or any(not isinstance(value, int) or value < 1 for value in compatible):
        fail("E_RELEASE_METADATA", "Workspace compatibility is invalid")
    return release


def source_manifest(
    release: dict[str, Any],
    *,
    kind: str,
    repository: str | None,
    tag: str | None,
    archive_sha256: str | None,
) -> dict[str, Any]:
    if kind not in {"github", "local-release"}:
        fail("E_SOURCE", kind)
    if tag is not None and tag != release["tag"]:
        fail("E_SOURCE", "source tag does not match archive")
    if repository is not None and repository != release["repository"]:
        fail("E_SOURCE", "source repository does not match archive")
    if archive_sha256 is not None and not SHA_RE.fullmatch(archive_sha256):
        fail("E_SOURCE", "archive SHA-256 is invalid")
    return {
        "kind": kind,
        "repository": repository or release["repository"],
        "tag": tag or release["tag"],
        "source_commit": release["source_commit"],
        "archive_sha256": archive_sha256,
    }


def validate_workspace(root: Path, mode: str) -> None:
    result = subprocess.run(
        [sys.executable, str(root / ".podo/scripts/validate_workspace.py"), str(root), "--mode", mode],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        fail("E_VALIDATION", " ".join(result.stdout.strip().splitlines()) or "Workspace validation failed")


def build_stage(package_root: Path, stage: Path, source: dict[str, Any], release: dict[str, Any]) -> dict[str, Any]:
    product = package_root / "product"
    shutil.copy2(product / "AGENTS.podo.md", stage / "AGENTS.md")
    shutil.copytree(product / ".codex", stage / ".codex", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    shutil.copytree(
        product / ".podo",
        stage / ".podo",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "install-manifest.json"),
    )
    for directory in USER_DIRS:
        (stage / directory).mkdir()
    shutil.copy2(product / ".podo/templates/workspace/WORKSPACE_VERSION", stage / "WORKSPACE_VERSION")
    write_text(stage / "user_config.md", render_user_config(product / ".podo/templates/workspace/user_config.md"))
    workspace_version = int((stage / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip())
    if workspace_version not in release["workspace_versions"]:
        fail("E_WORKSPACE_INCOMPATIBLE", f"release does not support initial Workspace {workspace_version}")
    manifest = {
        "manifest_version": 2,
        "product_version": release["product_version"],
        "workspace_version": workspace_version,
        "source": source,
        "product_files": scan_product(stage),
    }
    write_text(stage / MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    validate_workspace(stage, "installed-empty")
    return manifest


def reject_managed_symlinks(target: Path) -> None:
    if target.is_symlink():
        fail("E_SYMLINK", f"Workspace is a symlink: {target}")
    for relative in (*PRODUCT_ROOTS, *USER_FILES, *USER_DIRS):
        if (target / relative).is_symlink():
            fail("E_SYMLINK", f"managed path is a symlink: {relative}")


def inspect_target(target: Path, desired: dict[str, Any]) -> bool:
    if target.exists() and not target.is_dir():
        fail("E_PATH_TYPE", f"Workspace must be a directory: {target}")
    reject_managed_symlinks(target)
    present = [relative for relative in PRODUCT_ROOTS if (target / relative).exists()]
    if present and set(present) != set(PRODUCT_ROOTS):
        fail("E_PARTIAL_PRODUCT", "partial product paths: " + ",".join(sorted(present)))
    if not present:
        if (target / "WORKSPACE_VERSION").exists():
            try:
                workspace_version = int((target / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                fail("E_WORKSPACE_INCOMPATIBLE", "WORKSPACE_VERSION is invalid")
            if workspace_version != desired["workspace_version"]:
                fail("E_WORKSPACE_INCOMPATIBLE", str(workspace_version))
        return False
    current = load_json(target / MANIFEST_PATH, "E_PARTIAL_PRODUCT")
    if current != desired:
        fail("E_PRODUCT_COLLISION", "installed product identity differs from requested package")
    if scan_product(target) != current.get("product_files"):
        fail("E_PRODUCT_COLLISION", "installed product files differ from manifest")
    return True


def inject(point: str) -> None:
    if os.environ.get("PODO_TEST_INSTALL_FAILURES") == "1" and os.environ.get("PODO_TEST_INSTALL_FAIL_AT") == point:
        fail("E_INJECTED_FAILURE", point)


def rollback_created(created: list[CreatedPath]) -> None:
    for value in reversed(created):
        path = value.path
        if not path.exists() or path.is_symlink():
            continue
        if value.kind == "file" and path.is_file():
            path.unlink()
        elif value.kind == "product-dir" and path.is_dir():
            shutil.rmtree(path)
        elif value.kind in {"directory", "workspace"} and path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def apply_fresh(stage: Path, target: Path, already_installed: bool) -> str:
    if already_installed:
        return "already-installed"
    created: list[CreatedPath] = []
    try:
        if not target.exists():
            target.mkdir()
            created.append(CreatedPath(target, "workspace"))
        for relative in PRODUCT_ROOTS:
            source = stage / relative
            destination = target / relative
            if destination.exists() or destination.is_symlink():
                fail("E_PRODUCT_COLLISION", relative)
            os.replace(source, destination)
            created.append(CreatedPath(destination, "file" if relative == "AGENTS.md" else "product-dir"))
        inject("after-product")
        for relative in USER_DIRS:
            path = target / relative
            if not path.exists():
                path.mkdir()
                created.append(CreatedPath(path, "directory"))
        for relative in USER_FILES:
            path = target / relative
            if not path.exists():
                shutil.copy2(stage / relative, path)
                created.append(CreatedPath(path, "file"))
        inject("after-user-init")
        inject("before-final-validation")
        validate_workspace(target, "installed-empty")
    except Exception:
        rollback_created(created)
        raise
    return "installed"


def normalize_target(raw: Path, package_root: Path) -> Path:
    expanded = raw.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    parent = expanded.parent.resolve()
    if not parent.is_dir():
        fail("E_PARENT_MISSING", str(parent))
    target = parent / expanded.name
    try:
        target.resolve(strict=False).relative_to(package_root.resolve())
    except ValueError:
        pass
    else:
        fail("E_PACKAGE_BOUNDARY", "Workspace must be outside extracted package")
    return target


def install_package(
    package_root: Path,
    workspace: Path,
    *,
    source_kind: str,
    source_repository: str | None,
    source_tag: str | None,
    archive_sha256: str | None,
) -> tuple[str, Path, dict[str, Any]]:
    package_root = package_root.resolve()
    release = validate_release(package_root)
    source = source_manifest(
        release,
        kind=source_kind,
        repository=source_repository,
        tag=source_tag,
        archive_sha256=archive_sha256,
    )
    target = normalize_target(workspace, package_root)
    with tempfile.TemporaryDirectory(prefix=".podo-package-install-", dir=target.parent) as temporary:
        stage = Path(temporary) / "workspace"
        stage.mkdir()
        manifest = build_stage(package_root, stage, source, release)
        inject("after-staging")
        already = inspect_target(target, manifest)
        result = apply_fresh(stage, target, already)
    return result, target, manifest


def package_main(package_root: Path) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--source-kind", choices=("github", "local-release"), required=True)
    parser.add_argument("--source-repository")
    parser.add_argument("--source-tag")
    parser.add_argument("--archive-sha256")
    args = parser.parse_args()
    try:
        result, target, manifest = install_package(
            package_root,
            args.workspace,
            source_kind=args.source_kind,
            source_repository=args.source_repository,
            source_tag=args.source_tag,
            archive_sha256=args.archive_sha256,
        )
    except (InstallError, OSError) as error:
        code = error.code if isinstance(error, InstallError) else "E_INSTALL_IO"
        print(f"ERROR {code} {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"{'ALREADY_INSTALLED' if result == 'already-installed' else 'INSTALLED'} {target}")
    print(f"PRODUCT {manifest['product_version']} WORKSPACE {manifest['workspace_version']}")
    print("NEXT Open this Workspace in Codex, review .codex/hooks.json, and trust the project if it is correct.")


if __name__ == "__main__":
    package_main(Path(__file__).resolve().parents[3])
