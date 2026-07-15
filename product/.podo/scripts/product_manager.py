#!/usr/bin/env python3
"""Download and apply a verified Podo GitHub Release."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any


REPOSITORY = "hj-n/podo"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}/releases"
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
MAX_DOWNLOAD = 100 * 1024 * 1024


class ProductManagerError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def fail(code: str, detail: str) -> None:
    raise ProductManagerError(code, detail)


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


def read_url(url: str, limit: int) -> bytes:
    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            "30",
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            "X-GitHub-Api-Version: 2022-11-28",
            url,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        fail("E_RELEASE_DOWNLOAD", result.stderr.decode("utf-8", errors="replace").strip())
    raw = result.stdout
    if len(raw) > limit:
        fail("E_RELEASE_DOWNLOAD", "response exceeds size limit")
    return raw


def github_release(version: str | None) -> tuple[dict[str, Any], dict[str, str]]:
    url = f"{API_ROOT}/latest" if version is None else f"{API_ROOT}/tags/v{version}"
    try:
        value = json.loads(read_url(url, 2 * 1024 * 1024).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        fail("E_RELEASE_API", str(error))
    if not isinstance(value, dict) or value.get("draft") or value.get("prerelease"):
        fail("E_RELEASE_API", "Release is missing, draft or prerelease")
    tag = str(value.get("tag_name") or "")
    selected = tag.removeprefix("v")
    if not SEMVER_RE.fullmatch(selected) or (version is not None and selected != version):
        fail("E_RELEASE_API", f"unexpected Release tag: {tag}")
    assets: dict[str, str] = {}
    expected_asset_prefix = f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
    for asset in value.get("assets", []):
        if isinstance(asset, dict) and isinstance(asset.get("name"), str) and isinstance(asset.get("browser_download_url"), str):
            if not asset["browser_download_url"].startswith(expected_asset_prefix):
                fail("E_RELEASE_ASSET", f"asset URL escapes selected Release: {asset['name']}")
            assets[asset["name"]] = asset["browser_download_url"]
    return {"version": selected, "tag": tag, "body": str(value.get("body") or "")}, assets


def local_release(version: str | None) -> tuple[dict[str, Any], dict[str, str]]:
    if os.environ.get("PODO_TEST_RELEASES") != "1" or not os.environ.get("PODO_RELEASE_DIR"):
        fail("E_RELEASE_SOURCE", "local Release source requires explicit test guard")
    root = Path(os.environ["PODO_RELEASE_DIR"]).resolve()
    if version is None:
        try:
            version = (root / "latest").read_text(encoding="utf-8").strip()
        except OSError as error:
            fail("E_RELEASE_SOURCE", str(error))
    if not SEMVER_RE.fullmatch(version):
        fail("E_RELEASE_SOURCE", "local Release version is invalid")
    directory = root / f"v{version}"
    metadata = load_json(directory / "release.json", "E_RELEASE_SOURCE")
    assets = {path.name: path.as_uri() for path in directory.iterdir() if path.is_file()}
    return {"version": version, "tag": f"v{version}", "body": metadata.get("release_notes", "")}, assets


def discover_release(version: str | None) -> tuple[dict[str, Any], dict[str, str]]:
    if os.environ.get("PODO_TEST_RELEASES") == "1":
        return local_release(version)
    return github_release(version)


def download(url: str, target: Path, limit: int = MAX_DOWNLOAD) -> None:
    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            "60",
            "--output",
            str(target),
            url,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        fail("E_RELEASE_DOWNLOAD", result.stderr.decode("utf-8", errors="replace").strip())
    try:
        size = target.stat().st_size
    except OSError as error:
        fail("E_RELEASE_DOWNLOAD", str(error))
    if size > limit:
        target.unlink(missing_ok=True)
        fail("E_RELEASE_DOWNLOAD", "asset exceeds size limit")


def required_asset(assets: dict[str, str], name: str) -> str:
    value = assets.get(name)
    if not value:
        fail("E_RELEASE_ASSET", f"missing asset: {name}")
    return value


def validate_metadata(metadata: dict[str, Any], version: str, archive_name: str) -> None:
    expected = {
        "product_version": version,
        "tag": f"v{version}",
        "repository": REPOSITORY,
        "archive_asset": archive_name,
        "checksum_asset": f"{archive_name}.sha256",
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            fail("E_RELEASE_IDENTITY", f"{key} does not match selected Release")
    if not SHA_RE.fullmatch(str(metadata.get("archive_sha256") or "")):
        fail("E_RELEASE_IDENTITY", "archive SHA-256 is invalid")


def checksum_value(path: Path, archive_name: str) -> str:
    try:
        line = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        fail("E_CHECKSUM_FORMAT", str(error))
    parts = line.split()
    if len(parts) != 2 or parts[1] != archive_name or not SHA_RE.fullmatch(parts[0]):
        fail("E_CHECKSUM_FORMAT", path.name)
    return parts[0]


def safe_extract(archive: Path, destination: Path, version: str) -> Path:
    root_name = f"podo-{version}"
    destination.mkdir()
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            for member in members:
                path = Path(member.name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                    or path.parts[0] != root_name
                    or member.issym()
                    or member.islnk()
                    or not (member.isfile() or member.isdir())
                ):
                    fail("E_ARCHIVE_PATH", member.name)
            bundle.extractall(destination, filter="data")
    except ProductManagerError:
        raise
    except (OSError, tarfile.TarError) as error:
        fail("E_ARCHIVE_INVALID", str(error))
    package = destination / root_name
    if not package.is_dir() or not (package / "install.py").is_file():
        fail("E_ARCHIVE_INVALID", "standalone installer is missing")
    return package


def prepare_release(version: str | None, directory: Path) -> tuple[dict[str, Any], dict[str, Any], Path, str]:
    """Download, verify, and extract a Release into a caller-owned temporary directory."""
    if version is not None and not SEMVER_RE.fullmatch(version):
        fail("E_VERSION", "--version must be MAJOR.MINOR.PATCH")
    selected, assets = discover_release(version)
    selected_version = selected["version"]
    archive_name = f"podo-{selected_version}.tar.gz"
    archive = directory / archive_name
    checksum = directory / f"{archive_name}.sha256"
    metadata_path = directory / "release.json"
    download(required_asset(assets, archive_name), archive)
    download(required_asset(assets, checksum.name), checksum, 4096)
    download(required_asset(assets, "release.json"), metadata_path, 1024 * 1024)
    metadata = load_json(metadata_path, "E_RELEASE_IDENTITY")
    validate_metadata(metadata, selected_version, archive_name)
    expected = checksum_value(checksum, archive_name)
    actual = sha256(archive)
    if expected != actual or metadata["archive_sha256"] != actual:
        fail("E_CHECKSUM_MISMATCH", archive_name)
    package = safe_extract(archive, directory / "extracted", selected_version)
    internal = load_json(package / "release.json", "E_RELEASE_IDENTITY")
    if internal != {key: value for key, value in metadata.items() if key != "archive_sha256"}:
        fail("E_RELEASE_IDENTITY", "internal and external metadata differ")
    return selected, metadata, package, actual


def update_workspace(root: Path, version: str | None) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="podo-update-") as temporary:
        directory = Path(temporary)
        selected, _metadata, package, actual = prepare_release(version, directory)
        selected_version = selected["version"]
        command = [
            sys.executable,
            str(package / "install.py"),
            "--workspace",
            str(root),
            "--source-kind",
            "github" if os.environ.get("PODO_TEST_RELEASES") != "1" else "local-release",
            "--source-repository",
            REPOSITORY,
            "--source-tag",
            f"v{selected_version}",
            "--archive-sha256",
            actual,
            "--update",
        ]
        return subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
