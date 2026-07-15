#!/usr/bin/env python3
"""Shared disposable-fixture and evidence helpers for Phase 8 journeys."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/codex_transcript_0.144.0-alpha.4.jsonl"


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **kwargs,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_snapshot(workspace: Path, roots: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for root_name in roots:
        root = workspace / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                values[path.relative_to(workspace).as_posix()] = sha256(path)
    return values


def context_snapshot(workspace: Path) -> dict[str, str]:
    return file_snapshot(workspace, ("events", "deltas", "state"))


def transcript(root: Path, name: str) -> tuple[Path, str, str]:
    session = f"phase8-{name}-session"
    turn = f"phase8-{name}-turn"
    text = (
        FIXTURE.read_text(encoding="utf-8")
        .replace("synthetic-session-001", session)
        .replace("synthetic-turn-001", turn)
    )
    path = root / f"{session}--{turn}.jsonl"
    path.write_text(text, encoding="utf-8")
    return path, session, turn


def capture(workspace: Path, root: Path, name: str) -> tuple[str, Path]:
    source, session, turn = transcript(root, name)
    payload = {
        "hook_event_name": "Stop",
        "session_id": session,
        "turn_id": turn,
        "transcript_path": str(source),
        "cwd": str(workspace),
        "model": "synthetic-phase8-model",
    }
    result = run(
        [str(workspace / ".podo/scripts/capture_event")],
        input=json.dumps(payload),
        cwd=workspace,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return f"{session}--{turn}", source


def request_file(workspace: Path, name: str, value: dict) -> Path:
    path = workspace / f".podo-work/requests/phase8-{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def cli(
    workspace: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return run([str(workspace / ".podo/bin/podo"), *args], cwd=workspace, env=env)


class EvidenceLedger:
    def __init__(self, journey: str, run_id: str):
        self.journey = journey
        self.run_id = run_id
        self.steps: list[dict] = []

    def passed(self, step_id: str, architecture: tuple[str, ...], *evidence: str) -> None:
        self.steps.append(
            {
                "id": step_id,
                "architecture": list(architecture),
                "outcome": "passed",
                "evidence": list(evidence),
            }
        )
        print(f"PASS {step_id}: {'; '.join(evidence)}")

    def value(self) -> dict:
        return {
            "schema_version": 1,
            "phase": 8,
            "journey": self.journey,
            "run_id": self.run_id,
            "status": "passed",
            "steps": self.steps,
        }

    def emit(self) -> None:
        print("PHASE8_SUMMARY " + json.dumps(self.value(), ensure_ascii=False, sort_keys=True))
