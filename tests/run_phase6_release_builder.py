#!/usr/bin/env python3
"""Verify deterministic, product-only Podo Release assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_release.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--output", str(output)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def tree(root: Path) -> dict[str, str]:
    return {path.name: sha256(path) for path in sorted(root.iterdir()) if path.is_file()}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase6-release-") as temporary:
        base = Path(temporary)
        first, second = base / "first", base / "second"
        build(first)
        build(second)
        if tree(first) != tree(second):
            raise AssertionError(f"release builds differ: {tree(first)} != {tree(second)}")
        metadata = json.loads((first / "release.json").read_text(encoding="utf-8"))
        archive = first / metadata["archive_asset"]
        checksum = (first / metadata["checksum_asset"]).read_text(encoding="utf-8").strip()
        if checksum != f"{sha256(archive)}  {archive.name}" or metadata["archive_sha256"] != sha256(archive):
            raise AssertionError("release checksum identity mismatch")
        if metadata["tag"] != f"v{metadata['product_version']}" or metadata["workspace_versions"] != [1]:
            raise AssertionError(str(metadata))

        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            names = [member.name for member in members]
            prefix = f"podo-{metadata['product_version']}/"
            if any(member.issym() or member.islnk() for member in members):
                raise AssertionError("release contains a link")
            if any("__pycache__" in name or name.endswith((".pyc", ".pyo", "install-manifest.json")) for name in names):
                raise AssertionError("release contains excluded generated files")
            if not {
                prefix + "install.py",
                prefix + "release.json",
                prefix + "product/AGENTS.podo.md",
                prefix + "product/.codex/hooks.json",
                prefix + "product/.podo/VERSION",
            }.issubset(set(names)):
                raise AssertionError("release is missing required product entries")
            forbidden = (
                prefix + "events/",
                prefix + "deltas/",
                prefix + "state/",
                prefix + "user_config.md",
                prefix + "dev_docs/",
                prefix + ".git/",
            )
            if any(name.startswith(forbidden) for name in names):
                raise AssertionError("release contains development or user Context")
            internal = json.loads(bundle.extractfile(prefix + "release.json").read().decode("utf-8"))
            if internal != {key: value for key, value in metadata.items() if key != "archive_sha256"}:
                raise AssertionError("internal and external release identities differ")
        if not (first / "install.sh").stat().st_mode & 0o111:
            raise AssertionError("bootstrap is not executable")
        print(f"PASS deterministic product-only Release {metadata['product_version']} {sha256(archive)}")


if __name__ == "__main__":
    main()
