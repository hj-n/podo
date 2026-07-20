#!/usr/bin/env python3
"""Verify canonical PDF intake, duplicate detection and Research discussion updates."""

from __future__ import annotations

import hashlib
import json
import os
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


def build(workspace: Path) -> None:
    result = run([sys.executable, str(BUILD), "--output", str(workspace)])
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def synthetic_pdf(path: Path, marker: bytes = b"SYNTHETIC RESEARCH TEXT") -> None:
    path.write_bytes(b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\n% " + marker + b"\n%%EOF\n")


def capture(workspace: Path, transcript: Path) -> str:
    payload = {
        "hook_event_name": "Stop",
        "session_id": "synthetic-session-001",
        "turn_id": "synthetic-turn-001",
        "transcript_path": str(transcript),
        "cwd": str(workspace),
        "model": "synthetic-model",
    }
    result = run([str(workspace / ".podo/scripts/capture_event")], input=json.dumps(payload), cwd=workspace)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return "synthetic-session-001--synthetic-turn-001"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-research-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        build(workspace)
        pdf = root / "paper.pdf"
        synthetic_pdf(pdf)
        podo = workspace / ".podo/bin/podo"
        command = [
            str(podo), "research", "import", "--file", str(pdf), "--slug", "synthetic-memory",
            "--title", "Synthetic Memory Paper", "--authors", "Ada Example", "--year", "2026",
        ]
        imported_result = run(command, cwd=workspace)
        if imported_result.returncode:
            raise AssertionError(imported_result.stdout + imported_result.stderr)
        imported = json.loads(imported_result.stdout)
        paper = workspace / imported["paper"]
        if (paper / "original.pdf").read_bytes() != pdf.read_bytes():
            raise AssertionError("Research did not preserve the exact PDF")
        duplicate = json.loads(run(command, cwd=workspace).stdout)
        if duplicate["status"] != "duplicate" or duplicate["paper"] != imported["paper"]:
            raise AssertionError(str(duplicate))
        listed = json.loads(run([str(podo), "research", "list", "Memory", "--json"], cwd=workspace).stdout)
        if listed["count"] != 1 or listed["papers"][0]["slug"] != "synthetic-memory":
            raise AssertionError(str(listed))
        valid = run([str(podo), "validate", "--mode", "context-present"], cwd=workspace)
        if valid.returncode:
            raise AssertionError(valid.stdout + valid.stderr)
        print("PASS canonical PDF import, Event/Delta trace and hash duplicate detection")

        transcript = root / "session.jsonl"
        shutil.copy2(TRANSCRIPT, transcript)
        capture_id = capture(workspace, transcript)
        notes_path = paper / "notes.md"
        notes_hash = hashlib.sha256(notes_path.read_bytes()).hexdigest()
        pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
        request = {
            "event": {"title": "Synthetic paper discussion", "context": "합성 논문을 토의하고 topic과 연결했다."},
            "updates": [
                {
                    "target_kind": "research-paper",
                    "research_slug": "synthetic-memory",
                    "expected_research_sha256": notes_hash,
                    "delta_title": "Synthetic paper analyzed",
                    "changed": "- 논문의 합성 주장을 분석했다.",
                    "why": "사용자와 논문을 토의했다.",
                    "confidence": "confirmed",
                    "needs_confirmation": "- 실제 연구 결론에는 사용하지 않는다.",
                    "research_markdown": (
                        f"# Synthetic Memory Paper\n\nUpdated: 2026-07-20\nPaper-SHA-256: {pdf_hash}\n\n"
                        "## Summary\n\n이 파일은 제품 동작만 검증하는 합성 논문이다.\n\n"
                        "## Claims and Evidence\n\n- 합성 claim이며 실제 사실이 아니다.\n\n"
                        "## Related Topics and Projects\n\n- [Agent Memory](../../topics/agent-memory.md)\n\n"
                        "## Reasons\n\n- [Delta]({{DELTA_LINK}})\n"
                    ),
                },
                {
                    "target_kind": "research-topic",
                    "research_slug": "agent-memory",
                    "expected_research_sha256": None,
                    "delta_title": "Agent memory topic started",
                    "changed": "- 합성 memory 논문을 topic에 연결했다.",
                    "why": "논문 토의에서 관련성이 명확해졌다.",
                    "confidence": "confirmed",
                    "needs_confirmation": "- 없음",
                    "research_markdown": (
                        "# Agent Memory\n\nUpdated: 2026-07-20\n\n## Current Synthesis\n\n합성 검증용 topic이다.\n\n"
                        "## Related Papers\n\n- [Synthetic Memory Paper](../papers/synthetic-memory/notes.md)\n\n"
                        "## Reasons\n\n- [Delta]({{DELTA_LINK}})\n"
                    ),
                },
            ],
        }
        request_path = workspace / ".podo-work/requests/research.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        applied = run(
            [str(podo), "context", "apply", "--capture", capture_id, "--request", request_path.relative_to(workspace).as_posix()],
            cwd=workspace,
        )
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        result = json.loads(applied.stdout)
        if sorted(result["research"]) != ["research/papers/synthetic-memory/notes.md", "research/topics/agent-memory.md"]:
            raise AssertionError(applied.stdout)
        valid = run([str(podo), "validate", "--mode", "context-present"], cwd=workspace)
        if valid.returncode:
            raise AssertionError(valid.stdout + valid.stderr)
        print("PASS one discussion transaction updates paper notes and a separate topic")

        failed = root / "failed"
        build(failed)
        failed_events_before = sorted(path.relative_to(failed).as_posix() for path in (failed / "events").glob("*/*/*"))
        env = {**os.environ, "PODO_TEST_RESEARCH_FAIL_AT": "after-event", "PYTHONDONTWRITEBYTECODE": "1"}
        failed_result = run(
            [str(failed / ".podo/bin/podo"), *command[1:]],
            cwd=failed,
            env=env,
        )
        if failed_result.returncode == 0 or "E_RESEARCH_INJECTED" not in failed_result.stderr:
            raise AssertionError(failed_result.stdout + failed_result.stderr)
        failed_events_after = sorted(path.relative_to(failed).as_posix() for path in (failed / "events").glob("*/*/*"))
        if list((failed / "research/papers").iterdir()) or failed_events_after != failed_events_before:
            raise AssertionError("failed Research import left permanent data")
        print("PASS injected PDF import failure removes partial Research and Event data")

        encrypted = root / "encrypted.pdf"
        synthetic_pdf(encrypted, b"/Encrypt")
        encrypted_result = run(
            [str(podo), "research", "import", "--file", str(encrypted), "--slug", "encrypted", "--title", "Encrypted"],
            cwd=workspace,
        )
        if encrypted_result.returncode == 0 or "E_RESEARCH_PDF_ENCRYPTED" not in encrypted_result.stderr:
            raise AssertionError(encrypted_result.stdout + encrypted_result.stderr)
        print("PASS encrypted PDF is reported without guessing content")


if __name__ == "__main__":
    main()
