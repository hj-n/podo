#!/usr/bin/env python3
"""Verify separate People storage, lookup and transactional updates."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools/build_synthetic_workspace.py"
FIXTURE = ROOT / "tests/fixtures/codex_transcript_0.145.0-alpha.18.jsonl"
SESSION = "synthetic-session-001"
TURN = "synthetic-turn-001"


def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def capture(workspace: Path, source: Path) -> str:
    payload = {
        "hook_event_name": "Stop",
        "session_id": SESSION,
        "turn_id": TURN,
        "transcript_path": str(source),
        "cwd": str(workspace),
        "model": "synthetic-model",
    }
    result = run([str(workspace / ".podo/scripts/capture_event")], input=json.dumps(payload), cwd=workspace)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return f"{SESSION}--{TURN}"


def request(person_markdown: str) -> dict[str, object]:
    return {
        "event": {"title": "Synthetic person introduction", "context": "별도 People 영역을 검증하는 합성 소개다."},
        "updates": [
            {
                "target_kind": "people",
                "person_slug": "kim-minsu",
                "expected_person_sha256": None,
                "delta_title": "민수 관계 맥락 추가",
                "changed": "- 김민수는 사용자의 대학 친구다.",
                "why": "사용자가 합성 대화에서 관계를 명확히 소개했다.",
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "person_markdown": person_markdown,
            }
        ],
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-people-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        if (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip() != "2":
            raise AssertionError("new Workspace did not use format 2")
        transcript = root / "session.jsonl"
        shutil.copy2(FIXTURE, transcript)
        capture_id = capture(workspace, transcript)
        request_path = workspace / ".podo-work/requests/person.json"
        request_path.parent.mkdir(parents=True)
        person_markdown = (
            "# 김민수\n\nName: 김민수\nAliases: 민수\nUpdated: 2026-07-20\n\n"
            "## Current Context\n\n사용자의 대학 친구다.\n\n## Reasons\n\n- [Delta]({{DELTA_LINK}})\n"
        )
        request_path.write_text(json.dumps(request(person_markdown), ensure_ascii=False), encoding="utf-8")
        applied = run(
            [str(workspace / ".podo/bin/podo"), "context", "apply", "--capture", capture_id, "--request", request_path.relative_to(workspace).as_posix()],
            cwd=workspace,
        )
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        result = json.loads(applied.stdout)
        if result["states"] or result["people"] != ["people/kim-minsu.md"]:
            raise AssertionError(applied.stdout)
        person = workspace / "people/kim-minsu.md"
        if "[Delta](../deltas/" not in person.read_text(encoding="utf-8"):
            raise AssertionError(person.read_text(encoding="utf-8"))
        lookup = run([str(workspace / ".podo/bin/podo"), "people", "민수", "--json"], cwd=workspace)
        if json.loads(lookup.stdout)["people"][0]["slug"] != "kim-minsu":
            raise AssertionError(lookup.stdout)
        valid = run([str(workspace / ".podo/bin/podo"), "validate", "--mode", "context-present"], cwd=workspace)
        if valid.returncode:
            raise AssertionError(valid.stdout + valid.stderr)
        print("PASS separate People transaction, Delta link and alias lookup")

        invalid_workspace = root / "invalid"
        built = run([sys.executable, str(BUILD), "--output", str(invalid_workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        invalid_transcript = root / "invalid-session.jsonl"
        shutil.copy2(FIXTURE, invalid_transcript)
        invalid_capture = capture(invalid_workspace, invalid_transcript)
        invalid_request = invalid_workspace / ".podo-work/requests/person.json"
        invalid_request.parent.mkdir(parents=True)
        with_todo = person_markdown.replace("## Reasons", "## Follow-ups\n\n- [ ] 민수에게 연락\n  - Created: 2026-07-20\n\n## Reasons")
        invalid_request.write_text(json.dumps(request(with_todo), ensure_ascii=False), encoding="utf-8")
        rejected = run(
            [str(invalid_workspace / ".podo/bin/podo"), "context", "apply", "--capture", invalid_capture, "--request", invalid_request.relative_to(invalid_workspace).as_posix()],
            cwd=invalid_workspace,
        )
        if rejected.returncode == 0 or "E_REQUEST_PERSON_TODO" not in rejected.stderr:
            raise AssertionError(rejected.stdout + rejected.stderr)
        if (invalid_workspace / "people/kim-minsu.md").exists():
            raise AssertionError("invalid People TODO changed permanent data")
        print("PASS People rejects canonical TODO duplication")


if __name__ == "__main__":
    main()
