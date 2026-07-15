#!/usr/bin/env python3
"""Validate the Phase 3 transcript adapter and atomic inbox capture."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD = REPO_ROOT / "tools/build_synthetic_workspace.py"
FIXTURE = REPO_ROOT / "tests/fixtures/codex_transcript_0.144.0-alpha.4.jsonl"
SESSION = "synthetic-session-001"
TURN = "synthetic-turn-001"


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def hook_payload(workspace: Path, transcript: Path, **overrides: str) -> dict[str, str]:
    value = {
        "hook_event_name": "Stop",
        "session_id": SESSION,
        "turn_id": TURN,
        "transcript_path": str(transcript),
        "cwd": str(workspace),
        "model": "synthetic-model",
    }
    value.update(overrides)
    return value


def invoke(workspace: Path, payload: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return run(
        [str(workspace / ".podo/scripts/capture_event")],
        input=json.dumps(payload),
        cwd=workspace,
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_failure(workspace: Path, transcript: Path, payload: dict[str, str], code: str) -> None:
    before = list((workspace / ".podo-work/inbox").glob("*")) if (workspace / ".podo-work/inbox").exists() else []
    result = invoke(workspace, payload)
    if result.returncode == 0 or code not in result.stderr:
        raise AssertionError(f"expected {code}\nstdout={result.stdout}\nstderr={result.stderr}")
    after = list((workspace / ".podo-work/inbox").glob("*")) if (workspace / ".podo-work/inbox").exists() else []
    if after != before:
        raise AssertionError(f"failure {code} changed inbox")
    print(f"PASS {code}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase3-capture-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        transcript = root / "session.jsonl"
        shutil.copy2(FIXTURE, transcript)
        payload = hook_payload(workspace, transcript)
        first = invoke(workspace, payload)
        if first.returncode or "captured" not in first.stdout:
            raise AssertionError(first.stdout + first.stderr)
        capture = workspace / f".podo-work/inbox/{SESSION}--{TURN}"
        metadata = json.loads((capture / "capture.json").read_text(encoding="utf-8"))
        original = capture / "original/session.jsonl"
        turn_view = capture / "turn.jsonl"
        if metadata["sha256"] != digest(original) or original.read_bytes() != transcript.read_bytes():
            raise AssertionError("captured original is not byte-for-byte identical")
        if metadata["runtime_version"] != "0.144.0-alpha.4":
            raise AssertionError("runtime was not recorded")
        if metadata["completeness"] != "complete-local-transcript":
            raise AssertionError(f"unexpected completeness: {metadata}")
        if TURN.encode("utf-8") not in turn_view.read_bytes() or SESSION.encode("utf-8") in turn_view.read_bytes():
            raise AssertionError("turn review view did not isolate the current turn span")
        before = (capture / "capture.json").read_bytes(), original.read_bytes()
        second = invoke(workspace, payload)
        after = (capture / "capture.json").read_bytes(), original.read_bytes()
        if second.returncode or "already-captured" not in second.stdout or before != after:
            raise AssertionError("idempotent capture changed immutable bytes")
        print("PASS exact, complete and idempotent inbox capture")

        shutil.rmtree(capture)
        wrong_session = hook_payload(workspace, transcript, session_id="synthetic-session-wrong")
        assert_failure(workspace, transcript, wrong_session, "PODO_CAPTURE_SESSION_MISMATCH")
        missing_turn = hook_payload(workspace, transcript, turn_id="synthetic-turn-missing")
        assert_failure(workspace, transcript, missing_turn, "PODO_CAPTURE_TURN_MISSING")

        unsupported = root / "unsupported.jsonl"
        unsupported.write_text(
            transcript.read_text(encoding="utf-8").replace("0.144.0-alpha.4", "9.9.9"),
            encoding="utf-8",
        )
        assert_failure(
            workspace,
            unsupported,
            hook_payload(workspace, unsupported),
            "PODO_CAPTURE_UNSUPPORTED_RUNTIME",
        )
        malformed = root / "malformed.jsonl"
        malformed.write_text("{not-json}\n", encoding="utf-8")
        assert_failure(
            workspace,
            malformed,
            hook_payload(workspace, malformed),
            "PODO_CAPTURE_INVALID_TRANSCRIPT",
        )

        partial = root / "partial.jsonl"
        lines = [line for line in transcript.read_text(encoding="utf-8").splitlines() if '"role":"assistant"' not in line]
        partial.write_text("\n".join(lines) + "\n", encoding="utf-8")
        partial_result = invoke(workspace, hook_payload(workspace, partial))
        if partial_result.returncode:
            raise AssertionError(partial_result.stdout + partial_result.stderr)
        partial_capture = workspace / f".podo-work/inbox/{SESSION}--{TURN}/capture.json"
        partial_metadata = json.loads(partial_capture.read_text(encoding="utf-8"))
        if partial_metadata["completeness"] != "partial" or "assistant_message" not in partial_metadata["missing_record_families"]:
            raise AssertionError("partial transcript did not declare its missing family")
        print("PASS partial transcript names missing record families")


if __name__ == "__main__":
    main()
