#!/usr/bin/env python3
"""Run the complete synthetic Phase 1 through Phase 8 regression gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = (
    "run_phase1_contracts.py",
    "run_phase2_installation.py",
    "run_phase3_capture.py",
    "run_phase3_context.py",
    "run_phase4_decisions.py",
    "run_phase4_todo.py",
    "run_phase5_suite.py",
    "run_phase6_suite.py",
    "run_phase7_suite.py",
    "run_phase8_suite.py",
)


def main() -> None:
    for name in PROGRAMS:
        print(f"RUN {name}", flush=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "tests" / name)],
            cwd=ROOT,
            check=False,
        )
        if result.returncode:
            raise SystemExit(result.returncode)
    print(f"PASS Phase 1-8 synthetic regression ({len(PROGRAMS)} programs)")


if __name__ == "__main__":
    main()
