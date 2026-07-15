#!/usr/bin/env python3
"""Exercise deterministic Phase 1 assembly and validator failure cases."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD = REPO_ROOT / "tools/build_synthetic_workspace.py"
VALIDATE = REPO_ROOT / "tools/validate_workspace.py"
CASES = REPO_ROOT / "tests/fixtures/phase1_cases.json"

EVENT_DIR = "events/2026/07/2026-07-15_090000-synthetic-planning"
DELTA = "deltas/2026/07/2026-07-15_091500-synthetic-planning.md"
STATE = "state/synthetic-planning.md"


def run(command: list[str], expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True)
    if expect_success and result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(command)}\n{result.stdout}{result.stderr}")
    return result


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def replace(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if old not in content:
        raise AssertionError(f"fixture mutation source not found in {path}: {old}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def mutate(root: Path, name: str) -> None:
    metadata = root / EVENT_DIR / "metadata.md"
    original = root / EVENT_DIR / "original/conversation.jsonl"
    delta = root / DELTA
    state = root / STATE
    if name == "missing-original":
        original.unlink()
    elif name == "event-hash-mismatch":
        original.write_text(original.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    elif name == "unknown-completeness":
        replace(metadata, "Completeness: complete-local-transcript", "Completeness: unknown")
    elif name == "broken-delta-link":
        replace(delta, "../../../state/synthetic-planning.md", "../../../state/missing.md")
    elif name == "todo-missing-created":
        lines = [line for line in state.read_text(encoding="utf-8").splitlines() if "  - Created:" not in line]
        state.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif name == "checked-todo-missing-completed":
        replace(state, "- [ ] 초록색 합성 문서를 준비한다.", "- [x] 초록색 합성 문서를 준비한다.")
    elif name == "unresolved-template-token":
        replace(state, "Phase 1 데이터 계약", "{{UNRESOLVED_TOKEN}} 데이터 계약")
    elif name == "incompatible-workspace-version":
        (root / "WORKSPACE_VERSION").write_text("2\n", encoding="utf-8")
    else:
        raise AssertionError(f"unknown fixture mutation: {name}")


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="podo-phase1-") as temporary:
        base = Path(temporary)
        first = base / "first"
        second = base / "second"
        run([sys.executable, str(BUILD), "--output", str(first)])
        run([sys.executable, str(BUILD), "--output", str(second)])
        run([sys.executable, str(VALIDATE), str(first)])
        run([sys.executable, str(VALIDATE), str(second)])
        if digest_tree(first) != digest_tree(second):
            raise AssertionError("two synthetic Workspace builds are not deterministic")

        for case in cases:
            damaged = base / case["name"]
            shutil.copytree(first, damaged)
            mutate(damaged, case["name"])
            result = run([sys.executable, str(VALIDATE), str(damaged)], expect_success=False)
            if result.returncode == 0:
                raise AssertionError(f"damaged fixture passed: {case['name']}")
            if case["expected_code"] not in result.stdout:
                raise AssertionError(
                    f"{case['name']} did not report {case['expected_code']}\n{result.stdout}{result.stderr}"
                )
            print(f"PASS {case['name']} -> {case['expected_code']}")

        print(f"PASS deterministic-build {digest_tree(first)}")
        print(f"PASS valid-workspace {len(cases)} failure cases")


if __name__ == "__main__":
    main()
