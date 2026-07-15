#!/usr/bin/env python3
"""Verify migration and full rollback approval boundaries across real Codex tasks."""

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


ROOT = Path(__file__).resolve().parents[1]
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
TEST_PARENT = Path("/Users/hj/Desktop/podo-test-workspaces")
SUITE = "realpodo-phase7-codex-migration"
RUN_ID = f"{os.getpid()}-{time.time_ns()}"
CONTAINER = TEST_PARENT / f"{RUN_ID}-codex-migration"
MARKER = ".podo-phase7-codex-test.json"

from run_phase6_product_update import apply, package, synthetic_product  # noqa: E402
from run_phase7_planning import add_migration, release_tree  # noqa: E402


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


def configure(workspace: Path, codex_home: Path, releases: Path) -> dict[str, str]:
    (workspace / "user_config.md").write_text(
        """# User Configuration

- Assistant name: 이전검증포도
- Personality: 영향 설명과 승인을 분리하고 확인된 결과만 보고함
- Response style: 요청된 acceptance marker와 핵심 version, plan, backup만 간결하게 답함

## Explicit Defaults

- 합성 acceptance 데이터만 사용한다.
- 일반 update 요청은 Workspace migration 승인이 아니다.

## Allowed External Sources

- 현재 테스트가 지정한 synthetic Podo Release
""",
        encoding="utf-8",
    )
    (workspace / "user_config.md").chmod(0o640)
    state = workspace / "state/project.md"
    state.write_text(
        "# Synthetic Project\n\nUpdated: 2026-07-15\n\n## Current Context\n\nCODEX_MIGRATION_ORIGINAL\n",
        encoding="utf-8",
    )
    state.chmod(0o600)
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
    return [str(item.get("command") or "") for item in items(result, "command_execution")]


def installed_version(workspace: Path) -> tuple[str, str]:
    return (
        (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip(),
        (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip(),
    )


def file_value(path: Path) -> tuple[str, int]:
    return hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode)


def only_plan(directory: Path, prefix: str) -> dict:
    paths = sorted(directory.glob(f"{prefix}-*.json"))
    assert_true(len(paths) == 1, f"expected one {prefix} plan: {paths}")
    return json.loads(paths[0].read_text(encoding="utf-8"))


def validate(workspace: Path) -> None:
    result = run([str(workspace / ".podo/bin/podo"), "validate"], cwd=workspace)
    assert_true(result.returncode == 0, result.stdout + result.stderr)


def run_acceptance(workspace: Path, env: dict[str, str]) -> None:
    original_state = file_value(workspace / "state/project.md")
    original_config = file_value(workspace / "user_config.md")

    first = codex_task(
        workspace,
        env,
        "Podo를 최신 제품으로 업데이트해줘. Workspace migration의 검토나 적용은 요청하지 않는다. "
        "호환되지 않아 migration이 필요하면 일반 update만 중단하고 UPDATE_STOPPED_NO_MIGRATION을 포함해 답해.",
    )
    assert_true("UPDATE_STOPPED_NO_MIGRATION" in messages(first), messages(first))
    assert_true(any(".podo/bin/podo update" in command for command in commands(first)), str(commands(first)))
    assert_true(installed_version(workspace) == ("0.9.0", "1"), "update-only task changed versions")
    plan_directory = workspace / ".podo-work/migration-plans"
    assert_true(not plan_directory.exists() or not list(plan_directory.glob("*.json")), "update-only task created migration plan")
    assert_true(not list((workspace / ".podo-backups").glob("*")), "update-only task created backup")
    print("PASS real Codex update-only request stops without migration plan or apply")

    second = codex_task(
        workspace,
        env,
        "Target Podo 1.0.0의 Workspace migration 영향만 검토해줘. product update policy의 canonical plan command를 사용해 "
        "변경 이유, 영향 파일, backup과 rollback 조건을 보여줘. 적용 승인은 아니며 PLAN_REVIEW_ONLY를 포함해 답해.",
    )
    second_message = messages(second)
    assert_true("PLAN_REVIEW_ONLY" in second_message and "state/project.md" in second_message, second_message)
    assert_true(any("podo migrate --version 1.0.0" in command for command in commands(second)), str(commands(second)))
    migration_plan = only_plan(plan_directory, "migration")
    assert_true(migration_plan["plan_id"] in second_message, second_message)
    assert_true(installed_version(workspace) == ("0.9.0", "1"), "plan review changed versions")
    assert_true(not list((workspace / ".podo-backups").glob("*")), "plan review created backup")
    print("PASS real Codex migration review creates only an exact impact plan")

    third = codex_task(
        workspace,
        env,
        f"방금 검토한 exact migration plan {migration_plan['plan_id']}의 적용을 명시적으로 승인한다. "
        "canonical apply command로 실행하고 version과 backup을 확인해. MIGRATION_APPLIED와 새 task 안내를 포함해 답해.",
    )
    third_message = messages(third)
    assert_true("MIGRATION_APPLIED" in third_message and "1.0.0" in third_message, third_message)
    assert_true(
        any(f"podo migrate --apply {migration_plan['plan_id']}" in command for command in commands(third)),
        str(commands(third)),
    )
    assert_true(installed_version(workspace) == ("1.0.0", "2"), "approved migration did not apply")
    assert_true("Format: 2" in (workspace / "state/project.md").read_text(encoding="utf-8"), "State was not migrated")
    assert_true(file_value(workspace / "user_config.md") == original_config, "migration changed user config")
    backup = workspace / ".podo-backups" / migration_plan["backup_id"]
    assert_true((backup / "backup.json").is_file(), "approved migration backup is missing")
    validate(workspace)
    print("PASS real Codex exact migration approval applies product and data together")

    fourth = codex_task(
        workspace,
        env,
        f"업데이트 뒤 새 task다. startup policy를 수행하고 migrated State의 Format과 product/Workspace version을 확인해. "
        f"그 다음 backup {migration_plan['backup_id']}의 full rollback 영향만 canonical command로 계획해. "
        "rollback 실행 승인은 아니며 ROLLBACK_REVIEW_ONLY를 포함해 답해.",
    )
    fourth_message = messages(fourth)
    assert_true(
        "ROLLBACK_REVIEW_ONLY" in fourth_message and "Format: 2" in fourth_message,
        fourth_message,
    )
    assert_true(
        any(f"podo migrate rollback --backup {migration_plan['backup_id']}" in command for command in commands(fourth)),
        str(commands(fourth)),
    )
    rollback_plan = only_plan(plan_directory, "rollback")
    assert_true(rollback_plan["plan_id"] in fourth_message, fourth_message)
    assert_true(installed_version(workspace) == ("1.0.0", "2"), "rollback review changed versions")
    assert_true(not (workspace / ".podo-backups" / rollback_plan["backup_id"]).exists(), "rollback review created safety backup")
    print("PASS new real Codex task reads migrated State and creates rollback plan only")

    fifth = codex_task(
        workspace,
        env,
        f"Exact full rollback plan {rollback_plan['plan_id']}의 적용을 명시적으로 승인한다. canonical apply command를 사용하고 "
        "이전 product와 Workspace가 함께 복원됐는지 확인해. FULL_ROLLBACK_APPLIED와 새 task 안내를 포함해 답해.",
    )
    fifth_message = messages(fifth)
    assert_true("FULL_ROLLBACK_APPLIED" in fifth_message and "0.9.0" in fifth_message, fifth_message)
    assert_true(
        any(f"podo migrate --apply {rollback_plan['plan_id']}" in command for command in commands(fifth)),
        str(commands(fifth)),
    )
    assert_true(installed_version(workspace) == ("0.9.0", "1"), "approved full rollback did not restore versions")
    assert_true(file_value(workspace / "state/project.md") == original_state, "full rollback did not restore original State")
    assert_true((workspace / ".podo-backups" / rollback_plan["backup_id"] / "backup.json").is_file(), "safety backup missing")
    validate(workspace)
    print("PASS real Codex exact full rollback approval restores old product and data")

    sixth = codex_task(
        workspace,
        env,
        "Full rollback 뒤 새 task다. startup policy를 수행하고 현재 State marker와 product/Workspace version을 확인해. "
        "추가 migration이나 rollback은 실행하지 말고 POST_ROLLBACK_STARTUP_OK를 포함해 답해.",
    )
    sixth_message = messages(sixth)
    assert_true(
        "POST_ROLLBACK_STARTUP_OK" in sixth_message
        and "CODEX_MIGRATION_ORIGINAL" in sixth_message
        and "0.9.0" in sixth_message,
        sixth_message,
    )
    assert_true(not any("podo migrate --apply" in command for command in commands(sixth)), str(commands(sixth)))
    assert_true(installed_version(workspace) == ("0.9.0", "1"), "post-rollback task changed versions")
    assert_true(file_value(workspace / "user_config.md") == original_config, "acceptance changed user config")
    validate(workspace)
    print("PASS post-rollback real Codex task starts from restored State without another apply")


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
    try:
        old_product = synthetic_product(CONTAINER, "0.9.0", [1])
        old_package, old_metadata = package(CONTAINER, old_product, "1")
        target_product = synthetic_product(CONTAINER, "1.0.0", [2])
        add_migration(target_product, 1, 2)
        releases, _target_metadata = release_tree(CONTAINER, target_product, "2")
        (releases / "latest").write_text("1.0.0\n", encoding="utf-8")
        workspace = CONTAINER / "workspace"
        installed = apply(old_package, old_metadata, workspace)
        assert_true(installed.returncode == 0, installed.stdout + installed.stderr)
        codex_home = CONTAINER / "codex-home"
        run_acceptance(workspace, configure(workspace, codex_home, releases))
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
    print("PASS Phase 7 real Codex Desktop artifacts cleaned")


if __name__ == "__main__":
    main()
