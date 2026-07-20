#!/usr/bin/env python3
"""Verify the dogfooded Codex runtime and task-start capture health surface."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools/build_synthetic_workspace.py"
FIXTURE = ROOT / "tests/fixtures/codex_transcript_0.145.0-alpha.18.jsonl"


def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-capture-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        transcript = root / "session.jsonl"
        shutil.copy2(FIXTURE, transcript)
        before = run([str(workspace / ".podo/bin/podo"), "inbox", "--json"], cwd=workspace)
        before_value = json.loads(before.stdout)
        if before_value["capture_health"]["status"] != "not-diagnosed":
            raise AssertionError(before.stdout)
        payload = {
            "hook_event_name": "Stop",
            "session_id": "synthetic-session-001",
            "turn_id": "synthetic-turn-001",
            "transcript_path": str(transcript),
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
        inbox = run([str(workspace / ".podo/bin/podo"), "inbox", "--json"], cwd=workspace)
        value = json.loads(inbox.stdout)
        if value["capture_health"]["status"] != "ready":
            raise AssertionError(inbox.stdout)
        if value["pending"][0]["runtime_version"] != "0.145.0-alpha.18":
            raise AssertionError(inbox.stdout)
        print("PASS runtime 0.145.0-alpha.18 capture and task-start health")


if __name__ == "__main__":
    main()
