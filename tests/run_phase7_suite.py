#!/usr/bin/env python3
"""Run the complete disposable Phase 7 migration and rollback suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    "run_phase7_contracts.py",
    "run_phase7_planning.py",
    "run_phase7_migration.py",
    "run_phase7_rollback.py",
    "run_phase7_cli.py",
)


def main() -> None:
    for name in TESTS:
        result = subprocess.run([sys.executable, str(ROOT / "tests" / name)], cwd=ROOT, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
    print(f"PASS Phase 7 synthetic migration suite ({len(TESTS)} programs)")


if __name__ == "__main__":
    main()
