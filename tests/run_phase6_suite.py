#!/usr/bin/env python3
"""Run the complete disposable Phase 6 distribution suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    "run_phase6_release_builder.py",
    "run_phase6_package_install.py",
    "run_phase6_product_update.py",
    "run_phase6_update_cli.py",
    "run_phase6_bootstrap.py",
)


def main() -> None:
    for name in TESTS:
        result = subprocess.run([sys.executable, str(ROOT / "tests" / name)], cwd=ROOT, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
    print(f"PASS Phase 6 synthetic distribution suite ({len(TESTS)} programs)")


if __name__ == "__main__":
    main()
