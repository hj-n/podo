#!/usr/bin/env python3
"""Build deterministic Podo GitHub Release assets from a product source tree."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCT = REPO_ROOT / "product"
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
EXCLUDED_NAMES = {"__pycache__", "install-manifest.json"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


class BuildError(Exception):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, value: str, mode: int = 0o644) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(mode)


def source_commit(value: str | None) -> str:
    if value is None:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode:
            raise BuildError(result.stderr.strip() or "cannot determine source commit")
        value = result.stdout.strip()
    if not COMMIT_RE.fullmatch(value):
        raise BuildError("source commit must be a full lowercase Git commit")
    return value


def product_version(product: Path) -> str:
    try:
        value = (product / ".podo/VERSION").read_text(encoding="utf-8").strip()
    except OSError as error:
        raise BuildError(f"cannot read product version: {error}") from error
    if not SEMVER_RE.fullmatch(value):
        raise BuildError("product version must be MAJOR.MINOR.PATCH")
    return value


def compatible_workspace_versions(product: Path, version: str) -> list[int]:
    try:
        contract = json.loads((product / ".podo/contracts/versions.json").read_text(encoding="utf-8"))
        values = contract["compatible"][version]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise BuildError(f"cannot read version compatibility: {error}") from error
    if not isinstance(values, list) or not values or any(not isinstance(value, int) or value < 1 for value in values):
        raise BuildError("compatible Workspace versions must be positive integers")
    return sorted(set(values))


def validate_source(product: Path) -> None:
    for relative in ("AGENTS.podo.md", ".codex/hooks.json", ".podo/VERSION", ".podo/bin/podo"):
        path = product / relative
        if path.is_symlink() or not path.is_file():
            raise BuildError(f"required regular product file is missing: {relative}")
    for path in product.rglob("*"):
        if path.is_symlink():
            raise BuildError(f"product source contains symlink: {path.relative_to(product)}")


def ignore_product(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in EXCLUDED_NAMES or Path(name).suffix in EXCLUDED_SUFFIXES
    }


INSTALL_LOADER = '''#!/usr/bin/env python3
"""Standalone entrypoint embedded in a Podo Release archive."""
from __future__ import annotations
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_ROOT / "product/.podo/scripts"))
from product_install import package_main  # noqa: E402

if __name__ == "__main__":
    package_main(PACKAGE_ROOT)
'''


def bootstrap(version: str) -> str:
    return f'''#!/bin/sh
set -eu

REPOSITORY="hj-n/podo"
DEFAULT_VERSION="{version}"
VERSION="${{PODO_VERSION:-$DEFAULT_VERSION}}"
WORKSPACE="${{1:-$HOME/podo-home}}"
ASSET="podo-$VERSION.tar.gz"
BASE="https://github.com/$REPOSITORY/releases/download/v$VERSION"
SOURCE_KIND="github"
if [ "${{PODO_TEST_RELEASES:-}}" = "1" ] && [ -n "${{PODO_RELEASE_BASE:-}}" ]; then
  BASE="${{PODO_RELEASE_BASE%/}}"
  SOURCE_KIND="local-release"
fi
TMP="$(mktemp -d "${{TMPDIR:-/tmp}}/podo-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

curl -fsSL "$BASE/$ASSET" -o "$TMP/$ASSET"
curl -fsSL "$BASE/$ASSET.sha256" -o "$TMP/$ASSET.sha256"

EXPECTED="$(awk -v name="$ASSET" '$2 == name {{print $1}}' "$TMP/$ASSET.sha256")"
if [ "${{#EXPECTED}}" -ne 64 ]; then
  echo "ERROR E_CHECKSUM_FORMAT invalid checksum length" >&2
  exit 1
fi
case "$EXPECTED" in
  *[!0-9a-f]*) echo "ERROR E_CHECKSUM_FORMAT invalid checksum value" >&2; exit 1 ;;
esac
if command -v shasum >/dev/null 2>&1; then
  ACTUAL="$(shasum -a 256 "$TMP/$ASSET" | awk '{{print $1}}')"
elif command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$TMP/$ASSET" | awk '{{print $1}}')"
else
  echo "ERROR E_PREREQUISITE shasum or sha256sum is required" >&2
  exit 1
fi
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "ERROR E_CHECKSUM_MISMATCH $ASSET" >&2
  exit 1
fi

python3 - "$TMP/$ASSET" "$TMP/extracted" <<'PY'
import os, sys, tarfile
from pathlib import Path
archive, destination = Path(sys.argv[1]), Path(sys.argv[2])
destination.mkdir()
with tarfile.open(archive, "r:gz") as bundle:
    for member in bundle.getmembers():
        path = Path(member.name)
        if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
            raise SystemExit("ERROR E_ARCHIVE_PATH unsafe archive member")
        target = destination / path
        target.resolve().relative_to(destination.resolve())
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            target.chmod(member.mode & 0o777)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise SystemExit("ERROR E_ARCHIVE_INVALID unreadable member")
            with source, target.open("wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            target.chmod(member.mode & 0o777)
PY

python3 "$TMP/extracted/podo-$VERSION/install.py" \
  --workspace "$WORKSPACE" \
  --source-kind "$SOURCE_KIND" \
  --source-repository "$REPOSITORY" \
  --source-tag "v$VERSION" \
  --archive-sha256 "$ACTUAL"
'''


def normalized_tar(stage: Path, archive: Path, root_name: str) -> None:
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as bundle:
                paths = [stage] + sorted(stage.rglob("*"), key=lambda path: path.relative_to(stage).as_posix())
                for path in paths:
                    relative = Path(root_name) if path == stage else Path(root_name) / path.relative_to(stage)
                    info = bundle.gettarinfo(str(path), arcname=relative.as_posix())
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    if info.isdir():
                        info.mode = 0o755
                        bundle.addfile(info)
                    elif info.isfile():
                        info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        with path.open("rb") as handle:
                            bundle.addfile(info, handle)
                    else:
                        raise BuildError(f"unsupported package entry: {path}")


def build(product: Path, output: Path, commit: str, notes: str) -> dict[str, str]:
    product = product.resolve()
    output = output.resolve()
    validate_source(product)
    version = product_version(product)
    compatible = compatible_workspace_versions(product, version)
    if output.exists() and any(output.iterdir()):
        raise BuildError(f"output must be absent or empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    root_name = f"podo-{version}"
    archive_name = f"{root_name}.tar.gz"
    identity = {
        "release_contract_version": 1,
        "product_version": version,
        "tag": f"v{version}",
        "repository": "hj-n/podo",
        "source_commit": commit,
        "workspace_versions": compatible,
        "archive_asset": archive_name,
        "checksum_asset": f"{archive_name}.sha256",
        "release_notes": notes.strip(),
    }
    with tempfile.TemporaryDirectory(prefix="podo-release-stage-") as temporary:
        stage = Path(temporary) / root_name
        stage.mkdir()
        shutil.copytree(product, stage / "product", ignore=ignore_product)
        write_text(stage / "install.py", INSTALL_LOADER, 0o755)
        write_text(stage / "release.json", json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        archive = output / archive_name
        normalized_tar(stage, archive, root_name)
    digest = sha256(archive)
    write_text(output / f"{archive_name}.sha256", f"{digest}  {archive_name}\n")
    external = {**identity, "archive_sha256": digest}
    write_text(output / "release.json", json.dumps(external, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(output / "install.sh", bootstrap(version), 0o755)
    return {"version": version, "archive": archive_name, "sha256": digest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--product", type=Path, default=DEFAULT_PRODUCT)
    parser.add_argument("--source-commit")
    parser.add_argument("--notes-file", type=Path)
    args = parser.parse_args()
    notes = (
        args.notes_file.read_text(encoding="utf-8")
        if args.notes_file is not None
        else f"Podo {product_version(args.product)} release."
    )
    try:
        result = build(args.product, args.output, source_commit(args.source_commit), notes)
    except (BuildError, OSError) as error:
        print(f"ERROR E_RELEASE_BUILD {error}", file=os.sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
