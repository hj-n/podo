#!/usr/bin/env python3
"""Verify that Podo doctor is read-only and reports distinct recovery evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL = REPO_ROOT / "tools/install_local.py"
FIXTURE = REPO_ROOT / "tests/fixtures/codex_transcript_0.144.0-alpha.4.jsonl"


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def install(workspace: Path) -> None:
    result = run([sys.executable, str(INSTALL), "--workspace", str(workspace)])
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def capture(workspace: Path, source_root: Path, name: str) -> str:
    session = f"doctor-session-{name}"
    turn = f"doctor-turn-{name}"
    source = source_root / f"{session}--{turn}.jsonl"
    source.write_text(
        FIXTURE.read_text(encoding="utf-8")
        .replace("synthetic-session-001", session)
        .replace("synthetic-turn-001", turn),
        encoding="utf-8",
    )
    payload = {
        "hook_event_name": "Stop",
        "session_id": session,
        "turn_id": turn,
        "transcript_path": str(source),
        "cwd": str(workspace),
        "model": "synthetic-model",
    }
    result = run([str(workspace / ".podo/scripts/capture_event")], cwd=workspace, input=json.dumps(payload))
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return f"{session}--{turn}"


def snapshot(workspace: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if path.is_file() and not path.is_symlink():
            values[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def doctor(workspace: Path) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = run([str(workspace / ".podo/bin/podo"), "doctor", "--json"], cwd=workspace)
    return result, json.loads(result.stdout)


def codes(report: dict) -> set[str]:
    return {str(item["code"]) for item in report["findings"]}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase5-doctor-") as temporary:
        root = Path(temporary)

        healthy = root / "healthy"
        install(healthy)
        capture(healthy, root, "healthy")
        before = snapshot(healthy)
        result, report = doctor(healthy)
        after = snapshot(healthy)
        if result.returncode or report["status"] != "healthy" or report["findings"]:
            raise AssertionError(result.stdout + result.stderr)
        if before != after:
            raise AssertionError("doctor changed Workspace files")
        print("PASS doctor reports a verified installed Workspace as healthy without writes")

        interrupted = root / "interrupted"
        install(interrupted)
        capture_id = capture(interrupted, root, "interrupted")
        request = interrupted / ".podo-work/requests/interrupted.json"
        request.parent.mkdir(parents=True)
        request.write_text(
            json.dumps(
                {
                    "event": {"title": "Doctor interrupted transaction", "context": "synthetic fixture"},
                    "updates": [
                        {
                            "state_slug": "doctor-fixture",
                            "expected_state_sha256": None,
                            "delta_title": "Doctor fixture decision",
                            "changed": "- 복구 진단용 합성 결정을 기록한다.",
                            "why": "Phase 5 중단 transaction을 검증한다.",
                            "confidence": "confirmed",
                            "needs_confirmation": "- 없음",
                            "state_markdown": "# Doctor Fixture\n\nUpdated: 2026-07-15\n\n## Current Decisions\n\n- 복구 진단용 합성 결정을 기록한다.\n\n## Reasons\n\n- [Relevant Delta]({{DELTA_LINK}})\n",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        failure_env = os.environ.copy()
        failure_env.update({"PODO_TEST_FAILURES": "1", "PODO_TEST_FAIL_AT": "after-prepared"})
        failed = run(
            [
                str(interrupted / ".podo/bin/podo"),
                "context",
                "apply",
                "--capture",
                capture_id,
                "--request",
                str(request),
            ],
            cwd=interrupted,
            env=failure_env,
        )
        if failed.returncode == 0 or "E_INJECTED_FAILURE" not in failed.stderr:
            raise AssertionError(failed.stdout + failed.stderr)
        before = snapshot(interrupted)
        result, report = doctor(interrupted)
        if result.returncode == 0 or "PODO_D001_TRANSACTION_INCOMPLETE" not in codes(report):
            raise AssertionError(result.stdout + result.stderr)
        if before != snapshot(interrupted):
            raise AssertionError("doctor changed interrupted transaction evidence")
        inbox = run([str(interrupted / ".podo/bin/podo"), "inbox", "--json"], cwd=interrupted)
        if not json.loads(inbox.stdout)["recovery_required"]:
            raise AssertionError(inbox.stdout + inbox.stderr)
        print("PASS unfinished transaction is visible to doctor and task startup")

        damaged = root / "damaged"
        install(damaged)
        capture(damaged, root, "damaged")
        (damaged / ".podo/policies/todo.md").write_text("modified product\n", encoding="utf-8")
        receipt = damaged / ".podo-work/receipts/orphan.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(
            json.dumps({"capture_id": "orphan", "outcome": "applied", "event": "events/missing/metadata.md", "deltas": [], "states": []}) + "\n",
            encoding="utf-8",
        )
        deferred = damaged / ".podo-work/deferred/orphan.json"
        deferred.parent.mkdir(parents=True)
        deferred.write_text(json.dumps({"capture_id": "orphan"}) + "\n", encoding="utf-8")
        product_update = damaged / ".podo-work/product-updates/product-synthetic"
        product_update.mkdir(parents=True)
        (product_update / "journal.json").write_text(
            json.dumps(
                {
                    "journal_version": 1,
                    "update_id": "product-synthetic",
                    "state": "applying",
                    "from_version": "0.5.0",
                    "to_version": "0.5.1",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        before = snapshot(damaged)
        result, report = doctor(damaged)
        expected = {
            "PODO_D201_DEFERRED_WITHOUT_CAPTURE",
            "PODO_D205_RECEIPT_TARGET_MISSING",
            "PODO_D303_PRODUCT_MODIFIED",
            "PODO_D310_PRODUCT_UPDATE_INCOMPLETE",
        }
        if result.returncode == 0 or not expected.issubset(codes(report)):
            raise AssertionError(json.dumps(report, ensure_ascii=False, indent=2))
        if before != snapshot(damaged):
            raise AssertionError("doctor changed damaged evidence")
        print("PASS doctor distinguishes lifecycle, receipt target and product modification findings")

        product_startup = root / "product-startup"
        install(product_startup)
        product_update = product_startup / ".podo-work/product-updates/product-synthetic"
        product_update.mkdir(parents=True)
        (product_update / "journal.json").write_text(
            json.dumps({"update_id": "product-synthetic", "state": "applying"}) + "\n",
            encoding="utf-8",
        )
        inbox = run([str(product_startup / ".podo/bin/podo"), "inbox", "--json"], cwd=product_startup)
        if inbox.returncode or not inbox.stdout:
            raise AssertionError(inbox.stdout + inbox.stderr)
        inbox_value = json.loads(inbox.stdout)
        if inbox_value["product_recovery_required"] != ["product-synthetic"] or inbox_value["recovery_diagnosis"] is None:
            raise AssertionError(inbox.stdout + inbox.stderr)
        print("PASS task startup surfaces unfinished product update diagnosis")


if __name__ == "__main__":
    main()
