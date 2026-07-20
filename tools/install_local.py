#!/usr/bin/env python3
"""Install the checked-in Podo product into an external User Workspace."""

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


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOT = REPO_ROOT / "product"
PRODUCT_ROOTS = ("AGENTS.md", ".codex", ".podo")
USER_FILES = ("WORKSPACE_VERSION", "user_config.md")
USER_DIRS = (".podo-work", ".podo-backups", "events", "deltas", "state", "people", "research")
USER_SUBDIRS = ("research/papers", "research/topics", "research/projects")
MANIFEST_PATH = ".podo/install-manifest.json"
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


def file_record(path: Path) -> dict[str, str]:
    return {
        "sha256": sha256(path),
        "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
    }


def scan_product_files(root: Path) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    candidates = [root / "AGENTS.md"]
    for directory in (root / ".codex", root / ".podo"):
        if directory.is_dir():
            candidates.extend(sorted(directory.rglob("*")))
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST_PATH:
            continue
        if path.is_symlink():
            fail("E_SYMLINK", f"product path is a symlink: {relative}")
        if path.is_file():
            records[relative] = file_record(path)
    return dict(sorted(records.items()))


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
    missing = sorted(required - values.keys())
    if missing:
        fail("E_TEMPLATE", "missing user config values: " + ",".join(missing))
    for key in required:
        content = content.replace("{{" + key + "}}", values[key])
    if TOKEN_RE.search(content):
        fail("E_TEMPLATE", "unresolved user config token")
    return content


def write_text(path: Path, content: str, mode: int = 0o644) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def build_stage(stage: Path) -> dict:
    shutil.copy2(PRODUCT_ROOT / "AGENTS.podo.md", stage / "AGENTS.md")
    shutil.copytree(
        PRODUCT_ROOT / ".codex",
        stage / ".codex",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    shutil.copytree(
        PRODUCT_ROOT / ".podo",
        stage / ".podo",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "install-manifest.json"),
    )
    for directory in USER_DIRS:
        (stage / directory).mkdir()
    for directory in ("research/papers", "research/topics", "research/projects"):
        (stage / directory).mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        PRODUCT_ROOT / ".podo/templates/workspace/WORKSPACE_VERSION",
        stage / "WORKSPACE_VERSION",
    )
    write_text(
        stage / "user_config.md",
        render_user_config(PRODUCT_ROOT / ".podo/templates/workspace/user_config.md"),
    )

    product_version = (stage / ".podo/VERSION").read_text(encoding="utf-8").strip()
    workspace_version = int((stage / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip())
    manifest = {
        "manifest_version": 1,
        "product_version": product_version,
        "workspace_version": workspace_version,
        "source": {"kind": "local", "path": str(PRODUCT_ROOT.resolve())},
        "product_files": scan_product_files(stage),
    }
    write_text(
        stage / MANIFEST_PATH,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    validate(stage, "installed-empty")
    return manifest


def validate(workspace: Path, mode: str) -> None:
    validator = workspace / ".podo/scripts/validate_workspace.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(workspace), "--mode", mode],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        detail = " ".join(result.stdout.strip().splitlines())
        fail("E_VALIDATION", detail or "Workspace validation failed")


def reject_symlinks(target: Path) -> None:
    if target.is_symlink():
        fail("E_SYMLINK", f"Workspace path is a symlink: {target}")
    for relative in (*PRODUCT_ROOTS, *USER_FILES, *USER_DIRS):
        path = target / relative
        if path.is_symlink():
            fail("E_SYMLINK", f"managed path is a symlink: {relative}")


def check_path_types(target: Path) -> None:
    for relative in USER_FILES:
        path = target / relative
        if path.exists() and not path.is_file():
            fail("E_PATH_TYPE", f"expected file: {relative}")
    for relative in USER_DIRS:
        path = target / relative
        if path.exists() and not path.is_dir():
            fail("E_PATH_TYPE", f"expected directory: {relative}")


def check_workspace_version(target: Path, desired: dict) -> None:
    path = target / "WORKSPACE_VERSION"
    if not path.exists():
        return
    try:
        current = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        fail("E_WORKSPACE_INCOMPATIBLE", "WORKSPACE_VERSION must be a positive integer")
    if current != desired["workspace_version"]:
        fail(
            "E_WORKSPACE_INCOMPATIBLE",
            f"product {desired['product_version']} requires Workspace {desired['workspace_version']}; found {current}",
        )


def load_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail("E_PARTIAL_PRODUCT", f"cannot read verified install manifest: {error}")
    if not isinstance(value, dict):
        fail("E_PARTIAL_PRODUCT", "install manifest must be a JSON object")
    return value


def inspect_existing_product(target: Path, desired: dict) -> bool:
    present = [relative for relative in PRODUCT_ROOTS if (target / relative).exists()]
    if not present:
        return False
    if set(present) != set(PRODUCT_ROOTS):
        fail("E_PARTIAL_PRODUCT", "partial product paths: " + ",".join(sorted(present)))
    if not (target / "AGENTS.md").is_file():
        fail("E_PATH_TYPE", "expected file: AGENTS.md")
    for relative in (".codex", ".podo"):
        if not (target / relative).is_dir():
            fail("E_PATH_TYPE", f"expected directory: {relative}")

    current = load_manifest(target / MANIFEST_PATH)
    for field in ("manifest_version", "product_version", "workspace_version", "product_files"):
        if field not in current:
            fail("E_PARTIAL_PRODUCT", f"manifest field is missing: {field}")
    if current["manifest_version"] != 1:
        fail("E_PARTIAL_PRODUCT", "unsupported install manifest version")
    if (
        current["product_version"] != desired["product_version"]
        or current["workspace_version"] != desired["workspace_version"]
        or current["product_files"] != desired["product_files"]
    ):
        fail("E_PRODUCT_COLLISION", "installed product does not match the requested local product")
    actual_files = scan_product_files(target)
    if actual_files != current["product_files"]:
        changed = sorted(set(actual_files) ^ set(current["product_files"]))
        if not changed:
            changed = sorted(
                path for path in actual_files if actual_files[path] != current["product_files"].get(path)
            )
        fail("E_PRODUCT_COLLISION", "modified product files: " + ",".join(changed[:10]))
    return True


def preflight(target: Path, desired: dict) -> bool:
    if target.exists() and not target.is_dir():
        fail("E_PATH_TYPE", f"Workspace must be a directory: {target}")
    reject_symlinks(target)
    if target.exists():
        check_path_types(target)
        check_workspace_version(target, desired)
    return inspect_existing_product(target, desired) if target.exists() else False


def inject(point: str | None, expected: str) -> None:
    if point == expected:
        fail("E_INJECTED_FAILURE", expected)


def remove_created(record: CreatedPath, desired_files: set[str], target: Path) -> None:
    path = record.path
    if not path.exists() and not path.is_symlink():
        return
    if record.kind == "file":
        if path.is_file() and not path.is_symlink():
            path.unlink()
        return
    if record.kind == "empty-dir" or record.kind == "target":
        try:
            path.rmdir()
        except OSError:
            pass
        return
    if record.kind == "product-dir":
        prefix = path.relative_to(target).as_posix() + "/"
        allowed = {item for item in desired_files if item.startswith(prefix)}
        if path == target / ".podo":
            allowed.add(MANIFEST_PATH)
        actual: set[str] = set()
        for item in path.rglob("*"):
            if item.is_symlink():
                return
            if item.is_file():
                actual.add(item.relative_to(target).as_posix())
        if actual <= allowed:
            shutil.rmtree(path)


def rollback(created: list[CreatedPath], desired: dict, target: Path) -> None:
    desired_files = set(desired["product_files"])
    for record in reversed(created):
        remove_created(record, desired_files, target)


def apply_install(
    stage: Path,
    target: Path,
    desired: dict,
    product_installed: bool,
    fail_at: str | None,
) -> str:
    created: list[CreatedPath] = []
    target_existed = target.exists()
    try:
        if not target_existed:
            target.mkdir()
            created.append(CreatedPath(target, "target"))

        if not product_installed:
            os.replace(stage / "AGENTS.md", target / "AGENTS.md")
            created.append(CreatedPath(target / "AGENTS.md", "file"))
            for relative in (".codex", ".podo"):
                os.replace(stage / relative, target / relative)
                created.append(CreatedPath(target / relative, "product-dir"))
        inject(fail_at, "after-product")

        for relative in USER_DIRS:
            path = target / relative
            if not path.exists():
                path.mkdir()
                created.append(CreatedPath(path, "empty-dir"))
        for relative in USER_SUBDIRS:
            path = target / relative
            if not path.exists():
                path.mkdir(parents=True)
                created.append(CreatedPath(path, "empty-dir"))
        for relative in USER_FILES:
            path = target / relative
            if not path.exists():
                shutil.copy2(stage / relative, path)
                created.append(CreatedPath(path, "file"))
        inject(fail_at, "after-user-init")
        inject(fail_at, "before-final-validation")
        validate(target, "installed-empty")
    except (InstallError, OSError) as error:
        rollback(created, desired, target)
        if isinstance(error, InstallError):
            raise
        fail("E_APPLY", str(error))

    if product_installed and not created:
        return "already-installed"
    return "installed"


def normalize_target(raw: Path) -> Path:
    expanded = raw.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    if expanded.is_symlink():
        fail("E_SYMLINK", f"Workspace path is a symlink: {expanded}")
    parent = expanded.parent.resolve()
    if not parent.is_dir():
        fail("E_PARENT_MISSING", f"Workspace parent must already exist: {parent}")
    target = parent / expanded.name
    try:
        target.resolve(strict=False).relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    else:
        fail("E_DEVELOPMENT_BOUNDARY", "User Workspace must be outside the Development Workspace")
    return target


def install(workspace: Path, fail_at: str | None) -> tuple[str, Path]:
    target = normalize_target(workspace)
    with tempfile.TemporaryDirectory(prefix=".podo-install-", dir=target.parent) as temporary:
        stage = Path(temporary) / "workspace"
        stage.mkdir()
        desired = build_stage(stage)
        inject(fail_at, "after-staging")
        product_installed = preflight(target, desired)
        result = apply_install(stage, target, desired, product_installed, fail_at)
    return result, target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument(
        "--fail-at",
        choices=("after-staging", "after-product", "after-user-init", "before-final-validation"),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    try:
        result, target = install(args.workspace, args.fail_at)
    except InstallError as error:
        print(f"ERROR {error.code} {error.detail}", file=sys.stderr)
        raise SystemExit(1)
    if result == "already-installed":
        print(f"ALREADY_INSTALLED {target}")
    else:
        print(f"INSTALLED {target}")
    print("NEXT Review this Workspace and its .codex/hooks.json in Codex before trusting project hooks.")
    print("CAPTURE guard-not-ready; Phase 3 implements Event capture.")


if __name__ == "__main__":
    main()
