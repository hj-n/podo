#!/usr/bin/env python3
"""Verify lossless, planned Event storage conversion and failure rollback."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools/build_synthetic_workspace.py"


def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> None:
    result = run([sys.executable, str(BUILD), "--output", str(path)])
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-storage-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        build(workspace)
        podo = workspace / ".podo/bin/podo"
        metadata = next((workspace / "events").glob("*/*/*/metadata.md"))
        original = metadata.parent / "original/conversation.jsonl"
        original_raw = original.read_bytes()
        plan_result = run([str(podo), "event-storage", "plan"], cwd=workspace)
        plan = json.loads(plan_result.stdout)
        if plan["summary"]["event_count"] != 1 or plan["status"] != "planned":
            raise AssertionError(plan_result.stdout)
        applied = run([str(podo), "event-storage", "apply", "--plan", plan["plan_id"]], cwd=workspace)
        if applied.returncode:
            raise AssertionError(applied.stdout + applied.stderr)
        if original.exists() or not (metadata.parent / "original/manifest.json").is_file():
            raise AssertionError("legacy original was not safely switched")
        output = workspace / ".podo-work/materialized.jsonl"
        materialized = run(
            [str(podo), "event-storage", "materialize", "--event", metadata.relative_to(workspace).as_posix(), "--output", output.relative_to(workspace).as_posix()],
            cwd=workspace,
        )
        if materialized.returncode or output.read_bytes() != original_raw:
            raise AssertionError(materialized.stdout + materialized.stderr)
        valid = run([str(podo), "validate", "--mode", "context-present"], cwd=workspace)
        if valid.returncode:
            raise AssertionError(valid.stdout + valid.stderr)
        backup_id = json.loads(applied.stdout)["backup_id"]
        backed_up = workspace / f".podo-backups/{backup_id}/user-data/{original.relative_to(workspace)}"
        if not backed_up.is_file() or sha(backed_up) != hashlib.sha256(original_raw).hexdigest():
            raise AssertionError("exact legacy backup is missing")
        print("PASS planned chunk storage, byte-exact materialization and legacy backup")

        rollback_plan_result = run([str(podo), "event-storage", "rollback-plan", "--backup", backup_id], cwd=workspace)
        rollback_plan = json.loads(rollback_plan_result.stdout)
        rolled_back = run([str(podo), "event-storage", "apply", "--plan", rollback_plan["plan_id"]], cwd=workspace)
        if rolled_back.returncode or original.read_bytes() != original_raw:
            raise AssertionError(rolled_back.stdout + rolled_back.stderr)
        if (metadata.parent / "original/manifest.json").exists():
            raise AssertionError("rollback left the chunk manifest active")
        print("PASS separately planned rollback restores legacy Event")

        failed = root / "failed"
        build(failed)
        failed_podo = failed / ".podo/bin/podo"
        failed_metadata = next((failed / "events").glob("*/*/*/metadata.md"))
        failed_original = failed_metadata.parent / "original/conversation.jsonl"
        before_metadata = failed_metadata.read_bytes()
        before_original = failed_original.read_bytes()
        failed_plan = json.loads(run([str(failed_podo), "event-storage", "plan"], cwd=failed).stdout)
        env = {**os.environ, "PODO_TEST_EVENT_STORAGE_FAIL_AT": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        injected = run([str(failed_podo), "event-storage", "apply", "--plan", failed_plan["plan_id"]], cwd=failed, env=env)
        if injected.returncode == 0 or "E_EVENT_STORAGE_INJECTED" not in injected.stderr:
            raise AssertionError(injected.stdout + injected.stderr)
        if failed_metadata.read_bytes() != before_metadata or failed_original.read_bytes() != before_original:
            raise AssertionError("injected failure did not restore legacy Event")
        print("PASS injected conversion failure restores metadata and original")


if __name__ == "__main__":
    main()
