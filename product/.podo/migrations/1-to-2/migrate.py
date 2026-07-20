#!/usr/bin/env python3
"""Create the additive People and Research roots in a staged Workspace."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    if os.environ.get("PODO_MIGRATION_STAGE") != "1":
        raise SystemExit("migration entrypoint only runs in the staged migration engine")
    workspace = args.workspace.resolve()
    for relative in ("people", "research/papers", "research/topics", "research/projects"):
        path = (workspace / relative).resolve()
        path.relative_to(workspace)
        if path.exists() and not path.is_dir():
            raise SystemExit(f"expected directory or missing path: {relative}")
        path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
