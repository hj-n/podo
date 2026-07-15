#!/usr/bin/env python3
"""Run interrupted transaction diagnosis and approved recovery across real Codex tasks."""

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
SUITE = "realpodo-phase5-codex-recovery"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
MARKER = ".podo-phase5-test.json"
BASELINE = "RECOVERY_BASELINE_09"
TARGET = "RECOVERY_TARGET_10"


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


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, timeout: int = 300):
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

- Assistant name: 복구포도
- Personality: 차분하고 확인된 진단과 승인을 분리함
- Response style: 요청된 acceptance marker를 글자 그대로 포함하고 핵심만 답함

## Explicit Defaults

- 합성 acceptance 데이터만 사용한다.
- 복구 승인이 없으면 Context transaction을 적용하지 않는다.

## Allowed External Sources

- 없음.
""",
        encoding="utf-8",
    )
    result = run(["git", "init", "-q"], cwd=workspace)
    assert_true(result.returncode == 0, result.stderr)
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


def codex_task(workspace: Path, env: dict[str, str], prompt: str):
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
    assert_true(result.returncode == 0, result.stdout[-12000:] + result.stderr[-12000:])
    return result


def items(result, kind: str) -> list[dict]:
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


def messages(result) -> str:
    return "\n".join(str(item.get("text") or "") for item in items(result, "agent_message"))


def commands(result) -> list[str]:
    return [
        str(item.get("command") or "")
        for item in items(result, "command_execution")
        if item.get("status") == "completed"
    ]


def permanent_snapshot(workspace: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for root_name in ("events", "deltas", "state"):
        for path in sorted((workspace / root_name).rglob("*")):
            if path.is_file() and not path.is_symlink():
                values[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def state_containing(workspace: Path, marker: str) -> Path:
    matches = [path for path in (workspace / "state").glob("*.md") if marker in path.read_text(encoding="utf-8")]
    assert_true(len(matches) == 1, f"expected one State containing {marker}: {matches}")
    return matches[0]


def unfinished(workspace: Path) -> list[Path]:
    directory = workspace / ".podo-work/transactions"
    return sorted(path for path in directory.glob("context-*") if path.is_dir()) if directory.is_dir() else []


def validate(workspace: Path) -> None:
    result = run([str(workspace / ".podo/bin/podo"), "validate"], cwd=workspace)
    assert_true(result.returncode == 0, result.stdout + result.stderr)


def run_acceptance(workspace: Path, env: dict[str, str]) -> None:
    first = codex_task(
        workspace,
        env,
        f"합성 복구 프로젝트의 현재 결정 marker를 {BASELINE}으로 명확히 확정한다. Context 파일은 직접 수정하지 말고 BASELINE_CAPTURED만 답해.",
    )
    assert_true("BASELINE_CAPTURED" in messages(first), messages(first))

    second = codex_task(
        workspace,
        env,
        "startup policy대로 이전 pending의 명확한 결정을 Context에 적용한 뒤, 합성 복구 프로젝트의 현재 결정 marker와 BASELINE_APPLIED를 답해.",
    )
    assert_true(BASELINE in messages(second) and "BASELINE_APPLIED" in messages(second), messages(second))
    try:
        baseline_state = state_containing(workspace, BASELINE)
    except AcceptanceFailure as error:
        states = {path.name: path.read_text(encoding="utf-8") for path in (workspace / "state").glob("*.md")}
        raise AcceptanceFailure(f"{error}; commands={commands(second)}; states={states}; output={messages(second)}") from error
    validate(workspace)
    print("PASS tasks 1-2 establish verified baseline Context")

    third = codex_task(
        workspace,
        env,
        f"합성 복구 프로젝트의 현재 결정을 {BASELINE}에서 {TARGET}으로 명확히 변경한다. Context 파일은 직접 수정하지 말고 TARGET_CAPTURED만 답해.",
    )
    assert_true("TARGET_CAPTURED" in messages(third), messages(third))
    before_failure = permanent_snapshot(workspace)

    failure_env = env.copy()
    failure_env.update({"PODO_TEST_FAILURES": "1", "PODO_TEST_FAIL_AT": "after-delta-1"})
    fourth = codex_task(
        workspace,
        failure_env,
        "이 task에서 이전 capture 적용이 실패하면 재시도하거나 doctor/recover를 실행하지 마. 실패를 관찰한 뒤 FAILURE_OBSERVED만 포함해 답해.",
    )
    assert_true("FAILURE_OBSERVED" in messages(fourth), messages(fourth))
    assert_true(len(unfinished(workspace)) == 1, "injected failure did not leave one transaction")
    assert_true(BASELINE in baseline_state.read_text(encoding="utf-8") and TARGET not in baseline_state.read_text(encoding="utf-8"), "failure overwrote baseline State")
    print("PASS task 4 forced interruption preserves baseline State and transaction evidence")

    before_diagnosis = permanent_snapshot(workspace)
    fifth = codex_task(
        workspace,
        env,
        "복구를 승인하지 않는다. startup inbox의 자동 read-only `recovery_diagnosis` evidence만 설명해. doctor를 반복 실행하거나 recover --apply를 실행하지 말고 DIAGNOSIS_ONLY를 포함해 high-level로 답해.",
    )
    fifth_message = messages(fifth)
    assert_true("DIAGNOSIS_ONLY" in fifth_message, fifth_message)
    startup = run([str(workspace / ".podo/bin/podo"), "inbox", "--json"], cwd=workspace)
    startup_value = json.loads(startup.stdout)
    diagnosis_codes = {
        finding["code"] for finding in startup_value.get("recovery_diagnosis", {}).get("findings", [])
    }
    assert_true("PODO_D001_TRANSACTION_INCOMPLETE" in diagnosis_codes, startup.stdout + startup.stderr)
    assert_true(not any("recover --apply" in command for command in commands(fifth)), str(commands(fifth)))
    assert_true(permanent_snapshot(workspace) == before_diagnosis, "diagnosis changed permanent Context")
    assert_true(len(unfinished(workspace)) == 1, "diagnosis auto-completed transaction")
    print("PASS task 5 discovers and explains failure without approval or State change")

    sixth = codex_task(
        workspace,
        env,
        f"미완료 transaction의 doctor 결과가 기계적으로 안전한 resume이라면 복구를 명시적으로 승인한다. `podo recover --json`으로 plan을 확인하고 exact plan ID를 `podo recover --apply`에 전달해. 완료 후 {TARGET}과 RECOVERY_APPLIED를 답해.",
    )
    sixth_message = messages(sixth)
    assert_true(TARGET in sixth_message and "RECOVERY_APPLIED" in sixth_message, sixth_message)
    sixth_commands = commands(sixth)
    assert_true(any("recover" in command and "--apply" in command for command in sixth_commands), str(sixth_commands))
    assert_true(not unfinished(workspace), "approved recovery left unfinished transaction")
    recovered_state = state_containing(workspace, TARGET)
    assert_true(BASELINE not in recovered_state.read_text(encoding="utf-8"), recovered_state.read_text(encoding="utf-8"))
    validate(workspace)
    print("PASS task 6 exact approved plan completes transaction")

    recovered = permanent_snapshot(workspace)
    seventh = codex_task(
        workspace,
        env,
        "합성 복구 프로젝트의 현재 결정 marker와 STATE_FIRST_OK만 State 우선으로 답해. marker는 그대로 써.",
    )
    seventh_message = messages(seventh)
    assert_true(TARGET in seventh_message and "STATE_FIRST_OK" in seventh_message, seventh_message)
    seventh_commands = commands(seventh)
    assert_true(any("state/" in command for command in seventh_commands), str(seventh_commands))
    history_neutral = [
        command.replace("!events/**", "").replace("!deltas/**", "") for command in seventh_commands
    ]
    assert_true(not any("events/" in command or "deltas/" in command for command in history_neutral), str(seventh_commands))
    assert_true(permanent_snapshot(workspace) == recovered, "State-first verification changed permanent Context")
    print("PASS task 7 restores recovered State without Event or Delta read")


def safe_cleanup(child: Path, role: str) -> None:
    assert_true(child.resolve().parent == TEST_PARENT.resolve(), f"unsafe cleanup target: {child}")
    marker = child / MARKER
    assert_true(marker.is_file() and not marker.is_symlink(), f"cleanup marker missing: {child}")
    assert_true(json.loads(marker.read_text(encoding="utf-8")) == marker_value(role), f"cleanup marker mismatch: {child}")
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
        run_acceptance(workspace, configure(workspace, codex_home))
    except (AcceptanceFailure, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        failures: list[str] = []
        for child, role in reversed(children):
            if not child.exists():
                continue
            try:
                safe_cleanup(child, role)
            except (AcceptanceFailure, OSError, json.JSONDecodeError) as error:
                failures.append(str(error))
        if parent_created:
            try:
                TEST_PARENT.rmdir()
            except OSError:
                pass
        if failures:
            raise AcceptanceFailure("; ".join(failures))
    print("PASS Phase 5 Desktop Codex artifacts cleaned")


if __name__ == "__main__":
    main()
