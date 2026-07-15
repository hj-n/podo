#!/usr/bin/env python3
"""Verify explicit-only product updates across real Codex tasks."""

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


CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
TEST_PARENT = Path("/Users/hj/Desktop/podo-test-workspaces")
SUITE = "realpodo-phase6-codex-update"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
CONTAINER = TEST_PARENT / f"{RUN_ID}-codex-update"
MARKER = ".podo-phase6-codex-update-test.json"
FROM_VERSION = "0.5.2"
TO_VERSION = "0.5.3"
REPOSITORY = "https://github.com/hj-n/podo"


class AcceptanceFailure(Exception):
    pass


def assert_true(value: bool, detail: str) -> None:
    if not value:
        raise AcceptanceFailure(detail)


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 600,
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


def install_public(workspace: Path) -> None:
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


def configure(workspace: Path, codex_home: Path) -> dict[str, str]:
    (workspace / "user_config.md").write_text(
        """# User Configuration

- Assistant name: 배포검증포도
- Personality: 차분하고 확인된 제품 상태만 보고함
- Response style: 요청된 acceptance marker와 핵심 결과를 간결하게 답함

## Explicit Defaults

- 합성 acceptance 데이터만 사용한다.
- 명시적 요청 없이는 제품 update나 rollback을 실행하지 않는다.

## Allowed External Sources

- Podo public GitHub Release
""",
        encoding="utf-8",
    )
    state = workspace / "state/user-sentinel.md"
    state.write_text(
        "# Product Acceptance\n\nUpdated: 2026-07-15\n\n"
        "## Current Context\n\nCODEX_UPDATE_USER_SENTINEL\n",
        encoding="utf-8",
    )
    backup = workspace / ".podo-backups/user-sentinel.txt"
    backup.write_text("CODEX_UPDATE_BACKUP_SENTINEL\n", encoding="utf-8")
    for path in (workspace / "user_config.md", state, backup):
        path.chmod(0o640)

    initialized = run(["git", "init", "-q"], cwd=workspace)
    assert_true(initialized.returncode == 0, initialized.stderr)
    auth = Path.home() / ".codex/auth.json"
    assert_true(auth.is_file(), "Codex authentication is unavailable")
    codex_home.mkdir()
    (codex_home / "auth.json").symlink_to(auth)
    escaped = str(workspace.resolve()).replace("\\", "\\\\").replace('"', '\\"')
    (codex_home / "config.toml").write_text(
        f'[projects."{escaped}"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    return env


def codex_task(workspace: Path, env: dict[str, str], prompt: str) -> subprocess.CompletedProcess[str]:
    result = run(
        [
            str(CODEX),
            "--dangerously-bypass-hook-trust",
            "--cd",
            str(workspace),
            "--sandbox",
            "danger-full-access",
            "--ask-for-approval",
            "never",
            "exec",
            "--json",
            prompt,
        ],
        cwd=workspace,
        env=env,
    )
    assert_true(result.returncode == 0, result.stdout[-12000:] + result.stderr[-12000:])
    return result


def items(result: subprocess.CompletedProcess[str], kind: str) -> list[dict]:
    values: list[dict] = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == kind:
            values.append(item)
    return values


def messages(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(str(item.get("text") or "") for item in items(result, "agent_message"))


def commands(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [
        str(item.get("command") or "")
        for item in items(result, "command_execution")
        if item.get("status") == "completed"
    ]


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


def validate(workspace: Path) -> None:
    result = run([str(workspace / ".podo/bin/podo"), "validate"], cwd=workspace)
    assert_true(result.returncode == 0, result.stdout + result.stderr)


def run_acceptance(workspace: Path, env: dict[str, str]) -> None:
    user_paths = ["user_config.md", "state/user-sentinel.md", ".podo-backups/user-sentinel.txt"]
    before = snapshot(workspace, user_paths)
    assert_true(product_version(workspace) == FROM_VERSION, "public baseline version is wrong")

    first = codex_task(
        workspace,
        env,
        "현재 설치된 Podo 버전을 확인해서 NO_UPDATE_CHECK와 함께 답해. "
        "이 요청은 제품 update나 rollback 요청이 아니다. 제품 파일을 변경하거나 update 명령을 실행하지 마.",
    )
    first_message = messages(first)
    first_commands = commands(first)
    assert_true("NO_UPDATE_CHECK" in first_message and FROM_VERSION in first_message, first_message)
    assert_true(not any("podo update" in command for command in first_commands), str(first_commands))
    assert_true(product_version(workspace) == FROM_VERSION, "non-update task changed product version")
    assert_true(snapshot(workspace, user_paths) == before, "non-update task changed user sentinels")
    print("PASS real Codex does not update without an explicit request")

    second = codex_task(
        workspace,
        env,
        "Podo를 최신 안정 버전으로 업데이트해줘. product update policy를 읽고 canonical command만 사용해. "
        "성공 출력과 설치된 version을 확인한 뒤 NEW_TASK_REQUIRED를 포함하여 새 Codex task와 hook 재검토를 안내해.",
    )
    second_message = messages(second)
    second_commands = commands(second)
    assert_true("NEW_TASK_REQUIRED" in second_message and TO_VERSION in second_message, second_message)
    assert_true(
        any(".podo/bin/podo update" in command for command in second_commands),
        str(second_commands),
    )
    assert_true(product_version(workspace) == TO_VERSION, "explicit update did not install latest product")
    assert_true(snapshot(workspace, user_paths) == before, "explicit update changed user sentinels")
    validate(workspace)
    print("PASS real Codex uses the canonical command and reports new-task guidance")

    third = codex_task(
        workspace,
        env,
        "업데이트 뒤 새 task 검증이다. startup policy를 수행하고 현재 Podo version을 확인한 뒤 "
        "POST_UPDATE_STARTUP_OK와 version을 답해. 추가 update나 rollback은 실행하지 마.",
    )
    third_message = messages(third)
    third_commands = commands(third)
    assert_true("POST_UPDATE_STARTUP_OK" in third_message and TO_VERSION in third_message, third_message)
    assert_true(not any("podo update" in command for command in third_commands), str(third_commands))
    assert_true(product_version(workspace) == TO_VERSION, "new task changed installed product")
    assert_true(snapshot(workspace, user_paths) == before, "new task changed user sentinels")
    validate(workspace)
    print("PASS a new real Codex task starts normally on the updated product")


def safe_cleanup() -> None:
    assert_true(CONTAINER.resolve().parent == TEST_PARENT.resolve(), f"unsafe cleanup target: {CONTAINER}")
    marker = CONTAINER / MARKER
    expected = {"managed_by": SUITE, "run_id": RUN_ID}
    assert_true(marker.is_file() and not marker.is_symlink(), f"cleanup marker missing: {CONTAINER}")
    assert_true(json.loads(marker.read_text(encoding="utf-8")) == expected, "cleanup marker mismatch")
    shutil.rmtree(CONTAINER)


def main() -> None:
    assert_true(CODEX.is_file(), f"bundled Codex CLI is missing: {CODEX}")
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
    workspace = CONTAINER / "workspace"
    codex_home = CONTAINER / "codex-home"
    try:
        install_public(workspace)
        run_acceptance(workspace, configure(workspace, codex_home))
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
    print("PASS Phase 6 real Codex Desktop artifacts cleaned")


if __name__ == "__main__":
    main()
