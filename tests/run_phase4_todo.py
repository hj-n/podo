#!/usr/bin/env python3
"""Exercise Phase 4 TODO lifecycle validation and traceable updates."""

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


def make_capture(workspace: Path, root: Path, number: int) -> str:
    session = f"todo-session-{number:03d}"
    turn = f"todo-turn-{number:03d}"
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
    captured = run(
        [str(workspace / ".podo/scripts/capture_event")],
        input=json.dumps(payload),
        cwd=workspace,
    )
    if captured.returncode:
        raise AssertionError(captured.stdout + captured.stderr)
    return f"{session}--{turn}"


def state_markdown(todo_lines: list[str]) -> str:
    return "\n".join(
        [
            "# Synthetic Planning",
            "",
            "Updated: 2026-07-17",
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


def request_file(workspace: Path, number: int, todo_lines: list[str]) -> Path:
    state = workspace / "state/synthetic-planning.md"
    value = {
        "event": {
            "title": f"Synthetic TODO lifecycle {number}",
            "context": "Phase 4 TODO lifecycle을 검증하는 합성 대화다.",
        },
        "updates": [
            {
                "state_slug": "synthetic-planning",
                "expected_state_sha256": hashlib.sha256(state.read_bytes()).hexdigest(),
                "delta_title": f"Synthetic TODO lifecycle {number}",
                "changed": "- 사용자가 TODO 상태를 자연어로 명확히 변경했다.",
                "why": "명시적인 TODO 요청 자체가 이 내부 Context 변경의 승인이다.",
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "state_markdown": state_markdown(todo_lines),
            }
        ],
    }
    path = workspace / f".podo-work/requests/todo-{number}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def apply(workspace: Path, capture_id: str, request: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            str(workspace / ".podo/bin/podo"),
            "context",
            "apply",
            "--capture",
            capture_id,
            "--request",
            str(request),
        ],
        cwd=workspace,
    )


def apply_ok(workspace: Path, root: Path, number: int, todo_lines: list[str]) -> None:
    capture_id = make_capture(workspace, root, number)
    result = apply(workspace, capture_id, request_file(workspace, number, todo_lines))
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    validated = run([str(workspace / ".podo/bin/podo"), "validate"], cwd=workspace)
    if validated.returncode:
        raise AssertionError(validated.stdout + validated.stderr)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase4-todo-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        apply_ok(
            workspace,
            root,
            1,
            [
                "- [ ] 준비 문서를 작성한다.",
                "  - Created: 2026-07-15",
                "  - Due: 2026-07-18",
            ],
        )
        apply_ok(
            workspace,
            root,
            2,
            [
                "- [x] 준비 문서를 작성한다.",
                "  - Created: 2026-07-15",
                "  - Due: 2026-07-18",
                "  - Completed: 2026-07-16",
                "  - Result: 합성 문서 초안을 만들었다.",
            ],
        )
        apply_ok(
            workspace,
            root,
            3,
            [
                "- [x] 준비 문서 배포를 취소한다.",
                "  - Created: 2026-07-15",
                "  - Cancelled: 2026-07-16",
                "  - Result: 계획 변경으로 배포하지 않는다.",
            ],
        )
        apply_ok(
            workspace,
            root,
            4,
            [
                "- [ ] 준비 문서 배포를 다시 검토한다.",
                "  - Created: 2026-07-15",
                "  - Cancelled: 2026-07-16",
                "  - Reopened: 2026-07-17",
            ],
        )
        print("PASS TODO create, due, complete, cancel and reopen lifecycle")

        invalid_id = make_capture(workspace, root, 5)
        invalid_request = request_file(
            workspace,
            5,
            [
                "- [x] terminal date가 없는 잘못된 TODO",
                "  - Created: 2026-07-15",
            ],
        )
        before = (workspace / "state/synthetic-planning.md").read_bytes()
        failed = apply(workspace, invalid_id, invalid_request)
        if failed.returncode == 0 or "E_REQUEST_TODO_LIFECYCLE" not in failed.stderr:
            raise AssertionError(failed.stdout + failed.stderr)
        if (workspace / "state/synthetic-planning.md").read_bytes() != before:
            raise AssertionError("invalid TODO lifecycle changed State")
        print("PASS invalid TODO lifecycle preserves current State")


if __name__ == "__main__":
    main()
