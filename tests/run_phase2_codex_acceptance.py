#!/usr/bin/env python3
"""Run a real Codex task in a marker-owned Desktop Podo Workspace."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "tools/install_local.py"
PRODUCT_VERSION = (REPO_ROOT / "product/.podo/VERSION").read_text(encoding="utf-8").strip()
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
TEST_PARENT = Path("/Users/hj/Desktop/podo-test-workspaces")
SUITE = "realpodo-phase2-codex-acceptance"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
MARKER = ".podo-phase2-test.json"
DECISION_MARKER = "DESKTOP_PHASE2_OK"


class AcceptanceFailure(Exception):
    pass


def assert_true(value: bool, detail: str) -> None:
    if not value:
        raise AcceptanceFailure(detail)


def marker_value(role: str) -> dict[str, str]:
    return {"managed_by": SUITE, "run_id": RUN_ID, "role": role}


def create_marked_child(role: str) -> Path:
    child = TEST_PARENT / f"{RUN_ID}-{role}"
    assert_true(child.parent.resolve() == TEST_PARENT.resolve(), "test child escaped Desktop parent")
    assert_true(not child.exists(), f"test child already exists: {child}")
    child.mkdir()
    (child / MARKER).write_text(
        json.dumps(marker_value(role), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return child


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def install(workspace: Path) -> None:
    result = run(
        [sys.executable, str(INSTALLER), "--workspace", str(workspace)],
        cwd=REPO_ROOT,
    )
    assert_true(result.returncode == 0, "installer failed: " + result.stdout + result.stderr)


def configure_workspace(workspace: Path) -> None:
    (workspace / "user_config.md").write_text(
        """# User Configuration

- Assistant name: 합성포도
- Personality: 차분하고 검증 가능한 사실만 말함
- Response style: 요청한 형식을 그대로 사용함

## Explicit Defaults

- 합성 진단에서는 파일을 수정하지 않는다.

## Allowed External Sources

- 없음.
""",
        encoding="utf-8",
    )
    (workspace / "state/phase-2-acceptance.md").write_text(
        f"""# Phase 2 Acceptance

Updated: 2026-07-15

## Current Decision

- {DECISION_MARKER}
""",
        encoding="utf-8",
    )


def context_hashes(workspace: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    roots = ("WORKSPACE_VERSION", "user_config.md", "events", "deltas", "state")
    for relative in roots:
        root = workspace / relative
        if root.is_file():
            hashes[relative] = hashlib.sha256(root.read_bytes()).hexdigest()
        elif root.is_dir():
            for path in sorted(root.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    name = path.relative_to(workspace).as_posix()
                    hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def configure_codex_home(codex_home: Path, workspace: Path) -> None:
    auth = Path.home() / ".codex/auth.json"
    assert_true(auth.is_file(), "existing Codex authentication is unavailable")
    (codex_home / "auth.json").symlink_to(auth)
    escaped = str(workspace.resolve()).replace("\\", "\\\\").replace('"', '\\"')
    (codex_home / "config.toml").write_text(
        f'[projects."{escaped}"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )


def evidence_blob(codex_home: Path, result: subprocess.CompletedProcess[str]) -> str:
    chunks = [result.stdout, result.stderr]
    for path in codex_home.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            if path.stat().st_size <= 10 * 1024 * 1024:
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def run_acceptance(workspace: Path, codex_home: Path) -> tuple[str, str]:
    git = run(["git", "init", "-q"], cwd=workspace)
    assert_true(git.returncode == 0, git.stderr)
    configure_codex_home(codex_home, workspace)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    prompt = (
        "Phase 2 synthetic acceptance다. 과거 Context가 필요하므로 현재 State에서 유효한 결정을 찾고, "
        "설치된 .podo/bin/podo version을 직접 실행해 확인해. 파일은 수정하지 마. "
        "마지막 답은 정확히 NAME=<비서 이름>;DECISION=<결정 marker>;VERSION=<제품 version> 한 줄만 써."
    )
    result = run(
        [
            str(CODEX),
            "--dangerously-bypass-hook-trust",
            "--cd",
            str(workspace),
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "never",
            "exec",
            "--json",
            prompt,
        ],
        cwd=workspace,
        env=env,
    )
    blob = evidence_blob(codex_home, result)
    expected = f"NAME=합성포도;DECISION={DECISION_MARKER};VERSION={PRODUCT_VERSION}"
    assert_true(expected in blob, "Codex policy/State/CLI evidence missing\n" + result.stdout[-4000:] + result.stderr[-4000:])
    pending = list((workspace / ".podo-work/inbox").glob("*/capture.json"))
    assert_true(len(pending) == 1, f"expected one Stop hook capture, found {len(pending)}")
    health = json.loads((workspace / ".podo-work/capture-health.json").read_text(encoding="utf-8"))
    assert_true(health.get("status") == "ready", f"capture health is not ready: {health}")
    return expected, "capture-ready"


def safe_cleanup(child: Path, role: str) -> None:
    resolved = child.resolve()
    assert_true(resolved.parent == TEST_PARENT.resolve(), f"cleanup target is not a direct child: {child}")
    marker = child / MARKER
    assert_true(marker.is_file() and not marker.is_symlink(), f"cleanup marker missing: {child}")
    try:
        actual = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceFailure(f"invalid cleanup marker at {child}: {error}") from error
    assert_true(actual == marker_value(role), f"cleanup marker mismatch: {child}")
    shutil.rmtree(child)


def main() -> None:
    assert_true(CODEX.is_file(), f"bundled Codex CLI is missing: {CODEX}")
    parent_created = not TEST_PARENT.exists()
    if TEST_PARENT.exists():
        assert_true(TEST_PARENT.is_dir(), "Desktop test parent is not a directory")
    TEST_PARENT.mkdir(exist_ok=True)
    children: list[tuple[Path, str]] = []
    try:
        workspace = create_marked_child("codex-workspace")
        children.append((workspace, "codex-workspace"))
        codex_home = create_marked_child("codex-home")
        children.append((codex_home, "codex-home"))
        install(workspace)
        configure_workspace(workspace)
        before = context_hashes(workspace)
        answer, hook = run_acceptance(workspace, codex_home)
        after = context_hashes(workspace)
        assert_true(after == before, "Codex task or failed guard changed user Context")
        print(f"PASS Codex answer {answer}")
        print(f"PASS Stop hook {hook}")
        print("PASS Context hashes unchanged")
    except (AcceptanceFailure, subprocess.TimeoutExpired) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        cleanup_failures: list[str] = []
        for child, role in reversed(children):
            if not child.exists():
                continue
            try:
                safe_cleanup(child, role)
            except AcceptanceFailure as error:
                cleanup_failures.append(str(error))
        if parent_created:
            try:
                TEST_PARENT.rmdir()
            except OSError:
                pass
        if cleanup_failures:
            raise AcceptanceFailure("; ".join(cleanup_failures))
    print("PASS Desktop Codex acceptance artifacts cleaned")


if __name__ == "__main__":
    main()
