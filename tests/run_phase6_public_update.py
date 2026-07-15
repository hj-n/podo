#!/usr/bin/env python3
"""Verify anonymous GitHub install, latest update, and exact rollback."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path


TEST_PARENT = Path("/Users/hj/Desktop/podo-test-workspaces")
SUITE = "realpodo-phase6-public-update"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
CONTAINER = TEST_PARENT / f"{RUN_ID}-public-update"
MARKER = ".podo-phase6-public-update-test.json"
FROM_VERSION = "0.5.2"
TO_VERSION = "0.5.3"
REPOSITORY = "https://github.com/hj-n/podo"


class AcceptanceFailure(Exception):
    pass


def assert_true(value: bool, detail: str) -> None:
    if not value:
        raise AcceptanceFailure(detail)


def run(args: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def manifest(workspace: Path) -> dict:
    return json.loads((workspace / ".podo/install-manifest.json").read_text(encoding="utf-8"))


def product_version(workspace: Path) -> str:
    return (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip()


def snapshot(workspace: Path, paths: list[str]) -> dict[str, tuple[str, int]]:
    values: dict[str, tuple[str, int]] = {}
    for relative in paths:
        path = workspace / relative
        values[relative] = (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            stat.S_IMODE(path.stat().st_mode),
        )
    return values


def safe_cleanup() -> None:
    assert_true(CONTAINER.resolve().parent == TEST_PARENT.resolve(), f"unsafe cleanup target: {CONTAINER}")
    marker = CONTAINER / MARKER
    expected = {"managed_by": SUITE, "run_id": RUN_ID}
    assert_true(marker.is_file() and not marker.is_symlink(), f"cleanup marker missing: {CONTAINER}")
    assert_true(json.loads(marker.read_text(encoding="utf-8")) == expected, "cleanup marker mismatch")
    shutil.rmtree(CONTAINER)


def main() -> None:
    parent_created = not TEST_PARENT.exists()
    if TEST_PARENT.exists():
        assert_true(TEST_PARENT.is_dir(), "Desktop test parent is not a directory")
    TEST_PARENT.mkdir(exist_ok=True)
    assert_true(not CONTAINER.exists(), f"test container already exists: {CONTAINER}")
    CONTAINER.mkdir()
    (CONTAINER / MARKER).write_text(
        json.dumps({"managed_by": SUITE, "run_id": RUN_ID}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    workspace = CONTAINER / "workspace with space"
    try:
        installer = CONTAINER / f"install-v{FROM_VERSION}.sh"
        downloaded = run(
            [
                "curl",
                "-fsSL",
                "-o",
                str(installer),
                f"{REPOSITORY}/releases/download/v{FROM_VERSION}/install.sh",
            ],
            cwd=CONTAINER,
        )
        assert_true(downloaded.returncode == 0, downloaded.stderr)
        installed = run(["sh", str(installer), str(workspace)], cwd=CONTAINER)
        assert_true(installed.returncode == 0, installed.stdout + installed.stderr)
        assert_true(product_version(workspace) == FROM_VERSION, installed.stdout)
        assert_true(manifest(workspace)["source"]["tag"] == f"v{FROM_VERSION}", str(manifest(workspace)))
        print(f"PASS anonymous GitHub bootstrap installs v{FROM_VERSION}")

        sentinels = {
            "user_config.md": (
                "# User Configuration\n\n"
                "- Assistant name: 공개검증포도\n"
                "- Personality: 차분한 합성 테스트 비서\n"
                "- Response style: 핵심만 간결하게 답함\n"
            ),
            ".podo-work/user-sentinel.txt": "WORK_SENTINEL\n",
            ".podo-backups/user-sentinel.txt": "BACKUP_SENTINEL\n",
            "state/public-test.md": (
                "# Synthetic State\n\n"
                "Updated: 2026-07-15\n\n"
                "## Current Context\n\nPUBLIC_UPDATE_SENTINEL\n"
            ),
        }
        for relative, content in sentinels.items():
            path = workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            path.chmod(0o640)
        before = snapshot(workspace, list(sentinels))

        updated = run([str(workspace / ".podo/bin/podo"), "update"], cwd=workspace)
        assert_true(updated.returncode == 0, updated.stdout + updated.stderr)
        assert_true(product_version(workspace) == TO_VERSION, updated.stdout)
        assert_true(manifest(workspace)["source"]["tag"] == f"v{TO_VERSION}", str(manifest(workspace)))
        assert_true("Start a new Codex task" in updated.stdout, updated.stdout)
        assert_true(snapshot(workspace, list(sentinels)) == before, "latest update changed user-owned files")
        print(f"PASS public latest update reaches v{TO_VERSION} and preserves user files")

        rolled_back = run(
            [str(workspace / ".podo/bin/podo"), "update", "--version", FROM_VERSION],
            cwd=workspace,
        )
        assert_true(rolled_back.returncode == 0, rolled_back.stdout + rolled_back.stderr)
        assert_true(product_version(workspace) == FROM_VERSION, rolled_back.stdout)
        assert_true(manifest(workspace)["source"]["tag"] == f"v{FROM_VERSION}", str(manifest(workspace)))
        assert_true("ROLLED_BACK" in rolled_back.stdout, rolled_back.stdout)
        assert_true(snapshot(workspace, list(sentinels)) == before, "rollback changed user-owned files")
        validated = run([str(workspace / ".podo/bin/podo"), "validate"], cwd=workspace)
        assert_true(validated.returncode == 0, validated.stdout + validated.stderr)
        print(f"PASS exact public rollback returns to v{FROM_VERSION} with a valid Workspace")
    except (AcceptanceFailure, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        if CONTAINER.exists():
            safe_cleanup()
        if parent_created:
            try:
                TEST_PARENT.rmdir()
            except OSError:
                pass
    print("PASS public distribution Desktop artifacts cleaned")


if __name__ == "__main__":
    main()
