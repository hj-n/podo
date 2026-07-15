#!/usr/bin/env python3
"""Exercise Phase 3 Event, Delta, State, No Delta, and failure safety."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD = REPO_ROOT / "tools/build_synthetic_workspace.py"
FIXTURE = REPO_ROOT / "tests/fixtures/codex_transcript_0.144.0-alpha.4.jsonl"


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def capture(workspace: Path, transcript: Path, session: str, turn: str) -> str:
    payload = {
        "hook_event_name": "Stop",
        "session_id": session,
        "turn_id": turn,
        "transcript_path": str(transcript),
        "cwd": str(workspace),
        "model": "synthetic-model",
    }
    result = run(
        [str(workspace / ".podo/scripts/capture_event")],
        input=json.dumps(payload),
        cwd=workspace,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return f"{session}--{turn}"


def transcript(root: Path, session: str, turn: str, *, partial: bool = False) -> Path:
    text = FIXTURE.read_text(encoding="utf-8")
    text = text.replace("synthetic-session-001", session).replace("synthetic-turn-001", turn)
    if partial:
        text = "\n".join(line for line in text.splitlines() if '"role":"assistant"' not in line) + "\n"
    path = root / f"{session}--{turn}.jsonl"
    path.write_text(text, encoding="utf-8")
    return path


def request_file(workspace: Path, name: str, value: dict) -> Path:
    path = workspace / f".podo-work/requests/{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def state_text(title: str, decision: str, todo: str | None = None, *, updated: str = "2026-07-15") -> str:
    lines = [
        f"# {title}",
        "",
        f"Updated: {updated}",
        "",
        "## Current Context",
        "",
        "Phase 3 synthetic Context다.",
        "",
        "## Current Decisions",
        "",
        f"- {decision}",
    ]
    if todo:
        lines.extend(
            [
                "",
                "## TODO",
                "",
                f"- [ ] {todo}",
                "  - Created: 2026-07-15",
                "  - Due: 2026-07-18",
            ]
        )
    lines.extend(["", "## Reasons", "", "- [Relevant Delta]({{DELTA_LINK}})", ""])
    return "\n".join(lines)


def update(slug: str, decision: str, *, todo: str | None = None, expected: str | None = None) -> dict:
    return {
        "state_slug": slug,
        "expected_state_sha256": expected,
        "delta_title": f"{slug} changed",
        "changed": f"- {decision}",
        "why": "사용자가 synthetic transcript에서 명확히 결정했다.",
        "confidence": "confirmed",
        "needs_confirmation": "- 없음",
        "state_markdown": state_text(slug.replace("-", " ").title(), decision, todo),
    }


def request(updates: list[dict]) -> dict:
    return {
        "event": {
            "title": "Synthetic Phase 3 decision",
            "context": "Phase 3 Context writer를 검증하는 합성 Codex 대화다.",
        },
        "updates": updates,
    }


def cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([str(workspace / ".podo/bin/podo"), *args], cwd=workspace)


def permanent_snapshot(workspace: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for root_name in ("events", "deltas", "state"):
        for path in sorted((workspace / root_name).rglob("*")):
            if path.is_file():
                values[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def expect_failure(workspace: Path, capture_id: str, request_path: Path, code: str) -> None:
    before = permanent_snapshot(workspace)
    result = cli(workspace, "context", "apply", "--capture", capture_id, "--request", str(request_path))
    if result.returncode == 0 or code not in result.stderr:
        raise AssertionError(f"expected {code}\n{result.stdout}{result.stderr}")
    if permanent_snapshot(workspace) != before:
        raise AssertionError(f"{code} changed permanent Context")
    print(f"PASS {code} preserves permanent Context")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase3-context-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        for name in ("events", "deltas", "state"):
            shutil.rmtree(workspace / name)
            (workspace / name).mkdir()

        session, turn = "context-session-001", "context-turn-001"
        capture_id = capture(workspace, transcript(root, session, turn), session, turn)
        inbox = cli(workspace, "inbox", "--json")
        if inbox.returncode or capture_id not in inbox.stdout:
            raise AssertionError(inbox.stdout + inbox.stderr)
        first_request = request_file(
            workspace,
            "first",
            request([update("synthetic-planning", "회의는 금요일 오전 9시에 한다.", todo="회의 자료를 준비한다.")]),
        )
        applied = cli(workspace, "context", "apply", "--capture", capture_id, "--request", str(first_request))
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        result = json.loads(applied.stdout)
        if result["status"] != "applied" or len(result["deltas"]) != 1:
            raise AssertionError(applied.stdout)
        validated = cli(workspace, "validate")
        if validated.returncode:
            raise AssertionError(validated.stdout + validated.stderr)
        event_original = workspace / Path(result["event"]).parent / "original/session.jsonl"
        if event_original.read_bytes() != transcript(root, session, turn).read_bytes():
            raise AssertionError("promoted Event original changed bytes")
        repeat = cli(workspace, "context", "apply", "--capture", capture_id, "--request", str(first_request))
        if repeat.returncode or "already-processed" not in repeat.stdout:
            raise AssertionError(repeat.stdout + repeat.stderr)
        print("PASS Event → Delta → State apply, links, TODO and idempotency")

        before_no_delta = permanent_snapshot(workspace)
        session, turn = "context-session-002", "context-turn-002"
        no_delta_id = capture(workspace, transcript(root, session, turn), session, turn)
        discarded = cli(workspace, "context", "discard", "--capture", no_delta_id, "--reason", "no-delta")
        if discarded.returncode or '"outcome": "no-delta"' not in discarded.stdout:
            raise AssertionError(discarded.stdout + discarded.stderr)
        if permanent_snapshot(workspace) != before_no_delta:
            raise AssertionError("No Delta changed permanent Context")
        print("PASS No Delta receipt without Event, Delta or State change")

        session, turn = "context-session-003", "context-turn-003"
        multiple_id = capture(workspace, transcript(root, session, turn), session, turn)
        multi_request = request_file(
            workspace,
            "multiple",
            request(
                [
                    update("project-alpha", "Alpha는 보라색 표식을 사용한다."),
                    update("project-beta", "Beta는 초록색 표식을 사용한다."),
                ]
            ),
        )
        multiple = cli(workspace, "context", "apply", "--capture", multiple_id, "--request", str(multi_request))
        if multiple.returncode:
            raise AssertionError(multiple.stdout + multiple.stderr)
        multi_result = json.loads(multiple.stdout)
        if len(multi_result["deltas"]) != 2 or len(multi_result["states"]) != 2:
            raise AssertionError(multiple.stdout)
        if len({Path(path).parts[3] for path in [multi_result["event"]]}) != 1:
            raise AssertionError("multi-State apply did not share one Event")
        print("PASS one Event applies two traceable Delta and State updates")

        session, turn = "context-session-004", "context-turn-004"
        partial_id = capture(workspace, transcript(root, session, turn, partial=True), session, turn)
        partial_request = request_file(workspace, "partial", request([update("partial-state", "적용하면 안 된다.")]))
        expect_failure(workspace, partial_id, partial_request, "E_CAPTURE_PARTIAL")

        state_path = workspace / "state/synthetic-planning.md"
        session, turn = "context-session-005", "context-turn-005"
        stale_id = capture(workspace, transcript(root, session, turn), session, turn)
        stale_request = request_file(
            workspace,
            "stale",
            request([update("synthetic-planning", "새 결정", expected="0" * 64)]),
        )
        expect_failure(workspace, stale_id, stale_request, "E_STATE_STALE")

        session, turn = "context-session-006", "context-turn-006"
        invalid_date_id = capture(workspace, transcript(root, session, turn), session, turn)
        bad_update = update("invalid-date", "날짜가 잘못됐다.")
        bad_update["state_markdown"] = state_text("Invalid Date", "날짜가 잘못됐다.", updated="15-07-2026")
        invalid_date_request = request_file(workspace, "invalid-date", request([bad_update]))
        expect_failure(workspace, invalid_date_id, invalid_date_request, "E_REQUEST_INVALID_DATE")

        session, turn = "context-session-007", "context-turn-007"
        missing_link_id = capture(workspace, transcript(root, session, turn), session, turn)
        bad_link = update("missing-link", "링크가 없다.")
        bad_link["state_markdown"] = bad_link["state_markdown"].replace("{{DELTA_LINK}}", "missing.md")
        missing_link_request = request_file(workspace, "missing-link", request([bad_link]))
        expect_failure(workspace, missing_link_id, missing_link_request, "E_REQUEST_STATE_LINK")

        if not state_path.is_file():
            raise AssertionError("existing State disappeared during failure cases")
        print("PASS Phase 3 context suite")


if __name__ == "__main__":
    main()
