#!/usr/bin/env python3
"""Exercise Phase 2 installation only in marker-owned Desktop workspaces."""

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


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "tools/install_local.py"
TEST_PARENT = Path("/Users/hj/Desktop/podo-test-workspaces")
SUITE = "realpodo-phase2-installation"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
MARKER = ".podo-phase2-test.json"


class TestFailure(Exception):
    pass


def assert_true(value: bool, detail: str) -> None:
    if not value:
        raise TestFailure(detail)


def command(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def install(workspace: Path, fail_at: str | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(INSTALLER), "--workspace", str(workspace)]
    if fail_at:
        args.extend(("--fail-at", fail_at))
    return command(*args, cwd=REPO_ROOT)


def marker_value(scenario: str) -> dict[str, str]:
    return {"managed_by": SUITE, "run_id": RUN_ID, "scenario": scenario}


def write_marker(workspace: Path, scenario: str) -> None:
    (workspace / MARKER).write_text(
        json.dumps(marker_value(scenario), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def make_workspace(scenario: str, existing: bool = True) -> Path:
    workspace = TEST_PARENT / f"{RUN_ID}-{scenario}"
    assert_true(workspace.parent.resolve() == TEST_PARENT.resolve(), "test child escaped Desktop parent")
    assert_true(not workspace.exists(), f"test child already exists: {workspace}")
    if existing:
        workspace.mkdir()
        write_marker(workspace, scenario)
    return workspace


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_snapshot(root: Path) -> dict[str, tuple[str, str, int]]:
    if not root.exists():
        return {}
    snapshot: dict[str, tuple[str, str, int]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            snapshot[relative] = ("symlink", os.readlink(path), mode)
        elif path.is_file():
            snapshot[relative] = ("file", sha256(path), mode)
        elif path.is_dir():
            snapshot[relative] = ("dir", "", mode)
    return snapshot


def expect_failure(result: subprocess.CompletedProcess[str], code: str) -> None:
    assert_true(result.returncode != 0, f"expected {code}, command succeeded: {result.stdout}")
    assert_true(code in result.stdout, f"expected {code}, got: {result.stdout}")


def valid_user_config() -> str:
    return """# User Configuration

- Assistant name: 합성포도
- Personality: 차분하고 명확함
- Response style: 결과 우선

## Explicit Defaults

- 합성 데이터만 사용한다.
"""


def test_fresh_idempotent(workspaces: list[tuple[Path, str]]) -> None:
    scenario = "fresh-idempotent"
    workspace = make_workspace(scenario, existing=False)
    result = install(workspace)
    assert_true(result.returncode == 0 and "INSTALLED" in result.stdout, result.stdout)
    write_marker(workspace, scenario)
    workspaces.append((workspace, scenario))

    cli = workspace / ".podo/bin/podo"
    assert_true(os.access(cli, os.X_OK), "installed podo CLI is not executable")
    version = command(str(cli), "version", cwd=TEST_PARENT)
    assert_true(version.returncode == 0 and "Podo 0.1.0 (Workspace 1)" in version.stdout, version.stdout)
    validation = command(str(cli), "validate", cwd=TEST_PARENT)
    assert_true(validation.returncode == 0 and "mode=context-present" in validation.stdout, validation.stdout)
    synthetic = command(str(cli), "validate", "--mode", "synthetic-fixture", cwd=TEST_PARENT)
    expect_failure(synthetic, "E_EVENT_MISSING")
    hook = command(str(cli), "hook-status", cwd=TEST_PARENT)
    assert_true(hook.returncode == 0, hook.stdout)
    assert_true("hook-installed: yes" in hook.stdout, hook.stdout)
    assert_true("hook-trust: unverified" in hook.stdout, hook.stdout)
    assert_true("capture: guard-not-ready" in hook.stdout, hook.stdout)

    before = tree_snapshot(workspace)
    second = install(workspace)
    assert_true(second.returncode == 0 and "ALREADY_INSTALLED" in second.stdout, second.stdout)
    assert_true(tree_snapshot(workspace) == before, "same-version reinstall changed the Workspace")
    print("PASS fresh install, installed CLI and idempotent reinstall")


def test_existing_preserved(workspaces: list[tuple[Path, str]]) -> None:
    scenario = "existing-user-data"
    workspace = make_workspace(scenario)
    config = workspace / "user_config.md"
    config.write_text(valid_user_config(), encoding="utf-8")
    config.chmod(0o600)
    version = workspace / "WORKSPACE_VERSION"
    version.write_text("1\n", encoding="utf-8")
    version.chmod(0o640)
    note = workspace / "personal-note.txt"
    note.write_text("synthetic existing bytes\n", encoding="utf-8")
    note.chmod(0o600)
    before = {path.name: (sha256(path), stat.S_IMODE(path.stat().st_mode)) for path in (config, version, note)}
    result = install(workspace)
    assert_true(result.returncode == 0, result.stdout)
    workspaces.append((workspace, scenario))
    after = {path.name: (sha256(path), stat.S_IMODE(path.stat().st_mode)) for path in (config, version, note)}
    assert_true(after == before, "existing user-owned bytes or permissions changed")
    print("PASS existing user-owned bytes and permissions preserved")


def test_preflight_failures(workspaces: list[tuple[Path, str]]) -> None:
    cases: list[tuple[str, str]] = []

    workspace = make_workspace("partial-product")
    (workspace / "AGENTS.md").write_text("different product\n", encoding="utf-8")
    workspaces.append((workspace, "partial-product"))
    before = tree_snapshot(workspace)
    result = install(workspace)
    expect_failure(result, "E_PARTIAL_PRODUCT")
    assert_true(tree_snapshot(workspace) == before, "partial product failure changed target")
    cases.append(("partial-product", "E_PARTIAL_PRODUCT"))

    workspace = make_workspace("modified-product", existing=False)
    result = install(workspace)
    assert_true(result.returncode == 0, result.stdout)
    write_marker(workspace, "modified-product")
    workspaces.append((workspace, "modified-product"))
    (workspace / "AGENTS.md").write_text("modified after install\n", encoding="utf-8")
    before = tree_snapshot(workspace)
    result = install(workspace)
    expect_failure(result, "E_PRODUCT_COLLISION")
    assert_true(tree_snapshot(workspace) == before, "product collision changed target")
    cases.append(("modified-product", "E_PRODUCT_COLLISION"))

    workspace = make_workspace("incompatible-workspace")
    (workspace / "WORKSPACE_VERSION").write_text("2\n", encoding="utf-8")
    workspaces.append((workspace, "incompatible-workspace"))
    before = tree_snapshot(workspace)
    result = install(workspace)
    expect_failure(result, "E_WORKSPACE_INCOMPATIBLE")
    assert_true(tree_snapshot(workspace) == before, "version failure changed target")
    cases.append(("incompatible-workspace", "E_WORKSPACE_INCOMPATIBLE"))

    workspace = make_workspace("managed-symlink")
    (workspace / "real-state").mkdir()
    (workspace / "state").symlink_to("real-state", target_is_directory=True)
    workspaces.append((workspace, "managed-symlink"))
    before = tree_snapshot(workspace)
    result = install(workspace)
    expect_failure(result, "E_SYMLINK")
    assert_true(tree_snapshot(workspace) == before, "symlink failure changed target")
    cases.append(("managed-symlink", "E_SYMLINK"))

    workspace = make_workspace("path-type")
    (workspace / "events").write_text("not a directory\n", encoding="utf-8")
    workspaces.append((workspace, "path-type"))
    before = tree_snapshot(workspace)
    result = install(workspace)
    expect_failure(result, "E_PATH_TYPE")
    assert_true(tree_snapshot(workspace) == before, "path type failure changed target")
    cases.append(("path-type", "E_PATH_TYPE"))

    print("PASS preflight failures " + ", ".join(f"{name}:{code}" for name, code in cases))


def test_failure_rollback(workspaces: list[tuple[Path, str]]) -> None:
    points = ("after-staging", "after-product", "after-user-init", "before-final-validation")
    for point in points:
        missing = make_workspace(f"failure-missing-{point}", existing=False)
        result = install(missing, point)
        expect_failure(result, "E_INJECTED_FAILURE")
        assert_true(not missing.exists(), f"fresh failure left target behind at {point}")

        scenario = f"failure-existing-{point}"
        existing = make_workspace(scenario)
        workspaces.append((existing, scenario))
        note = existing / "unknown-existing.txt"
        note.write_text("must survive rollback\n", encoding="utf-8")
        note.chmod(0o600)
        before = tree_snapshot(existing)
        result = install(existing, point)
        expect_failure(result, "E_INJECTED_FAILURE")
        assert_true(tree_snapshot(existing) == before, f"existing rollback mismatch at {point}")
    print("PASS failure injection rollback at " + ", ".join(points))


def safe_cleanup(workspace: Path, scenario: str) -> None:
    parent = TEST_PARENT.resolve()
    resolved = workspace.resolve()
    assert_true(resolved.parent == parent, f"cleanup target is not a direct child: {workspace}")
    marker = workspace / MARKER
    assert_true(marker.is_file() and not marker.is_symlink(), f"cleanup marker missing: {workspace}")
    try:
        actual = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TestFailure(f"invalid cleanup marker at {workspace}: {error}") from error
    assert_true(actual == marker_value(scenario), f"cleanup marker mismatch: {workspace}")
    shutil.rmtree(workspace)


def cleanup(workspaces: list[tuple[Path, str]], parent_created: bool) -> None:
    failures: list[str] = []
    for workspace, scenario in reversed(workspaces):
        if not workspace.exists():
            continue
        try:
            safe_cleanup(workspace, scenario)
        except TestFailure as error:
            failures.append(str(error))
    if parent_created:
        try:
            TEST_PARENT.rmdir()
        except OSError:
            pass
    if failures:
        raise TestFailure("; ".join(failures))


def main() -> None:
    parent_created = not TEST_PARENT.exists()
    if TEST_PARENT.exists() and not TEST_PARENT.is_dir():
        raise SystemExit(f"FAIL Desktop test parent is not a directory: {TEST_PARENT}")
    TEST_PARENT.mkdir(exist_ok=True)
    workspaces: list[tuple[Path, str]] = []
    try:
        test_fresh_idempotent(workspaces)
        test_existing_preserved(workspaces)
        test_preflight_failures(workspaces)
        test_failure_rollback(workspaces)
    except TestFailure as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        try:
            cleanup(workspaces, parent_created)
        except TestFailure as error:
            print(f"CLEANUP_BLOCKED {error}", file=sys.stderr)
            raise
    print("PASS Desktop marker-owned workspaces cleaned")


if __name__ == "__main__":
    main()
