#!/usr/bin/env python3
"""Exercise hash-pinned recovery planning and explicitly approved apply."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True
from run_phase5_concurrency import request as concurrency_request  # noqa: E402
from run_phase5_transactions import apply, build, capture, request, run  # noqa: E402
from run_phase4_decisions import (  # noqa: E402
    capture as decision_capture,
    defer_request,
    request_file,
    state_request,
    transcript,
)


def recover(workspace: Path, plan_id: str | None = None):
    command = [str(workspace / ".podo/bin/podo"), "recover", "--json"]
    if plan_id is not None:
        command.extend(["--apply", plan_id])
    result = run(command, cwd=workspace)
    value = json.loads(result.stdout) if result.stdout else None
    return result, value


def snapshot_without_plans(workspace: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace).as_posix()
        if relative.startswith(".podo-work/recovery-plans/"):
            continue
        if path.is_file() and not path.is_symlink():
            values[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def one_plan(value: dict) -> dict:
    plans = value.get("plans", [])
    if len(plans) != 1:
        raise AssertionError(json.dumps(value, ensure_ascii=False, indent=2))
    return plans[0]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase5-recovery-") as temporary:
        root = Path(temporary)

        empty = root / "empty"
        build(empty)
        before = snapshot_without_plans(empty)
        result, value = recover(empty)
        if result.returncode or value["status"] != "nothing-to-recover":
            raise AssertionError(result.stdout + result.stderr)
        if before != snapshot_without_plans(empty):
            raise AssertionError("nothing-to-recover changed Workspace evidence")
        print("PASS recovery planner is inert when no unfinished transaction exists")

        workspace = root / "safe"
        build(workspace)
        state = workspace / "state/synthetic-planning.md"
        capture_id = capture(workspace, root, "safe")
        request_path = request(workspace, "safe", "RECOVERED_SAFE_DECISION")
        interrupted = apply(workspace, capture_id, request_path, "after-delta-1")
        if interrupted.returncode == 0 or "E_INJECTED_FAILURE" not in interrupted.stderr:
            raise AssertionError(interrupted.stdout + interrupted.stderr)
        before_plan = snapshot_without_plans(workspace)
        result, value = recover(workspace)
        plan = one_plan(value)
        if result.returncode or value["status"] != "planned" or plan["action"] != "resume-transaction":
            raise AssertionError(result.stdout + result.stderr)
        if before_plan != snapshot_without_plans(workspace):
            raise AssertionError("recovery planning changed Context or transaction evidence")
        plan_path = workspace / f".podo-work/recovery-plans/{plan['plan_id']}.json"
        stored = json.loads(plan_path.read_text(encoding="utf-8"))
        if not stored["pins"] or state.relative_to(workspace).as_posix() not in stored["pins"]:
            raise AssertionError("recovery plan did not pin affected State")
        print("PASS planner writes only an impact plan pinned to current evidence")

        state_before = state.read_bytes()
        state.write_bytes(state_before + b"\n")
        stale, _ = recover(workspace, plan["plan_id"])
        if stale.returncode == 0 or "E_RECOVERY_PLAN_STALE" not in stale.stderr:
            raise AssertionError(stale.stdout + stale.stderr)
        state.write_bytes(state_before)
        applied, applied_value = recover(workspace, plan["plan_id"])
        if applied.returncode or applied_value["status"] != "applied":
            raise AssertionError(applied.stdout + applied.stderr)
        if "RECOVERED_SAFE_DECISION" not in state.read_text(encoding="utf-8"):
            raise AssertionError("approved recovery did not install staged State")
        if list((workspace / ".podo-work/transactions").glob("*")):
            raise AssertionError("committed recovery left unfinished transaction")
        stable_before = snapshot_without_plans(workspace)
        repeated, repeated_value = recover(workspace, plan["plan_id"])
        if repeated.returncode or repeated_value["status"] != "already-applied":
            raise AssertionError(repeated.stdout + repeated.stderr)
        if stable_before != snapshot_without_plans(workspace):
            raise AssertionError("idempotent recovery replay changed Context")
        print("PASS stale plan is rejected and exact approved plan applies once")

        conflict = root / "conflict"
        build(conflict)
        conflict_state = conflict / "state/synthetic-planning.md"
        base = conflict_state.read_text(encoding="utf-8")
        old = "- 합성 프로젝트 회의는 금요일 오전 9시에 한다."
        first_text = base.replace(old, "- RECOVERY_CONFLICT_A ([Delta]({{DELTA_LINK}}))")
        second_text = base.replace(old, "- RECOVERY_CONFLICT_B ([Delta]({{DELTA_LINK}}))")
        first_capture = capture(conflict, root, "conflict-first")
        first_request = concurrency_request(conflict, "conflict-first", first_text)
        if apply(conflict, first_capture, first_request, "after-prepared").returncode == 0:
            raise AssertionError("conflict transaction was not interrupted")
        second_capture = capture(conflict, root, "conflict-second")
        second_request = concurrency_request(conflict, "conflict-second", second_text)
        second = apply(conflict, second_capture, second_request)
        if second.returncode:
            raise AssertionError(second.stdout + second.stderr)
        current = conflict_state.read_bytes()
        result, value = recover(conflict)
        plan = one_plan(value)
        if result.returncode == 0 or value["status"] != "manual-required" or plan["action"] != "manual-confirmation-required":
            raise AssertionError(result.stdout + result.stderr)
        blocked, _ = recover(conflict, plan["plan_id"])
        if blocked.returncode == 0 or "E_RECOVERY_MANUAL_REQUIRED" not in blocked.stderr:
            raise AssertionError(blocked.stdout + blocked.stderr)
        if conflict_state.read_bytes() != current or "RECOVERY_CONFLICT_B" not in conflict_state.read_text(encoding="utf-8"):
            raise AssertionError("manual conflict changed current State")
        print("PASS overlapping State recovery remains manual and preserves current State")

        resolution = root / "resolution"
        build(resolution)
        deferred_session, deferred_turn = "recovery-deferred-session", "recovery-deferred-turn"
        deferred_id = decision_capture(
            resolution,
            transcript(root, deferred_session, deferred_turn),
            deferred_session,
            deferred_turn,
        )
        deferred_request = request_file(resolution, "recovery-defer", defer_request())
        deferred_result = run(
            [
                str(resolution / ".podo/bin/podo"),
                "context",
                "defer",
                "--capture",
                deferred_id,
                "--request",
                str(deferred_request),
            ],
            cwd=resolution,
        )
        if deferred_result.returncode:
            raise AssertionError(deferred_result.stdout + deferred_result.stderr)
        answer_session, answer_turn = "recovery-answer-session", "recovery-answer-turn"
        answer_id = decision_capture(
            resolution,
            transcript(root, answer_session, answer_turn),
            answer_session,
            answer_turn,
        )
        resolution_request = request_file(
            resolution,
            "recovery-confirmed",
            state_request(resolution, "합성 프로젝트 회의는 복구 후 오전 10시에 한다."),
        )
        failure_env = os.environ.copy()
        failure_env.update({"PODO_TEST_FAILURES": "1", "PODO_TEST_FAIL_AT": "after-receipt-1"})
        failed_resolution = run(
            [
                str(resolution / ".podo/bin/podo"),
                "context",
                "resolve",
                "--deferred",
                deferred_id,
                "--capture",
                answer_id,
                "--decision",
                "confirmed",
                "--request",
                str(resolution_request),
            ],
            cwd=resolution,
            env=failure_env,
        )
        if failed_resolution.returncode == 0 or "E_INJECTED_FAILURE" not in failed_resolution.stderr:
            raise AssertionError(failed_resolution.stdout + failed_resolution.stderr)
        if not (resolution / f".podo-work/receipts/{answer_id}.json").is_file():
            raise AssertionError("first resolution receipt was not installed before failure")
        if (resolution / f".podo-work/receipts/{deferred_id}.json").exists():
            raise AssertionError("second resolution receipt unexpectedly existed before recovery")
        result, value = recover(resolution)
        resolution_plan = one_plan(value)
        if result.returncode or resolution_plan["action"] != "resume-transaction":
            raise AssertionError(result.stdout + result.stderr)
        applied, _ = recover(resolution, resolution_plan["plan_id"])
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        old_receipt = json.loads(
            (resolution / f".podo-work/receipts/{deferred_id}.json").read_text(encoding="utf-8")
        )
        if old_receipt.get("outcome") != "confirmed" or old_receipt.get("resolved_by_capture") != answer_id:
            raise AssertionError(str(old_receipt))
        if (resolution / f".podo-work/inbox/{answer_id}").exists() or (resolution / f".podo-work/deferred/{deferred_id}.json").exists():
            raise AssertionError("resolution recovery did not perform validated cleanup")
        print("PASS recovery completes the second resolution receipt before cleanup")


if __name__ == "__main__":
    main()
