# Experiment 07 — Synthetic Distribution Suite

## Question

두 compatible version과 모든 주요 실패를 disposable Workspace에서 반복할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

`python3 tests/run_phase6_suite.py` runs five disposable programs covering reproducible packaging, standalone fresh install, three-root update/rollback, latest/exact CLI selection, checksum/traversal rejection and shell bootstrap behavior.

Two compatible synthetic versions exercise update and downgrade. Every fresh-install and product-replacement injection boundary preserves or restores the expected product and user-owned sentinels.
