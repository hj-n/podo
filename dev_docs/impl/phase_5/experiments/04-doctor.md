# Experiment 04 — Read-only Doctor

## Question

주요 손상과 고아 상태를 사용자 파일 수정 없이 발견할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- `podo doctor --json` reports stable finding codes for unfinished transactions, invalid Context links, original hashes, capture/deferred/receipt lifecycle, product manifest drift, hook configuration and capture health.
- An installed Workspace with a successful local capture reports `healthy`.
- An interrupted transaction reports `PODO_D001_TRANSACTION_INCOMPLETE`, and `podo inbox --json` exposes the transaction through `recovery_required` instead of hiding it among ordinary captures.
- Synthetic lifecycle, missing receipt target and product modification damage are reported as separate findings.
- Whole-Workspace file hashes are identical before and after every doctor run, including damaged and interrupted cases.

## Command

```bash
python3 tests/run_phase5_doctor.py
```

## Limitation

Doctor explains evidence but does not yet produce or apply a recovery plan. That boundary remains intentionally closed until Experiments 05 and 06 pass.
