#!/usr/bin/env python3
"""Run the integrated Phase 8 user journey across real Codex tasks."""

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


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
TEST_PARENT = Path("/Users/hj/Desktop/podo-test-workspaces")
SUITE = "realpodo-phase8-codex-e2e"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
CONTAINER = TEST_PARENT / f"{RUN_ID}-phase8-e2e"
MARKER = ".podo-phase8-codex-test.json"

from phase8_support import capture, request_file  # noqa: E402
from run_phase6_product_update import apply, package, synthetic_product  # noqa: E402
from run_phase7_planning import add_migration, release_tree  # noqa: E402


CONFIG_MARKER = "PHASE8_CONFIG_APPLIED"
DECISION_09 = "E2E_ORCHARD_AT_09"
DECISION_10 = "E2E_ORCHARD_AT_10"
TODO = "E2E_PREPARE_PACKET"
DUE = "2026-07-20"
RECOVERED = "E2E_RECOVERED_DECISION"


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
    ]


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
    assert_true(result.returncode == 0, result.stdout[-16000:] + result.stderr[-16000:])
    return result


def configure(workspace: Path, codex_home: Path, releases: Path) -> dict[str, str]:
    (workspace / "user_config.md").write_text(
        f"""# User Configuration

- Assistant name: 통합포도
- Personality: 차분하고 확인된 사실, 추론과 승인 경계를 분리함
- Response style: 핵심만 간결하게 답하고 첫 답변에 `{CONFIG_MARKER}`를 포함함

## Explicit Defaults

- 합성 Phase 8 acceptance marker는 글자 그대로 보존한다.
- 확정되지 않은 제안은 현재 결정으로 기록하지 않는다.
- 일반 product update는 Workspace migration 승인이 아니다.

## Allowed External Sources

- 현재 acceptance가 지정한 synthetic local Podo Release
""",
        encoding="utf-8",
    )
    (workspace / "user_config.md").chmod(0o640)
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
    env.update(
        {
            "CODEX_HOME": str(codex_home),
            "PODO_TEST_RELEASES": "1",
            "PODO_RELEASE_DIR": str(releases),
        }
    )
    return env


def permanent_snapshot(workspace: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for root_name in ("events", "deltas", "state"):
        for path in sorted((workspace / root_name).rglob("*")):
            if path.is_file() and not path.is_symlink():
                values[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def user_evidence(workspace: Path) -> dict[str, tuple[str, int]]:
    candidates = [workspace / "WORKSPACE_VERSION", workspace / "user_config.md"]
    for root_name in ("events", "deltas", "state"):
        candidates.extend(path for path in sorted((workspace / root_name).rglob("*")) if path.is_file())
    return {
        path.relative_to(workspace).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            stat.S_IMODE(path.stat().st_mode),
        )
        for path in candidates
    }


def state_containing(workspace: Path, marker: str) -> Path:
    matches = [
        path
        for path in sorted((workspace / "state").glob("*.md"))
        if marker in path.read_text(encoding="utf-8")
    ]
    assert_true(len(matches) == 1, f"expected one State containing {marker}, found {matches}")
    return matches[0]


def inbox(workspace: Path, env: dict[str, str]) -> dict:
    result = run([str(workspace / ".podo/bin/podo"), "inbox", "--json"], cwd=workspace, env=env)
    assert_true(result.returncode == 0, result.stdout + result.stderr)
    return json.loads(result.stdout)


def validate(workspace: Path) -> None:
    result = run([str(workspace / ".podo/bin/podo"), "validate"], cwd=workspace)
    assert_true(result.returncode == 0, result.stdout + result.stderr)


def installed_version(workspace: Path) -> tuple[str, str]:
    return (
        (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip(),
        (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip(),
    )


def only_plan(directory: Path, prefix: str) -> dict:
    paths = sorted(directory.glob(f"{prefix}-*.json"))
    assert_true(len(paths) == 1, f"expected one {prefix} plan: {paths}")
    return json.loads(paths[0].read_text(encoding="utf-8"))


def unfinished(workspace: Path) -> list[Path]:
    directory = workspace / ".podo-work/transactions"
    return sorted(directory.glob("context-*")) if directory.is_dir() else []


def build_target_release(base: Path, state: Path) -> None:
    relative = state.relative_to(base / "workspace").as_posix()
    target = synthetic_product(base, "1.0.0", [2])
    add_migration(target, 1, 2, affected=[relative])
    script = target / ".podo/migrations/1-to-2/migrate.py"
    script.write_text(
        """#!/usr/bin/env python3
import argparse
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument("--workspace", required=True, type=Path)
args = parser.parse_args()
path = args.workspace / %r
text = path.read_text(encoding="utf-8")
path.write_text(text.replace("Updated:", "Format: 2\\n\\nUpdated:", 1), encoding="utf-8")
"""
        % relative,
        encoding="utf-8",
    )
    release_tree(base, target, "3")


def recovery_request(workspace: Path, state: Path) -> Path:
    current = state.read_text(encoding="utf-8")
    lines = current.splitlines()
    for index, line in enumerate(lines):
        if DECISION_10 in line:
            lines[index] = line.replace(DECISION_10, RECOVERED)
            break
    else:
        raise AcceptanceFailure("could not locate the current decision line for recovery fixture")
    lines.extend(
        [
            "",
            "## Recovery Evidence",
            "",
            "- [Recovery Delta]({{DELTA_LINK}})",
        ]
    )
    value = {
        "event": {"title": "Phase 8 recovery target", "context": "Synthetic integrated interruption."},
        "updates": [
            {
                "state_slug": state.stem,
                "expected_state_sha256": hashlib.sha256(state.read_bytes()).hexdigest(),
                "delta_title": "Phase 8 recovery target",
                "changed": f"- {RECOVERED}",
                "why": "통합 acceptance의 명확한 recovery target이다.",
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "state_markdown": "\n".join(lines) + "\n",
            }
        ],
    }
    return request_file(workspace, "codex-recovery-target", value)


def inject_interruption(workspace: Path, root: Path, state: Path) -> None:
    capture_id, _ = capture(workspace, root, "codex-recovery-target")
    env = os.environ.copy()
    env.update({"PODO_TEST_FAILURES": "1", "PODO_TEST_FAIL_AT": "after-delta-1"})
    result = run(
        [
            str(workspace / ".podo/bin/podo"),
            "context",
            "apply",
            "--capture",
            capture_id,
            "--request",
            str(recovery_request(workspace, state)),
        ],
        cwd=workspace,
        env=env,
    )
    assert_true(result.returncode != 0 and "E_INJECTED_FAILURE" in result.stderr, result.stdout + result.stderr)
    assert_true(len(unfinished(workspace)) == 1, "injected failure did not leave one transaction")


def run_acceptance(workspace: Path, env: dict[str, str], base: Path) -> list[str]:
    passed: list[str] = []
    first = codex_task(
        workspace,
        env,
        f"합성 Orchard 프로젝트에서 결정 marker를 {DECISION_09}로 확정하고 TODO marker {TODO}를 Due {DUE}로 추가한다. "
        f"이번 task에는 Context 파일을 직접 수정하지 말고 확정 내용과 {CONFIG_MARKER}만 답해.",
    )
    assert_true(CONFIG_MARKER in messages(first), messages(first))
    assert_true(len(inbox(workspace, env)["pending"]) == 1, "task 1 did not leave one pending capture")

    second = codex_task(
        workspace,
        env,
        "startup policy대로 이전 pending의 명확한 결정과 TODO를 적용한 뒤 현재 marker, TODO와 Due를 답하고 E2E_CONTEXT_APPLIED를 포함해.",
    )
    second_message = messages(second)
    assert_true(
        all(value in second_message for value in (DECISION_09, TODO, DUE, "E2E_CONTEXT_APPLIED")),
        second_message,
    )
    state = state_containing(workspace, DECISION_09)
    validate(workspace)
    baseline = permanent_snapshot(workspace)
    passed.append("personalized-context")
    print("PASS real Codex tasks 1-2 personalize and establish traceable Context")

    third = codex_task(workspace, env, "고마워. E2E_NO_DELTA만 답해.")
    assert_true("E2E_NO_DELTA" in messages(third), messages(third))
    assert_true(permanent_snapshot(workspace) == baseline, "No Delta task changed permanent Context")
    passed.append("no-delta")
    print("PASS real Codex task 3 leaves permanent Context unchanged")

    fourth = codex_task(
        workspace,
        env,
        f"Orchard 결정을 {DECISION_09}로 유지할지 {DECISION_10}으로 바꿀지 아직 확정하지 않았다. 기존 State를 바꾸지 말고 다음 task에서 확인할 내용으로 남겨.",
    )
    assert_true(messages(fourth), "task 4 returned no message")
    fifth = codex_task(
        workspace,
        env,
        "직전 미확정 충돌은 기존 State를 유지한 채 한 번만 보류해. 지금 질문을 반복하지 말고 E2E_UNRELATED_OK만 답해.",
    )
    assert_true("E2E_UNRELATED_OK" in messages(fifth), messages(fifth))
    deferred = inbox(workspace, env)["deferred"]
    assert_true(len(deferred) == 1, f"expected one deferred conflict: {deferred}")
    assert_true(DECISION_09 in state.read_text(encoding="utf-8"), state.read_text(encoding="utf-8"))

    sixth = codex_task(
        workspace,
        env,
        f"보류한 Orchard 결정을 {DECISION_10}으로 명확히 확정하고 TODO {TODO}를 오늘 완료했으며 결과는 packet 준비 완료다. Context 파일은 직접 수정하지 말고 E2E_CONFIRM_CAPTURED를 답해.",
    )
    assert_true("E2E_CONFIRM_CAPTURED" in messages(sixth), messages(sixth))
    seventh = codex_task(
        workspace,
        env,
        "startup에서 직전 확인을 보류 내용과 resolve한 뒤 현재 결정과 TODO 상태를 State 우선으로 답하고 E2E_RESOLVED를 포함해.",
    )
    seventh_message = messages(seventh)
    assert_true(DECISION_10 in seventh_message and "E2E_RESOLVED" in seventh_message, seventh_message)
    state = state_containing(workspace, DECISION_10)
    state_text = state.read_text(encoding="utf-8")
    assert_true(DECISION_09 not in state_text and TODO in state_text and "Completed:" in state_text, state_text)
    validate(workspace)
    passed.append("conflict-todo")
    print("PASS real Codex tasks 4-7 defer/resolve conflict and complete TODO")

    build_target_release(base, state)
    before_interruption = permanent_snapshot(workspace)
    inject_interruption(workspace, base, state)
    assert_true(RECOVERED not in state.read_text(encoding="utf-8"), "interruption changed current State")
    eighth = codex_task(
        workspace,
        env,
        "복구 적용을 승인하지 않는다. startup의 read-only recovery_diagnosis만 설명하고 recover --apply는 실행하지 마. E2E_RECOVERY_REVIEW_ONLY를 포함해.",
    )
    eighth_message = messages(eighth)
    assert_true("E2E_RECOVERY_REVIEW_ONLY" in eighth_message, eighth_message)
    assert_true(not any("recover --apply" in command for command in commands(eighth)), str(commands(eighth)))
    startup = inbox(workspace, env)
    startup_codes = {
        finding["code"]
        for finding in startup.get("recovery_diagnosis", {}).get("findings", [])
    }
    assert_true("PODO_D001_TRANSACTION_INCOMPLETE" in startup_codes, json.dumps(startup, ensure_ascii=False))
    assert_true(RECOVERED not in state.read_text(encoding="utf-8"), "diagnosis applied recovery")
    assert_true(permanent_snapshot(workspace) != before_interruption, "injected Delta evidence was not retained")

    ninth = codex_task(
        workspace,
        env,
        f"미완료 transaction이 기계적으로 안전한 resume이면 복구를 명시적으로 승인한다. podo recover --json plan을 확인하고 exact plan ID로 apply해. {RECOVERED}와 E2E_RECOVERY_APPLIED를 답해.",
    )
    ninth_message = messages(ninth)
    assert_true(RECOVERED in ninth_message and "E2E_RECOVERY_APPLIED" in ninth_message, ninth_message)
    assert_true(any("recover" in command and "--apply" in command for command in commands(ninth)), str(commands(ninth)))
    assert_true(not unfinished(workspace), "approved recovery left an unfinished transaction")
    state = state_containing(workspace, RECOVERED)
    validate(workspace)
    passed.append("approved-recovery")
    print("PASS real Codex tasks 8-9 diagnose then exactly recover interrupted Context")

    pre_update = user_evidence(workspace)
    tenth = codex_task(
        workspace,
        env,
        "Podo 제품만 0.9.0으로 update하는 것을 명시적으로 승인한다. Workspace migration 승인은 아니다. canonical command로 적용하고 E2E_PRODUCT_UPDATED를 답해.",
    )
    assert_true("E2E_PRODUCT_UPDATED" in messages(tenth), messages(tenth))
    assert_true(any("podo update --version 0.9.0" in command for command in commands(tenth)), str(commands(tenth)))
    assert_true(installed_version(workspace) == ("0.9.0", "1"), str(installed_version(workspace)))
    assert_true(user_evidence(workspace) == pre_update, "compatible real Codex update changed user evidence")
    passed.append("compatible-update")
    print("PASS real Codex task 10 updates product only and preserves user evidence")

    plans = workspace / ".podo-work/migration-plans"
    eleventh = codex_task(
        workspace,
        env,
        "Podo 1.0.0으로 일반 product update만 요청한다. migration 검토나 적용은 승인하지 않는다. 호환되지 않으면 멈추고 E2E_UPDATE_STOPPED를 답해.",
    )
    assert_true("E2E_UPDATE_STOPPED" in messages(eleventh), messages(eleventh))
    assert_true(any("podo update --version 1.0.0" in command for command in commands(eleventh)), str(commands(eleventh)))
    assert_true(installed_version(workspace) == ("0.9.0", "1"), "incompatible update changed versions")
    assert_true(not plans.exists() or not list(plans.glob("*.json")), "update-only task created a migration plan")
    assert_true(not list((workspace / ".podo-backups").glob("*")), "update-only task created a backup")
    passed.append("update-migration-boundary")
    print("PASS real Codex task 11 stops incompatible update without migration artifacts")

    twelfth = codex_task(
        workspace,
        env,
        "Podo 1.0.0 Workspace migration 영향만 검토한다. canonical plan command로 변경 이유, 영향 path, backup과 rollback 조건을 보여주고 적용하지 마. E2E_MIGRATION_REVIEW_ONLY를 답해.",
    )
    twelfth_message = messages(twelfth)
    assert_true("E2E_MIGRATION_REVIEW_ONLY" in twelfth_message and state.name in twelfth_message, twelfth_message)
    assert_true(any("podo migrate --version 1.0.0" in command for command in commands(twelfth)), str(commands(twelfth)))
    migration_plan = only_plan(plans, "migration")
    assert_true(migration_plan["plan_id"] in twelfth_message, twelfth_message)
    assert_true(installed_version(workspace) == ("0.9.0", "1"), "migration review changed versions")
    assert_true(not list((workspace / ".podo-backups").glob("*")), "migration review created a backup")

    pre_migration = user_evidence(workspace)
    thirteenth = codex_task(
        workspace,
        env,
        f"Exact migration plan {migration_plan['plan_id']} 적용을 명시적으로 승인한다. canonical apply 후 version과 backup을 확인하고 E2E_MIGRATION_APPLIED를 답해.",
    )
    assert_true("E2E_MIGRATION_APPLIED" in messages(thirteenth), messages(thirteenth))
    assert_true(
        any(f"podo migrate --apply {migration_plan['plan_id']}" in command for command in commands(thirteenth)),
        str(commands(thirteenth)),
    )
    assert_true(installed_version(workspace) == ("1.0.0", "2"), "approved migration did not apply")
    assert_true("Format: 2" in state.read_text(encoding="utf-8"), state.read_text(encoding="utf-8"))
    backup = workspace / ".podo-backups" / migration_plan["backup_id"]
    assert_true((backup / "backup.json").is_file(), "migration backup is missing")
    validate(workspace)
    passed.append("migration-review-apply")
    print("PASS real Codex tasks 12-13 separate migration review and exact apply")

    fourteenth = codex_task(
        workspace,
        env,
        f"Migration 뒤 새 task다. 현재 Format과 version을 확인하고 backup {migration_plan['backup_id']}의 full rollback 영향만 canonical command로 계획해. 실행 승인은 아니며 E2E_ROLLBACK_REVIEW_ONLY를 답해.",
    )
    fourteenth_message = messages(fourteenth)
    assert_true(
        "E2E_ROLLBACK_REVIEW_ONLY" in fourteenth_message
        and "Format" in fourteenth_message
        and "2" in fourteenth_message,
        fourteenth_message,
    )
    assert_true(
        any(f"podo migrate rollback --backup {migration_plan['backup_id']}" in command for command in commands(fourteenth)),
        str(commands(fourteenth)),
    )
    rollback_plan = only_plan(plans, "rollback")
    assert_true(rollback_plan["plan_id"] in fourteenth_message, fourteenth_message)
    assert_true(installed_version(workspace) == ("1.0.0", "2"), "rollback review changed versions")
    assert_true(not (workspace / ".podo-backups" / rollback_plan["backup_id"]).exists(), "review created safety backup")

    fifteenth = codex_task(
        workspace,
        env,
        f"Exact full rollback plan {rollback_plan['plan_id']} 적용을 명시적으로 승인한다. canonical apply 후 product와 Workspace를 확인하고 E2E_FULL_ROLLBACK_APPLIED를 답해.",
    )
    assert_true("E2E_FULL_ROLLBACK_APPLIED" in messages(fifteenth), messages(fifteenth))
    assert_true(
        any(f"podo migrate --apply {rollback_plan['plan_id']}" in command for command in commands(fifteenth)),
        str(commands(fifteenth)),
    )
    assert_true(installed_version(workspace) == ("0.9.0", "1"), "full rollback did not restore versions")
    assert_true(user_evidence(workspace) == pre_migration, "full rollback did not restore pre-migration user evidence")
    assert_true((workspace / ".podo-backups" / rollback_plan["backup_id"] / "backup.json").is_file(), "safety backup is missing")
    validate(workspace)
    passed.append("full-rollback")
    print("PASS real Codex tasks 14-15 review then apply exact full rollback")

    final_before = permanent_snapshot(workspace)
    sixteenth = codex_task(
        workspace,
        env,
        f"Full rollback 뒤 새 task다. State 우선으로 현재 결정 marker {RECOVERED}, TODO marker {TODO}의 완료 상태와 product/Workspace version을 확인해. 추가 apply 없이 E2E_FINAL_STATE_OK를 답해.",
    )
    final_message = messages(sixteenth)
    assert_true(
        all(value in final_message for value in (RECOVERED, TODO, "0.9.0", "E2E_FINAL_STATE_OK")),
        final_message,
    )
    assert_true(not any("podo migrate --apply" in command for command in commands(sixteenth)), str(commands(sixteenth)))
    assert_true(permanent_snapshot(workspace) == final_before, "final State-first task changed permanent Context")
    passed.append("post-rollback-state-first")
    print("PASS real Codex task 16 restores final State without another product/data apply")
    return passed


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
    passed: list[str] = []
    try:
        old = synthetic_product(CONTAINER, "0.8.0", [1])
        old_package, old_metadata = package(CONTAINER, old, "1")
        compatible = synthetic_product(CONTAINER, "0.9.0", [1])
        releases, _ = release_tree(CONTAINER, compatible, "2")
        (releases / "latest").write_text("0.9.0\n", encoding="utf-8")
        workspace = CONTAINER / "workspace"
        installed = apply(old_package, old_metadata, workspace)
        assert_true(installed.returncode == 0, installed.stdout + installed.stderr)
        passed = run_acceptance(
            workspace,
            configure(workspace, CONTAINER / "codex-home", releases),
            CONTAINER,
        )
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
    summary = {
        "schema_version": 1,
        "phase": 8,
        "kind": "real-codex-e2e",
        "status": "passed",
        "tasks": 16,
        "steps": passed,
        "desktop_cleanup": "passed",
    }
    print("PHASE8_CODEX_SUMMARY " + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
