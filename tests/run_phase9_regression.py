#!/usr/bin/env python3
"""Run Phase 1–8 regression followed by all Phase 9 scenarios."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for name in ("run_phase8_regression.py", "run_phase9_suite.py"):
        result = subprocess.run([sys.executable, str(ROOT / "tests" / name)], cwd=ROOT, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
    print("PASS Phase 1–9 synthetic regression")


if __name__ == "__main__":
    main()
