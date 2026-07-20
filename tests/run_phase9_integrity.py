#!/usr/bin/env python3
"""Verify Phase 9 read-only views and reference diagnostics."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools/build_synthetic_workspace.py"


def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase9-integrity-") as temporary:
        workspace = Path(temporary) / "workspace"
        built = run([sys.executable, str(BUILD), "--output", str(workspace)])
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        podo = workspace / ".podo/bin/podo"
        todos = run([str(podo), "todos", "--due-before", "2026-07-17", "--json"], cwd=workspace)
        value = json.loads(todos.stdout)
        if value["count"] != 1 or value["todos"][0]["state"] != "synthetic-planning":
            raise AssertionError(todos.stdout)
        before = (workspace / "state/synthetic-planning.md").read_bytes()
        none = run([str(podo), "todos", "--due-before", "2026-07-16", "--json"], cwd=workspace)
        if json.loads(none.stdout)["count"] != 0 or before != (workspace / "state/synthetic-planning.md").read_bytes():
            raise AssertionError("TODO view was not a read-only filter")
        print("PASS read-only TODO aggregate and due filter")

        second = workspace / "state/second-context.md"
        second.write_text(
            "# Second\n\nUpdated: 2026-07-20\n\n## Current\n\n합성 프로젝트 회의는 금요일 오전 9시에 한다.\n",
            encoding="utf-8",
        )
        first = workspace / "state/synthetic-planning.md"
        first.write_text(first.read_text(encoding="utf-8") + "\n합성 프로젝트 회의는 금요일 오전 9시에 한다.\n", encoding="utf-8")
        duplicates = run([str(podo), "duplicates", "--json"], cwd=workspace)
        duplicate_value = json.loads(duplicates.stdout)
        if duplicate_value["count"] != 1:
            raise AssertionError(duplicates.stdout)
        if before == first.read_bytes():
            pass
        print("PASS exact cross-document duplicate report")

        first.write_text(first.read_text(encoding="utf-8") + "\n근거: ../deltas/2026/07/2026-07-15_091500-synthetic-planning.md\n", encoding="utf-8")
        valid = run([str(podo), "validate", "--mode", "context-present"], cwd=workspace)
        if valid.returncode:
            raise AssertionError(valid.stdout + valid.stderr)
        doctor = run([str(podo), "doctor", "--json"], cwd=workspace)
        value = json.loads(doctor.stdout)
        plain = [finding for finding in value["findings"] if finding["code"] == "PODO_D121_PLAIN_REFERENCE"]
        if len(plain) != 1 or plain[0]["severity"] != "warning":
            raise AssertionError(doctor.stdout)
        print("PASS legacy plain tracking reference is a read-only doctor warning")


if __name__ == "__main__":
    main()
