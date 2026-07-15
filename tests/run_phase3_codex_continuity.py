#!/usr/bin/env python3
"""Run the Phase 3 capture/apply/restore loop across real Codex tasks."""

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
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
TEST_PARENT = Path("/Users/hj/Desktop/podo-test-workspaces")
SUITE = "realpodo-phase3-codex-continuity"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
MARKER = ".podo-phase3-test.json"
DECISION = "PURPLE_ORCHARD_AT_09"
TODO = "PREPARE_GREEN_PACKET"
DUE = "2026-07-18"


class AcceptanceFailure(Exception):
    pass


def assert_true(value: bool, detail: str) -> None:
    if not value:
        raise AcceptanceFailure(detail)


def marker_value(role: str) -> dict[str, str]:
    return {"managed_by": SUITE, "run_id": RUN_ID, "role": role}


def create_child(role: str) -> Path:
    child = TEST_PARENT / f"{RUN_ID}-{role}"
    assert_true(child.parent.resolve() == TEST_PARENT.resolve(), "test child escaped Desktop parent")
    assert_true(not child.exists(), f"test child already exists: {child}")
    child.mkdir()
    (child / MARKER).write_text(json.dumps(marker_value(role), sort_keys=True) + "\n", encoding="utf-8")
    return child


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 240,
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
    result = run([sys.executable, str(INSTALLER), "--workspace", str(workspace)], cwd=REPO_ROOT)
    assert_true(result.returncode == 0, result.stdout + result.stderr)


def configure(workspace: Path, codex_home: Path) -> dict[str, str]:
    (workspace / "user_config.md").write_text(
        """# User Configuration

- Assistant name: 연속성포도
- Personality: 차분하고 검증 가능한 사실만 말함
- Response style: marker와 날짜를 그대로 보존해 간결하게 답함

## Explicit Defaults

- 합성 acceptance 데이터만 사용한다.

## Allowed External Sources

- 없음.
""",
        encoding="utf-8",
    )
    git = run(["git", "init", "-q"], cwd=workspace)
    assert_true(git.returncode == 0, git.stderr)
    auth = Path.home() / ".codex/auth.json"
    assert_true(auth.is_file(), "Codex authentication is unavailable")
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
    assert_true(result.returncode == 0, result.stdout[-8000:] + result.stderr[-8000:])
    return result


def final_messages(result: subprocess.CompletedProcess[str]) -> str:
    messages: list[str] = []
    for line in result.stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = value.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            messages.append(str(item.get("text") or ""))
    return "\n".join(messages)


def executed_commands(result: subprocess.CompletedProcess[str]) -> list[str]:
    commands: list[str] = []
    for line in result.stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = value.get("item")
        if isinstance(item, dict) and item.get("type") == "command_execution" and item.get("status") == "completed":
            commands.append(str(item.get("command") or ""))
    return commands


def permanent_snapshot(workspace: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for root_name in ("events", "deltas", "state"):
        for path in sorted((workspace / root_name).rglob("*")):
            if path.is_file() and not path.is_symlink():
                values[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def validate_context(workspace: Path) -> None:
    cli = workspace / ".podo/bin/podo"
    result = run([str(cli), "validate"], cwd=workspace)
    assert_true(result.returncode == 0, result.stdout + result.stderr)


def inbox_metadata(workspace: Path) -> list[Path]:
    return sorted((workspace / ".podo-work/inbox").glob("*/capture.json"))


def run_continuity(workspace: Path, env: dict[str, str]) -> None:
    first = codex_task(
        workspace,
        env,
        (
            "합성 연속성 프로젝트에서 다음을 명확히 확정한다. 결정 marker는 "
            f"{DECISION}이고, TODO marker는 {TODO}, 마감일은 {DUE}다. "
            "이번 turn에는 이 내용을 간결히 확인만 하고 Context 파일은 직접 수정하지 마."
        ),
    )
    assert_true(len(inbox_metadata(workspace)) == 1, "first Stop hook did not create exactly one pending capture")
    print("PASS task 1 exact Stop-hook inbox capture")

    second = codex_task(
        workspace,
        env,
        (
            "이전 합성 연속성 논의를 이어가자. 현재 결정 marker, TODO marker와 마감일을 알려줘. "
            "marker 문자열은 바꾸지 마."
        ),
    )
    second_messages = final_messages(second)
    for expected in (DECISION, TODO, DUE):
        assert_true(expected in second_messages, f"task 2 did not restore {expected}: {second_messages}")
    validate_context(workspace)
    snapshot = permanent_snapshot(workspace)
    events = [path for path in snapshot if path.startswith("events/") and path.endswith("/metadata.md")]
    deltas = [path for path in snapshot if path.startswith("deltas/")]
    states = [path for path in snapshot if path.startswith("state/")]
    assert_true(len(events) == 1 and len(deltas) == 1 and len(states) == 1, f"unexpected Context shape: {snapshot}")
    state_text = (workspace / states[0]).read_text(encoding="utf-8")
    for expected in (DECISION, TODO, DUE):
        assert_true(expected in state_text, f"State is missing {expected}")
    print("PASS task 2 Event → Delta → State apply and immediate continuity")

    before_thanks = permanent_snapshot(workspace)
    third = codex_task(workspace, env, "고마워.")
    assert_true(final_messages(third), "task 3 returned no assistant message")
    assert_true(permanent_snapshot(workspace) == before_thanks, "thank-you task changed permanent Context")
    print("PASS task 3 No Delta leaves permanent Context unchanged")

    fourth = codex_task(
        workspace,
        env,
        "현재 합성 연속성 프로젝트의 결정 marker와 TODO marker, 마감일만 알려줘. marker는 그대로 써.",
    )
    fourth_messages = final_messages(fourth)
    for expected in (DECISION, TODO, DUE):
        assert_true(expected in fourth_messages, f"task 4 did not restore {expected}: {fourth_messages}")
    assert_true(permanent_snapshot(workspace) == before_thanks, "State-first restore changed permanent Context")
    commands = executed_commands(fourth)
    assert_true(any("state/" in command for command in commands), f"task 4 did not read State: {commands}")
    assert_true(not any("events/" in command or "deltas/" in command for command in commands), f"task 4 read history unnecessarily: {commands}")
    receipts = list((workspace / ".podo-work/receipts").glob("*.json"))
    no_delta = 0
    for receipt in receipts:
        value = json.loads(receipt.read_text(encoding="utf-8"))
        if value.get("outcome") == "no-delta":
            no_delta += 1
    assert_true(no_delta >= 2, f"expected no-delta receipts for tasks 2 and 3, found {no_delta}")
    validate_context(workspace)
    print("PASS task 4 State-first restore without Delta or Event read")


def safe_cleanup(child: Path, role: str) -> None:
    resolved = child.resolve()
    assert_true(resolved.parent == TEST_PARENT.resolve(), f"cleanup target is not a direct child: {child}")
    marker = child / MARKER
    assert_true(marker.is_file() and not marker.is_symlink(), f"cleanup marker missing: {child}")
    actual = json.loads(marker.read_text(encoding="utf-8"))
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
        workspace = create_child("workspace")
        children.append((workspace, "workspace"))
        codex_home = create_child("codex-home")
        children.append((codex_home, "codex-home"))
        install(workspace)
        env = configure(workspace, codex_home)
        run_continuity(workspace, env)
    except (AcceptanceFailure, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        cleanup_failures: list[str] = []
        for child, role in reversed(children):
            if not child.exists():
                continue
            try:
                safe_cleanup(child, role)
            except (AcceptanceFailure, OSError, json.JSONDecodeError) as error:
                cleanup_failures.append(str(error))
        if parent_created:
            try:
                TEST_PARENT.rmdir()
            except OSError:
                pass
        if cleanup_failures:
            raise AcceptanceFailure("; ".join(cleanup_failures))
    print("PASS Phase 3 Desktop Codex artifacts cleaned")


if __name__ == "__main__":
    main()
