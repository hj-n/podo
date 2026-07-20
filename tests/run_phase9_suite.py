#!/usr/bin/env python3
"""Run the complete Phase 9 synthetic feature and integration suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    "run_phase9_capture.py",
    "run_phase9_integrity.py",
    "run_phase9_event_storage.py",
    "run_phase9_workspace2_migration.py",
    "run_phase9_people.py",
    "run_phase9_research.py",
    "run_phase9_journey.py",
)


def main() -> None:
    for name in TESTS:
        result = subprocess.run([sys.executable, str(ROOT / "tests" / name)], cwd=ROOT, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
    print(f"PASS Phase 9 synthetic suite ({len(TESTS)} programs)")


if __name__ == "__main__":
    main()
