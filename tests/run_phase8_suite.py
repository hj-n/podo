#!/usr/bin/env python3
"""Run all Phase 8 synthetic journeys twice and verify cleanup/repeatability."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


from phase8_support import ROOT
from run_phase8_everyday import run_journey as everyday
from run_phase8_product_lifecycle import run_journey as product
from run_phase8_recovery import run_journey as recovery


JOURNEYS = (
    ("everyday", everyday),
    ("recovery", recovery),
    ("product", product),
)
PREFIXES = tuple(f"podo-phase8-{name}-" for name, _ in JOURNEYS)


def temporary_artifacts() -> set[str]:
    root = Path(tempfile.gettempdir())
    return {
        path.name
        for prefix in PREFIXES
        for path in root.glob(prefix + "*")
        if path.exists()
    }


def stable_shape(summary: dict) -> list[tuple[str, str]]:
    if summary.get("schema_version") != 1 or summary.get("phase") != 8:
        raise AssertionError(json.dumps(summary, ensure_ascii=False, indent=2))
    return [(str(step["id"]), str(step["outcome"])) for step in summary["steps"]]


def failure_summary(stdout: str) -> dict:
    summaries = [
        json.loads(line.removeprefix("PHASE8_SUMMARY "))
        for line in stdout.splitlines()
        if line.startswith("PHASE8_SUMMARY ")
    ]
    if len(summaries) != 1:
        raise AssertionError(f"expected one controlled failure summary, found {len(summaries)}")
    return summaries[0]


def main() -> None:
    before = temporary_artifacts()
    results: dict[str, list[dict]] = {name: [] for name, _ in JOURNEYS}
    for repeat in (1, 2):
        for name, function in JOURNEYS:
            summary = function(f"repeat-{repeat}")
            if summary.get("status") != "passed" or summary.get("journey") != name:
                raise AssertionError(json.dumps(summary, ensure_ascii=False, indent=2))
            results[name].append(summary)
    for name, summaries in results.items():
        first = stable_shape(summaries[0])
        second = stable_shape(summaries[1])
        if first != second or not first:
            raise AssertionError(f"{name} evidence shape changed across clean runs: {first} != {second}")
        print(f"PASS {name} stable evidence shape across two clean Workspaces ({len(first)} steps)")
    after_success = temporary_artifacts()
    if after_success != before:
        raise AssertionError(f"successful journeys left temporary artifacts: {after_success - before}")

    env = os.environ.copy()
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PODO_PHASE8_TEST_FAILURES": "1",
            "PODO_PHASE8_TEST_FAIL_AT": "after-personalize",
        }
    )
    controlled = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests/run_phase8_everyday.py"),
            "--run-id",
            "controlled-failure",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if controlled.returncode == 0:
        raise AssertionError("controlled journey failure unexpectedly succeeded")
    failed = failure_summary(controlled.stdout)
    if failed.get("status") != "failed" or stable_shape(failed)[-1] != ("journey-failure", "failed"):
        raise AssertionError(json.dumps(failed, ensure_ascii=False, indent=2))
    after_failure = temporary_artifacts()
    if after_failure != before:
        raise AssertionError(f"failed journey left temporary artifacts: {after_failure - before}")
    print("PASS controlled failure emits a failed summary and removes its temporary Workspace")

    suite = {
        "schema_version": 1,
        "phase": 8,
        "status": "passed",
        "repeats": 2,
        "journeys": {
            name: {
                "runs": 2,
                "steps": [step_id for step_id, _ in stable_shape(summaries[0])],
            }
            for name, summaries in results.items()
        },
        "controlled_failure_cleanup": "passed",
    }
    print("PHASE8_SUITE_SUMMARY " + json.dumps(suite, sort_keys=True))


if __name__ == "__main__":
    main()
