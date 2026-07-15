#!/usr/bin/env python3
"""Run one connected stale-write, interruption, diagnosis, and recovery journey."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


from phase8_support import EvidenceLedger, capture, cli, context_snapshot, request_file, sha256
from run_phase6_package_install import build_and_extract, install


BASE = "RECOVERY_BASELINE"
WINNER = "CONCURRENT_WINNER"
LOSER = "CONCURRENT_STALE_LOSER"
RECOVERED = "INTERRUPTED_CHANGE_RECOVERED"


def state_markdown(marker: str, *, updated: str) -> str:
    return "\n".join(
        [
            "# Recovery Planning",
            "",
            f"Updated: {updated}",
            "",
            "## Current Context",
            "",
            "Phase 8 failure and recovery journey다.",
            "",
            "## Current Decisions",
            "",
            f"- {marker}",
            "",
            "## Reasons",
            "",
            "- [Relevant Delta]({{DELTA_LINK}})",
            "",
        ]
    )


def change_request(workspace: Path, name: str, marker: str, expected: str | None) -> Path:
    value = {
        "event": {"title": f"Recovery journey {name}", "context": "Phase 8 synthetic recovery."},
        "updates": [
            {
                "state_slug": "recovery-planning",
                "expected_state_sha256": expected,
                "delta_title": f"Recovery journey {name}",
                "changed": f"- {marker}",
                "why": "사용자가 synthetic recovery fixture에서 명확히 결정했다.",
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "state_markdown": state_markdown(marker, updated="2026-07-15"),
            }
        ],
    }
    return request_file(workspace, name, value)


def apply(
    workspace: Path,
    capture_id: str,
    request: Path,
    *,
    fail_at: str | None = None,
):
    env = os.environ.copy()
    if fail_at is not None:
        env.update({"PODO_TEST_FAILURES": "1", "PODO_TEST_FAIL_AT": fail_at})
    return cli(
        workspace,
        "context",
        "apply",
        "--capture",
        capture_id,
        "--request",
        str(request),
        env=env,
    )


def doctor(workspace: Path) -> tuple[object, dict]:
    result = cli(workspace, "doctor", "--json")
    return result, json.loads(result.stdout)


def codes(report: dict) -> set[str]:
    return {str(value["code"]) for value in report["findings"]}


def snapshot_without_plans(workspace: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace).as_posix()
        if relative.startswith(".podo-work/recovery-plans/"):
            continue
        if path.is_file() and not path.is_symlink():
            result[relative] = sha256(path)
    return result


def run_journey(run_id: str, ledger: EvidenceLedger | None = None) -> dict:
    ledger = ledger or EvidenceLedger("recovery", run_id)
    with tempfile.TemporaryDirectory(prefix=f"podo-phase8-recovery-{run_id}-") as temporary:
        root = Path(temporary)
        package, metadata = build_and_extract(root)
        workspace = root / "workspace"
        installed = install(package, metadata, workspace)
        if installed.returncode:
            raise AssertionError(installed.stdout + installed.stderr)

        base_id, _ = capture(workspace, root, "recovery-base")
        created = apply(workspace, base_id, change_request(workspace, "recovery-base", BASE, None))
        if created.returncode:
            raise AssertionError(created.stdout + created.stderr)
        state = workspace / "state/recovery-planning.md"
        baseline_hash = sha256(state)
        ledger.passed(
            "recovery-baseline",
            ("5", "7"),
            "valid traceable Context created before failure injection",
            f"baseline State hash {baseline_hash}",
        )

        winner_id, _ = capture(workspace, root, "concurrent-winner")
        loser_id, _ = capture(workspace, root, "concurrent-loser")
        winner_request = change_request(workspace, "concurrent-winner", WINNER, baseline_hash)
        loser_request = change_request(workspace, "concurrent-loser", LOSER, baseline_hash)
        winner = apply(workspace, winner_id, winner_request)
        if winner.returncode:
            raise AssertionError(winner.stdout + winner.stderr)
        after_winner = context_snapshot(workspace)
        stale = apply(workspace, loser_id, loser_request)
        if stale.returncode == 0 or "E_STATE_STALE" not in stale.stderr:
            raise AssertionError(stale.stdout + stale.stderr)
        if context_snapshot(workspace) != after_winner:
            raise AssertionError("stale concurrent update changed permanent Context")
        discarded = cli(
            workspace,
            "context",
            "discard",
            "--capture",
            loser_id,
            "--reason",
            "no-delta",
        )
        if discarded.returncode:
            raise AssertionError(discarded.stdout + discarded.stderr)
        current_text = state.read_text(encoding="utf-8")
        if WINNER not in current_text or LOSER in current_text:
            raise AssertionError(current_text)
        ledger.passed(
            "stale-concurrency",
            ("11",),
            "first exact State evidence committed",
            "second stale evidence rejected without permanent writes",
        )

        interrupted_id, _ = capture(workspace, root, "interrupted")
        interrupted_request = change_request(workspace, "interrupted", RECOVERED, sha256(state))
        interrupted = apply(
            workspace,
            interrupted_id,
            interrupted_request,
            fail_at="after-delta-1",
        )
        if interrupted.returncode == 0 or "E_INJECTED_FAILURE" not in interrupted.stderr:
            raise AssertionError(interrupted.stdout + interrupted.stderr)
        transactions = sorted((workspace / ".podo-work/transactions").glob("context-*"))
        if len(transactions) != 1:
            raise AssertionError(f"expected one interrupted transaction, found {transactions}")
        state_after_failure = state.read_bytes()
        result, report = doctor(workspace)
        inbox_result = cli(workspace, "inbox", "--json")
        inbox = json.loads(inbox_result.stdout)
        if result.returncode == 0 or "PODO_D001_TRANSACTION_INCOMPLETE" not in codes(report):
            raise AssertionError(json.dumps(report, ensure_ascii=False, indent=2))
        if not inbox["recovery_required"] or inbox["recovery_diagnosis"] is None:
            raise AssertionError(inbox_result.stdout + inbox_result.stderr)
        if RECOVERED in state.read_text(encoding="utf-8"):
            raise AssertionError("interrupted State became current before recovery")
        ledger.passed(
            "interruption-diagnosis",
            ("5", "11"),
            "failure journal retained after Delta boundary",
            "doctor and startup expose recovery-required",
            "current State remains the concurrent winner",
        )

        before_plan = snapshot_without_plans(workspace)
        planned = cli(workspace, "recover", "--json")
        if planned.returncode:
            raise AssertionError(planned.stdout + planned.stderr)
        planned_value = json.loads(planned.stdout)
        plans = planned_value.get("plans", [])
        if planned_value.get("status") != "planned" or len(plans) != 1:
            raise AssertionError(planned.stdout)
        plan = plans[0]
        if plan.get("action") != "resume-transaction":
            raise AssertionError(planned.stdout)
        if snapshot_without_plans(workspace) != before_plan or state.read_bytes() != state_after_failure:
            raise AssertionError("recovery planning changed transaction or Context evidence")
        exact = cli(workspace, "recover", "--json", "--apply", plan["plan_id"])
        if exact.returncode:
            raise AssertionError(exact.stdout + exact.stderr)
        exact_value = json.loads(exact.stdout)
        if exact_value.get("status") != "applied" or RECOVERED not in state.read_text(encoding="utf-8"):
            raise AssertionError(exact.stdout + state.read_text(encoding="utf-8"))
        if list((workspace / ".podo-work/transactions").glob("*")):
            raise AssertionError("approved recovery left an unfinished transaction")
        result, report = doctor(workspace)
        if result.returncode or report["status"] != "healthy":
            raise AssertionError(json.dumps(report, ensure_ascii=False, indent=2))
        ledger.passed(
            "exact-recovery",
            ("11",),
            "planning changed only a recovery-plan artifact",
            "exact approved plan completed the interrupted State",
            "post-recovery doctor is healthy",
        )

        damaged = root / "damaged-workspace"
        shutil.copytree(workspace, damaged)
        event_metadata = sorted((damaged / "events").glob("*/*/*/metadata.md"))[0]
        fields = {}
        for line in event_metadata.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator:
                fields[key] = value.strip()
        original = event_metadata.parent / fields["Original-Entrypoint"]
        original.unlink()
        damaged_state = damaged / "state/recovery-planning.md"
        damaged_state.write_text(
            damaged_state.read_text(encoding="utf-8").replace(
                "[Relevant Delta](",
                "[Relevant Delta](missing/",
                1,
            ),
            encoding="utf-8",
        )
        before_doctor = snapshot_without_plans(damaged)
        damaged_result, damaged_report = doctor(damaged)
        damaged_codes = codes(damaged_report)
        expected = {"PODO_D100_E_EVENT_ORIGINAL", "PODO_D100_E_STATE_LINK"}
        if damaged_result.returncode == 0 or not expected.issubset(damaged_codes):
            raise AssertionError(json.dumps(damaged_report, ensure_ascii=False, indent=2))
        if snapshot_without_plans(damaged) != before_doctor:
            raise AssertionError("doctor changed missing-original or broken-link evidence")
        automatic = cli(damaged, "recover", "--json")
        automatic_value = json.loads(automatic.stdout)
        if automatic.returncode or automatic_value.get("status") != "nothing-to-recover":
            raise AssertionError(automatic.stdout + automatic.stderr)
        ledger.passed(
            "damage-diagnosis",
            ("11",),
            "missing Event original and broken State link reported separately",
            "doctor remained read-only",
            "damage was not guessed into an automatic recovery",
        )

        final_hash = hashlib.sha256(state.read_bytes()).hexdigest()
        ledger.passed(
            "recovery-final",
            ("11",),
            f"recovered State hash {final_hash}",
            "healthy source Workspace preserved beside isolated damage fixture",
        )
    ledger.emit()
    return ledger.value()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="standalone")
    args = parser.parse_args()
    ledger = EvidenceLedger("recovery", args.run_id)
    try:
        run_journey(args.run_id, ledger)
    except Exception as error:
        ledger.failed(
            "journey-failure",
            (),
            f"{type(error).__name__} stopped the disposable journey",
            "temporary Workspace cleanup runs before process exit",
        )
        ledger.emit()
        raise


if __name__ == "__main__":
    main()
