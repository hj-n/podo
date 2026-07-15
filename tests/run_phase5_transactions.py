#!/usr/bin/env python3
"""Exercise prepared Context transactions and every commit failure boundary."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD = REPO_ROOT / "tools/build_synthetic_workspace.py"
FIXTURE = REPO_ROOT / "tests/fixtures/codex_transcript_0.144.0-alpha.4.jsonl"
FAILURE_POINTS = (
    "after-prepared",
    "after-event",
    "after-delta-1",
    "before-states",
    "after-state-1",
    "after-receipt-1",
    "before-final-validation",
    "after-final-validation",
)


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def build(workspace: Path) -> None:
    result = run([sys.executable, str(BUILD), "--output", str(workspace)])
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def capture(workspace: Path, root: Path, name: str) -> str:
    session = f"transaction-session-{name}"
    turn = f"transaction-turn-{name}"
    text = FIXTURE.read_text(encoding="utf-8")
    text = text.replace("synthetic-session-001", session).replace("synthetic-turn-001", turn)
    source = root / f"{session}--{turn}.jsonl"
    source.write_text(text, encoding="utf-8")
    payload = {
        "hook_event_name": "Stop",
        "session_id": session,
        "turn_id": turn,
        "transcript_path": str(source),
        "cwd": str(workspace),
        "model": "synthetic-model",
    }
    result = run([str(workspace / ".podo/scripts/capture_event")], input=json.dumps(payload), cwd=workspace)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return f"{session}--{turn}"


def request(workspace: Path, name: str, marker: str) -> Path:
    state = workspace / "state/synthetic-planning.md"
    state_text = "\n".join(
        [
            "# Synthetic Planning",
            "",
            "Updated: 2026-07-15",
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
    value = {
        "event": {"title": f"Transaction {name}", "context": "Phase 5 transaction failure fixture다."},
        "updates": [
            {
                "state_slug": "synthetic-planning",
                "expected_state_sha256": hashlib.sha256(state.read_bytes()).hexdigest(),
                "delta_title": f"Transaction {name}",
                "changed": f"- {marker}",
                "why": "사용자가 합성 fixture에서 명확히 결정했다.",
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "state_markdown": state_text,
            }
        ],
    }
    path = workspace / f".podo-work/requests/{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def apply(workspace: Path, capture_id: str, request_path: Path, point: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if point is not None:
        env["PODO_TEST_FAILURES"] = "1"
        env["PODO_TEST_FAIL_AT"] = point
    return run(
        [
            str(workspace / ".podo/bin/podo"),
            "context",
            "apply",
            "--capture",
            capture_id,
            "--request",
            str(request_path),
        ],
        cwd=workspace,
        env=env,
    )


def one_transaction(workspace: Path) -> Path:
    values = sorted((workspace / ".podo-work/transactions").glob("context-*"))
    if len(values) != 1:
        raise AssertionError(f"expected one transaction, found {values}")
    return values[0]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase5-transaction-") as temporary:
        root = Path(temporary)
        normal = root / "normal"
        build(normal)
        capture_id = capture(normal, root, "normal")
        applied = apply(normal, capture_id, request(normal, "normal", "TRANSACTION_NORMAL"))
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        result = json.loads(applied.stdout)
        if "transaction" not in result or list((normal / ".podo-work/transactions").glob("*")):
            raise AssertionError(applied.stdout)
        transaction_receipts = list((normal / ".podo-work/transaction-receipts").glob("*.json"))
        if len(transaction_receipts) != 1:
            raise AssertionError("committed transaction receipt is missing")
        print("PASS normal Context apply commits from a prepared transaction")

        for index, point in enumerate(FAILURE_POINTS, start=1):
            workspace = root / f"failure-{index}"
            build(workspace)
            state = workspace / "state/synthetic-planning.md"
            before = state.read_bytes()
            capture_id = capture(workspace, root, f"failure-{index}")
            request_path = request(workspace, f"failure-{index}", f"TRANSACTION_FAILURE_{index}")
            failed = apply(workspace, capture_id, request_path, point)
            if failed.returncode == 0 or "E_INJECTED_FAILURE" not in failed.stderr:
                raise AssertionError(f"{point} did not fail\n{failed.stdout}{failed.stderr}")
            transaction = one_transaction(workspace)
            journal = json.loads((transaction / "journal.json").read_text(encoding="utf-8"))
            plan = json.loads((transaction / "plan.json").read_text(encoding="utf-8"))
            if journal.get("state") != "recovery-required" or journal.get("failure", {}).get("point") != point:
                raise AssertionError(str(journal))
            original = transaction / plan["states"][0]["original"]
            if original.read_bytes() != before:
                raise AssertionError(f"{point} did not preserve original State evidence")
            current_hash = hashlib.sha256(state.read_bytes()).hexdigest()
            allowed = {hashlib.sha256(before).hexdigest(), plan["states"][0]["new_sha256"]}
            if current_hash not in allowed:
                raise AssertionError(f"{point} left an unknown State version")
            if point == "after-receipt-1":
                repeated = apply(workspace, capture_id, request_path)
                if repeated.returncode == 0 or "E_TRANSACTION_PENDING" not in repeated.stderr:
                    raise AssertionError("partial receipt hid its unfinished transaction")
            print(f"PASS {point} leaves journal, staged bytes and a known State version")


if __name__ == "__main__":
    main()
