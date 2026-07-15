# Experiment 07 — Synthetic Failure Suite

## Question

정상, 중단, 동시성, 진단과 복구 경로를 disposable Workspace에서 반복할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

`python3 tests/run_phase5_suite.py` runs four disposable programs covering:

- normal commit and every injected transaction boundary
- non-overlapping merge and overlapping conflict preservation
- healthy, interrupted and damaged read-only doctor cases
- plan-only behavior, stale pin rejection, idempotent approved apply and the two-receipt resolution boundary

The suite uses only generated synthetic Workspaces and leaves no persistent test Context.
