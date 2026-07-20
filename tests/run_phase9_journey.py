#!/usr/bin/env python3
"""Run one connected State, People, Research, TODO and Event-storage journey."""

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
TRANSCRIPT = ROOT / "tests/fixtures/codex_transcript_0.145.0-alpha.18.jsonl"


def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-journey-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        podo = workspace / ".podo/bin/podo"
        pdf = root / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n% SYNTHETIC AGENT MEMORY PAPER\n%%EOF\n")
        imported = run(
            [str(podo), "research", "import", "--file", str(pdf), "--slug", "agent-memory-paper", "--title", "Agent Memory Paper", "--authors", "Synthetic Author", "--year", "2026"],
            cwd=workspace,
        )
        if imported.returncode:
            raise AssertionError(imported.stdout + imported.stderr)

        transcript = root / "session.jsonl"
        shutil.copy2(TRANSCRIPT, transcript)
        payload = {
            "hook_event_name": "Stop",
            "session_id": "synthetic-session-001",
            "turn_id": "synthetic-turn-001",
            "transcript_path": str(transcript),
            "cwd": str(workspace),
            "model": "synthetic-model",
        }
        capture = run([str(workspace / ".podo/scripts/capture_event")], input=json.dumps(payload), cwd=workspace)
        if capture.returncode:
            raise AssertionError(capture.stdout + capture.stderr)
        request = {
            "event": {"title": "Connected People and Research decision", "context": "사람과 논문을 Podo 프로젝트에 연결한 합성 결정이다."},
            "updates": [
                {
                    "target_kind": "state",
                    "state_slug": "podo-project",
                    "expected_state_sha256": None,
                    "delta_title": "Podo research discussion planned",
                    "changed": "- 민수와 agent memory 논문을 토의하기로 했다.",
                    "why": "사용자가 합성 계획을 명확히 확정했다.",
                    "confidence": "confirmed",
                    "needs_confirmation": "- 없음",
                    "state_markdown": (
                        "# Podo Project\n\nUpdated: 2026-07-20\n\n## Current Context\n\n"
                        "[김민수](../people/kim-minsu.md)와 [Research](../research/projects/podo.md)를 연결한다.\n\n"
                        "## TODO\n\n- [ ] 논문을 민수와 토의한다.\n  - Created: 2026-07-20\n  - Due: 2026-07-25\n\n"
                        "## Reasons\n\n- [Delta]({{DELTA_LINK}})\n"
                    ),
                },
                {
                    "target_kind": "people",
                    "person_slug": "kim-minsu",
                    "expected_person_sha256": None,
                    "delta_title": "민수와 Podo 연구 연결",
                    "changed": "- 민수와 Podo 연구를 토의할 계획이다.",
                    "why": "사용자가 관련 사람을 명확히 지정했다.",
                    "confidence": "confirmed",
                    "needs_confirmation": "- 없음",
                    "person_markdown": (
                        "# 김민수\n\nName: 김민수\nAliases: 민수\nUpdated: 2026-07-20\n\n"
                        "## Related Work\n\n- [Podo Project](../state/podo-project.md)\n\n"
                        "## Reasons\n\n- [Delta]({{DELTA_LINK}})\n"
                    ),
                },
                {
                    "target_kind": "research-project",
                    "research_slug": "podo",
                    "expected_research_sha256": None,
                    "delta_title": "Agent memory paper linked to Podo",
                    "changed": "- Agent memory paper를 Podo 프로젝트 연구에 연결했다.",
                    "why": "사용자가 프로젝트 관련성을 확정했다.",
                    "confidence": "confirmed",
                    "needs_confirmation": "- 실제 제품 결정은 논문 토의 후 검토한다.",
                    "research_markdown": (
                        "# Podo Research\n\nUpdated: 2026-07-20\n\n## Current Application\n\n"
                        "Agent memory 접근을 검토한다.\n\n## Related Papers\n\n"
                        "- [Agent Memory Paper](../papers/agent-memory-paper/notes.md)\n\n## Related State\n\n"
                        "- [Podo Project](../../state/podo-project.md)\n\n## Reasons\n\n- [Delta]({{DELTA_LINK}})\n"
                    ),
                },
            ],
        }
        request_path = workspace / ".podo-work/requests/connected.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        applied = run(
            [str(podo), "context", "apply", "--capture", "synthetic-session-001--synthetic-turn-001", "--request", request_path.relative_to(workspace).as_posix()],
            cwd=workspace,
        )
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        value = json.loads(applied.stdout)
        if len(value["deltas"]) != 3 or len(value["states"]) != 1 or len(value["people"]) != 1 or len(value["research"]) != 1:
            raise AssertionError(applied.stdout)

        todos = json.loads(run([str(podo), "todos", "--due-before", "2026-07-25", "--json"], cwd=workspace).stdout)
        people = json.loads(run([str(podo), "people", "민수", "--json"], cwd=workspace).stdout)
        papers = json.loads(run([str(podo), "research", "list", "Agent Memory", "--json"], cwd=workspace).stdout)
        if todos["count"] != 2 or people["count"] != 1 or papers["count"] != 1:
            raise AssertionError(json.dumps({"todos": todos, "people": people, "papers": papers}, ensure_ascii=False))

        storage_plan = json.loads(run([str(podo), "event-storage", "plan"], cwd=workspace).stdout)
        storage = run([str(podo), "event-storage", "apply", "--plan", storage_plan["plan_id"]], cwd=workspace)
        if storage.returncode:
            raise AssertionError(storage.stdout + storage.stderr)
        doctor = run([str(podo), "doctor", "--json"], cwd=workspace)
        doctor_value = json.loads(doctor.stdout)
        if doctor_value["status"] not in {"healthy", "warning"}:
            raise AssertionError(doctor.stdout)
        unexpected = [
            finding for finding in doctor_value["findings"]
            if finding["code"] != "PODO_D301_PRODUCT_MANIFEST_MISSING"
        ]
        if unexpected:
            raise AssertionError(doctor.stdout)
        print("PASS connected State, People, Research, TODO, links and lossless Event storage journey")


if __name__ == "__main__":
    main()
