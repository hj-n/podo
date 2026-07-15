#!/usr/bin/env python3
"""Run the complete disposable Phase 5 transaction and recovery suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    "run_phase5_transactions.py",
    "run_phase5_concurrency.py",
    "run_phase5_doctor.py",
    "run_phase5_recovery.py",
)


def main() -> None:
    for name in TESTS:
        result = subprocess.run([sys.executable, str(ROOT / "tests" / name)], cwd=ROOT, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
    print(f"PASS Phase 5 synthetic suite ({len(TESTS)} programs)")


if __name__ == "__main__":
    main()
