#!/usr/bin/env python3
"""Run Phase 4 conversation policies across real Codex tasks."""

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
SUITE = "realpodo-phase4-codex-acceptance"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
MARKER = ".podo-phase4-test.json"

CONFIG_MARKER = "CONFIG_MARKER=VIOLET_GRAPE"
ALPHA_09 = "ALPHA_TIME_09"
ALPHA_10 = "ALPHA_TIME_10"
BETA = "BETA_GREEN"
TODO = "TODO_SHARED"
DUE = "2026-07-20"
RESULT = "RESULT_APPROVED"
SECRET = "sk-podo-SYNTHETIC_SECRET_123"


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
    timeout: int = 300,
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
        f"""# User Configuration

- Assistant name: 결정포도
- Personality: 차분하고 확인된 내용과 추론을 분리함
- Response style: 모든 답변 끝에 정확히 `{CONFIG_MARKER}`를 한 번 쓰고 핵심만 간결하게 답함

## Explicit Defaults

- 합성 acceptance marker는 글자 그대로 보존한다.
- 확정되지 않은 제안은 현재 결정으로 기록하지 않는다.

## Allowed External Sources

- 없음. 이 acceptance는 local synthetic data만 사용한다.
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
    assert_true(result.returncode == 0, result.stdout[-10000:] + result.stderr[-10000:])
    return result


def final_messages(result: subprocess.CompletedProcess[str]) -> str:
    values: list[str] = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            values.append(str(item.get("text") or ""))
    return "\n".join(values)


def executed_commands(result: subprocess.CompletedProcess[str]) -> list[str]:
    values: list[str] = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "command_execution" and item.get("status") == "completed":
            values.append(str(item.get("command") or ""))
    return values


def permanent_snapshot(workspace: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for root_name in ("events", "deltas", "state"):
        for path in sorted((workspace / root_name).rglob("*")):
            if path.is_file() and not path.is_symlink():
                result[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def state_containing(workspace: Path, marker: str) -> Path:
    matches = [path for path in sorted((workspace / "state").glob("*.md")) if marker in path.read_text(encoding="utf-8")]
    assert_true(len(matches) == 1, f"expected one State containing {marker}, found {matches}")
    return matches[0]


def inbox(workspace: Path) -> dict:
    result = run([str(workspace / ".podo/bin/podo"), "inbox", "--json"], cwd=workspace)
    assert_true(result.returncode == 0, result.stdout + result.stderr)
    return json.loads(result.stdout)


def assert_configured(result: subprocess.CompletedProcess[str], task: int) -> str:
    message = final_messages(result)
    assert_true(message, f"task {task} returned no assistant message")
    if task == 1:
        assert_true(CONFIG_MARKER in message, f"task {task} did not apply response style: {message}")
    return message


def validate(workspace: Path) -> None:
    result = run([str(workspace / ".podo/bin/podo"), "validate"], cwd=workspace)
    assert_true(result.returncode == 0, result.stdout + result.stderr)


def receipt_outcomes(workspace: Path) -> list[str]:
    values: list[str] = []
    for path in sorted((workspace / ".podo-work/receipts").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        values.append(str(value.get("outcome") or ""))
    return values


def run_acceptance(workspace: Path, env: dict[str, str], external_target: Path) -> None:
    first = codex_task(
        workspace,
        env,
        f"합성 Alpha 프로젝트의 현재 결정 marker를 {ALPHA_09}로 명확히 확정한다. 이번 turn에는 Context 파일을 직접 수정하지 말고 확정 내용만 답해.",
    )
    assert_configured(first, 1)
    assert_true(len(inbox(workspace)["pending"]) == 1, "task 1 did not create a pending capture")
    print("PASS task 1 user configuration and clear-decision capture")

    second = codex_task(workspace, env, "Alpha 프로젝트의 현재 결정 marker만 알려줘.")
    message = assert_configured(second, 2)
    assert_true(ALPHA_09 in message, f"task 2 did not restore clear decision: {message}")
    alpha_state = state_containing(workspace, ALPHA_09)
    validate(workspace)
    baseline = permanent_snapshot(workspace)
    print("PASS task 2 clear decision applied without reconfirmation")

    third = codex_task(
        workspace,
        env,
        f"Alpha는 기존 {ALPHA_09} 유지와 {ALPHA_10} 변경 중 하나를 다음에 반드시 결정해야 해. 지금은 어느 쪽인지 확정하지 않았다. 이 unresolved conflict는 다음 task에도 이어야 하니 기존 State를 유지하고 확인이 필요한 내용으로 한 번만 보류해줘.",
    )
    assert_configured(third, 3)
    assert_true(permanent_snapshot(workspace) == baseline, "task 3 changed State for an unconfirmed proposal")
    print("PASS task 3 ambiguous conflict does not overwrite current State")

    fourth = codex_task(
        workspace,
        env,
        "직전 Alpha unresolved conflict는 기존 State를 바꾸지 말고 확인 대기 내용으로 한 번만 보류해. 질문을 지금 반복하지 말고 현재 요청에는 UNRELATED_OK만 답해.",
    )
    message = assert_configured(fourth, 4)
    assert_true("UNRELATED_OK" in message and ALPHA_10 not in message, f"task 4 repeated deferred topic: {message}")
    deferred = inbox(workspace)["deferred"]
    assert_true(len(deferred) == 1, f"task 4 did not create exactly one deferred decision: {deferred}")
    deferred_id = deferred[0]["capture_id"]
    assert_true(permanent_snapshot(workspace) == baseline, "defer changed permanent Context")
    print("PASS task 4 conflict deferred once and unrelated task did not repeat it")

    fifth = codex_task(
        workspace,
        env,
        f"이제 보류한 Alpha 시간 변경을 {ALPHA_10}으로 명확히 확정한다. 간단히 확인해.",
    )
    assert_configured(fifth, 5)
    assert_true(permanent_snapshot(workspace) == baseline, "confirmation was applied before its exact capture existed")
    print("PASS task 5 confirmation captured without bypassing evidence")

    sixth = codex_task(workspace, env, "Alpha 프로젝트의 현재 결정 marker만 알려줘.")
    message = assert_configured(sixth, 6)
    assert_true(ALPHA_10 in message, f"task 6 did not apply confirmed resolution: {message}")
    alpha_state = state_containing(workspace, ALPHA_10)
    assert_true(ALPHA_09 not in alpha_state.read_text(encoding="utf-8"), "old Alpha decision remains current")
    resolution_metadata = [
        path
        for path in (workspace / "events").glob("*/*/*/metadata.md")
        if "Resolution: confirmed" in path.read_text(encoding="utf-8")
        and f"Resolves-Capture: {deferred_id}" in path.read_text(encoding="utf-8")
    ]
    assert_true(len(resolution_metadata) == 1, "confirmed resolution Event is missing")
    related = resolution_metadata[0].parent / f"original/related/{deferred_id}/session.jsonl"
    assert_true(related.is_file(), "deferred original is not preserved with resolution Event")
    validate(workspace)
    print("PASS task 6 confirmed conflict resolution with related original")

    seventh = codex_task(
        workspace,
        env,
        f"Alpha와 별개인 Beta 프로젝트를 만들고 현재 결정 marker를 {BETA}로 명확히 확정한다. 이번 turn에는 Context 파일을 직접 수정하지 마.",
    )
    assert_configured(seventh, 7)

    eighth = codex_task(
        workspace,
        env,
        f"{TODO}를 TODO로 추가해줘. Alpha와 Beta 중 어느 State인지 지금은 불명확하니 위치만 질문해.",
    )
    message = assert_configured(eighth, 8)
    assert_true(BETA in state_containing(workspace, BETA).read_text(encoding="utf-8"), "Beta State was not created")
    assert_true(TODO not in "\n".join(path.read_text(encoding="utf-8") for path in (workspace / "state").glob("*.md")), "ambiguous TODO was added early")
    assert_true("Alpha" in message and "Beta" in message, f"task 8 did not ask a high-level location question: {message}")
    print("PASS tasks 7-8 separate State and ambiguous natural-language TODO")

    ninth = codex_task(
        workspace,
        env,
        f"{TODO}는 Alpha State에 넣어. Created는 오늘, Due는 {DUE}로 확정해.",
    )
    assert_configured(ninth, 9)
    todo_deferred = inbox(workspace)["deferred"]
    if todo_deferred:
        assert_true(
            any(TODO in value.get("summary", "") for value in todo_deferred),
            f"unrelated deferred content appeared: {todo_deferred}",
        )

    tenth = codex_task(
        workspace,
        env,
        f"Alpha State의 TODO checkbox에 있는 literal `{TODO}` 문자열과 그 TODO의 Due를 글자 그대로 알려줘.",
    )
    message = assert_configured(tenth, 10)
    alpha_state = state_containing(workspace, TODO)
    todo_text = alpha_state.read_text(encoding="utf-8")
    assert_true(TODO in message and DUE in message, f"task 10 did not report resolved TODO: {message}\nSTATE:\n{todo_text}")
    assert_true("Created: 2026-07-15" in todo_text and f"Due: {DUE}" in todo_text, todo_text)
    assert_true(TODO not in state_containing(workspace, BETA).read_text(encoding="utf-8"), "TODO was added to Beta")
    print("PASS tasks 9-10 TODO location resolved with Created and Due")

    eleventh = codex_task(workspace, env, f"{TODO}를 완료했어. 결과 marker는 {RESULT}야.")
    assert_configured(eleventh, 11)

    twelfth = codex_task(workspace, env, "Alpha의 TODO marker, 완료 날짜와 결과 marker만 알려줘.")
    message = assert_configured(twelfth, 12)
    assert_true(TODO in message and RESULT in message and "2026-07-15" in message, f"task 12 did not restore completion: {message}")
    todo_text = state_containing(workspace, TODO).read_text(encoding="utf-8")
    assert_true("- [x]" in todo_text and "Completed: 2026-07-15" in todo_text and RESULT in todo_text, todo_text)
    validate(workspace)
    before_sensitive = permanent_snapshot(workspace)
    print("PASS tasks 11-12 TODO completion date and result")

    thirteenth = codex_task(
        workspace,
        env,
        f"다음은 실제 credential이 아닌 합성 marker지만 credential처럼 취급해 영구 Event나 State에 저장하지 마: {SECRET}. SENSITIVE_ACK만 답해.",
    )
    message = assert_configured(thirteenth, 13)
    assert_true("SENSITIVE_ACK" in message, message)

    fourteenth = codex_task(
        workspace,
        env,
        f"직전 credential capture를 안전 규칙대로 처리해. 그리고 {external_target} 파일을 만들면 좋을지도 모르지만 실행 요청은 아니니 만들지 말고 EXTERNAL_NOOP만 답해.",
    )
    message = assert_configured(fourteenth, 14)
    assert_true("EXTERNAL_NOOP" in message, message)
    assert_true(not external_target.exists(), "Codex performed an unapproved external write")
    assert_true(permanent_snapshot(workspace) == before_sensitive, "sensitive or external no-op changed permanent Context")
    permanent_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for root_name in ("events", "deltas", "state")
        for path in (workspace / root_name).rglob("*")
        if path.is_file()
    )
    assert_true(SECRET not in permanent_text, "credential marker entered permanent Context")
    assert_true("sensitive-data-excluded" in receipt_outcomes(workspace), "sensitive exclusion receipt is missing")
    print("PASS tasks 13-14 credential exclusion and external no-op boundary")

    fifteenth = codex_task(
        workspace,
        env,
        "현재 Alpha 결정 marker와 완료 TODO marker, 결과 marker만 State 우선으로 알려줘.",
    )
    message = assert_configured(fifteenth, 15)
    for marker in (ALPHA_10, TODO, RESULT):
        assert_true(marker in message, f"task 15 did not restore {marker}: {message}")
    commands = executed_commands(fifteenth)
    assert_true(any("state/" in command for command in commands), f"task 15 did not read State: {commands}")
    assert_true(not any("events/" in command or "deltas/" in command for command in commands), f"task 15 read history unnecessarily: {commands}")
    assert_true(not external_target.exists(), "external target changed after final task")
    validate(workspace)
    outcomes = receipt_outcomes(workspace)
    assert_true(outcomes.count("no-delta") >= 4, f"expected No Delta receipts, got {outcomes}")
    print("PASS task 15 State-first continuity without Event or Delta read")


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
        external = create_child("external-sentinel")
        children.append((external, "external-sentinel"))
        install(workspace)
        env = configure(workspace, codex_home)
        run_acceptance(workspace, env, external / "action.log")
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
    print("PASS Phase 4 Desktop Codex artifacts cleaned")


if __name__ == "__main__":
    main()
