#!/usr/bin/env python3
"""Exercise standalone Release package installation and rollback."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_release.py"
FAILURE_POINTS = ("after-staging", "after-product", "after-user-init", "before-final-validation")


def run(args: list[str], **kwargs):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_and_extract(base: Path) -> tuple[Path, dict]:
    assets = base / "assets"
    result = run([sys.executable, str(BUILDER), "--output", str(assets)], cwd=ROOT)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    metadata = json.loads((assets / "release.json").read_text(encoding="utf-8"))
    extracted = base / "extracted"
    with tarfile.open(assets / metadata["archive_asset"], "r:gz") as bundle:
        bundle.extractall(extracted, filter="data")
    return extracted / f"podo-{metadata['product_version']}", metadata


def install(package: Path, metadata: dict, workspace: Path, env: dict[str, str] | None = None):
    return run(
        [
            sys.executable,
            str(package / "install.py"),
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
        ],
        cwd=package,
        env=env,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase6-package-install-") as temporary:
        base = Path(temporary)
        package, metadata = build_and_extract(base)

        fresh = base / "fresh"
        first = install(package, metadata, fresh)
        if first.returncode or "INSTALLED" not in first.stdout:
            raise AssertionError(first.stdout + first.stderr)
        manifest = json.loads((fresh / ".podo/install-manifest.json").read_text(encoding="utf-8"))
        if manifest["manifest_version"] != 2 or manifest["source"]["archive_sha256"] != metadata["archive_sha256"]:
            raise AssertionError(str(manifest))
        version = run([str(fresh / ".podo/bin/podo"), "version"], cwd=fresh)
        if version.returncode or metadata["product_version"] not in version.stdout:
            raise AssertionError(version.stdout + version.stderr)
        repeated = install(package, metadata, fresh)
        if repeated.returncode or "ALREADY_INSTALLED" not in repeated.stdout:
            raise AssertionError(repeated.stdout + repeated.stderr)
        print("PASS standalone package fresh install and idempotent reinstall")

        existing = base / "existing"
        existing.mkdir()
        user_config = existing / "user_config.md"
        user_config.write_text(
            """# User Configuration

- Assistant name: USER_OWNED_PACKAGE_CONFIG
- Personality: synthetic
- Response style: concise
""",
            encoding="utf-8",
        )
        user_config.chmod(0o600)
        state = existing / "state"
        state.mkdir()
        state_file = state / "personal.md"
        state_file.write_text(
            "# Personal\n\nUpdated: 2026-07-15\n\n## Current Context\n\nUSER_OWNED_PACKAGE_STATE\n",
            encoding="utf-8",
        )
        before = {"config": digest(user_config), "state": digest(state_file), "mode": user_config.stat().st_mode & 0o777}
        result = install(package, metadata, existing)
        after = {"config": digest(user_config), "state": digest(state_file), "mode": user_config.stat().st_mode & 0o777}
        if result.returncode or before != after:
            raise AssertionError(result.stdout + result.stderr + str((before, after)))
        print("PASS package install preserves pre-existing user-owned bytes and mode")

        partial = base / "partial"
        partial.mkdir()
        (partial / "AGENTS.md").write_text("collision\n", encoding="utf-8")
        rejected = install(package, metadata, partial)
        if rejected.returncode == 0 or "E_PARTIAL_PRODUCT" not in rejected.stderr:
            raise AssertionError(rejected.stdout + rejected.stderr)
        symlinked = base / "symlinked"
        symlinked.mkdir()
        (symlinked / "state").symlink_to(existing / "state")
        rejected = install(package, metadata, symlinked)
        if rejected.returncode == 0 or "E_SYMLINK" not in rejected.stderr:
            raise AssertionError(rejected.stdout + rejected.stderr)
        print("PASS package preflight rejects partial product and managed symlink")

        for index, point in enumerate(FAILURE_POINTS):
            workspace = base / f"failure-{index}"
            env = os.environ.copy()
            env.update({"PODO_TEST_INSTALL_FAILURES": "1", "PODO_TEST_INSTALL_FAIL_AT": point})
            failed = install(package, metadata, workspace, env)
            if failed.returncode == 0 or "E_INJECTED_FAILURE" not in failed.stderr:
                raise AssertionError(f"{point}: {failed.stdout}{failed.stderr}")
            if workspace.exists() and any(workspace.iterdir()):
                raise AssertionError(f"{point} left partial Workspace: {list(workspace.iterdir())}")
        print("PASS package install failure injection rolls back every apply boundary")


if __name__ == "__main__":
    main()
