#!/usr/bin/env python3
"""Exercise Phase 4 decision lifecycle in disposable synthetic Workspaces."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD = REPO_ROOT / "tools/build_synthetic_workspace.py"
FIXTURE = REPO_ROOT / "tests/fixtures/codex_transcript_0.144.0-alpha.4.jsonl"


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def transcript(root: Path, session: str, turn: str, *, partial: bool = False) -> Path:
    text = FIXTURE.read_text(encoding="utf-8")
    text = text.replace("synthetic-session-001", session).replace("synthetic-turn-001", turn)
    if partial:
        text = "\n".join(line for line in text.splitlines() if '"role":"assistant"' not in line) + "\n"
    path = root / f"{session}--{turn}.jsonl"
    path.write_text(text, encoding="utf-8")
    return path


def capture(workspace: Path, source: Path, session: str, turn: str) -> str:
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


def request_file(workspace: Path, name: str, value: dict) -> Path:
    path = workspace / f".podo-work/requests/{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([str(workspace / ".podo/bin/podo"), *args], cwd=workspace)


def permanent_snapshot(workspace: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for root_name in ("events", "deltas", "state"):
        for path in sorted((workspace / root_name).rglob("*")):
            if path.is_file():
                result[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def defer_request(candidates: list[str] | None = None) -> dict:
    return {
        "summary": "회의 시간을 오전 9시에서 10시로 옮길 가능성을 사용자가 언급했다.",
        "why_confirmation": "기존 결정과 충돌하지만 변경 의도가 확정되지 않았다.",
        "question": "회의 시간을 오전 10시로 확정할까요?",
        "state_candidates": candidates or ["synthetic-planning"],
    }


def state_request(workspace: Path, decision: str, *, title: str = "Confirmed meeting change") -> dict:
    state_path = workspace / "state/synthetic-planning.md"
    expected = hashlib.sha256(state_path.read_bytes()).hexdigest()
    state = "\n".join(
        [
            "# Synthetic Planning",
            "",
            "Updated: 2026-07-15",
            "",
            "## Current Context",
            "",
            "Phase 4 resolution을 검증하는 합성 프로젝트다.",
            "",
            "## Current Decisions",
            "",
            f"- {decision}",
            "",
            "## Reasons",
            "",
            "- [Relevant Delta]({{DELTA_LINK}})",
            "",
        ]
    )
    return {
        "event": {
            "title": title,
            "context": "사용자가 이전에 보류된 회의 시간 변경을 명확히 확인했다.",
        },
        "updates": [
            {
                "state_slug": "synthetic-planning",
                "expected_state_sha256": expected,
                "delta_title": title,
                "changed": f"- 이전 오전 9시 결정에서 {decision}로 정정했다.",
                "why": "사용자가 후속 turn에서 보류된 변경을 명확히 확인했다.",
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "state_markdown": state,
            }
        ],
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase4-decisions-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        before = permanent_snapshot(workspace)
        session, turn = "defer-session-001", "defer-turn-001"
        capture_id = capture(workspace, transcript(root, session, turn), session, turn)
        request = request_file(workspace, "defer", defer_request())
        result = cli(workspace, "context", "defer", "--capture", capture_id, "--request", str(request))
        if result.returncode or json.loads(result.stdout).get("status") != "deferred":
            raise AssertionError(result.stdout + result.stderr)
        if permanent_snapshot(workspace) != before:
            raise AssertionError("defer changed permanent Context")
        listing = cli(workspace, "inbox", "--json")
        value = json.loads(listing.stdout)
        if value["pending"] or [item["capture_id"] for item in value["deferred"]] != [capture_id]:
            raise AssertionError(listing.stdout)
        repeated = cli(workspace, "context", "defer", "--capture", capture_id, "--request", str(request))
        if repeated.returncode or json.loads(repeated.stdout).get("status") != "already-deferred":
            raise AssertionError(repeated.stdout + repeated.stderr)
        bypass_request = request_file(
            workspace,
            "deferred-bypass",
            state_request(workspace, "이 변경은 직접 적용되면 안 된다."),
        )
        bypassed = cli(
            workspace,
            "context",
            "apply",
            "--capture",
            capture_id,
            "--request",
            str(bypass_request),
        )
        if bypassed.returncode == 0 or "E_CAPTURE_DEFERRED" not in bypassed.stderr:
            raise AssertionError(bypassed.stdout + bypassed.stderr)
        if permanent_snapshot(workspace) != before:
            raise AssertionError("direct apply bypass changed permanent Context")
        print("PASS uncertain conflict defers once without permanent Context change")

        confirm_session, confirm_turn = "confirm-session-002", "confirm-turn-002"
        confirm_source = transcript(root, confirm_session, confirm_turn)
        confirm_id = capture(workspace, confirm_source, confirm_session, confirm_turn)
        missing_request = cli(
            workspace,
            "context",
            "resolve",
            "--deferred",
            capture_id,
            "--capture",
            confirm_id,
            "--decision",
            "confirmed",
        )
        if missing_request.returncode == 0 or "E_RESOLUTION_REQUEST" not in missing_request.stderr:
            raise AssertionError(missing_request.stdout + missing_request.stderr)
        if permanent_snapshot(workspace) != before:
            raise AssertionError("confirmation without request changed permanent Context")
        apply_request = request_file(
            workspace,
            "confirmed",
            state_request(workspace, "합성 프로젝트 회의는 오전 10시에 한다."),
        )
        resolved = cli(
            workspace,
            "context",
            "resolve",
            "--deferred",
            capture_id,
            "--capture",
            confirm_id,
            "--decision",
            "confirmed",
            "--request",
            str(apply_request),
        )
        if resolved.returncode:
            raise AssertionError(resolved.stdout + resolved.stderr)
        resolved_value = json.loads(resolved.stdout)
        event_dir = workspace / Path(resolved_value["event"]).parent
        if (event_dir / "original/session.jsonl").read_bytes() != confirm_source.read_bytes():
            raise AssertionError("confirmation original changed bytes")
        related = event_dir / f"original/related/{capture_id}/session.jsonl"
        if related.read_bytes() != transcript(root, session, turn).read_bytes():
            raise AssertionError("deferred related original changed bytes")
        metadata = (event_dir / "metadata.md").read_text(encoding="utf-8")
        if f"Resolves-Capture: {capture_id}" not in metadata or "Resolution: confirmed" not in metadata:
            raise AssertionError(metadata)
        state_text = (workspace / "state/synthetic-planning.md").read_text(encoding="utf-8")
        if "오전 10시" not in state_text or "금요일 오전 9시" in state_text:
            raise AssertionError(state_text)
        delta_text = (workspace / resolved_value["deltas"][0]).read_text(encoding="utf-8")
        if "이전 오전 9시" not in delta_text or "오전 10시" not in delta_text:
            raise AssertionError(delta_text)
        old_receipt = json.loads((workspace / f".podo-work/receipts/{capture_id}.json").read_text(encoding="utf-8"))
        if old_receipt.get("outcome") != "confirmed" or old_receipt.get("resolved_by_capture") != confirm_id:
            raise AssertionError(str(old_receipt))
        repeated = cli(
            workspace,
            "context",
            "resolve",
            "--deferred",
            capture_id,
            "--capture",
            confirm_id,
            "--decision",
            "confirmed",
        )
        if repeated.returncode or json.loads(repeated.stdout).get("status") != "already-resolved":
            raise AssertionError(repeated.stdout + repeated.stderr)
        print("PASS confirmed resolution preserves confirmation and deferred originals")

        reject_session, reject_turn = "reject-source-session-003", "reject-source-turn-003"
        reject_deferred_id = capture(
            workspace,
            transcript(root, reject_session, reject_turn),
            reject_session,
            reject_turn,
        )
        reject_request = request_file(workspace, "reject-defer", defer_request())
        deferred_result = cli(
            workspace,
            "context",
            "defer",
            "--capture",
            reject_deferred_id,
            "--request",
            str(reject_request),
        )
        if deferred_result.returncode:
            raise AssertionError(deferred_result.stdout + deferred_result.stderr)
        before_rejection = permanent_snapshot(workspace)
        answer_session, answer_turn = "reject-answer-session-004", "reject-answer-turn-004"
        answer_id = capture(workspace, transcript(root, answer_session, answer_turn), answer_session, answer_turn)
        rejected = cli(
            workspace,
            "context",
            "resolve",
            "--deferred",
            reject_deferred_id,
            "--capture",
            answer_id,
            "--decision",
            "rejected",
        )
        if rejected.returncode or json.loads(rejected.stdout).get("status") != "rejected":
            raise AssertionError(rejected.stdout + rejected.stderr)
        if permanent_snapshot(workspace) != before_rejection:
            raise AssertionError("receipt-only rejection changed permanent Context")
        rejection_receipt = json.loads(
            (workspace / f".podo-work/receipts/{reject_deferred_id}.json").read_text(encoding="utf-8")
        )
        if rejection_receipt.get("outcome") != "rejected" or rejection_receipt.get("resolved_by_capture") != answer_id:
            raise AssertionError(str(rejection_receipt))
        print("PASS rejected resolution closes both captures without permanent Context change")

        before = permanent_snapshot(workspace)

        session, turn = "invalid-session-005", "invalid-turn-005"
        invalid_id = capture(workspace, transcript(root, session, turn), session, turn)
        invalid = defer_request(["Not A State"])
        invalid_request = request_file(workspace, "invalid", invalid)
        failed = cli(workspace, "context", "defer", "--capture", invalid_id, "--request", str(invalid_request))
        if failed.returncode == 0 or "E_REQUEST_STATE" not in failed.stderr:
            raise AssertionError(failed.stdout + failed.stderr)
        listing = json.loads(cli(workspace, "inbox", "--json").stdout)
        if invalid_id not in [item["capture_id"] for item in listing["pending"]]:
            raise AssertionError("invalid defer did not preserve pending capture")
        if permanent_snapshot(workspace) != before:
            raise AssertionError("invalid defer changed permanent Context")
        print("PASS invalid defer request preserves pending capture")

        session, turn = "partial-session-006", "partial-turn-006"
        partial_id = capture(workspace, transcript(root, session, turn, partial=True), session, turn)
        partial_request = request_file(workspace, "partial", defer_request())
        failed = cli(workspace, "context", "defer", "--capture", partial_id, "--request", str(partial_request))
        if failed.returncode == 0 or "E_CAPTURE_PARTIAL" not in failed.stderr:
            raise AssertionError(failed.stdout + failed.stderr)
        if permanent_snapshot(workspace) != before:
            raise AssertionError("partial defer changed permanent Context")
        print("PASS partial capture cannot become a deferred decision")

        inference_session, inference_turn = "inference-session-007", "inference-turn-007"
        inference_id = capture(
            workspace,
            transcript(root, inference_session, inference_turn),
            inference_session,
            inference_turn,
        )
        inferred = state_request(workspace, "사용자가 아침 회의를 선호한다고 추론했다.")
        inferred["updates"][0]["confidence"] = "inferred"
        inference_request = request_file(workspace, "inferred", inferred)
        failed = cli(
            workspace,
            "context",
            "apply",
            "--capture",
            inference_id,
            "--request",
            str(inference_request),
        )
        if failed.returncode == 0 or "E_REQUEST_CONFIDENCE" not in failed.stderr:
            raise AssertionError(failed.stdout + failed.stderr)
        if permanent_snapshot(workspace) != before:
            raise AssertionError("inferred apply changed permanent Context")
        print("PASS inference cannot be applied as confirmed user State")

        sensitive_session, sensitive_turn = "sensitive-session-008", "sensitive-turn-008"
        sensitive_id = capture(
            workspace,
            transcript(root, sensitive_session, sensitive_turn),
            sensitive_session,
            sensitive_turn,
        )
        excluded = cli(
            workspace,
            "context",
            "discard",
            "--capture",
            sensitive_id,
            "--reason",
            "sensitive-data",
        )
        if excluded.returncode or json.loads(excluded.stdout).get("outcome") != "sensitive-data-excluded":
            raise AssertionError(excluded.stdout + excluded.stderr)
        if permanent_snapshot(workspace) != before:
            raise AssertionError("sensitive exclusion changed permanent Context")
        if (workspace / f".podo-work/inbox/{sensitive_id}").exists():
            raise AssertionError("sensitive temporary original was not removed")
        print("PASS sensitive credential capture is excluded from permanent Context")


if __name__ == "__main__":
    main()
