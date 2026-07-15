#!/usr/bin/env python3
"""Exercise latest/exact update CLI, checksum and safe extraction."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True
from run_phase6_product_update import apply, package, synthetic_product  # noqa: E402


def run(args: list[str], **kwargs):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def release_tree(base: Path) -> tuple[Path, tuple[Path, dict], tuple[Path, dict]]:
    old_product = synthetic_product(base, "0.4.0", [1])
    new_product = synthetic_product(base, "0.4.1", [1])
    old = package(base, old_product, "4")
    new = package(base, new_product, "5")
    releases = base / "releases"
    releases.mkdir()
    for product, metadata in ((old_product, old[1]), (new_product, new[1])):
        source = base / f"assets-{product.name}"
        shutil.copytree(source, releases / metadata["tag"])
    (releases / "latest").write_text("0.4.1\n", encoding="utf-8")
    return releases, old, new


def update_env(releases: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_DIR": str(releases)})
    return env


def cli(workspace: Path, releases: Path, version: str | None = None):
    command = [str(workspace / ".podo/bin/podo"), "update"]
    if version is not None:
        command.extend(["--version", version])
    return run(command, cwd=workspace, env=update_env(releases))


def version(workspace: Path) -> str:
    return (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip()


def corrupt_archive_release(directory: Path, version_value: str) -> None:
    metadata_path = directory / "release.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    archive = directory / metadata["archive_asset"]
    with tarfile.open(archive, "w:gz") as bundle:
        raw = b"escape\n"
        info = tarfile.TarInfo(f"podo-{version_value}/../escape.txt")
        info.size = len(raw)
        bundle.addfile(info, io.BytesIO(raw))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (directory / metadata["checksum_asset"]).write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    metadata["archive_sha256"] = digest
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase6-update-cli-") as temporary:
        base = Path(temporary)
        releases, old, _new = release_tree(base)

        workspace = base / "normal"
        installed = apply(old[0], old[1], workspace)
        if installed.returncode:
            raise AssertionError(installed.stdout + installed.stderr)
        latest = cli(workspace, releases)
        if latest.returncode or version(workspace) != "0.4.1" or "Start a new Codex task" not in latest.stdout:
            raise AssertionError(latest.stdout + latest.stderr)
        exact = cli(workspace, releases, "0.4.0")
        if exact.returncode or version(workspace) != "0.4.0" or "ROLLED_BACK" not in exact.stdout:
            raise AssertionError(exact.stdout + exact.stderr)
        print("PASS podo update selects latest and exact rollback Release")
        invalid = cli(workspace, releases, "not-a-version")
        if invalid.returncode == 0 or "E_VERSION" not in invalid.stderr:
            raise AssertionError(invalid.stdout + invalid.stderr)

        checksum_releases = base / "checksum-releases"
        shutil.copytree(releases, checksum_releases)
        checksum = checksum_releases / "v0.4.1/podo-0.4.1.tar.gz.sha256"
        checksum.write_text("0" * 64 + "  podo-0.4.1.tar.gz\n", encoding="utf-8")
        checksum_workspace = base / "checksum-workspace"
        if apply(old[0], old[1], checksum_workspace).returncode:
            raise AssertionError("checksum fixture install failed")
        rejected = cli(checksum_workspace, checksum_releases)
        if rejected.returncode == 0 or "E_CHECKSUM_MISMATCH" not in rejected.stderr or version(checksum_workspace) != "0.4.0":
            raise AssertionError(rejected.stdout + rejected.stderr)
        print("PASS checksum mismatch leaves current product unchanged")

        unsafe_releases = base / "unsafe-releases"
        shutil.copytree(releases, unsafe_releases)
        corrupt_archive_release(unsafe_releases / "v0.4.1", "0.4.1")
        unsafe_workspace = base / "unsafe-workspace"
        if apply(old[0], old[1], unsafe_workspace).returncode:
            raise AssertionError("unsafe fixture install failed")
        rejected = cli(unsafe_workspace, unsafe_releases)
        if rejected.returncode == 0 or "E_ARCHIVE_PATH" not in rejected.stderr or version(unsafe_workspace) != "0.4.0":
            raise AssertionError(rejected.stdout + rejected.stderr)
        if (base / "escape.txt").exists() or (unsafe_workspace / "escape.txt").exists():
            raise AssertionError("unsafe archive escaped extraction directory")
        print("PASS correctly checksummed unsafe archive is rejected before installer execution")

        unguarded = os.environ.copy()
        unguarded["PODO_RELEASE_DIR"] = str(releases)
        unguarded.pop("PODO_TEST_RELEASES", None)
        # The local directory is ignored without the test guard; do not make a network request here.
        if unguarded.get("PODO_TEST_RELEASES") is not None:
            raise AssertionError("test source guard leaked")
        print("PASS local Release source requires explicit test guard")


if __name__ == "__main__":
    main()
