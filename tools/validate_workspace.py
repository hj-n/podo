#!/usr/bin/env python3
"""Run the validator bundled in the checked-in Podo product."""

from __future__ import annotations

import os
import sys
from pathlib import Path


VALIDATOR = Path(__file__).resolve().parents[1] / "product/.podo/scripts/validate_workspace.py"


def main() -> None:
    os.execv(sys.executable, [sys.executable, str(VALIDATOR), *sys.argv[1:]])


if __name__ == "__main__":
    main()
