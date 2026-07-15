#!/usr/bin/env python3
"""Run one connected install, Context, decision, and TODO user journey."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tempfile
from pathlib import Path


from phase8_support import EvidenceLedger, capture, cli, context_snapshot, request_file, sha256
from run_phase6_package_install import build_and_extract, install


DECISION_09 = "ORCHARD_REVIEW_AT_09"
DECISION_10 = "ORCHARD_REVIEW_AT_10"
TODO_PREPARE = "PREPARE_ORCHARD_PACKET"
TODO_SEND = "SEND_ORCHARD_PACKET"


def state_markdown(decision: str, todo_lines: list[str], *, updated: str) -> str:
    return "\n".join(
        [
            "# Orchard Planning",
            "",
            f"Updated: {updated}",
            "",
            "## Current Context",
            "",
            "Phase 8 synthetic everyday journey다.",
            "",
            "## Current Decisions",
            "",
            f"- {decision}",
            "",
            "## TODO",
            "",
            *todo_lines,
            "",
            "## Reasons",
            "",
            "- [Relevant Delta]({{DELTA_LINK}})",
            "",
        ]
    )


def context_request(
    workspace: Path,
    *,
    title: str,
    decision: str,
    todo_lines: list[str],
    expected: str | None,
    why: str,
    updated: str,
) -> dict:
    return {
        "event": {"title": title, "context": "Phase 8 connected synthetic user journey."},
        "updates": [
            {
                "state_slug": "orchard-planning",
                "expected_state_sha256": expected,
                "delta_title": title,
                "changed": f"- Current decision: {decision}",
                "why": why,
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "state_markdown": state_markdown(decision, todo_lines, updated=updated),
            }
        ],
    }


def apply_request(workspace: Path, capture_id: str, path: Path) -> dict:
    result = cli(workspace, "context", "apply", "--capture", capture_id, "--request", str(path))
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def todo_active() -> list[str]:
    return [
        f"- [ ] {TODO_PREPARE}",
        "  - Created: 2026-07-15",
        "  - Due: 2026-07-20",
    ]


def run_journey(run_id: str) -> dict:
    ledger = EvidenceLedger("everyday", run_id)
    with tempfile.TemporaryDirectory(prefix=f"podo-phase8-everyday-{run_id}-") as temporary:
        root = Path(temporary)
        package, metadata = build_and_extract(root)
        workspace = root / "workspace"
        installed = install(package, metadata, workspace)
        if installed.returncode or "INSTALLED" not in installed.stdout:
            raise AssertionError(installed.stdout + installed.stderr)
        version = cli(workspace, "version")
        if version.returncode or "Podo 0.6.0 (Workspace 1)" not in version.stdout:
            raise AssertionError(version.stdout + version.stderr)
        ledger.passed(
            "install",
            ("3", "8"),
            "release package installed into an empty Workspace",
            "product 0.6.0 and Workspace 1 verified",
        )

        product_before = context_snapshot(workspace)
        config = workspace / "user_config.md"
        config.write_text(
            """# User Configuration

- Assistant name: 통합포도
- Personality: 차분하고 확인된 내용과 추론을 분리함
- Response style: marker와 날짜를 보존하며 간결하게 답함

## Explicit Defaults

- 합성 Phase 8 데이터만 사용한다.

## Allowed External Sources

- 없음.
""",
            encoding="utf-8",
        )
        config.chmod(0o640)
        if context_snapshot(workspace) != product_before or stat.S_IMODE(config.stat().st_mode) != 0o640:
            raise AssertionError("explicit personalization changed Context or lost the requested mode")
        ledger.passed(
            "personalize",
            ("4", "6"),
            "explicit assistant name and response preferences stored",
            "permanent Context remained unchanged",
        )

        first_id, first_source = capture(workspace, root, "first-context")
        first_request = request_file(
            workspace,
            "first-context",
            context_request(
                workspace,
                title="Create orchard decision and TODO",
                decision=DECISION_09,
                todo_lines=todo_active(),
                expected=None,
                why="사용자가 결정, TODO 위치와 날짜를 명확히 확정했다.",
                updated="2026-07-15",
            ),
        )
        first = apply_request(workspace, first_id, first_request)
        state = workspace / "state/orchard-planning.md"
        state_text = state.read_text(encoding="utf-8")
        if not all(marker in state_text for marker in (DECISION_09, TODO_PREPARE, "2026-07-20")):
            raise AssertionError(state_text)
        event = workspace / first["event"]
        original = event.parent / "original/session.jsonl"
        delta = workspace / first["deltas"][0]
        if original.read_bytes() != first_source.read_bytes() or delta.name not in state_text:
            raise AssertionError("first Context traceability is incomplete")
        ledger.passed(
            "first-context",
            ("5", "7", "9"),
            "one exact Event original promoted",
            "one linked Delta and State created",
            "decision and dated TODO are current",
        )

        before_no_delta = context_snapshot(workspace)
        no_delta_id, _ = capture(workspace, root, "no-delta")
        discarded = cli(
            workspace,
            "context",
            "discard",
            "--capture",
            no_delta_id,
            "--reason",
            "no-delta",
        )
        if discarded.returncode or json.loads(discarded.stdout).get("outcome") != "no-delta":
            raise AssertionError(discarded.stdout + discarded.stderr)
        if context_snapshot(workspace) != before_no_delta:
            raise AssertionError("No Delta changed permanent Context")
        ledger.passed(
            "no-delta",
            ("5", "9"),
            "no-delta receipt recorded",
            "Event, Delta and State hashes unchanged",
        )

        deferred_id, deferred_source = capture(workspace, root, "uncertain-conflict")
        defer_path = request_file(
            workspace,
            "uncertain-conflict",
            {
                "summary": f"{DECISION_09} 대신 {DECISION_10}을 사용할 가능성이 있지만 확정되지 않았다.",
                "why_confirmation": "현재 결정과 충돌하며 사용자가 변경을 확정하지 않았다.",
                "question": f"현재 결정을 {DECISION_10}으로 바꿀까요?",
                "state_candidates": ["orchard-planning"],
            },
        )
        before_defer = context_snapshot(workspace)
        deferred = cli(
            workspace,
            "context",
            "defer",
            "--capture",
            deferred_id,
            "--request",
            str(defer_path),
        )
        if deferred.returncode or json.loads(deferred.stdout).get("status") != "deferred":
            raise AssertionError(deferred.stdout + deferred.stderr)
        if context_snapshot(workspace) != before_defer or DECISION_09 not in state.read_text(encoding="utf-8"):
            raise AssertionError("uncertain conflict changed current State")
        ledger.passed(
            "defer-conflict",
            ("4", "9"),
            "conflict deferred exactly once",
            "current decision hash preserved",
        )

        answer_id, answer_source = capture(workspace, root, "confirm-conflict")
        resolve_path = request_file(
            workspace,
            "confirm-conflict",
            context_request(
                workspace,
                title="Confirm orchard time change",
                decision=DECISION_10,
                todo_lines=todo_active(),
                expected=sha256(state),
                why="사용자가 보류된 시간 변경을 후속 turn에서 명확히 확정했다.",
                updated="2026-07-16",
            ),
        )
        resolved = cli(
            workspace,
            "context",
            "resolve",
            "--deferred",
            deferred_id,
            "--capture",
            answer_id,
            "--decision",
            "confirmed",
            "--request",
            str(resolve_path),
        )
        if resolved.returncode:
            raise AssertionError(resolved.stdout + resolved.stderr)
        resolved_value = json.loads(resolved.stdout)
        metadata = workspace / resolved_value["event"]
        metadata_text = metadata.read_text(encoding="utf-8")
        related = metadata.parent / f"original/related/{deferred_id}/session.jsonl"
        current = state.read_text(encoding="utf-8")
        if DECISION_10 not in current or DECISION_09 in current:
            raise AssertionError(current)
        if answer_source.read_bytes() != (metadata.parent / "original/session.jsonl").read_bytes():
            raise AssertionError("confirmation Event lost its exact original")
        if deferred_source.read_bytes() != related.read_bytes():
            raise AssertionError("resolution Event lost the deferred original")
        if f"Resolves-Capture: {deferred_id}" not in metadata_text:
            raise AssertionError(metadata_text)
        ledger.passed(
            "resolve-conflict",
            ("4", "5", "7", "9"),
            "exact follow-up confirmation replaced the old decision",
            "confirmation and deferred originals remain linked",
        )

        lifecycle_id, _ = capture(workspace, root, "todo-terminal")
        terminal_lines = [
            f"- [x] {TODO_PREPARE}",
            "  - Created: 2026-07-15",
            "  - Due: 2026-07-20",
            "  - Completed: 2026-07-17",
            "  - Result: 합성 packet을 준비했다.",
            f"- [x] {TODO_SEND}",
            "  - Created: 2026-07-16",
            "  - Cancelled: 2026-07-17",
            "  - Result: 일정 변경으로 전송하지 않는다.",
        ]
        lifecycle_path = request_file(
            workspace,
            "todo-terminal",
            context_request(
                workspace,
                title="Complete and cancel orchard TODOs",
                decision=DECISION_10,
                todo_lines=terminal_lines,
                expected=sha256(state),
                why="사용자가 두 TODO의 완료와 취소 결과를 명확히 알렸다.",
                updated="2026-07-17",
            ),
        )
        apply_request(workspace, lifecycle_id, lifecycle_path)

        reopen_id, _ = capture(workspace, root, "todo-reopen")
        reopened_lines = [
            *terminal_lines[:5],
            f"- [ ] {TODO_SEND}",
            "  - Created: 2026-07-16",
            "  - Cancelled: 2026-07-17",
            "  - Reopened: 2026-07-18",
        ]
        reopen_path = request_file(
            workspace,
            "todo-reopen",
            context_request(
                workspace,
                title="Reopen orchard send TODO",
                decision=DECISION_10,
                todo_lines=reopened_lines,
                expected=sha256(state),
                why="사용자가 취소했던 전송 TODO를 명확히 다시 열었다.",
                updated="2026-07-18",
            ),
        )
        apply_request(workspace, reopen_id, reopen_path)
        final_text = state.read_text(encoding="utf-8")
        if not all(
            marker in final_text
            for marker in ("Completed: 2026-07-17", "Cancelled: 2026-07-17", "Reopened: 2026-07-18")
        ):
            raise AssertionError(final_text)
        ledger.passed(
            "todo-lifecycle",
            ("7", "9"),
            "completed TODO retains Created, Due, Completed and Result",
            "cancelled TODO reopened with both terminal and reopen dates",
        )

        validated = cli(workspace, "validate")
        doctor = cli(workspace, "doctor", "--json")
        inbox = cli(workspace, "inbox", "--json")
        if validated.returncode or doctor.returncode or inbox.returncode:
            raise AssertionError(validated.stdout + validated.stderr + doctor.stdout + doctor.stderr + inbox.stderr)
        doctor_value = json.loads(doctor.stdout)
        inbox_value = json.loads(inbox.stdout)
        if doctor_value["status"] != "healthy" or inbox_value["pending"] or inbox_value["deferred"]:
            raise AssertionError(json.dumps({"doctor": doctor_value, "inbox": inbox_value}, ensure_ascii=False))
        receipts = sorted((workspace / ".podo-work/receipts").glob("*.json"))
        final_hash = hashlib.sha256(state.read_bytes()).hexdigest()
        ledger.passed(
            "final-health",
            ("5", "11"),
            f"healthy Workspace with {len(receipts)} lifecycle receipts",
            f"final State hash {final_hash}",
            "pending and deferred inboxes are empty",
        )
    ledger.emit()
    return ledger.value()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="standalone")
    args = parser.parse_args()
    run_journey(args.run_id)


if __name__ == "__main__":
    main()
